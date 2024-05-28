"""My retsu tasks."""

from __future__ import annotations

from time import sleep

import celery
import redis

from celery import Celery
from retsu import ResultTask, TaskManager
from retsu.celery import ParallelCeleryTask, SerialCeleryTask
from settings import RESULTS_PATH

app = Celery(
    "retsu",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

LOG_FORMAT_PREFIX = "[%(asctime)s: %(levelname)s/%(processName)s]"

app.conf.update(
    broker_url="redis://localhost:6379/0",
    result_backend="redis://localhost:6379/0",
    worker_log_format=f"{LOG_FORMAT_PREFIX} %(message)s",
    worker_task_log_format=(
        f"{LOG_FORMAT_PREFIX} %(task_name)s[%(task_id)s]: %(message)s"
    ),
    task_annotations={"*": {"rate_limit": "10/s"}},
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=30 * 60,
    worker_redirect_stdouts_level="DEBUG",
)

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    ssl=False,
)


try:
    print("Pinging Redis...")
    redis_client.ping()
    print("Redis connection is working.")
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    exit(1)


class MySerialTask1(SerialCeleryTask):
    """MySerialTask1."""

    def request(self, a: int, b: int) -> str:
        """Receive the request for processing."""
        return super().request(a=a, b=b)

    def get_chord_tasks(
        self, a: int, b: int, task_id: str
    ) -> tuple[list[celery.local.PromiseProxy], celery.local.PromiseProxy]:
        """Define the list of tasks for celery chord."""
        return (
            [
                self.task_a1.s(a, b, task_id),
                self.task_a2.s(task_id),
            ],
            self.final_task.s(task_id),
        )

    @app.task
    @staticmethod
    def task_a1(a: int, b: int, task_id: str) -> int:  # type: ignore
        """Define the task_a1."""
        sleep(a + b)
        print("running task a1")
        result = a + b
        redis_client.set(f"result-{task_id}", result)
        return result

    @app.task
    @staticmethod
    def task_a2(task_id: str) -> int:  # type: ignore
        """Define the task_a2."""
        print("running task a2")
        result = redis_client.get(f"result-{task_id}")
        return result

    @app.task
    @staticmethod
    def final_task(results, task_id: str) -> int:  # type: ignore
        """Define the final_task."""
        print("running final task")

        result = redis_client.get(f"result-{task_id}")
        final_result = f"Final result: {result}"
        print(final_result)

        task_result = ResultTask()

        task_result.save(task_id=task_id, result=final_result)

        return final_result


class MyParallelTask1(ParallelCeleryTask):
    """MyParallelTask1."""

    def request(self, a: int, b: int) -> str:
        """Receive the request for processing."""
        return super().request(a=a, b=b)

    def get_chord_tasks(
        self, a: int, b: int, task_id: str
    ) -> list[celery.local.PromiseProxy]:
        """Define the list of tasks for celery chord."""
        return (
            [
                self.task_a1.s(a, b, task_id),
                self.task_a2.s(task_id),
            ],
            self.final_task.s(task_id),
        )

    @app.task
    @staticmethod
    def task_a1(a: int, b: int, task_id: str) -> int:  # type: ignore
        """Define the task_a1."""
        sleep(a + b)
        print("running task a1")
        result = a + b
        redis_client.set(f"result-{task_id}", result)
        return result

    @app.task
    @staticmethod
    def task_a2(task_id: str) -> int:  # type: ignore
        """Define the task_a2."""
        print("running task a2")
        result = redis_client.get(f"result-{task_id}")
        return result

    @app.task
    @staticmethod
    def final_task(results, task_id: str) -> int:  # type: ignore
        """Define the final_task."""
        print("running final task")

        result = redis_client.get(f"result-{task_id}")
        final_result = f"Final result: {result}"
        print(final_result)

        task_result = ResultTask()

        task_result.save(task_id=task_id, result=final_result)

        return final_result


class MyTaskManager(TaskManager):
    """MyTaskManager."""

    def __init__(self) -> None:
        """Create a list of retsu tasks."""
        self.tasks = {
            "serial": MySerialTask1(RESULTS_PATH),
            "parallel": MyParallelTask1(RESULTS_PATH, workers=2),
        }
