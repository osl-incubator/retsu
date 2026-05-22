"""Celery helpers for Retsu guard mode."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Mapping, Optional

from retsu.exceptions import ResourceUnavailable
from retsu.resources import ResourceValue
from retsu.task import acquire


@contextmanager
def celery_guard(
    task,
    resources: Optional[Mapping[str, ResourceValue]] = None,
    concurrency: Optional[Mapping[str, ResourceValue]] = None,
    ttl_seconds: Optional[int] = None,
    acquire_timeout_seconds: Optional[float] = None,
    wait_strategy: str = "retry",
) -> Iterator[None]:
    """Guard a Celery task and convert retry policy into task.retry()."""
    try:
        with acquire(
            resources=resources,
            concurrency=concurrency,
            ttl_seconds=ttl_seconds,
            acquire_timeout_seconds=acquire_timeout_seconds,
            wait_strategy=wait_strategy,
        ):
            yield
    except ResourceUnavailable as exc:
        if wait_strategy == "retry":
            raise task.retry(countdown=exc.retry_after_seconds or 1) from exc
        raise

