"""
# celeryconfig.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'

# Optional: Define task routes if needed
task_queues = {
    'default': {
        'exchange': 'tasks',
        'routing_key': 'task.default',
    },
    'queue_a1': {
        'exchange': 'tasks',
        'routing_key': 'task.a1',
    },
    'queue_a2': {
        'exchange': 'tasks',
        'routing_key': 'task.a2',
    },
    'queue_b': {
        'exchange': 'tasks',
        'routing_key': 'task.b',
    },
    'queue_c': {
        'exchange': 'tasks',
        'routing_key': 'task.c',
    },
}

task_routes = {
    'tasks.task_a1': {'queue': 'queue_a1'},
    'tasks.task_a2': {'queue': 'queue_a2'},
    'tasks.task_b': {'queue': 'queue_b'},
    'tasks.task_c': {'queue': 'queue_c'},
}
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from celery import Celery

from retsu.core import ParallelTask, SerialTask


class ParallelCeleryTask(ParallelTask):
    def __init__(
        self,
        result_path: Path,
        workers: int=1,
        name: str="retsu",
        broker_url: str='valkey://localhost:6379/0',
        result_backend: str='valkey://localhost:6379/0'
    ) -> None:
        super().__init__(result_path, workers)
        self.name = name
        self.app = Celery(self.name)
        self.broker_url = 'valkey://localhost:6379/0'
        self.result_backend = 'valkey://localhost:6379/0'


class SerialCeleryTask(ParallelTask):
    def __init__(
        self,
        result_path: Path,
        workers: int=1,
        name: str="retsu",
        broker_url: str='valkey://localhost:6379/0',
        result_backend: str='valkey://localhost:6379/0'
    ) -> None:
        super().__init__(result_path, workers)
        self.name = name
        self.app = Celery(self.name)
        self.broker_url = 'valkey://localhost:6379/0'
        self.result_backend = 'valkey://localhost:6379/0'
