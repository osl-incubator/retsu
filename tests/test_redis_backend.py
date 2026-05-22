"""Redis backend integration tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Generator
from uuid import uuid4

import pytest

from retsu.backends.redis import RedisBackend
from retsu.exceptions import JobNotFound, ResourceDefinitionMissing
from retsu.resources import ResourceRequest
from retsu.state import JobRecord, JobStatus

pytestmark = pytest.mark.redis


@pytest.fixture
def backend() -> Generator[RedisBackend, None, None]:
    """Create an isolated Redis namespace."""
    backend = RedisBackend(namespace=f"test-{uuid4().hex}")
    backend.flush_namespace()
    try:
        yield backend
    finally:
        backend.flush_namespace()


def make_job(
    job_id: str,
    status: JobStatus = JobStatus.QUEUED,
    priority: int = 0,
) -> JobRecord:
    """Create a minimal persisted job record."""
    now = datetime.now(timezone.utc)
    return JobRecord(
        id=job_id,
        task_name="tests.fn",
        status=status,
        args_blob=b"args",
        kwargs_blob=b"kwargs",
        resources={"memory_mb": 1},
        concurrency={"api": 1},
        executor="local",
        queue="default",
        priority=priority,
        attempt=0,
        max_attempts=2,
        created_at=now + timedelta(seconds=priority),
        updated_at=now,
    )


def test_redis_backend_acquire_release_renew_and_cleanup(
    backend: RedisBackend,
) -> None:
    """Redis backend performs atomic capacity accounting."""
    with pytest.raises(ValueError, match="non-empty"):
        backend.define_resource("", 1)
    with pytest.raises(ValueError, match="positive"):
        backend.define_concurrency("api", -1)

    with pytest.raises(ResourceDefinitionMissing):
        backend.acquire(
            "missing",
            "owner",
            ResourceRequest({"memory_mb": 1}, {}),
            ttl_seconds=1,
        )

    backend.define_resource("memory_mb", 10)
    backend.define_concurrency("api", 1)
    lease = backend.acquire(
        "job",
        "owner",
        ResourceRequest({"memory_mb": 6}, {"api": 1}),
        ttl_seconds=60,
    )
    assert lease.acquired is True

    denied_resource = backend.acquire(
        "job-2",
        "owner",
        ResourceRequest({"memory_mb": 6}, {}),
        ttl_seconds=60,
    )
    denied_concurrency = backend.acquire(
        "job-3",
        "owner",
        ResourceRequest({}, {"api": 1}),
        ttl_seconds=60,
    )
    assert denied_resource.reason == "insufficient_resource"
    assert denied_resource.blocked_by == "memory_mb"
    assert denied_concurrency.reason == "insufficient_concurrency"

    stored = backend.get_lease(lease.lease_id)
    assert stored is not None
    assert stored.resources == {"memory_mb": 6}
    assert backend.list_leases()[0].id == lease.lease_id

    backend.renew(lease.lease_id, "wrong-owner", ttl_seconds=1)
    before = backend.get_lease(lease.lease_id)
    backend.renew(lease.lease_id, "owner", ttl_seconds=120)
    after = backend.get_lease(lease.lease_id)
    assert before is not None
    assert after is not None
    assert after.expires_at >= before.expires_at

    backend.release(lease.lease_id, "wrong-owner")
    assert backend.get_lease(lease.lease_id) is not None
    backend.release(lease.lease_id, "owner")
    assert backend.get_lease(lease.lease_id) is None
    assert backend.get_usage().resources["memory_mb"].used == 0

    expired = backend.acquire(
        "expired",
        "owner",
        ResourceRequest({"memory_mb": 1}, {}),
        ttl_seconds=-1,
    )
    cleanup = backend.cleanup_expired_leases()
    assert expired.lease_id in cleanup.expired_lease_ids


def test_redis_backend_job_lifecycle_and_namespace_flush(
    backend: RedisBackend,
) -> None:
    """Redis backend persists and orders jobs."""
    backend.create_job(make_job("low", priority=1))
    backend.create_job(make_job("high", priority=10))
    backend.create_job(make_job("done", status=JobStatus.SUCCEEDED))

    assert [job.id for job in backend.list_queued_jobs()] == ["high", "low"]
    assert [job.id for job in backend.list_queued_jobs(limit=1)] == ["high"]

    backend.update_job_status("low", JobStatus.LEASED)
    backend.update_job_status("low", JobStatus.RUNNING)
    backend.update_job_status(
        "low",
        JobStatus.SUCCEEDED,
        result_blob=b"result",
    )
    job = backend.get_job("low")
    assert job.status == JobStatus.SUCCEEDED
    assert job.args_blob == b"args"
    assert job.kwargs_blob == b"kwargs"
    assert job.result_blob == b"result"
    assert job.leased_at is not None
    assert job.started_at is not None
    assert job.finished_at is not None

    backend.update_job_status("high", JobStatus.FAILED, error="bad")
    assert backend.get_job("high").error == "bad"
    backend.update_job_status("high", JobStatus.CANCELLED)
    assert backend.get_job("high").status == JobStatus.CANCELLED

    with pytest.raises(JobNotFound):
        backend.get_job("missing")
    with pytest.raises(JobNotFound):
        backend.update_job_status("missing", JobStatus.RUNNING)

    backend.flush_namespace()
    assert backend.list_queued_jobs() == []
