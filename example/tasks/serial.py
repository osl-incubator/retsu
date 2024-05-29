"""My retsu tasks."""

from __future__ import annotations

from time import sleep

import celery

from config import app, redis_client
from retsu import ResultTask
from retsu.celery import SerialCeleryTask


@app.task
def task_serial_a1(a: int, b: int, task_id: str) -> int:  # type: ignore
    """Define the task_a1."""
    sleep(a + b)
    print("running task a1")
    result = a + b
    redis_client.set(f"result-{task_id}", result)
    return result


@app.task
def task_serial_a2(task_id: str) -> int:  # type: ignore
    """Define the task_a2."""
    print("running task a2")
    result = redis_client.get(f"result-{task_id}")
    return result


@app.task
def task_serial_final(results, task_id: str) -> int:  # type: ignore
    """Define the final_task."""
    print("running final task")

    result = redis_client.get(f"result-{task_id}")
    final_result = f"Final result: {result}"
    print(final_result)

    task_result = ResultTask()

    task_result.save(task_id=task_id, result=final_result)

    return final_result


class MySerialTask1(SerialCeleryTask):
    """MySerialTask1."""

    def request(self, a: int, b: int) -> str:
        """Receive the request for processing."""
        return super().request(a=a, b=b)

    def get_chord_tasks(
        self, a: int, b: int, task_id: str
    ) -> tuple[list[celery.Signature], celery.Signature]:
        """Define the list of tasks for celery chord."""
        return (
            [
                task_serial_a1.s(a, b, task_id),
                task_serial_a2.s(task_id),
            ],
            task_serial_final.s(task_id),
        )
