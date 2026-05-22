"""Additional behavioral coverage for resource-control internals."""

from __future__ import annotations

import sys
import time

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Callable, Protocol, cast

import pytest
import retsu

from retsu.backends.memory import MemoryBackend
from retsu.cli.main import _print_usage, main
from retsu.config import configure, get_backend
from retsu.exceptions import (
    JobNotFound,
    ResourceDefinitionMissing,
    ResourceUnavailable,
)
from retsu.integrations.celery import celery_guard
from retsu.plugins.django import create_app_config
from retsu.resources import ResourceRequest, UsageItem
from retsu.scheduler import Scheduler
from retsu.state import JobRecord, JobStatus
from retsu.task import JobHandle

pytestmark = pytest.mark.no_services


class StoppableAppConfig(Protocol):
    """App config protocol returned by the Django plugin factory."""

    def ready(self) -> None:
        """Start the manager."""

    def stop_multiprocessing(self, **kwargs: Any) -> None:
        """Stop the manager."""


@pytest.fixture(autouse=True)
def isolated_backend() -> None:
    """Use an isolated in-memory backend."""
    configure(
        backend="memory",
        default_acquire_timeout_seconds=0.05,
        default_heartbeat_interval_seconds=0.01,
    )
    retsu.set_backend(MemoryBackend())


def make_job(
    job_id: str,
    status: JobStatus = JobStatus.QUEUED,
    priority: int = 0,
    resources: dict[str, float] | None = None,
    concurrency: dict[str, float] | None = None,
    executor: str = "local",
) -> JobRecord:
    """Create a minimal persisted job record."""
    now = datetime.now(timezone.utc)
    return JobRecord(
        id=job_id,
        task_name="tests.fn",
        status=status,
        args_blob=b"\x80\x04).",
        kwargs_blob=b"\x80\x04}.",
        resources=resources or {},
        concurrency=concurrency or {},
        executor=executor,
        queue=None,
        priority=priority,
        attempt=0,
        max_attempts=1,
        created_at=now + timedelta(seconds=priority),
        updated_at=now,
    )


def test_config_lazily_creates_memory_backend_and_rejects_unknown() -> None:
    """Configuration creates the selected backend lazily."""
    configure(backend="memory")
    assert isinstance(get_backend(), MemoryBackend)

    configure(backend="unsupported")
    with pytest.raises(ValueError, match="Unsupported Retsu backend"):
        get_backend()


def test_resource_request_validation_and_usage_available() -> None:
    """Resource requests validate names and finite values."""
    assert ResourceRequest({}, {}).empty is True
    assert UsageItem(used=8, capacity=5).available == 0

    with pytest.raises(ValueError, match="non-empty"):
        ResourceRequest({"": 1}, {})
    with pytest.raises(ValueError, match="finite"):
        ResourceRequest({"memory_mb": float("inf")}, {})


def test_memory_backend_capacity_edges_and_expiration() -> None:
    """Memory backend handles validation, misses, denial, and expiry."""
    backend = MemoryBackend()

    with pytest.raises(ValueError, match="non-empty"):
        backend.define_resource("", 1)
    with pytest.raises(ValueError, match="positive"):
        backend.define_concurrency("api", -1)

    with pytest.raises(ResourceDefinitionMissing, match="memory_mb"):
        backend.acquire(
            "job",
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
        ttl_seconds=1,
    )

    denied_resource = backend.acquire(
        "other",
        "owner",
        ResourceRequest({"memory_mb": 6}, {}),
        ttl_seconds=1,
    )
    denied_concurrency = backend.acquire(
        "other",
        "owner",
        ResourceRequest({}, {"api": 1}),
        ttl_seconds=1,
    )

    assert denied_resource.acquired is False
    assert denied_resource.reason == "insufficient_resource"
    assert denied_concurrency.reason == "insufficient_concurrency"

    backend.release(lease.lease_id, "wrong-owner")
    assert backend.get_lease(lease.lease_id) is not None

    backend.renew(lease.lease_id, "owner", ttl_seconds=10)
    renewed = backend.get_lease(lease.lease_id)
    assert renewed is not None
    assert renewed.expires_at > renewed.created_at

    backend._leases[lease.lease_id].expires_at = datetime.now(
        timezone.utc
    ) - timedelta(seconds=1)
    cleanup = backend.cleanup_expired_leases()
    assert cleanup.expired_lease_ids == [lease.lease_id]
    assert backend.get_usage().resources["memory_mb"].used == 0


def test_memory_backend_job_lifecycle_and_queue_order() -> None:
    """Memory backend persists job lifecycle metadata."""
    backend = MemoryBackend()
    jobs = [
        make_job("low", priority=1),
        make_job("high", priority=10),
        make_job("done", status=JobStatus.SUCCEEDED),
    ]
    for job in jobs:
        backend.create_job(job)

    assert [job.id for job in backend.list_queued_jobs()] == ["high", "low"]
    assert [job.id for job in backend.list_queued_jobs(limit=1)] == ["high"]

    backend.update_job_status("low", JobStatus.LEASED)
    backend.update_job_status("low", JobStatus.RUNNING)
    backend.update_job_status(
        "low",
        JobStatus.FAILED,
        error="boom",
        result_blob=b"result",
    )
    failed = backend.get_job("low")
    assert failed.error == "boom"
    assert failed.result_blob == b"result"
    assert failed.leased_at is not None
    assert failed.started_at is not None
    assert failed.finished_at is not None

    with pytest.raises(JobNotFound):
        backend.get_job("missing")
    with pytest.raises(JobNotFound):
        backend.update_job_status("missing", JobStatus.CANCELLED)


def test_job_handle_terminal_states_and_metadata() -> None:
    """Job handles expose status, result, cancellation, and metadata."""
    backend = MemoryBackend()
    retsu.set_backend(backend)
    backend.create_job(make_job("ok", status=JobStatus.SUCCEEDED))
    backend.update_job_status("ok", JobStatus.SUCCEEDED)
    assert JobHandle("ok").result(timeout=0) is None

    backend.create_job(make_job("failed", status=JobStatus.QUEUED))
    backend.update_job_status("failed", JobStatus.FAILED, error="bad")
    with pytest.raises(RuntimeError, match="bad"):
        JobHandle("failed").result(timeout=0)

    backend.create_job(make_job("queued", priority=3, executor="local"))
    handle = JobHandle("queued")
    assert handle.status() == JobStatus.QUEUED
    assert handle.metadata()["priority"] == 3
    handle.cancel()
    assert handle.status() == JobStatus.CANCELLED

    backend.create_job(make_job("waiting"))
    with pytest.raises(TimeoutError):
        JobHandle("waiting").result(timeout=0)


def test_lease_heartbeat_renews_until_context_exit() -> None:
    """Heartbeat periodically renews the active lease."""
    retsu.define_concurrency("api", 1)
    lease = retsu.acquire_with_policy(
        "job",
        "owner",
        ResourceRequest({}, {"api": 1}),
        ttl_seconds=1,
    )
    try:
        first = retsu.get_backend().get_lease(lease.id)
        assert first is not None
        with lease.heartbeat(0.01):
            time.sleep(0.03)
        second = retsu.get_backend().get_lease(lease.id)
        assert second is not None
        assert second.renewed_at > first.renewed_at
    finally:
        lease.release()


def test_scheduler_waits_and_marks_unknown_executor_failed() -> None:
    """Scheduler marks blocked jobs waiting and releases failed dispatches."""
    backend = MemoryBackend()
    backend.define_concurrency("api", 1)
    retsu.set_backend(backend)
    held = backend.acquire(
        "held",
        "owner",
        ResourceRequest({}, {"api": 1}),
        ttl_seconds=60,
    )
    waiting = make_job("waiting", concurrency={"api": 1})
    backend.create_job(waiting)
    Scheduler(backend=backend, owner_id="scheduler").run_once()
    assert backend.get_job("waiting").status == JobStatus.WAITING_FOR_RESOURCES

    backend.release(held.lease_id, "owner")
    backend.create_job(make_job("unknown", executor="missing"))
    Scheduler(backend=backend, owner_id="scheduler").run_once()
    failed = backend.get_job("unknown")
    assert failed.status == JobStatus.FAILED
    assert failed.error == "'missing'"
    assert backend.get_usage().concurrency["api"].used == 0


def test_celery_guard_retries_only_for_retry_strategy() -> None:
    """Celery guard maps resource unavailability to task.retry."""
    retsu.define_concurrency("api", 1)
    held = retsu.acquire_with_policy(
        "held",
        "owner",
        ResourceRequest({}, {"api": 1}),
        ttl_seconds=60,
    )

    class RetryTask:
        """Small task object exposing Celery's retry API."""

        def retry(self, countdown: float) -> RuntimeError:
            return RuntimeError(f"retry in {countdown:g}")

    try:
        with pytest.raises(RuntimeError, match="retry in"):
            with celery_guard(
                RetryTask(),
                concurrency={"api": 1},
                wait_strategy="retry",
            ):
                pass

        with pytest.raises(ResourceUnavailable):
            with celery_guard(
                RetryTask(),
                concurrency={"api": 1},
                wait_strategy="fail",
            ):
                pass
    finally:
        held.release()


def test_ray_task_decorator_uses_options_and_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ray task decorator wraps the function and forwards Ray options."""
    retsu.define_concurrency("api", 1)
    calls: list[dict[str, Any]] = []

    class RemoteFunction:
        """Minimal Ray remote function."""

        def __init__(self, func: Callable[..., Any]) -> None:
            self.func = func

        def remote(self, *args: Any, **kwargs: Any) -> Any:
            return self.func(*args, **kwargs)

    def remote(*args: Any, **kwargs: Any) -> Any:
        if args and callable(args[0]):
            return RemoteFunction(args[0])

        def decorator(func: Callable[..., Any]) -> RemoteFunction:
            calls.append(kwargs)
            return RemoteFunction(func)

        return decorator

    monkeypatch.setitem(sys.modules, "ray", SimpleNamespace(remote=remote))

    @retsu.ray_task(concurrency={"api": 1}, num_cpus=0)
    def guarded(value: int) -> tuple[int, float]:
        usage = retsu.get_usage().concurrency["api"].used
        return value + 1, usage

    assert guarded.remote(2) == (3, 1)
    assert calls == [{"num_cpus": 0}]
    assert retsu.get_usage().concurrency["api"].used == 0


def test_django_app_config_starts_and_stops_manager() -> None:
    """Django plugin config wires manager lifecycle hooks."""
    events: list[str] = []

    class Manager:
        """Minimal process manager for plugin lifecycle."""

        def start(self) -> None:
            events.append("start")

        def stop(self) -> None:
            events.append("stop")

    config_cls = create_app_config(Manager(), app_name="tests")
    config = cast(
        StoppableAppConfig,
        config_cls("tests", sys.modules[__name__]),
    )

    config.ready()
    config.stop_multiprocessing(signal=None)

    assert events == ["start", "stop"]


def test_cli_memory_backend_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI commands work against the memory backend."""
    assert main(["--backend", "memory", "resource", "memory_mb", "128"]) == 0
    assert "defined resource memory_mb=128" in capsys.readouterr().out

    assert main(["--backend", "memory", "concurrency", "api", "2"]) == 0
    assert "defined concurrency api=2" in capsys.readouterr().out

    assert main(["--backend", "memory", "usage"]) == 0
    usage_output = capsys.readouterr().out
    assert "RESOURCES" in usage_output
    assert "CONCURRENCY" in usage_output

    assert main(["--backend", "memory", "leases"]) == 0
    assert capsys.readouterr().out == ""

    assert main(["--backend", "memory", "cleanup"]) == 0
    assert "expired 0 leases" in capsys.readouterr().out


def test_cli_print_usage(capsys: pytest.CaptureFixture[str]) -> None:
    """Usage printing includes availability."""
    _print_usage("RESOURCES", {"memory_mb": UsageItem(used=32, capacity=128)})

    output = capsys.readouterr().out
    assert "name\tused\tcapacity\tavailable" in output
    assert "memory_mb\t32\t128\t96" in output
