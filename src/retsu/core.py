"""Retsu core classes."""

from __future__ import annotations

import logging
import multiprocessing as mp
import warnings

from abc import abstractmethod
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import redis

from public import public

from retsu.queues import RedisRetsuQueue, get_redis_queue_config
from retsu.results import ResultProcessManager, create_result_task_manager


@public
class Process:
    """Main class for handling a process."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize a process object."""
        _klass = self.__class__
        queue_in_name = f"{_klass.__module__}.{_klass.__qualname__}"

        self._client = redis.Redis(
            **get_redis_queue_config(),  # type: ignore
            decode_responses=False,
        )
        self.active = True
        self.workers = workers
        self.result: ResultProcessManager = create_result_task_manager()
        self.queue_in = RedisRetsuQueue(queue_in_name)
        self.processes: list[mp.Process] = []

    def __del__(self) -> None:
        """Close queues and process."""
        logging.info(f"Deleting process {self.__class__.__name__}")
        self.stop()

    @public
    def start(self) -> None:
        """Start processes."""
        logging.info(f"Starting process {self.__class__.__name__}")
        for _ in range(self.workers):
            p = mp.Process(target=self.run)
            p.start()
            self.processes.append(p)

    @public
    def stop(self) -> None:
        """Stop processes."""
        logging.info(f"Stopping process {self.__class__.__name__}")
        if not self.active:
            return

        self.active = False

        for i in range(self.workers):
            p = self.processes[i]
            p.terminate()
            p.join(timeout=1)

    @public
    def request(self, *args, **kwargs) -> str:  # type: ignore
        """Feed the queue with data from the request for the process."""
        task_id = uuid4().hex
        metadata = {
            "status": "starting",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.result.create(task_id, metadata)
        self.queue_in.put(
            {
                "task_id": task_id,
                "args": args,
                "kwargs": kwargs,
            },
        )
        return task_id

    @abstractmethod
    def process(self, *args, task_id: str, **kwargs) -> Any:  # type: ignore
        """Define the process to be executed."""
        raise Exception("`process` not implemented yet.")

    def prepare_process(self, data: dict[str, Any]) -> None:
        """Call the process with the necessary arguments."""
        task_id = data.pop("task_id")
        self.result.metadata.update(task_id, "status", "running")
        result = self.process(
            *data["args"],
            task_id=task_id,
            **data["kwargs"],
        )
        self.result.save(task_id, result)
        self.result.metadata.update(task_id, "status", "completed")

    @public
    def run(self) -> None:
        """Run the process with data from the queue."""
        while self.active:
            data = self.queue_in.get()
            self.prepare_process(data)


class SingleProcess(Process):
    """Single Process class."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize a serial process object."""
        if workers != 1:
            warnings.warn(
                "SingleProcess should have just 1 worker. "
                "Switching automatically to 1 ..."
            )
            workers = 1
        super().__init__(workers=workers)


class MultiProcess(Process):
    """Initialize a parallel process object."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize MultiProcess."""
        if workers <= 1:
            raise Exception("MultiProcess should have more than 1 worker.")

        super().__init__(workers=workers)


class ProcessManager:
    """Manage tasks."""

    tasks: dict[str, Process]

    def __init__(self) -> None:
        """Create a list of retsu tasks."""
        self.tasks: dict[str, Process] = {}

    @public
    def create_processes(self) -> None:
        """Get a process with the given name."""
        if self.tasks:
            return

        warnings.warn(
            "`self.tasks` is empty. Override `create_processes` and create "
            "`self.tasks` with the proper tasks."
        )

    @public
    def get_process(self, name: str) -> Optional[Process]:
        """Get a process with the given name."""
        return self.tasks.get(name)

    @public
    def start(self) -> None:
        """Start tasks."""
        if not self.tasks:
            self.create_processes()

        for task_name, process in self.tasks.items():
            process.start()

    @public
    def stop(self) -> None:
        """Stop tasks."""
        if not self.tasks:
            warnings.warn("There is no tasks to be stopped.")
            return

        for task_name, process in self.tasks.items():
            process.stop()
