"""Retsu tasks with celery."""

from __future__ import annotations

from typing import Any, Optional

import celery

from celery import chain, chord, group
from public import public

from retsu.core import MultiProcess, SingleProcess


class CeleryTask:
    """Celery Task class."""

    def task(self, *args, task_id: str, **kwargs) -> Any:  # type: ignore
        """Define the task to be executed."""
        chord_tasks, chord_callback = self.get_chord_tasks(
            *args,
            task_id=task_id,
            **kwargs,
        )
        group_tasks = self.get_group_tasks(
            *args,
            task_id=task_id,
            **kwargs,
        )
        chain_tasks = self.get_chain_tasks(
            *args,
            task_id=task_id,
            **kwargs,
        )

        # start the tasks
        if chord_tasks:
            workflow_chord = chord(chord_tasks, chord_callback)
            promise_chord = workflow_chord.apply_async()

        if group_tasks:
            workflow_group = group(group_tasks)
            promise_group = workflow_group.apply_async()

        if chain_tasks:
            workflow_chain = chain(chord_tasks)
            promise_chain = workflow_chain.apply_async()

        # wait for the tasks
        results: list[Any] = []
        if chord_tasks:
            chord_result = promise_chord.get()
            if isinstance(chord_result, list):
                results.extend(chord_result)
            else:
                results.append(chord_result)

        if group_tasks:
            group_result = promise_group.get()
            if isinstance(group_result, list):
                results.extend(group_result)
            else:
                results.append(group_result)

        if chain_tasks:
            chain_result = promise_chain.get()

            if isinstance(chain_result, list):
                results.extend(chain_result)
            else:
                results.append(chain_result)

        return results

    def get_chord_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> tuple[list[celery.Signature], Optional[celery.Signature]]:
        """
        Run tasks with chord.

        Return
        ------
        tuple:
            list of tasks for the chord, and the task to be used as a callback
        """
        chord_tasks: list[celery.Signature] = []
        callback_task = None
        return (chord_tasks, callback_task)

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """
        Run tasks with group.

        Return
        ------
        tuple:
            list of tasks for the chord, and the task to be used as a callback
        """
        group_tasks: list[celery.Signature] = []
        return group_tasks

    def get_chain_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Run tasks with chain."""
        chain_tasks: list[celery.Signature] = []
        return chain_tasks


@public
class MultiCeleryProcess(CeleryTask, MultiProcess):
    """Multi Task for Celery."""

    ...


@public
class SingleCeleryProcess(CeleryTask, SingleProcess):
    """Single Task for Celery."""

    ...
