"""Functions for handling queues and their configurations."""

from __future__ import annotations

import asyncio
import pickle

from abc import abstractmethod
from typing import Any

from public import public
from redis import asyncio as aioredis

from retsu.queues import BaseRetsuQueue, get_redis_queue_config


@public
class BaseRetsuAsyncQueue(BaseRetsuQueue):
    """Base Queue class."""

    def __init__(self, name: str) -> None:
        """Initialize BaseRetsuQueue."""
        self.name = name

    @abstractmethod
    async def put(self, data: Any) -> None:
        """Put data into the end of the queue."""
        ...

    @abstractmethod
    async def get(self) -> Any:
        """Get the next data from the queue."""
        ...


@public
class RedisRetsuAsyncQueue(BaseRetsuQueue):
    """Async RedisRetsuQueue class."""

    def __init__(self, name: str) -> None:
        """Initialize RedisRetsuQueue with async Redis client."""
        super().__init__(name)
        self._client = aioredis.Redis(
            **get_redis_queue_config(),  # Async Redis client configuration
            decode_responses=False,
        )

    async def put(self, data: Any) -> None:
        """Put data into the end of the queue asynchronously."""
        await self._client.rpush(self.name, pickle.dumps(data))

    async def get(self) -> Any:
        """Get the next data from the queue asynchronously."""
        while True:
            data = await self._client.lpop(self.name)
            if data is None:
                await asyncio.sleep(0.1)  # Non-blocking sleep for 100ms
                continue

            return pickle.loads(data)
