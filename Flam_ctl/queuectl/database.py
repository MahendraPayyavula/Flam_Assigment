"""
Database layer for job persistence
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from .models import Job, JobState
from .config import get_config


class Database:
    """SQLite database for job persistence"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database"""
        # Resolve database path from provided value or configuration. Support
        # both the legacy DB_FILE attribute and the instance-level db_file.
        cfg = get_config()
        cfg_db = getattr(cfg, "db_file", None) or getattr(cfg, "DB_FILE", None)
        self.db_path = db_path or cfg_db
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    locked_at TEXT,
                    locked_by TEXT
                )
            """)
            conn.commit()
    
    def add_job(self, job: Job) -> None:
        """Add a new job to the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs 
                (id, command, state, attempts, max_retries, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.command,
                job.state.value,
                job.attempts,
                job.max_retries,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
            ))
            conn.commit()
    
    def update_job(self, job: Job) -> None:
        """Update an existing job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE jobs
                SET command = ?, state = ?, attempts = ?, max_retries = ?, updated_at = ?,
                    locked_at = NULL, locked_by = NULL
                WHERE id = ?
            """, (
                job.command,
                job.state.value,
                job.attempts,
                job.max_retries,
                job.updated_at.isoformat(),
                job.id,
            ))
            conn.commit()
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_job(row)
        return None
    
    def get_jobs_by_state(self, state: JobState) -> List[Job]:
        """Get all jobs with a specific state"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE state = ? ORDER BY created_at ASC",
                (state.value,)
            )
            return [self._row_to_job(row) for row in cursor.fetchall()]
    
    def get_pending_jobs(self) -> List[Job]:
        """Get all pending jobs not locked"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM jobs 
                WHERE state = ? AND locked_at IS NULL
                ORDER BY created_at ASC
            """, (JobState.PENDING.value,))
            return [self._row_to_job(row) for row in cursor.fetchall()]
    
    def lock_job(self, job_id: str, worker_id: str) -> bool:
        """Lock a job for processing (prevent duplicate processing)"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if already locked
            cursor = conn.execute(
                "SELECT locked_by FROM jobs WHERE id = ? AND locked_at IS NOT NULL",
                (job_id,)
            )
            if cursor.fetchone():
                return False
            
            # Update state to processing and lock
            cursor = conn.execute("""
                UPDATE jobs
                SET state = ?, locked_at = ?, locked_by = ?, updated_at = ?
                WHERE id = ?
            """, (
                JobState.PROCESSING.value,
                datetime.utcnow().isoformat(),
                worker_id,
                datetime.utcnow().isoformat(),
                job_id,
            ))
            conn.commit()
            return cursor.rowcount > 0
    
    def unlock_job(self, job_id: str) -> None:
        """Unlock a job (release the lock)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE jobs
                SET locked_at = NULL, locked_by = NULL, updated_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), job_id))
            conn.commit()
    
    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            return [self._row_to_job(row) for row in cursor.fetchall()]
    
    def delete_job(self, job_id: str) -> None:
        """Delete a job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
    
    def get_stats(self) -> dict:
        """Get job statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT state, COUNT(*) as count
                FROM jobs
                GROUP BY state
            """)
            stats = {}
            for state, count in cursor.fetchall():
                stats[state] = count
            
            # Ensure all states are represented
            for state in JobState:
                stats.setdefault(state.value, 0)
            
            return stats
    
    @staticmethod
    def _row_to_job(row) -> Job:
        """Convert database row to Job object"""
        return Job(
            id=row[0],
            command=row[1],
            state=row[2],
            attempts=row[3],
            max_retries=row[4],
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
        )


# Global database instance
_db_instance = None


def get_db() -> Database:
    """Get or create global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
