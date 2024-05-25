"""

See Also
--------

- https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods

"""
from __future__ import annotations

import multiprocessing as mp
import os

from time import sleep

import redis

from celery import Celery, chain, chord
from retsu import ParallelTask, SerialTask

app = Celery(
    'retsu',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s[%(task_id)s]: %(message)s",
    task_annotations={'*': {'rate_limit': '10/s'}},
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=30 * 60,
    worker_redirect_stdouts_level='DEBUG'
)

redis_client = redis.Redis(
    host='localhost',
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


class MySerialTask1(SerialTask):

    def request(self, a: int, b: int) -> str:
        return super().request(a=a, b=b)

    def task(self, a: int, b: int, task_id: str) -> None:
        print("main task executed ...")
        sleep(a + b)

        workflow = chord([
            self.task_a1.s(self, a, b, task_id),
            self.task_a2.s(self, task_id),
        ])(self.final_task.s(self, task_id))

        workflow.apply_async()

        print(f"{self.__class__.__name__} Done ({task_id})")

    @app.task
    def task_a1(a: int, b: int, task_id: str):
        print("running task a1")
        result = a + b
        redis_client.set(f"result-{task_id}", result)
        return result

    @app.task
    def task_a2(task_id: str):
        print("running task a2")
        result = redis_client.get(f"result-{task_id}")
        return result

    @app.task
    def final_task(results, task_id: str):
        print("running final task")

        result = redis_client.get(f"result-{task_id}")
        final_result = f"Final result: {result}"
        print(final_result)

        self.result.save(
            task_id=task_id,
            result=final_result
        )

        return final_result



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
