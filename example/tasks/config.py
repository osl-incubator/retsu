"""Configuration for Celery app."""

import redis

from celery import Celery

app = Celery(
    "retsu",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

LOG_FORMAT_PREFIX = "[%(asctime)s: %(levelname)s/%(processName)s]"

app.conf.update(
    broker_url="redis://localhost:6379/0",
    result_backend="redis://localhost:6379/0",
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
    host="localhost",
    port=6379,
    db=0,
    ssl=False,
)


try:
    print("Pinging Redis...")
    redis_client.ping()
    print("Redis connection is working.")
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    exit(1)
