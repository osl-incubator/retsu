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
import warnings

from abc import abstractmethod
from pathlib import Path
from typing import Any
from uuid import uuid4

from public import public


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

    def get(self, task_id: str) -> Any:
        if not self.status(task_id):
            return {"status": False, "message": "Result not ready."}

        return self.load(task_id)


@public
class Task:
    def __init__(self, result_path: Path, workers: int=1) -> None:
        self.active = True
        self.workers = workers
        self.result = ResultTask(result_path)
        self.queue_in = mp.Queue()
        self.processes: list[Process] = []

        for _ in range(self.workers):
            p = mp.Process(target=self.run)
            p.start()
            self.processes.append(p)

    @public
    def get_result(self, task_id: str) -> Any:
        return self.result.get(task_id)

    @public
    def terminate(self) -> None:
        if not self.active:
            return

        self.active = False

        for i in range(self.workers):
            self.queue_in.put(None)
            p = self.processes[i]
            p.join()

        self.queue_in.close()
        self.queue_in.join_thread()

    @public
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

    @abstractmethod
    def task(self, *args, task_id: str, **kwargs) -> None:
        raise Exception("`task` not implemented yet.")

    def prepare_task(self, data: Any) -> None:
        self.task(
            *data["args"],
            task_id=data["task_id"],
            **data["kwargs"],
        )


    @public
    def run(self):
        while self.active:
            data = self.queue_in.get()
            if data is None:
                print("Process terminated.")
                self.active = False
                return
            self.prepare_task(data)



class SerialTask(Task):
    def __init__(self, result_path: Path, workers: int=1) -> None:
        if workers != 1:
            warnings.warn(
                "SerialTask should have just 1 worker. "
                "Switching automatically to 1 ..."
            )
            workers = 1
        super().__init__(result_path, workers=workers)


class ParallelTask(Task):
    def __init__(self, result_path: Path, workers: int=1) -> None:
        if workers <= 1:
            raise Exception("ParallelTask should have more than 1 worker.")

        super().__init__(result_path, workers=workers)
