"""Backend protocol for Retsu."""

from __future__ import annotations

from typing import List, Optional, Protocol

from retsu.resources import (
    AcquireResult,
    CleanupResult,
    ResourceRequest,
    UsageSnapshot,
)
from retsu.state import JobRecord, JobStatus, LeaseRecord


class Backend(Protocol):  # pragma: no cover
    """Storage and atomic accounting backend."""

    def define_resource(self, name: str, capacity: float) -> None:
        """Define a quantitative resource."""
        _ = (name, capacity)
        raise NotImplementedError

    def define_concurrency(self, name: str, capacity: float) -> None:
        """Define a named concurrency limit."""
        _ = (name, capacity)
        raise NotImplementedError

    def acquire(
        self,
        job_id: str,
        owner_id: str,
        request: ResourceRequest,
        ttl_seconds: int,
    ) -> AcquireResult:
        """Try to acquire capacity atomically."""
        _ = (job_id, owner_id, request, ttl_seconds)
        raise NotImplementedError

    def release(self, lease_id: str, owner_id: str) -> None:
        """Release an active lease."""
        _ = (lease_id, owner_id)
        raise NotImplementedError

    def renew(self, lease_id: str, owner_id: str, ttl_seconds: int) -> None:
        """Renew an active lease."""
        _ = (lease_id, owner_id, ttl_seconds)
        raise NotImplementedError

    def get_usage(self) -> UsageSnapshot:
        """Return usage and capacity for all configured limits."""
        raise NotImplementedError

    def list_leases(self) -> List[LeaseRecord]:
        """List active leases."""
        raise NotImplementedError

    def get_lease(self, lease_id: str) -> Optional[LeaseRecord]:
        """Return one active lease if present."""
        _ = lease_id
        raise NotImplementedError

    def cleanup_expired_leases(self) -> CleanupResult:
        """Release all expired leases."""
        raise NotImplementedError

    def create_job(self, job: JobRecord) -> None:
        """Create a persisted job."""
        _ = job
        raise NotImplementedError

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
        result_blob: Optional[bytes] = None,
    ) -> None:
        """Update a job status and optional terminal fields."""
        _ = (job_id, status, error, result_blob)
        raise NotImplementedError

    def get_job(self, job_id: str) -> JobRecord:
        """Load one job."""
        _ = job_id
        raise NotImplementedError

    def list_queued_jobs(self, limit: int = 100) -> List[JobRecord]:
        """List queued or waiting jobs."""
        _ = limit
        raise NotImplementedError
