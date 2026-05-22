"""In-memory backend for tests and local development."""

from __future__ import annotations

import time

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Dict, List, Optional
from uuid import uuid4

from retsu.exceptions import JobNotFound, ResourceDefinitionMissing
from retsu.resources import (
    AcquireResult,
    CleanupResult,
    ResourceRequest,
    UsageItem,
    UsageSnapshot,
)
from retsu.state import JobRecord, JobStatus, LeaseRecord


class MemoryBackend:
    """Thread-safe in-memory backend."""

    def __init__(self) -> None:
        """Initialize an empty backend."""
        self._lock = RLock()
        self._resource_capacity: Dict[str, float] = {}
        self._concurrency_capacity: Dict[str, float] = {}
        self._resource_usage: Dict[str, float] = {}
        self._concurrency_usage: Dict[str, float] = {}
        self._leases: Dict[str, LeaseRecord] = {}
        self._jobs: Dict[str, JobRecord] = {}

    def define_resource(self, name: str, capacity: float) -> None:
        """Define a quantitative resource."""
        self._define(
            self._resource_capacity,
            self._resource_usage,
            name,
            capacity,
        )

    def define_concurrency(self, name: str, capacity: float) -> None:
        """Define a named concurrency limit."""
        self._define(
            self._concurrency_capacity,
            self._concurrency_usage,
            name,
            capacity,
        )

    @staticmethod
    def _define(
        capacities: Dict[str, float],
        usage: Dict[str, float],
        name: str,
        capacity: float,
    ) -> None:
        if not name:
            raise ValueError("capacity name must be non-empty")
        if capacity < 0:
            raise ValueError(f"{name} capacity must be positive")
        capacities[name] = float(capacity)
        usage.setdefault(name, 0)

    def acquire(
        self,
        job_id: str,
        owner_id: str,
        request: ResourceRequest,
        ttl_seconds: int,
    ) -> AcquireResult:
        """Try to acquire capacity atomically."""
        with self._lock:
            self.cleanup_expired_leases()
            missing = self._find_missing(request)
            if missing:
                raise ResourceDefinitionMissing(missing)

            for name, amount in request.resources.items():
                current = self._resource_usage.get(name, 0)
                capacity = self._resource_capacity[name]
                if current + amount > capacity:
                    return AcquireResult(
                        acquired=False,
                        reason="insufficient_resource",
                        blocked_by=name,
                        retry_after_seconds=0.01,
                    )
            for name, amount in request.concurrency.items():
                current = self._concurrency_usage.get(name, 0)
                capacity = self._concurrency_capacity[name]
                if current + amount > capacity:
                    return AcquireResult(
                        acquired=False,
                        reason="insufficient_concurrency",
                        blocked_by=name,
                        retry_after_seconds=0.01,
                    )

            lease_id = uuid4().hex
            now = datetime.now(timezone.utc)
            for name, amount in request.resources.items():
                self._resource_usage[name] = (
                    self._resource_usage.get(name, 0) + amount
                )
            for name, amount in request.concurrency.items():
                self._concurrency_usage[name] = (
                    self._concurrency_usage.get(name, 0) + amount
                )
            self._leases[lease_id] = LeaseRecord(
                id=lease_id,
                job_id=job_id,
                owner_id=owner_id,
                resources=dict(request.resources),
                concurrency=dict(request.concurrency),
                expires_at=now + timedelta(seconds=ttl_seconds),
                created_at=now,
                renewed_at=now,
            )
            return AcquireResult(acquired=True, lease_id=lease_id)

    def _find_missing(self, request: ResourceRequest) -> str:
        for name in request.resources:
            if name not in self._resource_capacity:
                return name
        for name in request.concurrency:
            if name not in self._concurrency_capacity:
                return name
        return ""

    def release(self, lease_id: str, owner_id: str) -> None:
        """Release an active lease."""
        with self._lock:
            lease = self._leases.pop(lease_id, None)
            if lease is None:
                return
            if owner_id and lease.owner_id != owner_id:
                self._leases[lease_id] = lease
                return
            self._subtract_lease(lease)

    def renew(
        self, lease_id: str, owner_id: str, ttl_seconds: int
    ) -> None:
        """Renew an active lease."""
        with self._lock:
            lease = self._leases.get(lease_id)
            if lease is None or (owner_id and lease.owner_id != owner_id):
                return
            now = datetime.now(timezone.utc)
            lease.expires_at = now + timedelta(seconds=ttl_seconds)
            lease.renewed_at = now

    def get_usage(self) -> UsageSnapshot:
        """Return current usage."""
        with self._lock:
            self.cleanup_expired_leases()
            return UsageSnapshot(
                resources={
                    name: UsageItem(
                        used=self._resource_usage.get(name, 0),
                        capacity=capacity,
                    )
                    for name, capacity in self._resource_capacity.items()
                },
                concurrency={
                    name: UsageItem(
                        used=self._concurrency_usage.get(name, 0),
                        capacity=capacity,
                    )
                    for name, capacity in self._concurrency_capacity.items()
                },
            )

    def list_leases(self) -> List[LeaseRecord]:
        """List active leases."""
        with self._lock:
            self.cleanup_expired_leases()
            return list(deepcopy(self._leases).values())

    def get_lease(self, lease_id: str) -> Optional[LeaseRecord]:
        """Get one active lease."""
        with self._lock:
            self.cleanup_expired_leases()
            lease = self._leases.get(lease_id)
            return deepcopy(lease)

    def cleanup_expired_leases(self) -> CleanupResult:
        """Release expired leases."""
        with self._lock:
            now = datetime.now(timezone.utc)
            expired = [
                lease_id
                for lease_id, lease in self._leases.items()
                if lease.expires_at <= now
            ]
            for lease_id in expired:
                lease = self._leases.pop(lease_id)
                self._subtract_lease(lease)
            return CleanupResult(expired_lease_ids=expired)

    def _subtract_lease(self, lease: LeaseRecord) -> None:
        for name, amount in lease.resources.items():
            self._resource_usage[name] = max(
                self._resource_usage.get(name, 0) - amount,
                0,
            )
        for name, amount in lease.concurrency.items():
            self._concurrency_usage[name] = max(
                self._concurrency_usage.get(name, 0) - amount,
                0,
            )

    def create_job(self, job: JobRecord) -> None:
        """Create a job."""
        with self._lock:
            self._jobs[job.id] = deepcopy(job)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
        result_blob: Optional[bytes] = None,
    ) -> None:
        """Update job status."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            now = datetime.now(timezone.utc)
            job.status = status
            job.updated_at = now
            if status == JobStatus.LEASED:
                job.leased_at = now
            elif status == JobStatus.RUNNING:
                job.started_at = now
            elif status in (
                JobStatus.SUCCEEDED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            ):
                job.finished_at = now
            if error is not None:
                job.error = error
            if result_blob is not None:
                job.result_blob = result_blob

    def get_job(self, job_id: str) -> JobRecord:
        """Load one job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            return deepcopy(job)

    def list_queued_jobs(self, limit: int = 100) -> List[JobRecord]:
        """List queued and waiting jobs."""
        with self._lock:
            jobs = [
                deepcopy(job)
                for job in self._jobs.values()
                if job.status
                in (JobStatus.QUEUED, JobStatus.WAITING_FOR_RESOURCES)
            ]
            jobs.sort(
                key=lambda job: (
                    -job.priority,
                    time.mktime(job.created_at.timetuple()),
                )
            )
            return jobs[:limit]
