"""Ray helpers for Retsu guard mode."""

from __future__ import annotations

from contextlib import contextmanager
from importlib import import_module
from typing import Any, Callable, Iterator, Mapping, Optional

from retsu.resources import ResourceValue
from retsu.task import acquire, guard


@contextmanager
def ray_guard(
    resources: Optional[Mapping[str, ResourceValue]] = None,
    concurrency: Optional[Mapping[str, ResourceValue]] = None,
    ttl_seconds: Optional[int] = None,
    acquire_timeout_seconds: Optional[float] = None,
    wait_strategy: Optional[str] = None,
) -> Iterator[None]:
    """Guard a critical section inside a Ray task."""
    with acquire(
        resources=resources,
        concurrency=concurrency,
        ttl_seconds=ttl_seconds,
        acquire_timeout_seconds=acquire_timeout_seconds,
        wait_strategy=wait_strategy,
    ):
        yield


def ray_task(
    resources: Optional[Mapping[str, ResourceValue]] = None,
    concurrency: Optional[Mapping[str, ResourceValue]] = None,
    ttl_seconds: Optional[int] = None,
    acquire_timeout_seconds: Optional[float] = None,
    wait_strategy: Optional[str] = None,
    **ray_options: Any,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorate a function as a Ray remote guarded by Retsu."""

    def decorator(func: Callable[..., Any]) -> Any:
        guarded = guard(
            resources=resources,
            concurrency=concurrency,
            ttl_seconds=ttl_seconds,
            acquire_timeout_seconds=acquire_timeout_seconds,
            wait_strategy=wait_strategy,
        )(func)
        ray = import_module("ray")
        if ray_options:
            return ray.remote(**ray_options)(guarded)
        return ray.remote(guarded)

    return decorator
