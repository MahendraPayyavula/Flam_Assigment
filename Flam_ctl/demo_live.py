"""
Live demo script showing queuectl in action
Demonstrates: enqueue, worker processing, retries, DLQ
"""
import sys
import time
import subprocess
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from queuectl.models import JobState
from queuectl.queue import get_queue_manager
from queuectl.config import get_config
from queuectl.database import get_db
from queuectl.worker import Worker


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{Colors.RESET}\n")


def print_info(msg):
    print(f"{Colors.YELLOW}▶ {msg}{Colors.RESET}")


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def run_live_demo():
    print_section("QueueCTL - Live Processing Demo")
    
    qm = get_queue_manager()
    cfg = get_config()
    db = get_db()
    
    # Configure for demo
    print_info("Configuring for demo...")
    cfg.set("max_retries", 2)
    cfg.set("backoff_base", 2)
    cfg.set("worker_timeout", 10)
    print_success("Configuration set: max_retries=2, backoff_base=2")
    
    # Demo 1: Create test jobs
    print_section("Step 1: Creating Test Jobs")
    
    import uuid
    demo_id = str(uuid.uuid4())[:8]
    
    jobs = []
    
    # Successful job
    print_info("Creating successful job...")
    job1 = qm.enqueue("echo 'Job 1: Success!'", job_id=f"demo-success-{demo_id}")
    jobs.append(job1)
    print_success(f"Job {job1.id} enqueued")
    
    # Job that will fail
    print_info("Creating failing job...")
    job2 = qm.enqueue("false", job_id=f"demo-fail-{demo_id}", max_retries=1)
    jobs.append(job2)
    print_success(f"Job {job2.id} enqueued (will fail)")
    
    # Job with delay
    print_info("Creating job with delay...")
    job3 = qm.enqueue("echo 'Starting...' && timeout /t 1 /nobreak 2>nul || sleep 1; echo 'Done!'", job_id=f"demo-delay-{demo_id}")
    jobs.append(job3)
    print_success(f"Job {job3.id} enqueued")
    
    # Demo 2: Show status before processing
    print_section("Step 2: Queue Status Before Processing")
    stats = qm.get_stats()
    print_info("Job Statistics:")
    print(f"  {Colors.CYAN}Total: {stats['total']}{Colors.RESET}")
    print(f"  {Colors.YELLOW}Pending: {stats['pending']}{Colors.RESET}")
    print(f"  {Colors.GREEN}Completed: {stats['completed']}{Colors.RESET}")
    
    # Demo 3: Run worker in background
    print_section("Step 3: Starting Worker Process")
    print_info("Starting 1 worker to process jobs...")
    
    worker = Worker(worker_id="demo-worker-1", poll_interval=1)
    worker_thread = threading.Thread(target=worker.start, daemon=True)
    worker_thread.start()
    print_success("Worker started in background")
    
    # Demo 4: Monitor processing
    print_section("Step 4: Monitoring Job Processing")
    print_info("Processing jobs for 10 seconds...")
    
    for i in range(10):
        time.sleep(1)
        stats = qm.get_stats()
        completed = stats['completed']
        dead = stats['dead']
        pending = stats['pending']
        processing = stats['processing']
        
        status_line = f"  [{completed} completed] [{dead} dead] [{pending} pending] [{processing} processing]"
        print(f"  {Colors.CYAN}[{i+1}s]{Colors.RESET}{status_line}")
        
        if completed >= 2 and dead >= 1:
            print_success("All jobs processed!")
            break
    
    # Stop worker
    worker.running = False
    time.sleep(1)
    
    # Demo 5: Final results
    print_section("Step 5: Final Results")
    
    for job in jobs:
        job_updated = qm.get_job(job.id)
        if job_updated:
            state_color = Colors.GREEN if job_updated.state == JobState.COMPLETED else Colors.RED if job_updated.state == JobState.DEAD else Colors.YELLOW
            print_info(f"Job {job_updated.id}:")
            print(f"    State: {state_color}{job_updated.state.value}{Colors.RESET}")
            print(f"    Attempts: {job_updated.attempts}/{job_updated.max_retries}")
            print(f"    Command: {job_updated.command[:50]}...")
    
    # Demo 6: DLQ check
    print_section("Step 6: Dead Letter Queue")
    dlq_jobs = qm.get_dlq_jobs()
    if dlq_jobs:
        print_info(f"Found {len(dlq_jobs)} job(s) in DLQ:")
        for job in dlq_jobs:
            print(f"  - {job.id}: {job.command} (attempts: {job.attempts})")
        
        print_info("Retrying DLQ job...")
        retried = qm.retry_dlq_job(dlq_jobs[0].id)
        print_success(f"Job {retried.id} moved back to queue (state: {retried.state.value})")
    else:
        print_info("No jobs in DLQ")
    
    # Final summary
    print_section("Demo Summary")
    final_stats = qm.get_stats()
    print_success(f"Total jobs processed: {final_stats['total']}")
    print_success(f"Completed: {final_stats['completed']}")
    print_success(f"Failed/DLQ: {final_stats['dead']}")
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}Live demo completed successfully!{Colors.RESET}\n")
    
    print_info("Next steps:")
    print(f"  - View all commands: queuectl --help")
    print(f"  - Start multi-worker processing: queuectl worker start --count 3")
    print(f"  - Monitor queue: watch -n 1 'queuectl status'  (Unix/Linux)")
    print(f"  - Check completed jobs: queuectl list --state completed")
    print()


if __name__ == '__main__':
    try:
        run_live_demo()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user{Colors.RESET}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
