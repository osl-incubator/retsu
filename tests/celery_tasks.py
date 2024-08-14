"""Celery Process."""

from __future__ import annotations

import os
import sys

from datetime import datetime
from time import sleep

import redis

from celery import Celery

redis_host: str = os.getenv("RETSU_REDIS_HOST", "localhost")
redis_port: int = int(os.getenv("RETSU_REDIS_PORT", 6379))
redis_db: int = int(os.getenv("RETSU_REDIS_DB", 0))

redis_uri = f"redis://{redis_host}:{redis_port}/{redis_db}"

app = Celery(
    "celery_tasks",
    broker=redis_uri,
    backend=redis_uri,
)

LOG_FORMAT_PREFIX = "[%(asctime)s: %(levelname)s/%(processName)s]"

app.conf.update(
    broker_url=redis_uri,
    result_backend=redis_uri,
    worker_log_format=f"{LOG_FORMAT_PREFIX} %(message)s",
    worker_task_log_format=(
        f"{LOG_FORMAT_PREFIX} %(task_name)s[%(task_id)s]: %(message)s"
    ),
    task_annotations={"*": {"rate_limit": "10/s"}},
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=30 * 60,
    worker_redirect_stdouts_level="DEBUG",
)

redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    ssl=False,
)

try:
    print("Pinging Redis...")
    redis_client.ping()
    print("Redis connection is working.")
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    sys.exit(1)


@app.task  # type: ignore
def task_sum(x: int, y: int, task_id: str) -> int:
    """Sum two numbers, x and y."""
    result = x + y
    return result


@app.task  # type: ignore
def task_sleep(seconds: int, task_id: str) -> int:
    """Sum two numbers, x and y, and sleep the same amount of the sum."""
    sleep(seconds)
    return int(datetime.now().timestamp())
