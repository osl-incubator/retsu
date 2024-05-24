"""

See Also
--------

- https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods

"""
from __future__ import annotations

from time import sleep

from retsu import ParallelTask, SerialTask


class MySerialTask1(SerialTask):

    def request(self, a: int, b: int) -> str:
        return super().request(a=a, b=b)

    def task(self, a: int, b: int, task_id: str) -> None:
        sleep(a + b)

        self.result.save(
            task_id=task_id,
            result=a + b
        )
        print(f"{self.__class__.__name__} Done ({task_id})")


class MySerialTask2(MySerialTask1):
    pass


class MyParallelTask1(ParallelTask):

    def __init__(self, result_path: str, workers: int=1) -> None:
        super().__init__(result_path, workers=3)

    def request(self, a: int, b: int) -> str:
        return super().request(a=a, b=b)

    def task(self, a: int, b: int, task_id: str) -> None:
        sleep(a + b)

        self.result.save(
            task_id=task_id,
            result=a + b
        )
        print(f"{self.__class__.__name__} Done ({task_id})")


class MyParallelTask2(MyParallelTask1):
    pass
