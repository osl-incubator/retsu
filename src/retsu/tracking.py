"""Retsu tracking classes."""

from __future__ import annotations

import os
import pickle

from datetime import datetime
from time import sleep
from typing import Any

import redis


class TaskMetadataManager:
    def __init__(self, client: redis.Redis):
        self.client = client
        self.step = StepMetadataManager(self.client)

    def get_all(self, task_id: str) -> dict[str, Any]:
        return self.client.hgetall(f"task:{task_id}:metadata")

    def get(self, task_id: str, attribute: str) -> Any:
        return self.client.hget(f"task:{task_id}:metadata", attribute)

    def set(self, task_id: str, metadata: dict[str, Any]) -> None:
        self.client.hset(f"task:{task_id}:metadata", mapping=metadata)

    def update(self, task_id: str, attribute: str, value: Any) -> None:
        self.client.hset(f"task:{task_id}:metadata", attribute, value)
        self.client.hset(
            f"task:{task_id}:metadata",
            "updated_at",
            datetime.now().isoformat(),
        )


class StepMetadataManager:
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client

    def get_all(self, task_id: str, step_id: str) -> dict[str, Any]:
        return self.client.hgetall(f"task:{task_id}:step:{step_id}")

    def get(self, task_id: str, step_id: str, attribute: str) -> Any:
        return self.client.hget(f"task:{task_id}:step:{step_id}", attribute)

    def create(
        self, task_id: str, step_id: str, metadata: dict[str, Any]
    ) -> None:
        self.client.hset(f"task:{task_id}:step:{step_id}", mapping=metadata)

    def update(
        self, task_id: str, step_id: str, attribute: str, value: Any
    ) -> None:
        if attribute == "status" and value not in ["started", "completed"]:
            raise Exception("Status should be started or completed.")

        self.client.hset(f"task:{task_id}:step:{step_id}", attribute, value)
        self.client.hset(
            f"task:{task_id}:step:{step_id}",
            "updated_at",
            datetime.now().isoformat(),
        )


class ResultTaskManager:
    def __init__(self, host="localhost", port=6379, db=0):
        self.client = redis.Redis(
            host=host, port=port, db=db, decode_responses=False
        )
        self.metadata = TaskMetadataManager(self.client)

    def get(self, task_id: str, timeout: Optional[int] = None) -> Any:
        time_step = 0.5
        if timeout:
            while self.status(task_id) != "completed":
                sleep(time_step)
                timeout -= time_step
                if timeout <= 0:
                    status = self.status(task_id)
                    raise Exception(
                        "Timeout(get): Task result is not ready yet. "
                        f"Task status: {status}"
                    )
        result = self.metadata.get(task_id, "result")
        return pickle.loads(result) if result else result

    def load(self, task_id: str) -> dict[str, Any]:
        return self.metadata.get_all(task_id)

    def create(self, task_id: str, metadata: dict[str, Any]) -> None:
        self.metadata.set(task_id, metadata)

    def save(self, task_id: str, result: Any) -> None:
        self.metadata.update(task_id, "result", pickle.dumps(result))

    def status(self, task_id: str) -> str:
        status = self.metadata.get(task_id, "status")
        return status.decode("utf8")


def create_result_task_manager() -> ResultTaskManager:
    redis_host: str = os.getenv("RETSU_REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("RETSU_REDIS_PORT", 6379))
    redis_db: int = int(os.getenv("RETSU_REDIS_DB", 0))

    return ResultTaskManager(host=redis_host, port=redis_port, db=redis_db)


def track_task(redis_manager: TaskMetadataManager):
    def decorator(task_func: Callable[(Any,), Any]):
        def wrapper(self, *args, **kwargs):
            task_id = kwargs["task_id"]
            step_id = kwargs.get("step_id", task_func.__name__)
            redis_manager.update(task_id, step_id, "status", "started")
            result = task_func(self, *args, **kwargs)
            redis_manager.update(task_id, step_id, "status", "completed")
            redis_manager.set(task_id, step_id, "result", result)
            return result

        return wrapper

    return decorator
