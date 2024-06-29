"""Retsu results classes."""

from __future__ import annotations

import pickle

from datetime import datetime
from time import sleep
from typing import Any, Callable, Optional, cast

try:
    # Python 3.12+
    from typing import Unpack  # type: ignore[attr-defined]
except ImportError:
    # < Python 3.12
    from typing_extensions import Unpack


import redis

from public import public

from retsu.queues import get_redis_queue_config


class TaskMetadataManager:
    """Manage task metadata."""

    def __init__(self, client: redis.Redis):
        """Initialize TaskMetadataManager."""
        self.client = client
        self.step = StepMetadataManager(self.client)

    def get_all(self, task_id: str) -> dict[str, bytes]:
        """Get the entire metadata for a given task."""
        result = self.client.hgetall(f"task:{task_id}:metadata")
        return cast(dict[str, bytes], result)

    def get(self, task_id: str, attribute: str) -> bytes:
        """Get a specific metadata attribute for a given task."""
        result = self.client.hget(f"task:{task_id}:metadata", attribute)
        return cast(bytes, result)

    def create(self, task_id: str, metadata: dict[str, Any]) -> None:
        """Create an initial metadata for given task."""
        self.client.hset(f"task:{task_id}:metadata", mapping=metadata)

    def update(self, task_id: str, attribute: str, value: Any) -> None:
        """Update the value of given attribute for a given task."""
        self.client.hset(f"task:{task_id}:metadata", attribute, value)
        self.client.hset(
            f"task:{task_id}:metadata",
            "updated_at",
            datetime.now().isoformat(),
        )


class StepMetadataManager:
    """Manage metadata for steps of a task."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize StepMetadataManager."""
        self.client = redis_client

    def get_all(self, task_id: str, step_id: str) -> dict[str, bytes]:
        """Get the whole metadata for a given task and step."""
        result = self.client.hgetall(f"task:{task_id}:step:{step_id}")
        return cast(dict[str, bytes], result)

    def get(self, task_id: str, step_id: str, attribute: str) -> bytes:
        """Get the value of a given attribute for a given task and step."""
        result = self.client.hget(f"task:{task_id}:step:{step_id}", attribute)
        return cast(bytes, result)

    def create(
        self, task_id: str, step_id: str, metadata: dict[str, Any]
    ) -> None:
        """Create an initial metadata for given task and step."""
        self.client.hset(f"task:{task_id}:step:{step_id}", mapping=metadata)

    def update(
        self, task_id: str, step_id: str, attribute: str, value: Any
    ) -> None:
        """Update the value of given attribute for a given task and step."""
        if attribute == "status" and value not in ["started", "completed"]:
            raise Exception("Status should be started or completed.")

        self.client.hset(f"task:{task_id}:step:{step_id}", attribute, value)
        self.client.hset(
            f"task:{task_id}:step:{step_id}",
            "updated_at",
            datetime.now().isoformat(),
        )


@public
class ResultProcessManager:
    """Manage the result and metadata from tasks."""

    def __init__(
        self, host: str = "localhost", port: int = 6379, db: int = 0
    ) -> None:
        """Initialize ResultProcessManager."""
        self.client = redis.Redis(
            host=host, port=port, db=db, decode_responses=False
        )
        self.metadata = TaskMetadataManager(self.client)

    def get(self, task_id: str, timeout: Optional[int] = None) -> Any:
        """Get the result for a given task."""
        time_step = 0.5
        if timeout:
            timeout_countdown = float(timeout)
            while self.status(task_id) != "completed":
                sleep(time_step)
                timeout_countdown -= time_step
                if timeout_countdown <= 0:
                    status = self.status(task_id)
                    raise Exception(
                        "Timeout(get): Task result is not ready yet. "
                        f"Task status: {status}"
                    )

        elif self.status(task_id) != "completed":
            status = self.status(task_id)
            raise Exception(
                "Timeout(get): Task result is not ready yet. "
                f"Task status: {status}"
            )
        result = self.metadata.get(task_id, "result")
        return pickle.loads(result) if result else result

    def load(self, task_id: str) -> dict[str, Any]:
        """Load the whole metadata for a given task."""
        return self.metadata.get_all(task_id)

    def create(self, task_id: str, metadata: dict[str, Any]) -> None:
        """Create a new metadata for a given task."""
        self.metadata.create(task_id, metadata)

    def save(self, task_id: str, result: Any) -> None:
        """Save the result for a given task."""
        self.metadata.update(task_id, "result", pickle.dumps(result))

    def status(self, task_id: str) -> str:
        """Get the status for a given task."""
        status = self.metadata.get(task_id, "status")
        return status.decode("utf8")


@public
def create_result_task_manager() -> ResultProcessManager:
    """Create a ResultProcessManager with parameters from the environment."""
    return ResultProcessManager(**get_redis_queue_config())  # type: ignore


@public
def track_step(task_metadata: TaskMetadataManager) -> Callable[..., Any]:
    """Decorate a function with TaskMetadataManager."""

    def decorator(task_func: Callable[..., Any]) -> Callable[..., Any]:
        """Return a decorator for the given task."""

        def wrapper(
            *args: Unpack[Any], **kwargs: Unpack[dict[str, Any]]
        ) -> Any:
            """Wrap a function for registering the task metadata."""
            task_id = kwargs["task_id"]
            step_id = kwargs.get("step_id", task_func.__name__)

            step_metadata = task_metadata.step

            step_metadata.update(task_id, step_id, "status", "started")
            result = task_func(*args, **kwargs)
            step_metadata.update(task_id, step_id, "status", "completed")
            result_pickled = pickle.dumps(result)
            step_metadata.update(task_id, step_id, "result", result_pickled)
            return result

        return wrapper

    return decorator
