"""Configuration used by pytest."""

from __future__ import annotations

import logging

from typing import Any, Generator

import pytest
import redis

from celery.contrib.testing.worker import start_worker
from retsu.queues import get_redis_queue_config

from tests.celery_tasks import app as celery_app


def redis_flush() -> None:
    """Wipe-out redis database."""
    logging.info("Wiping-out redis database.")
    r = redis.Redis(**get_redis_queue_config())  # type: ignore
    r.flushdb()


@pytest.fixture(scope="session")
def celery_worker_parameters() -> dict[str, Any]:
    """Parameters for the Celery worker."""
    return {
        "loglevel": "debug",  # Set log level
        "concurrency": 4,  # Number of concurrent workers
        "perform_ping_check": False,
        "pool": "prefork",
    }


@pytest.fixture(autouse=True, scope="session")
def setup(
    celery_worker_parameters: dict[str, Any],
) -> Generator[None, None, None]:
    """Set up the services needed by the tests."""
    try:
        logging.info("Clean Redis queues")
        redis_flush()

        logging.info("Start the Celery worker")
        with start_worker(celery_app, **celery_worker_parameters) as worker:
            # Ensure worker is up and running
            yield worker  # Now you can use this worker in your tests

    finally:
        pass
