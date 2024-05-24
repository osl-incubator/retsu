"""

See Also
--------

- https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods

"""
from __future__ import annotations

from time import sleep

from retsu import SequentialTask


class TaskA1(SequentialTask):

    def request(self, a: int, b: int) -> str:
        return super().request(a=a, b=b)

    def task(self, a: int, b: int, task_id: str) -> None:
        sleep(5)

        self.result.save(
            task_id=task_id,
            result=a + b
        )
        print(f"task done ({task_id})")
