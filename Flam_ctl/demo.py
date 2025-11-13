"""
Demo script for QueueCTL - shows all features in action
"""
import sys
import time
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from queuectl.models import JobState
from queuectl.queue import get_queue_manager
from queuectl.config import get_config
from queuectl.database import get_db


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.RESET}\n")


def print_info(msg):
    print(f"{Colors.YELLOW}▶ {msg}{Colors.RESET}")


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_command(cmd):
    print(f"{Colors.CYAN}$ {cmd}{Colors.RESET}")


def run_demo():
    print_section("QueueCTL - Interactive Demo")
    
    qm = get_queue_manager()
    cfg = get_config()
    
    # Demo 1: Configuration
    print_section("Demo 1: Configuration Management")
    print_info("Current configuration:")
    all_config = cfg.get_all()
    for key, value in sorted(all_config.items()):
        print(f"  {key}: {value}")
    
    print_info("Setting custom configuration...")
    cfg.set("max_retries", 2)
    cfg.set("backoff_base", 2)
    print_success("Configuration updated!")
    
    # Demo 2: Enqueue Jobs
    print_section("Demo 2: Enqueueing Jobs")
    jobs = []
    
    print_info("Enqueueing successful job...")
    job1 = qm.enqueue("echo 'Success: Job completed!'", job_id="demo-success-1")
    jobs.append(job1)
    print_success(f"Enqueued: {job1.id}")
    
    print_info("Enqueueing failing job (will retry and go to DLQ)...")
    job2 = qm.enqueue("false", job_id="demo-fail-1", max_retries=2)
    jobs.append(job2)
    print_success(f"Enqueued: {job2.id}")
    
    print_info("Enqueueing multi-command job...")
    job3 = qm.enqueue("echo 'Starting...' && sleep 1 && echo 'Done!'", job_id="demo-complex-1")
    jobs.append(job3)
    print_success(f"Enqueued: {job3.id}")
    
    # Demo 3: Queue Status
    print_section("Demo 3: Queue Status Before Processing")
    stats = qm.get_stats()
    print_info("Job Statistics:")
    for state, count in stats.items():
        print(f"  {state}: {count}")
    
    # Demo 4: List Jobs
    print_section("Demo 4: List Jobs by State")
    all_jobs = qm.list_jobs(state="pending")
    print_info(f"Found {len(all_jobs)} pending job(s):")
    for job in all_jobs[:5]:
        print(f"  - {job.id}: {job.command[:40]}...")
    
    # Demo 5: Job Details
    print_section("Demo 5: Job Details")
    job_info = qm.get_job(job1.id)
    print_info(f"Job ID: {job_info.id}")
    print_info(f"Command: {job_info.command}")
    print_info(f"State: {job_info.state.value}")
    print_info(f"Attempts: {job_info.attempts}/{job_info.max_retries}")
    print_info(f"Created: {job_info.created_at.isoformat()}")
    
    # Demo 6: Simulate Job Processing
    print_section("Demo 6: Simulating Job Processing")
    
    print_info("Processing successful job...")
    db = get_db()
    
    if db.lock_job(job1.id, "demo-worker-1"):
        print_success("Job locked for processing")
        # Simulate execution
        job1.state = JobState.COMPLETED
        job1.updated_at = __import__('datetime').datetime.utcnow()
        db.update_job(job1)
        print_success(f"Job {job1.id} completed!")
    
    # Simulate failure
    print_info("Simulating job failure and retry...")
    if db.lock_job(job2.id, "demo-worker-1"):
        job2.state = JobState.FAILED
        job2.attempts += 1
        job2.updated_at = __import__('datetime').datetime.utcnow()
        db.update_job(job2)
        print_info(f"Job {job2.id} failed (attempt {job2.attempts}/{job2.max_retries})")
        
        # Retry
        if job2.attempts < job2.max_retries:
            job2.state = JobState.PENDING
            db.update_job(job2)
            print_info("Job queued for retry")
    
    # Demo 7: Updated Queue Status
    print_section("Demo 7: Queue Status After Processing")
    stats = qm.get_stats()
    print_info("Updated Job Statistics:")
    for state, count in stats.items():
        print(f"  {state}: {count}")
    
    # Demo 8: DLQ Operations
    print_section("Demo 8: Dead Letter Queue Operations")
    
    # Simulate moving job to DLQ
    job2.state = JobState.DEAD
    db.update_job(job2)
    print_info(f"Job {job2.id} moved to DLQ after max retries exceeded")
    
    dlq_jobs = qm.get_dlq_jobs()
    print_success(f"DLQ contains {len(dlq_jobs)} job(s):")
    for job in dlq_jobs:
        print(f"  - {job.id}: {job.command}")
    
    # Demo 9: DLQ Retry
    print_section("Demo 9: Retrying DLQ Job")
    print_info(f"Retrying job {job2.id} from DLQ...")
    retried = qm.retry_dlq_job(job2.id)
    print_success(f"Job {retried.id} moved back to PENDING state")
    print_info(f"Attempts reset: {retried.attempts}")
    
    # Demo 10: Final Stats
    print_section("Demo 10: Final Queue Status")
    stats = qm.get_stats()
    print_info("Final Job Statistics:")
    for state, count in stats.items():
        color = Colors.GREEN if count > 0 else Colors.RESET
        print(f"  {state}: {color}{count}{Colors.RESET}")
    
    # Summary
    print_section("Demo Summary")
    print_success("✓ Configuration management")
    print_success("✓ Job enqueueing")
    print_success("✓ Queue status monitoring")
    print_success("✓ Job listing and filtering")
    print_success("✓ Job details")
    print_success("✓ Job processing simulation")
    print_success("✓ Dead Letter Queue")
    print_success("✓ DLQ job retry")
    
    print_info("\nTo run actual workers with real job execution, use:")
    print_command("queuectl worker start --count 2")
    
    print_info("\nTo view commands, use:")
    print_command("queuectl --help")
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}Demo completed successfully!{Colors.RESET}\n")


if __name__ == '__main__':
    try:
        run_demo()
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}\n")
        sys.exit(1)
