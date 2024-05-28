"""Retsu tasks with celery."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

import celery

from celery import Celery, chain, chord

from retsu.core import ParallelTask, SerialTask


class CeleryTask:
    def task(self, *args, task_id: str, **kwargs) -> None:
        """Define the task to be executed."""
        chord_tasks, chord_callback = self.get_chord_tasks(
            *args, task_id=task_id, **kwargs
        )
        chain_tasks = self.get_chain_tasks(*args, task_id=task_id, **kwargs)

        if chord_tasks:
            _chord = chord(chord_tasks)
            workflow_chord = (
                _chord(chord_callback) if chord_callback else _chord()
            )
            workflow_chord.apply_async()

        if chain_tasks:
            workflow_chain = chain(chord_tasks)()
            workflow_chain.apply_async()

    def get_chord_tasks(
        self, *args, **kwargs
    ) -> tuple[
        list[celery.local.PromiseProxy], Optional[celery.local.PromiseProxy]
    ]:
        """
        Run tasks with chord.

        Return
        ------
        tuple:
            list of tasks for the chord, and the task to be used as a callback
        """
        chord_tasks: list[celery.local.PromiseProxy] = []
        callback_task = None
        return (chord_tasks, callback_task)

    def get_chain_tasks(
        self, *args, **kwargs
    ) -> list[celery.local.PromiseProxy]:
        """Run tasks with chain."""
        chain_tasks: list[celery.local.PromiseProxy] = []
        return chain_tasks


class ParallelCeleryTask(CeleryTask, ParallelTask):
    def __init__(
        self,
        result_path: Path,
        workers: int = 1,
        app: Celery = Celery(),
    ) -> None:
        super().__init__(result_path, workers)
        self.app = app


class SerialCeleryTask(CeleryTask, SerialTask):
    def __init__(
        self,
        result_path: Path,
        workers: int = 1,
        app: Celery = Celery(),
    ) -> None:
        super().__init__(result_path, workers)
        self.app = app
