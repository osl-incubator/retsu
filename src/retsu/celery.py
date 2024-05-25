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


class CeleryTask:
    def __init__(
        self,
        name: str="retsu",
        broker_url: str='valkey://localhost:6379/0',
        result_backend: str='valkey://localhost:6379/0'
    ) -> None:
        self.name = name
        self.app = Celery(self.name)
        self.broker_url = 'valkey://localhost:6379/0'
        self.result_backend = 'valkey://localhost:6379/0'
        self.task_queues = {}
        self.task_routes = {}

    def task(self, fn: Callable[(Any,), Any]) -> Callable[(Any,), Any]:
        @wraps
        def _task(*args, **kwargs) -> Any:
            return fn(*args, **kwargs)

        _module = f"{fn.__module__}."
        _class = f"{fn.__self.__.__name__}." if hasattr(fn, "__self__") else ""
        _func = f"{fn.__name___}"
        key = f'{_module}{_class}{_func}'

        queue_key = f"queue.{key}"
        task_key = f"task.{key}"

        self.task_queues[queue_key] = {
            'exchange': 'tasks',
            'routing_key': task_key,
        }
        self.task_routes[task_key] = {'queue': queue_key}
        return _task
