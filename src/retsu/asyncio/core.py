"""Async core module."""

import asyncio
import logging

from abc import abstractmethod
from datetime import datetime
from typing import Any
from uuid import uuid4

from redis import asyncio as aioredis

from retsu.asyncio.queues import RedisRetsuAsyncQueue
from retsu.asyncio.results import (
    ResultProcessManagerAsync,
    create_result_task_manager_async,
)
from retsu.core import Process
from retsu.queues import get_redis_queue_config


class AsyncProcess(Process):
    """Main class for handling an async process."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize an async process object."""
        _klass = self.__class__
        queue_in_name = f"{_klass.__module__}.{_klass.__qualname__}"

        self._client = aioredis.Redis(**get_redis_queue_config())
        self.active = True
        self.workers = workers
        self.result: ResultProcessManagerAsync = (
            create_result_task_manager_async()
        )
        self.queue_in = RedisRetsuAsyncQueue(queue_in_name)
        self.tasks = []

    async def start(self) -> None:
        """Start async tasks."""
        logging.info(f"Starting async process {self.__class__.__name__}")
        for _ in range(self.workers):
            task = asyncio.create_task(self.run())
            self.tasks.append(task)

    async def stop(self) -> None:
        """Stop async tasks."""
        logging.info(f"Stopping async process {self.__class__.__name__}")
        self.active = False
        for task in self.tasks:
            task.cancel()
            try:
                await (
                    task
                )  # Ensure the task is properly awaited before moving on
            except asyncio.CancelledError:
                logging.info(f"Task {task.get_name()} has been cancelled.")

    async def request(self, *args, **kwargs) -> str:  # type: ignore
        """Feed the queue with data from the request for the process."""
        task_id = uuid4().hex
        metadata = {
            "status": "starting",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        await self.result.create(task_id, metadata)  # Ensure this is awaited
        await self.queue_in.put(
            {
                "task_id": task_id,
                "args": args,
                "kwargs": kwargs,
            }
        )
        return task_id

    @abstractmethod
    async def process(self, *args, task_id: str, **kwargs) -> Any:  # type: ignore
        """Define the async process to be executed."""
        raise Exception("`process` not implemented yet.")

    async def prepare_process(self, data: dict[str, Any]) -> None:
        """Call the process with the necessary arguments."""
        task_id = data.pop("task_id")
        await self.result.metadata.update(task_id, "status", "running")
        result = await self.process(
            *data["args"],
            task_id=task_id,
            **data["kwargs"],
        )
        await self.result.save(task_id, result)
        await self.result.metadata.update(task_id, "status", "completed")

    async def run(self) -> None:
        """Run the async process with data from the queue."""
        while self.active:
            try:
                data = await self.queue_in.get()
                await self.prepare_process(data)
            except asyncio.CancelledError:
                logging.info(
                    f"Task {asyncio.current_task().get_name()} cancelled."
                )
                break  # Break out of the loop if the task is canceled
            except Exception as e:
                logging.error(f"Error in process: {e}")
                break  # Break out of the loop on any other exceptions
