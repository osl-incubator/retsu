"""Tests for the Retsu resource-control APIs."""

from __future__ import annotations

import sys
import threading
import time

from types import SimpleNamespace
from typing import Any, Callable

import pytest
import retsu

from retsu.backends.memory import MemoryBackend
from retsu.exceptions import (
    ResourceAcquireTimeout,
    ResourceEstimationError,
    ResourceUnavailable,
)
from retsu.resources import ResourceRequest, ResourceSpec
from retsu.scheduler import Scheduler
from retsu.state import JobStatus

pytestmark = pytest.mark.no_services


@pytest.fixture(autouse=True)
def memory_backend() -> None:
    """Use an isolated in-memory backend."""
    retsu.configure(
        backend="memory",
        default_acquire_timeout_seconds=3,
        default_heartbeat_interval_seconds=0.05,
    )
    retsu.set_backend(MemoryBackend())


def test_resource_spec_static_and_dynamic_values() -> None:
    """Resource specs evaluate static and callable values."""
    spec = ResourceSpec(
        resources={"memory_mb": lambda size_mb: size_mb * 4, "cpu": 2},
        concurrency={"api": 1},
    )

    request = spec.evaluate(500)

    assert request.resources == {"memory_mb": 2000.0, "cpu": 2.0}
    assert request.concurrency == {"api": 1.0}


def test_resource_spec_drops_zero_and_rejects_negative() -> None:
    """Requests are normalized before they reach a backend."""
    request = ResourceSpec(
        resources={"memory_mb": 0},
        concurrency={"api": 0},
    ).evaluate()

    assert request.resources == {}
    assert request.concurrency == {}

    with pytest.raises(ValueError, match="memory_mb"):
        ResourceSpec(resources={"memory_mb": -1}, concurrency={}).evaluate()


def test_estimator_error_fails_before_acquire() -> None:
    """Estimator failures are wrapped and do not create leases."""
    retsu.define_resource("memory_mb", 1000)

    with pytest.raises(ResourceEstimationError):
        ResourceSpec(
            resources={"memory_mb": lambda value: 1 / 0},
            concurrency={},
        ).evaluate(1)

    assert retsu.list_leases() == []
    assert retsu.get_usage().resources["memory_mb"].used == 0


def test_memory_backend_acquire_release_and_double_release() -> None:
    """The backend restores usage and never goes negative."""
    backend = MemoryBackend()
    backend.define_resource("memory_mb", 1000)
    backend.define_concurrency("api", 2)
    request = ResourceRequest(
        resources={"memory_mb": 500},
        concurrency={"api": 1},
    )

    result = backend.acquire("job-1", "worker-1", request, ttl_seconds=60)

    assert result.acquired is True
    usage = backend.get_usage()
    assert usage.resources["memory_mb"].used == 500
    assert usage.concurrency["api"].used == 1

    backend.release(result.lease_id, "worker-1")
    backend.release(result.lease_id, "worker-1")

    usage = backend.get_usage()
    assert usage.resources["memory_mb"].used == 0
    assert usage.concurrency["api"].used == 0


def test_guard_releases_on_exception() -> None:
    """Guard mode releases leases even when the function raises."""
    retsu.define_concurrency("api", 1)

    @retsu.guard(concurrency={"api": 1})
    def fn() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        fn()

    assert retsu.get_usage().concurrency["api"].used == 0


def test_guard_fail_strategy() -> None:
    """Fail strategy raises immediately when capacity is unavailable."""
    retsu.define_concurrency("api", 1)
    lease = retsu.acquire_with_policy(
        job_id="manual",
        owner_id="owner",
        request=ResourceRequest(resources={}, concurrency={"api": 1}),
        ttl_seconds=60,
    )

    @retsu.guard(concurrency={"api": 1}, wait_strategy="fail")
    def fn() -> str:
        return "never"

    try:
        with pytest.raises(ResourceUnavailable):
            fn()
    finally:
        lease.release()


def test_guard_timeout() -> None:
    """Block strategy honors acquire timeout."""
    retsu.define_concurrency("api", 1)
    lease = retsu.acquire_with_policy(
        job_id="manual",
        owner_id="owner",
        request=ResourceRequest(resources={}, concurrency={"api": 1}),
        ttl_seconds=60,
    )

    @retsu.guard(
        concurrency={"api": 1},
        wait_strategy="block",
        acquire_timeout_seconds=0.05,
    )
    def fn() -> str:
        return "never"

    try:
        with pytest.raises(ResourceAcquireTimeout):
            fn()
    finally:
        lease.release()


def test_thread_race_never_exceeds_limit() -> None:
    """Many callers cannot exceed a concurrency limit."""
    retsu.define_concurrency("api", 2)
    active = 0
    max_active = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal active, max_active
        with retsu.limit("api", slots=1):
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.01)
            with lock:
                active -= 1

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max_active <= 2
    assert retsu.get_usage().concurrency["api"].used == 0


def test_scheduler_local_executor_runs_when_capacity_available() -> None:
    """Admission mode queues and runs local jobs."""
    retsu.define_resource("memory_mb", 1000)

    def add(a: int, b: int) -> int:
        return a + b

    job = retsu.submit(
        add,
        args=(1, 2),
        resources={"memory_mb": 100},
        executor="local",
    )

    assert job.status() == JobStatus.QUEUED

    Scheduler().run_once()

    assert job.result(timeout=2) == 3
    assert job.status() == JobStatus.SUCCEEDED
    assert retsu.get_usage().resources["memory_mb"].used == 0


def test_ray_guard_limits_critical_section() -> None:
    """Ray guard can protect code running inside a Ray task."""
    retsu.define_concurrency("api", 1)

    with retsu.ray_guard(concurrency={"api": 1}):
        assert retsu.get_usage().concurrency["api"].used == 1

    assert retsu.get_usage().concurrency["api"].used == 0


def test_scheduler_ray_executor_runs_when_capacity_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admission mode can dispatch jobs through the Ray executor."""
    retsu.define_resource("memory_mb", 1000)

    class FakeObjectRef:
        """Fake Ray object reference."""

        def __init__(self, value: Any) -> None:
            self.value = value

    class FakeRemoteFunction:
        """Fake Ray remote function."""

        def __init__(self, func: Callable[..., Any]) -> None:
            self.func = func

        def remote(self, *args: Any, **kwargs: Any) -> FakeObjectRef:
            return FakeObjectRef(self.func(*args, **kwargs))

    def remote(func: Callable[..., Any]) -> FakeRemoteFunction:
        return FakeRemoteFunction(func)

    def get(object_ref: FakeObjectRef) -> Any:
        return object_ref.value

    monkeypatch.setitem(
        sys.modules,
        "ray",
        SimpleNamespace(remote=remote, get=get),
    )

    def add(a: int, b: int) -> int:
        return a + b

    job = retsu.submit(
        add,
        args=(2, 3),
        resources={"memory_mb": 100},
        executor="ray",
    )

    Scheduler().run_once()

    assert job.result(timeout=2) == 5
    assert job.status() == JobStatus.SUCCEEDED
    assert retsu.get_usage().resources["memory_mb"].used == 0
