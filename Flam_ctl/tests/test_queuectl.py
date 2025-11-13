"""
Test suite for queuectl
"""
import unittest
import tempfile
import shutil
import time
import json
from pathlib import Path
from datetime import datetime

from queuectl.models import Job, JobState
from queuectl.database import Database
from queuectl.queue import QueueManager
from queuectl.config import Config
from queuectl.worker import Worker


class TestJobModel(unittest.TestCase):
    """Test Job model"""
    
    def test_job_creation(self):
        """Test creating a job"""
        job = Job(id="test1", command="echo hello")
        self.assertEqual(job.id, "test1")
        self.assertEqual(job.command, "echo hello")
        self.assertEqual(job.state, JobState.PENDING)
        self.assertEqual(job.attempts, 0)
        self.assertEqual(job.max_retries, 3)
    
    def test_job_to_dict(self):
        """Test converting job to dict"""
        job = Job(id="test1", command="echo hello")
        job_dict = job.to_dict()
        self.assertEqual(job_dict["id"], "test1")
        self.assertEqual(job_dict["command"], "echo hello")
        self.assertEqual(job_dict["state"], "pending")
    
    def test_job_from_dict(self):
        """Test creating job from dict"""
        data = {
            "id": "test1",
            "command": "echo hello",
            "state": "pending",
            "attempts": 0,
            "max_retries": 3,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        job = Job.from_dict(data)
        self.assertEqual(job.id, "test1")
        self.assertEqual(job.command, "echo hello")


class TestDatabase(unittest.TestCase):
    """Test Database layer"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        shutil.rmtree(self.temp_dir)
    
    def test_add_job(self):
        """Test adding a job"""
        job = Job(id="test1", command="echo hello")
        self.db.add_job(job)
        
        retrieved = self.db.get_job("test1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "test1")
    
    def test_update_job(self):
        """Test updating a job"""
        job = Job(id="test1", command="echo hello")
        self.db.add_job(job)
        
        job.state = JobState.COMPLETED
        self.db.update_job(job)
        
        retrieved = self.db.get_job("test1")
        self.assertEqual(retrieved.state, JobState.COMPLETED)
    
    def test_get_jobs_by_state(self):
        """Test getting jobs by state"""
        job1 = Job(id="test1", command="echo hello")
        job2 = Job(id="test2", command="echo world")
        job2.state = JobState.COMPLETED
        
        self.db.add_job(job1)
        self.db.add_job(job2)
        
        pending = self.db.get_jobs_by_state(JobState.PENDING)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, "test1")
    
    def test_lock_job(self):
        """Test job locking"""
        job = Job(id="test1", command="echo hello")
        self.db.add_job(job)
        
        # Lock job
        locked = self.db.lock_job("test1", "worker1")
        self.assertTrue(locked)
        
        # Try to lock again (should fail)
        locked_again = self.db.lock_job("test1", "worker2")
        self.assertFalse(locked_again)
        
        # Verify state changed to processing
        retrieved = self.db.get_job("test1")
        self.assertEqual(retrieved.state, JobState.PROCESSING)
    
    def test_unlock_job(self):
        """Test unlocking a job"""
        job = Job(id="test1", command="echo hello")
        self.db.add_job(job)
        
        self.db.lock_job("test1", "worker1")
        self.db.unlock_job("test1")
        
        # Should be able to lock again
        locked = self.db.lock_job("test1", "worker2")
        self.assertTrue(locked)
    
    def test_get_stats(self):
        """Test getting statistics"""
        job1 = Job(id="test1", command="echo hello")
        job2 = Job(id="test2", command="echo world")
        job2.state = JobState.COMPLETED
        
        self.db.add_job(job1)
        self.db.add_job(job2)
        
        stats = self.db.get_stats()
        self.assertEqual(stats[JobState.PENDING.value], 1)
        self.assertEqual(stats[JobState.COMPLETED.value], 1)


class TestQueueManager(unittest.TestCase):
    """Test Queue Manager"""
    
    def setUp(self):
        """Set up test queue"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(db_path=self.db_path)
        self.qm = QueueManager()
        self.qm.db = self.db
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_enqueue(self):
        """Test enqueueing a job"""
        job = self.qm.enqueue("echo hello")
        self.assertIsNotNone(job.id)
        self.assertEqual(job.command, "echo hello")
        self.assertEqual(job.state, JobState.PENDING)
    
    def test_enqueue_with_custom_id(self):
        """Test enqueueing with custom ID"""
        job = self.qm.enqueue("echo hello", job_id="custom1")
        self.assertEqual(job.id, "custom1")
    
    def test_list_jobs(self):
        """Test listing jobs"""
        self.qm.enqueue("echo hello")
        self.qm.enqueue("echo world")
        
        jobs = self.qm.list_jobs()
        self.assertEqual(len(jobs), 2)
    
    def test_get_dlq_jobs(self):
        """Test getting DLQ jobs"""
        job = self.qm.enqueue("echo hello")
        job.state = JobState.DEAD
        self.qm.db.update_job(job)
        
        dlq_jobs = self.qm.get_dlq_jobs()
        self.assertEqual(len(dlq_jobs), 1)
        self.assertEqual(dlq_jobs[0].id, job.id)
    
    def test_retry_dlq_job(self):
        """Test retrying a DLQ job"""
        job = self.qm.enqueue("echo hello")
        job.state = JobState.DEAD
        self.qm.db.update_job(job)
        
        retried = self.qm.retry_dlq_job(job.id)
        self.assertEqual(retried.state, JobState.PENDING)
        self.assertEqual(retried.attempts, 0)
    
    def test_get_stats(self):
        """Test getting statistics"""
        self.qm.enqueue("echo hello")
        self.qm.enqueue("echo world")
        
        job = self.qm.enqueue("echo fail")
        job.state = JobState.DEAD
        self.qm.db.update_job(job)
        
        stats = self.qm.get_stats()
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['pending'], 2)
        self.assertEqual(stats['dead'], 1)


class TestConfig(unittest.TestCase):
    """Test Configuration"""
    
    def setUp(self):
        """Set up test config"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir)
        self.config = Config()
        self.config.config_dir = self.config_path
        self.config.CONFIG_FILE = self.config_path / "config.json"
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_get_default(self):
        """Test getting default config"""
        value = self.config.get("max_retries")
        self.assertEqual(value, 3)
    
    def test_set_get(self):
        """Test setting and getting config"""
        self.config.set("max_retries", 5)
        value = self.config.get("max_retries")
        self.assertEqual(value, 5)
    
    def test_persistence(self):
        """Test config persistence"""
        self.config.set("custom_key", "custom_value")
        
        # Create new instance
        new_config = Config()
        new_config.config_dir = self.config_path
        new_config.CONFIG_FILE = self.config_path / "config.json"
        new_config._config = new_config._load_config()
        
        value = new_config.get("custom_key")
        self.assertEqual(value, "custom_value")


class TestWorkerExecution(unittest.TestCase):
    """Test Worker execution"""
    
    def test_execute_successful_command(self):
        """Test executing a successful command"""
        worker = Worker()
        job = Job(id="test1", command="echo hello")
        
        success = worker._execute_job(job)
        self.assertTrue(success)
    
    def test_execute_failing_command(self):
        """Test executing a failing command"""
        worker = Worker()
        # Command that fails (non-existent command or error)
        job = Job(id="test1", command="false")
        
        success = worker._execute_job(job)
        self.assertFalse(success)
    
    def test_execute_timeout(self):
        """Test command timeout"""
        worker = Worker()
        worker.config._config["worker_timeout"] = 1
        # Sleep longer than timeout
        job = Job(id="test1", command="sleep 5")
        
        success = worker._execute_job(job)
        self.assertFalse(success)


def run_all_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestJobModel))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestQueueManager))
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkerExecution))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == '__main__':
    run_all_tests()
