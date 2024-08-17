"""Retsu results classes with async support."""

from __future__ import annotations

import asyncio
import pickle

from datetime import datetime
from typing import Any, Callable, Optional, cast

try:
    # Python 3.12+
    from typing import Unpack  # type: ignore[attr-defined]
except ImportError:
    # < Python 3.12
    from typing_extensions import Unpack

from public import public
from redis import asyncio as aioredis  # Import the asyncio version of redis

from retsu.queues import get_redis_queue_config


class ProcessMetadataManagerAsync:
    """Manage process metadata asynchronously."""

    def __init__(self, client: aioredis.Redis):
        """Initialize ProcessMetadataManagerAsync."""
        self.client = client
        self.step = StepMetadataManagerAsync(self.client)

    async def get_all(self, task_id: str) -> dict[str, bytes]:
        """Get the entire metadata for a given process asynchronously."""
        result = await self.client.hgetall(f"process:{task_id}:metadata")
        return cast(dict[str, bytes], result)

    async def get(self, task_id: str, attribute: str) -> bytes:
        """Get a specific metadata attr for a given process asynchronously."""
        result = await self.client.hget(
            f"process:{task_id}:metadata", attribute
        )
        return cast(bytes, result)

    async def create(self, task_id: str, metadata: dict[str, Any]) -> None:
        """Create an initial metadata for given process asynchronously."""
        await self.client.hset(f"process:{task_id}:metadata", mapping=metadata)

    async def update(self, task_id: str, attribute: str, value: Any) -> None:
        """Update the value of given attr for a given process in async."""
        await self.client.hset(f"process:{task_id}:metadata", attribute, value)
        await self.client.hset(
            f"process:{task_id}:metadata",
            "updated_at",
            datetime.now().isoformat(),
        )


class StepMetadataManagerAsync:
    """Manage metadata for steps of a process asynchronously."""

    def __init__(self, redis_client: aioredis.Redis):
        """Initialize StepMetadataManagerAsync."""
        self.client = redis_client

    async def get_all(self, task_id: str, step_id: str) -> dict[str, bytes]:
        """Get the metadata for a given process and step asynchronously."""
        result = await self.client.hgetall(f"process:{task_id}:step:{step_id}")
        return cast(dict[str, bytes], result)

    async def get(self, task_id: str, step_id: str, attribute: str) -> bytes:
        """Get the value of a given attr for a given process+step in async."""
        result = await self.client.hget(
            f"process:{task_id}:step:{step_id}", attribute
        )
        return cast(bytes, result)

    async def create(
        self, task_id: str, step_id: str, metadata: dict[str, Any]
    ) -> None:
        """Create an initial metadata for given process+step in async."""
        await self.client.hset(
            f"process:{task_id}:step:{step_id}", mapping=metadata
        )

    async def update(
        self, task_id: str, step_id: str, attribute: str, value: Any
    ) -> None:
        """Update the value of given attr for a given process+step async."""
        if attribute == "status" and value not in ["started", "completed"]:
            raise Exception("Status should be started or completed.")

        await self.client.hset(
            f"process:{task_id}:step:{step_id}", attribute, value
        )
        await self.client.hset(
            f"process:{task_id}:step:{step_id}",
            "updated_at",
            datetime.now().isoformat(),
        )


@public
class ResultProcessManagerAsync:
    """Manage the result and metadata from tasks asynchronously."""

    def __init__(
        self, host: str = "localhost", port: int = 6379, db: int = 0
    ) -> None:
        """Initialize ResultProcessManagerAsync."""
        self.client = aioredis.Redis(
            host=host, port=port, db=db, decode_responses=False
        )
        self.metadata = ProcessMetadataManagerAsync(self.client)

    async def get(self, task_id: str, timeout: Optional[int] = None) -> Any:
        """Get the result for a given process asynchronously."""
        time_step = 0.5
        if timeout:
            timeout_countdown = float(timeout)
            while await self.status(task_id) != "completed":
                await asyncio.sleep(time_step)
                timeout_countdown -= time_step
                if timeout_countdown <= 0:
                    status = await self.status(task_id)
                    raise Exception(
                        "Timeout(get): Process result is not ready yet. "
                        f"Process status: {status}"
                    )

        elif await self.status(task_id) != "completed":
            status = await self.status(task_id)
            raise Exception(
                "Timeout(get): Process result is not ready yet. "
                f"Process status: {status}"
            )
        result = await self.metadata.get(task_id, "result")
        return pickle.loads(result) if result else result

    async def load(self, task_id: str) -> dict[str, Any]:
        """Load the whole metadata for a given process asynchronously."""
        return await self.metadata.get_all(task_id)

    async def create(self, task_id: str, metadata: dict[str, Any]) -> None:
        """Create a new metadata for a given process asynchronously."""
        await self.metadata.create(task_id, metadata)

    async def save(self, task_id: str, result: Any) -> None:
        """Save the result for a given process asynchronously."""
        await self.metadata.update(task_id, "result", pickle.dumps(result))

    async def status(self, task_id: str) -> str:
        """Get the status for a given process asynchronously."""
        status = await self.metadata.get(task_id, "status")
        return status.decode("utf8")


@public
def create_result_task_manager_async() -> ResultProcessManagerAsync:
    """Create a ResultProcessManagerAsync from the environment vars."""
    return ResultProcessManagerAsync(**get_redis_queue_config())  # type: ignore


@public
def track_step_async(
    task_metadata: ProcessMetadataManagerAsync,
) -> Callable[..., Any]:
    """Decorate a function with ProcessMetadataManagerAsync."""

    def decorator(task_func: Callable[..., Any]) -> Callable[..., Any]:
        """Return a decorator for the given process."""

        async def wrapper(
            *args: Unpack[Any], **kwargs: Unpack[dict[str, Any]]
        ) -> Any:
            """Wrap a function for registering the process metadata async."""
            task_id = kwargs["task_id"]
            step_id = kwargs.get("step_id", task_func.__name__)

            step_metadata = task_metadata.step

            await step_metadata.update(task_id, step_id, "status", "started")
            result = await task_func(*args, **kwargs)
            await step_metadata.update(task_id, step_id, "status", "completed")
            result_pickled = pickle.dumps(result)
            await step_metadata.update(
                task_id, step_id, "result", result_pickled
            )
            return result

        return wrapper

    return decorator
