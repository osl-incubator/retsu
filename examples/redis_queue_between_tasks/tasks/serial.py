"""My retsu tasks."""

from __future__ import annotations

from time import sleep

import celery

from retsu.celery import SerialCeleryTask

from .config import app, redis_client


@app.task
def task_serial_a_plus_b(a: int, b: int, task_id: str) -> int:  # type: ignore
    """Define the task_serial_a_plus_b."""
    sleep(a + b)
    print("running task_serial_a_plus_b")
    result = a + b
    redis_client.set(f"serial-result-a-plus-b-{task_id}", result)
    return result


@app.task
def task_serial_result_plus_10(task_id: str) -> int:  # type: ignore
    """Define the task_serial_result_plus_10."""
    print("running task_serial_result_plus_10")
    result = redis_client.get(f"serial-result-a-plus-b-{task_id}")
    redis_client.set(f"serial-result-plus-10-{task_id}", result + 10)
    return result


@app.task
def task_serial_result_square(results, task_id: str) -> int:  # type: ignore
    """Define the task_serial_result_square."""
    print("running task_serial_result_square")
    result = redis_client.get(f"serial-result-plus-10-{task_id}")
    return result**2


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
                task_serial_a_plus_b.s(a, b, task_id),
                task_serial_result_plus_10.s(task_id),
            ],
            task_serial_result_square.s(task_id),
        )
