"""Public guard, context manager, and admission APIs."""

from __future__ import annotations

import functools
import os
import pickle
import socket
import time

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, Mapping, Optional
from uuid import uuid4

from retsu.config import get_backend, get_config
from retsu.exceptions import (
    ResourceAcquireTimeout,
    ResourceUnavailable,
)
from retsu.leases import Lease
from retsu.resources import ResourceRequest, ResourceSpec, ResourceValue
from retsu.state import JobRecord, JobStatus


def current_owner_id() -> str:
    """Return a stable owner id for this process."""
    return f"{socket.gethostname()}:{os.getpid()}"


def define_resource(name: str, capacity: float) -> None:
    """Define a quantitative resource on the configured backend."""
    get_backend().define_resource(name, capacity)


def define_concurrency(name: str, capacity: float) -> None:
    """Define a named concurrency limit on the configured backend."""
    get_backend().define_concurrency(name, capacity)


def get_usage():
    """Return backend usage snapshot."""
    return get_backend().get_usage()


def list_leases():
    """List active leases."""
    return get_backend().list_leases()


def cleanup_expired_leases():
    """Clean expired leases."""
    return get_backend().cleanup_expired_leases()


def acquire_with_policy(
    job_id: str,
    owner_id: str,
    request: ResourceRequest,
    ttl_seconds: Optional[int] = None,
    acquire_timeout_seconds: Optional[float] = None,
    wait_strategy: Optional[str] = None,
) -> Lease:
    """Acquire a lease according to the requested wait policy."""
    config = get_config()
    ttl = ttl_seconds or config.default_ttl_seconds
    timeout = (
        config.default_acquire_timeout_seconds
        if acquire_timeout_seconds is None
        else acquire_timeout_seconds
    )
    strategy = wait_strategy or config.default_wait_strategy
    start = time.monotonic()
    backend = get_backend()

    while True:
        result = backend.acquire(job_id, owner_id, request, ttl)
        if result.acquired:
            return Lease(
                id=result.lease_id,
                job_id=job_id,
                owner_id=owner_id,
                request=request,
                backend=backend,
                ttl_seconds=ttl,
            )

        if strategy == "fail" or strategy == "retry":
            raise ResourceUnavailable(
                blocked_by=result.blocked_by,
                retry_after_seconds=result.retry_after_seconds or 1,
                reason=result.reason,
            )

        if strategy != "block":
            raise ValueError(f"Unsupported wait strategy: {strategy}")

        if timeout is not None and time.monotonic() - start >= timeout:
            raise ResourceAcquireTimeout(
                blocked_by=result.blocked_by,
                retry_after_seconds=result.retry_after_seconds or 1,
                reason=result.reason,
            )
        time.sleep(min(result.retry_after_seconds or 0.1, 1))


@contextmanager
def acquire(
    resources: Optional[Mapping[str, ResourceValue]] = None,
    concurrency: Optional[Mapping[str, ResourceValue]] = None,
    ttl_seconds: Optional[int] = None,
    acquire_timeout_seconds: Optional[float] = None,
    wait_strategy: Optional[str] = None,
) -> Iterator[Lease]:
    """Acquire capacity for a critical section."""
    spec = ResourceSpec(resources or {}, concurrency or {})
    request = spec.evaluate()
    lease = acquire_with_policy(
        job_id=uuid4().hex,
        owner_id=current_owner_id(),
        request=request,
        ttl_seconds=ttl_seconds,
        acquire_timeout_seconds=acquire_timeout_seconds,
        wait_strategy=wait_strategy,
    )
    interval = get_config().default_heartbeat_interval_seconds
    try:
        with lease.heartbeat(interval):
            yield lease
    finally:
        lease.release()


def limit(
    name: str,
    slots: float = 1,
    ttl_seconds: Optional[int] = None,
    acquire_timeout_seconds: Optional[float] = None,
    wait_strategy: Optional[str] = None,
):
    """Acquire one named concurrency limit for a critical section."""
    return acquire(
        concurrency={name: slots},
        ttl_seconds=ttl_seconds,
        acquire_timeout_seconds=acquire_timeout_seconds,
        wait_strategy=wait_strategy,
    )


def guard(
    resources: Optional[Mapping[str, ResourceValue]] = None,
    concurrency: Optional[Mapping[str, ResourceValue]] = None,
    ttl_seconds: Optional[int] = None,
    acquire_timeout_seconds: Optional[float] = None,
    wait_strategy: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate a function so it runs only while capacity is leased."""
    spec = ResourceSpec(resources or {}, concurrency or {})

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = spec.evaluate(*args, **kwargs)
            job_id = kwargs.pop("_retsu_job_id", uuid4().hex)
            lease = acquire_with_policy(
                job_id=job_id,
                owner_id=current_owner_id(),
                request=request,
                ttl_seconds=ttl_seconds,
                acquire_timeout_seconds=acquire_timeout_seconds,
                wait_strategy=wait_strategy,
            )
            interval = get_config().default_heartbeat_interval_seconds
            try:
                with lease.heartbeat(interval):
                    return func(*args, **kwargs)
            finally:
                lease.release()

        return wrapper

    return decorator


class JobHandle:
    """Handle returned by admission-mode submit."""

    def __init__(self, job_id: str) -> None:
        """Initialize the handle."""
        self.id = job_id

    def status(self) -> JobStatus:
        """Return the current job status."""
        return get_backend().get_job(self.id).status

    def cancel(self) -> None:
        """Cancel the job if it has not completed."""
        get_backend().update_job_status(self.id, JobStatus.CANCELLED)

    def result(self, timeout: Optional[float] = None) -> Any:
        """Return the job result, waiting up to timeout seconds."""
        start = time.monotonic()
        while True:
            job = get_backend().get_job(self.id)
            if job.status == JobStatus.SUCCEEDED:
                if job.result_blob is None:
                    return None
                return pickle.loads(job.result_blob)
            if job.status in (JobStatus.FAILED, JobStatus.CANCELLED):
                raise RuntimeError(job.error or f"Job {job.status.value}")
            if timeout is not None and time.monotonic() - start >= timeout:
                raise TimeoutError(f"Job {self.id} did not complete")
            time.sleep(0.05)

    def metadata(self) -> Dict[str, Any]:
        """Return a dictionary of job metadata."""
        job = get_backend().get_job(self.id)
        return {
            "id": job.id,
            "task_name": job.task_name,
            "status": job.status.value,
            "resources": dict(job.resources),
            "concurrency": dict(job.concurrency),
            "executor": job.executor,
            "queue": job.queue,
            "priority": job.priority,
            "attempt": job.attempt,
            "max_attempts": job.max_attempts,
            "error": job.error,
        }


def submit(
    func: Callable[..., Any],
    args: tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    resources: Optional[Mapping[str, ResourceValue]] = None,
    concurrency: Optional[Mapping[str, ResourceValue]] = None,
    executor: str = "local",
    queue: Optional[str] = None,
    priority: int = 0,
    max_attempts: int = 1,
) -> JobHandle:
    """Submit a job for admission-mode scheduling."""
    kwargs = kwargs or {}
    request = ResourceSpec(resources or {}, concurrency or {}).evaluate(
        *args, **kwargs
    )
    now = datetime.now(timezone.utc)
    job = JobRecord(
        id=uuid4().hex,
        task_name=f"{func.__module__}.{func.__qualname__}",
        status=JobStatus.QUEUED,
        args_blob=pickle.dumps(args),
        kwargs_blob=pickle.dumps(kwargs),
        resources=dict(request.resources),
        concurrency=dict(request.concurrency),
        executor=executor,
        queue=queue,
        priority=priority,
        attempt=0,
        max_attempts=max_attempts,
        created_at=now,
        updated_at=now,
    )
    setattr(job, "_retsu_func", func)
    get_backend().create_job(job)
    _LOCAL_FUNCTIONS[job.id] = func
    return JobHandle(job.id)


_LOCAL_FUNCTIONS: Dict[str, Callable[..., Any]] = {}
