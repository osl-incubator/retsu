"""Retsu core classes."""

from __future__ import annotations

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
class Task:
    """Main class for handling a task."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize a task object."""
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

    @public
    def start(self) -> None:
        """Start processes."""
        for _ in range(self.workers):
            p = mp.Process(target=self.run)
            p.start()
            self.processes.append(p)

    @public
    def stop(self) -> None:
        """Stop processes."""
        if not self.active:
            return

        self.active = False

        for i in range(self.workers):
            self.queue_in.put(None)

        for i in range(self.workers):
            p = self.processes[i]
            p.join()

        # self.queue_in.close()
        # self.queue_in.join_thread()

    @public
    def request(self, *args, **kwargs) -> str:  # type: ignore
        """Feed the queue with data from the request for the task."""
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
    def task(self, *args, task_id: str, **kwargs) -> Any:  # type: ignore
        """Define the task to be executed."""
        raise Exception("`task` not implemented yet.")

    def prepare_task(self, data: dict[str, Any]) -> None:
        """Call the task with the necessary arguments."""
        task_id = data.pop("task_id")
        self.result.metadata.update(task_id, "status", "running")
        result = self.task(
            *data["args"],
            task_id=task_id,
            **data["kwargs"],
        )
        self.result.save(task_id, result)
        self.result.metadata.update(task_id, "status", "completed")

    @public
    def run(self) -> None:
        """Run the task with data from the queue."""
        while self.active:
            data = self.queue_in.get()
            if data is None:
                print("Process terminated.")
                self.active = False
                return
            self.prepare_task(data)


class SingleProcess(Task):
    """Single Task class."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize a serial task object."""
        if workers != 1:
            warnings.warn(
                "SingleProcess should have just 1 worker. "
                "Switching automatically to 1 ..."
            )
            workers = 1
        super().__init__(workers=workers)


class MultiProcess(Task):
    """Initialize a parallel task object."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize MultiProcess."""
        if workers <= 1:
            raise Exception("MultiProcess should have more than 1 worker.")

        super().__init__(workers=workers)


class ProcessManager:
    """Manage tasks."""

    tasks: dict[str, Task]

    def __init__(self) -> None:
        """Create a list of retsu tasks."""
        self.tasks: dict[str, Task] = {}

    @public
    def create_tasks(self) -> None:
        """Get a task with the given name."""
        if self.tasks:
            return

        warnings.warn(
            "`self.tasks` is empty. Override `create_tasks` and create "
            "`self.tasks` with the proper tasks."
        )

    @public
    def get_task(self, name: str) -> Optional[Task]:
        """Get a task with the given name."""
        return self.tasks.get(name)

    @public
    def start(self) -> None:
        """Start tasks."""
        if not self.tasks:
            self.create_tasks()

        for task_name, task in self.tasks.items():
            print(f"Task `{task_name}` is starting ...")
            task.start()

    @public
    def stop(self) -> None:
        """Stop tasks."""
        if not self.tasks:
            warnings.warn("There is no tasks to be stopped.")
            return

        for task_name, task in self.tasks.items():
            print(f"Task `{task_name}` is stopping ...")
            task.stop()
