"""Functions for handling queues and their configurations."""

from __future__ import annotations

import os
import pickle
import time

from abc import abstractmethod
from typing import Any, Union

import redis

from public import public


@public
def get_redis_queue_config() -> dict[str, Union[str, int]]:
    """Get Redis Queue parameters from the environment."""
    redis_host: str = os.getenv("RETSU_REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("RETSU_REDIS_PORT", 6379))
    redis_db: int = int(os.getenv("RETSU_REDIS_DB", 0))

    return {"host": redis_host, "port": redis_port, "db": redis_db}


@public
class BaseRetsuQueue:
    """Base Queue class."""

    def __init__(self, name: str) -> None:
        """Initialize BaseRetsuQueue."""
        self.name = name

    @abstractmethod
    def put(self, data: Any) -> None:
        """Put data into the end of the queue."""
        ...

    @abstractmethod
    def get(self) -> Any:
        """Get the next data from the queue."""
        ...


@public
class RedisRetsuQueue(BaseRetsuQueue):
    """RedisRetsuQueue class."""

    def __init__(self, name: str) -> None:
        """Initialize RedisRetsuQueue."""
        super().__init__(name)
        self._client = redis.Redis(
            **get_redis_queue_config(),  # type: ignore
            decode_responses=False,
        )

    def put(self, data: Any) -> None:
        """Put data into the end of the queue."""
        self._client.rpush(self.name, pickle.dumps(data))

    def get(self) -> Any:
        """Get the next data from the queue."""
        while True:
            data = self._client.lpop(self.name)
            if data is None:
                time.sleep(0.1)
                continue

            return pickle.loads(data)  # type: ignore
