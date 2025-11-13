"""
Job queue management
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional
from .models import Job, JobState
from .database import get_db
from .config import get_config


class QueueManager:
    """Manages job queue operations"""
    
    def __init__(self):
        """Initialize queue manager"""
        self.db = get_db()
        self.config = get_config()
    
    def enqueue(self, command: str, job_id: Optional[str] = None, max_retries: Optional[int] = None) -> Job:
        """
        Enqueue a new job
        
        Args:
            command: Command to execute
            job_id: Optional custom job ID (auto-generated if not provided)
            max_retries: Max retries (uses config default if not provided)
        
        Returns:
            Created job
        """
        job_id = job_id or str(uuid.uuid4())[:12]
        max_retries = max_retries or self.config.get("max_retries", 3)
        
        job = Job(
            id=job_id,
            command=command,
            state=JobState.PENDING,
            attempts=0,
            max_retries=max_retries,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add_job(job)
        return job
    
    def get_job(self, job_id: str) -> Job:
        """Get job by ID"""
        return self.db.get_job(job_id)
    
    def list_jobs(self, state: str = None) -> List[Job]:
        """
        List jobs by state
        
        Args:
            state: Filter by state (pending, processing, completed, failed, dead)
        
        Returns:
            List of jobs
        """
        if state:
            return self.db.get_jobs_by_state(JobState(state))
        return self.db.get_all_jobs()
    
    def get_dlq_jobs(self) -> List[Job]:
        """Get all jobs in Dead Letter Queue"""
        return self.db.get_jobs_by_state(JobState.DEAD)
    
    def retry_dlq_job(self, job_id: str) -> Job:
        """Retry a job from DLQ"""
        job = self.db.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.state != JobState.DEAD:
            raise ValueError(f"Job {job_id} is not in DLQ")
        
        # Reset job for retry
        job.state = JobState.PENDING
        job.attempts = 0
        job.updated_at = datetime.utcnow()
        self.db.update_job(job)
        
        return job
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        stats = self.db.get_stats()
        return {
            "total": sum(stats.values()),
            "pending": stats.get(JobState.PENDING.value, 0),
            "processing": stats.get(JobState.PROCESSING.value, 0),
            "completed": stats.get(JobState.COMPLETED.value, 0),
            "failed": stats.get(JobState.FAILED.value, 0),
            "dead": stats.get(JobState.DEAD.value, 0),
        }
    
    def clean_old_jobs(self, days: int = 7) -> int:
        """Clean up old completed/failed jobs"""
        # This can be implemented for cleanup purposes
        pass


# Global queue manager instance
_queue_manager_instance = None


def get_queue_manager() -> QueueManager:
    """Get or create global queue manager instance"""
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = QueueManager()
    return _queue_manager_instance
