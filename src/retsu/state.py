"""Job and lease state models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class JobStatus(str, Enum):
    """Admission-mode job statuses."""

    CREATED = "created"
    QUEUED = "queued"
    WAITING_FOR_RESOURCES = "waiting_for_resources"
    LEASED = "leased"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    CANCELLED_REQUESTED = "cancelled_requested"
    EXPIRED = "expired"
    DEAD = "dead"


@dataclass
class LeaseRecord:
    """Persisted lease metadata."""

    id: str
    job_id: str
    owner_id: str
    resources: Dict[str, float]
    concurrency: Dict[str, float]
    expires_at: datetime
    created_at: datetime
    renewed_at: datetime


@dataclass
class JobRecord:
    """Persisted admission-mode job metadata."""

    id: str
    task_name: str
    status: JobStatus
    args_blob: Optional[bytes]
    kwargs_blob: Optional[bytes]
    resources: Dict[str, float]
    concurrency: Dict[str, float]
    executor: str
    queue: Optional[str]
    priority: int
    attempt: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    leased_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None
    error: Optional[str] = None
    result_blob: Optional[bytes] = None

    @property
    def args(self) -> tuple[Any, ...]:
        """Return decoded positional arguments."""
        import pickle

        if self.args_blob is None:
            return ()
        return pickle.loads(self.args_blob)

    @property
    def kwargs(self) -> Dict[str, Any]:
        """Return decoded keyword arguments."""
        import pickle

        if self.kwargs_blob is None:
            return {}
        return pickle.loads(self.kwargs_blob)

