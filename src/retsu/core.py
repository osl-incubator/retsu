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
        self.result = ResultTask(result_path)
        self.queue_in = mp.Queue()

        self.process = mp.Process(target=self.run)
        self.process.start()


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
        raise Exception("Task not implemented yet.")

    def run(self):
        raise Exception("Task not implemented yet.")


class SequentialTask(Task):
    def __init__(self, result_path: Path) -> None:
        self.result = ResultTask(result_path)
        self.queue_in = mp.Queue()
        # self.queue_out = mp.Queue()

        self.process = mp.Process(target=self.run)
        self.process.start()


    def run(self):
        while True:
            data = self.queue_in.get()
            self.task(
                *data["args"],
                task_id=data["task_id"],
                **data["kwargs"],
            )
