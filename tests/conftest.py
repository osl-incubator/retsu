"""Configuration used by pytest."""

from __future__ import annotations

import logging

from typing import Generator

import pytest
import redis

from retsu.queues import get_redis_queue_config


def redis_flush() -> None:
    """Wipe-out redis database."""
    logging.info("Wiping-out redis database.")
    r = redis.Redis(**get_redis_queue_config())  # type: ignore
    r.flushdb()


@pytest.fixture(autouse=True, scope="session")
def setup(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Set up the services needed by the tests."""
    if request.session.items and all(
        item.get_closest_marker("no_services")
        for item in request.session.items
    ):
        yield
        return

    logging.info("Clean Redis database")
    redis_flush()
    yield
