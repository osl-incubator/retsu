"""My retsu tasks."""

from __future__ import annotations

from time import sleep

import celery

from retsu.celery import MultiCeleryProcess

from .config import app, redis_client


@app.task
def task_parallel_a_plus_b(a: int, b: int, task_id: str) -> int:  # type: ignore
    """Define the task_parallel_a_plus_b."""
    sleep(a + b)
    print("running task_parallel_a_plus_b")
    result = a + b
    redis_client.set(f"parallel-result-a-plus-b-{task_id}", result)
    return result


@app.task
def task_parallel_result_plus_10(task_id: str) -> int:  # type: ignore
    """Define the task_parallel_result_plus_10."""
    print("running task_parallel_result_plus_10")
    result = None
    while result is None:
        result = redis_client.get(f"parallel-result-a-plus-b-{task_id}")
        sleep(1)

    final_result = int(result) + 10
    redis_client.set(f"parallel-result-plus-10-{task_id}", final_result)
    return final_result


@app.task
def task_parallel_result_square(results, task_id: str) -> int:  # type: ignore
    """Define the task_parallel_result_square."""
    print("running task_parallel_result_square")
    result = None
    while result is None:
        result = redis_client.get(f"parallel-result-plus-10-{task_id}")
        sleep(1)
    return int(result) ** 2


class MyMultiProcess1(MultiCeleryProcess):
    """MyMultiProcess1."""

    def request(self, a: int, b: int) -> str:
        """Receive the request for processing."""
        return super().request(a=a, b=b)

    def get_chord_tasks(
        self, a: int, b: int, task_id: str
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        return (
            [
                task_parallel_a_plus_b.s(a, b, task_id),
                task_parallel_result_plus_10.s(task_id),
            ],
            task_parallel_result_square.s(task_id),
        )
