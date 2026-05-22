"""Admission-mode scheduler."""

from __future__ import annotations

from typing import Dict, Optional
from uuid import uuid4

from retsu.backends.base import Backend
from retsu.config import get_backend, get_config
from retsu.executors.base import Executor
from retsu.executors.local import LocalExecutor
from retsu.executors.ray import RayExecutor
from retsu.resources import ResourceRequest
from retsu.state import JobStatus


class Scheduler:
    """Small admission scheduler."""

    def __init__(
        self,
        backend: Optional[Backend] = None,
        executors: Optional[Dict[str, Executor]] = None,
        owner_id: Optional[str] = None,
    ) -> None:
        """Initialize the scheduler."""
        self.backend = backend or get_backend()
        self.owner_id = owner_id or uuid4().hex
        self.executors = executors or {"local": LocalExecutor(self.backend)}

    def run_once(self, limit: int = 100) -> None:
        """Attempt to dispatch queued jobs once."""
        self.backend.cleanup_expired_leases()
        for job in self.backend.list_queued_jobs(limit=limit):
            request = ResourceRequest(job.resources, job.concurrency)
            result = self.backend.acquire(
                job_id=job.id,
                owner_id=self.owner_id,
                request=request,
                ttl_seconds=get_config().default_ttl_seconds,
            )
            if not result.acquired:
                self.backend.update_job_status(
                    job.id,
                    JobStatus.WAITING_FOR_RESOURCES,
                )
                continue

            try:
                self.backend.update_job_status(job.id, JobStatus.LEASED)
                executor = self._get_executor(job.executor)
                self.backend.update_job_status(job.id, JobStatus.DISPATCHED)
                executor.dispatch(job, result.lease_id, self.owner_id)
            except Exception as exc:
                self.backend.release(result.lease_id, self.owner_id)
                self.backend.update_job_status(
                    job.id,
                    JobStatus.FAILED,
                    error=str(exc),
                )

    def _get_executor(self, name: str) -> Executor:
        """Return an executor, creating optional integrations on demand."""
        executor = self.executors.get(name)
        if executor is not None:
            return executor
        if name == "ray":
            executor = RayExecutor(self.backend)
            self.executors[name] = executor
            return executor
        raise KeyError(name)
