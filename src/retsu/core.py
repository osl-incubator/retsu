"""Retsu core classes."""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import warnings

from abc import abstractmethod
from pathlib import Path
from typing import Any, Optional, cast
from uuid import uuid4

from public import public


class ResultTask:
    """Result from a task."""

    def __init__(self) -> None:
        """Initialize ResultTask."""
        self.result_path = Path(
            os.getenv("RETSU_RESULT_PATH", "/tmp/retsu/results")
        )
        os.makedirs(self.result_path, exist_ok=True)

    @public
    def save(self, task_id: str, result: Any) -> None:
        """Save the result in a file."""
        with open(self.result_path / f"{task_id}.json", "w") as f:
            json.dump(
                {"task_id": task_id, "result": result},
                f,
                indent=2,
            )

    @public
    def load(self, task_id: str) -> dict[str, Any]:
        """Load the result from a file."""
        result_file = self.result_path / f"{task_id}.json"
        if not result_file.exists():
            raise Exception(f"File {result_file} doesn't exist.")
        with open(result_file, "r") as f:
            return cast(dict[str, Any], json.load(f))

    @public
    def status(self, task_id: str) -> bool:
        """Return if the result for a given task was already stored."""
        result_file = self.result_path / f"{task_id}.json"
        return result_file.exists()

    @public
    def get(self, task_id: str) -> Any:
        """Return the result for given task."""
        if not self.status(task_id):
            return {"status": False, "message": "Result not ready."}

        return self.load(task_id)


@public
class Task:
    """Main class for handling a task."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize a task object."""
        self.active = True
        self.workers = workers
        self.result = ResultTask()
        self.queue_in: mp.Queue[Any] = mp.Queue()
        self.processes: list[mp.Process] = []

    @public
    def get_result(self, task_id: str) -> Any:
        """Get the result for given task id."""
        return self.result.get(task_id)

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

        self.queue_in.close()
        self.queue_in.join_thread()

    @public
    def request(self, *args, **kwargs) -> str:  # type: ignore
        """Feed the queue with data from the request for the task."""
        key = uuid4().hex
        print(
            {
                "task_id": key,
                "args": args,
                "kwargs": kwargs,
            }
        )
        self.queue_in.put(
            {
                "task_id": key,
                "args": args,
                "kwargs": kwargs,
            },
            block=False,
        )
        return key

    @abstractmethod
    def task(self, *args, task_id: str, **kwargs) -> None:  # type: ignore
        """Define the task to be executed."""
        raise Exception("`task` not implemented yet.")

    def prepare_task(self, data: Any) -> None:
        """Call the task with the necessary arguments."""
        self.task(
            *data["args"],
            task_id=data["task_id"],
            **data["kwargs"],
        )

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


class SerialTask(Task):
    """Serial Task class."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize a serial task object."""
        if workers != 1:
            warnings.warn(
                "SerialTask should have just 1 worker. "
                "Switching automatically to 1 ..."
            )
            workers = 1
        super().__init__(workers=workers)


class ParallelTask(Task):
    """Initialize a parallel task object."""

    def __init__(self, workers: int = 1) -> None:
        """Initialize ParallelTask."""
        if workers <= 1:
            raise Exception("ParallelTask should have more than 1 worker.")

        super().__init__(workers=workers)


class TaskManager:
    """Manage tasks."""

    tasks: dict[str, Task]

    def __init__(self) -> None:
        """Create a list of retsu tasks."""
        self.tasks: dict[str, Task] = {}

    @public
    def get_task(self, name: str) -> Optional[Task]:
        """Get a task with the given name."""
        return self.tasks.get(name)

    @public
    def start(self) -> None:
        """Start tasks."""
        for task_name, task in self.tasks.items():
            print(f"Task `{task_name}` is starting ...")
            task.start()

    @public
    def stop(self) -> None:
        """Stop tasks."""
        for task_name, task in self.tasks.items():
            print(f"Task `{task_name}` is stopping ...")
            task.stop()
