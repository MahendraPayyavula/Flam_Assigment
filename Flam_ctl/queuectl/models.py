"""
Data models and enums for queuectl
"""
from enum import Enum
from datetime import datetime
from typing import Optional
import json


class JobState(str, Enum):
    """Job states in the lifecycle"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


class Job:
    """Represents a background job"""
    
    def __init__(
        self,
        id: str,
        command: str,
        state: JobState = JobState.PENDING,
        attempts: int = 0,
        max_retries: int = 3,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.command = command
        self.state = state if isinstance(state, JobState) else JobState(state)
        self.attempts = attempts
        self.max_retries = max_retries
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert job to dictionary"""
        return {
            "id": self.id,
            "command": self.command,
            "state": self.state.value,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create job from dictionary"""
        return cls(
            id=data["id"],
            command=data["command"],
            state=data.get("state", JobState.PENDING.value),
            attempts=data.get("attempts", 0),
            max_retries=data.get("max_retries", 3),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at"),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at"),
        )
    
    def __repr__(self) -> str:
        return f"Job({self.id}, {self.command}, {self.state.value}, attempts={self.attempts})"
