"""Redis connection configuration helpers."""

from __future__ import annotations

import os

from typing import Union

from public import public


@public
def get_redis_queue_config() -> dict[str, Union[str, int]]:
    """Get Redis Queue parameters from the environment."""
    redis_host: str = os.getenv("RETSU_REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("RETSU_REDIS_PORT", 6379))
    redis_db: int = int(os.getenv("RETSU_REDIS_DB", 0))

    return {"host": redis_host, "port": redis_port, "db": redis_db}
