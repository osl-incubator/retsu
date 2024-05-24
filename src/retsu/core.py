"""

See Also
--------

- https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods

"""
from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import os

from pathlib import Path
from typing import Any
from uuid import uuid4


class ResultTask:
    def __init__(self, result_path: Path) -> None:
        self.result_path = result_path

    def save(self, task_id: str, result: Any) -> None:
        with open(self.result_path / f"{task_id}.json", "w") as f:
            json.dump(
                {"task_id": task_id, "result": result},
                f,
                indent=2,
            )

    def load(self, task_id: str) -> dict[str, Any]:
        result_file = self.result_path / f"{task_id}.json"
        if not result_file.exists():
            raise Exception(
                f"File {result_file} doesn't exist."
            )
        with open(result_file, "r") as f:
            return json.load(f)

    def status(self, task_id: str) -> bool:
        result_file = self.result_path / f"{task_id}.json"
        return result_file.exists()

    def get_result(self, task_id: str) -> Any:
        if not self.status(task_id):
            return {"status": False, "message": "Result not ready."}

        return self.result.load(task_id)


class Task:
    def __init__(self, result_path: Path) -> None:
        self.active = True
        self.result = ResultTask(result_path)
        self.queue_in = mp.Queue()

        self.process = mp.Process(target=self.run)
        self.process.start()

    def __del__(self) -> None:
        """
        Avoid terminating processes.

        Using the Process.terminate method to stop a process is liable to
        cause any shared resources (such as locks, semaphores, pipes and
        queues) currently being used by the process to become broken or
        unavailable to other processes.

        Therefore it is probably best to only consider using Process.terminate
        on processes which never use any shared resources.
        """
        self.terminate()

    def terminate(self) -> None:
        if not self.active:
            return

        self.active = False
        self.queue_in.put(None)
        self.process.join()


    def request(self, *args, **kwargs) -> str:
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
            block=False
        )
        return key

    def task(self, *args, task_id: str, **kwargs) -> None:
        raise Exception("`task` not implemented yet.")

    def prepare_task(self, data: Any) -> None:
        raise Exception("`prepare_task` not implemented yet.")

    def run(self):
        while self.active:
            data = self.queue_in.get()
            if data is None:
                print("process terminated.")
                break
            self.prepare_task(data)



class SequentialTask(Task):
    def __init__(self, result_path: Path) -> None:
        super().__init__(result_path)

    def prepare_task(self, data: Any) -> None:
        self.task(
            *data["args"],
            task_id=data["task_id"],
            **data["kwargs"],
        )
