"""
Integration test and validation script for queuectl
"""
import sys
import time
import json
import subprocess
import tempfile
import shutil
import gc
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from queuectl.models import Job, JobState
from queuectl.database import Database
from queuectl.queue import QueueManager
from queuectl.config import Config
from queuectl.worker import Worker


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name):
    print(f"\n{Colors.CYAN}{Colors.BOLD}Testing: {name}{Colors.RESET}")


def print_pass(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_fail(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg):
    print(f"{Colors.YELLOW}ℹ {msg}{Colors.RESET}")


def cleanup_temp_dir(temp_dir):
    """Cleanup temporary directory (handles Windows file locking)"""
    import time
    gc.collect()
    time.sleep(0.1)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            shutil.rmtree(temp_dir)
            return
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(0.1)
            else:
                pass  # Ignore cleanup errors on Windows


def test_basic_job_enqueue():
    """Test 1: Basic job enqueue"""
    print_test("Basic Job Enqueue")
    
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path=db_path)
        
        job = Job(id="job1", command="echo 'Hello World'")
        db.add_job(job)
        
        retrieved = db.get_job("job1")
        assert retrieved is not None, "Job not found"
        assert retrieved.command == "echo 'Hello World'", "Command mismatch"
        assert retrieved.state == JobState.PENDING, "State should be pending"
        
        print_pass("Job enqueued and retrieved successfully")
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False
    finally:
        cleanup_temp_dir(temp_dir)


def test_job_retry_and_dlq():
    """Test 2: Job retry and DLQ movement"""
    print_test("Job Retry and DLQ Movement")
    
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path=db_path)
        qm = QueueManager()
        qm.db = db
        
        job = qm.enqueue("false", max_retries=2)
        print_info(f"Created job {job.id} with max_retries=2")
        
        # Simulate retry
        for attempt in range(1, 3):
            job.attempts = attempt
            job.state = JobState.FAILED
            db.update_job(job)
            print_info(f"Job failed, attempt {attempt}/2")
            
            if attempt >= job.max_retries:
                job.state = JobState.DEAD
                db.update_job(job)
                print_info("Job moved to DLQ")
        
        dlq_jobs = qm.get_dlq_jobs()
        assert len(dlq_jobs) == 1, "Job should be in DLQ"
        assert dlq_jobs[0].id == job.id, "Wrong job in DLQ"
        
        print_pass("Job retried and moved to DLQ correctly")
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False
    finally:
        cleanup_temp_dir(temp_dir)


def test_multiple_workers():
    """Test 3: Multiple workers processing jobs"""
    print_test("Multiple Workers Processing Jobs")
    
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path=db_path)
        qm = QueueManager()
        qm.db = db
        
        # Create jobs
        jobs = []
        for i in range(3):
            job = qm.enqueue(f"echo 'Job {i}'", job_id=f"job{i}")
            jobs.append(job)
        
        print_info(f"Created {len(jobs)} jobs")
        
        # Simulate worker processing
        worker1 = Worker(worker_id="worker1")
        worker2 = Worker(worker_id="worker2")
        
        # Process jobs
        for i, job_ref in enumerate(jobs):
            if i % 2 == 0:
                locked = db.lock_job(jobs[i].id, "worker1")
            else:
                locked = db.lock_job(jobs[i].id, "worker2")
            
            assert locked, f"Failed to lock job {jobs[i].id}"
        
        # Verify all jobs are processing
        processing = db.get_jobs_by_state(JobState.PROCESSING)
        assert len(processing) == 3, f"Should have 3 processing jobs, got {len(processing)}"
        
        print_pass(f"All {len(jobs)} jobs locked without conflicts")
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False
    finally:
        cleanup_temp_dir(temp_dir)


def test_job_persistence():
    """Test 4: Job data survives restart"""
    print_test("Job Data Persistence Across Restart")
    
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        
        # First instance - create jobs
        db1 = Database(db_path=db_path)
        job = Job(id="persistent1", command="echo test")
        db1.add_job(job)
        print_info("Created job in first instance")
        
        # Simulate restart - create new instance
        db2 = Database(db_path=db_path)
        retrieved = db2.get_job("persistent1")
        
        assert retrieved is not None, "Job not found after restart"
        assert retrieved.command == "echo test", "Job data corrupted"
        
        print_pass("Job data persisted across restart")
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False
    finally:
        cleanup_temp_dir(temp_dir)


def test_command_execution():
    """Test 5: Command execution success/failure"""
    print_test("Command Execution Success/Failure")
    
    try:
        worker = Worker()
        
        # Test successful command
        job_success = Job(id="success", command="echo 'Success'")
        result = worker._execute_job(job_success)
        assert result == True, "Should succeed"
        print_pass("Successful command executed correctly")
        
        # Test failing command
        job_fail = Job(id="fail", command="false")
        result = worker._execute_job(job_fail)
        assert result == False, "Should fail"
        print_pass("Failing command handled correctly")
        
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False


def test_configuration_management():
    """Test 6: Configuration management"""
    print_test("Configuration Management")
    
    temp_dir = tempfile.mkdtemp()
    try:
        config_file = Path(temp_dir) / "config.json"
        config = Config()
        config.CONFIG_FILE = config_file
        
        # Test set/get
        config.set("custom_key", 42)
        value = config.get("custom_key")
        assert value == 42, f"Expected 42, got {value}"
        print_pass("Config set/get works")
        
        # Test get default
        default = config.get("max_retries")
        assert default == 3, f"Expected default 3, got {default}"
        print_pass("Config defaults work")
        
        # Test reset
        config.reset()
        assert config.get("max_retries") == 3, "Reset failed"
        print_pass("Config reset works")
        
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False
    finally:
        cleanup_temp_dir(temp_dir)


def test_dlq_retry():
    """Test 7: DLQ job retry"""
    print_test("DLQ Job Retry")
    
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path=db_path)
        qm = QueueManager()
        qm.db = db
        
        # Create and move to DLQ
        job = qm.enqueue("failing_command", max_retries=1)
        job.state = JobState.DEAD
        job.attempts = 1
        db.update_job(job)
        
        print_info(f"Job {job.id} moved to DLQ")
        
        # Retry from DLQ
        retried = qm.retry_dlq_job(job.id)
        assert retried.state == JobState.PENDING, "Job should be pending"
        assert retried.attempts == 0, "Attempts should be reset"
        
        print_pass("DLQ job retried successfully")
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False
    finally:
        cleanup_temp_dir(temp_dir)


def test_queue_statistics():
    """Test 8: Queue statistics"""
    print_test("Queue Statistics")
    
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path=db_path)
        qm = QueueManager()
        qm.db = db
        
        # Create jobs with different states
        jobs = []
        for i in range(2):
            job = qm.enqueue(f"job{i}")
            jobs.append(job)
        
        job = qm.enqueue("completed_job")
        job.state = JobState.COMPLETED
        db.update_job(job)
        
        job = qm.enqueue("dead_job")
        job.state = JobState.DEAD
        db.update_job(job)
        
        stats = qm.get_stats()
        assert stats['total'] == 4, f"Expected 4 total, got {stats['total']}"
        assert stats['pending'] == 2, f"Expected 2 pending, got {stats['pending']}"
        assert stats['completed'] == 1, f"Expected 1 completed, got {stats['completed']}"
        assert stats['dead'] == 1, f"Expected 1 dead, got {stats['dead']}"
        
        print_pass(f"Statistics correct: {stats}")
        return True
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return False
    finally:
        cleanup_temp_dir(temp_dir)


def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== QueueCTL Integration Test Suite ==={Colors.RESET}\n")
    
    tests = [
        test_basic_job_enqueue,
        test_job_retry_and_dlq,
        test_multiple_workers,
        test_job_persistence,
        test_command_execution,
        test_configuration_management,
        test_dlq_retry,
        test_queue_statistics,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print_fail(f"Test crashed: {e}")
            results.append(False)
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== Test Summary ==={Colors.RESET}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {Colors.GREEN}{passed}/{total}{Colors.RESET}")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}Some tests failed!{Colors.RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
