"""
Worker engine for executing jobs
"""
import subprocess
import signal
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import sys
import uuid

from .models import Job, JobState
from .database import get_db
from .config import get_config


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Worker:
    """Background job worker process"""
    
    def __init__(self, worker_id: Optional[str] = None, poll_interval: int = 1):
        """
        Initialize worker
        
        Args:
            worker_id: Unique worker identifier (auto-generated if not provided)
            poll_interval: Seconds to wait between job polls
        """
        self.worker_id = worker_id or str(uuid.uuid4())[:8]
        self.poll_interval = poll_interval
        self.running = False
        self.db = get_db()
        self.config = get_config()
    
    def start(self) -> None:
        """Start the worker loop"""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")
        
        # Handle shutdown signals (only works in main thread)
        try:
            def signal_handler(signum, frame):
                logger.info(f"Worker {self.worker_id} received shutdown signal")
                self.running = False
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except (ValueError, RuntimeError):
            # Signals can't be registered in non-main thread
            logger.debug("Signals not available (likely running in non-main thread)")
        
        try:
            while self.running:
                self._process_next_job()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} interrupted")
        finally:
            logger.info(f"Worker {self.worker_id} stopped")
    
    def _process_next_job(self) -> None:
        """Process the next available job"""
        # Get pending job
        pending_jobs = self.db.get_pending_jobs()
        if not pending_jobs:
            return
        
        job = pending_jobs[0]
        
        # Try to lock the job
        if not self.db.lock_job(job.id, self.worker_id):
            logger.debug(f"Job {job.id} is locked by another worker")
            return
        
        logger.info(f"Processing job {job.id}: {job.command}")
        
        try:
            # Execute the job
            success = self._execute_job(job)
            
            if success:
                job.state = JobState.COMPLETED
                logger.info(f"Job {job.id} completed successfully")
            else:
                job.attempts += 1
                
                if job.attempts >= job.max_retries:
                    job.state = JobState.DEAD
                    logger.warning(f"Job {job.id} moved to DLQ (max retries exceeded)")
                else:
                    job.state = JobState.PENDING
                    logger.warning(f"Job {job.id} failed, will retry (attempt {job.attempts}/{job.max_retries})")
            
            job.updated_at = datetime.utcnow()
            self.db.update_job(job)
        
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}")
            job.state = JobState.FAILED
            job.updated_at = datetime.utcnow()
            self.db.update_job(job)
            self.db.unlock_job(job.id)
    
    def _execute_job(self, job: Job) -> bool:
        """
        Execute a job command
        
        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = self.config.get("worker_timeout", 300)
            
            # Execute the command
            if sys.platform == "win32":
                # Windows: use shell=True for proper command parsing
                result = subprocess.run(
                    job.command,
                    shell=True,
                    capture_output=True,
                    timeout=timeout,
                    text=True
                )
            else:
                # Unix-like: use shell=True for consistency
                result = subprocess.run(
                    job.command,
                    shell=True,
                    capture_output=True,
                    timeout=timeout,
                    text=True
                )
            
            # Log output
            if result.stdout:
                logger.debug(f"Job {job.id} stdout: {result.stdout[:200]}")
            if result.stderr:
                logger.debug(f"Job {job.id} stderr: {result.stderr[:200]}")
            
            # Success if exit code is 0
            return result.returncode == 0
        
        except subprocess.TimeoutExpired:
            logger.error(f"Job {job.id} timed out after {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Job {job.id} execution error: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the worker gracefully"""
        self.running = False


class WorkerManager:
    """Manages multiple worker processes"""
    
    def __init__(self):
        """Initialize worker manager"""
        self.workers = []
    
    def start_workers(self, count: int = 1) -> None:
        """Start multiple worker processes"""
        logger.info(f"Starting {count} worker(s)")
        
        for i in range(count):
            worker = Worker()
            self.workers.append(worker)
            worker.start()
    
    def stop_workers(self) -> None:
        """Stop all workers"""
        for worker in self.workers:
            worker.stop()
        self.workers.clear()
    
    def get_active_workers(self) -> int:
        """Get number of active workers"""
        return len([w for w in self.workers if w.running])
