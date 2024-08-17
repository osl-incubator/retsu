"""Retsu tasks with celery."""

from __future__ import annotations

from typing import Any, Optional

import celery

from celery import chain, chord, group
from public import public

from retsu.asyncio.core import AsyncProcess


@public
class CeleryAsyncProcess(AsyncProcess):
    """Async Celery Process class."""

    async def process(self, *args, task_id: str, **kwargs) -> Any:
        """Define the async process to be executed."""
        chord_tasks, chord_callback = await self.get_chord_tasks(
            *args,
            task_id=task_id,
            **kwargs,
        )
        group_tasks = await self.get_group_tasks(
            *args,
            task_id=task_id,
            **kwargs,
        )
        chain_tasks = await self.get_chain_tasks(
            *args,
            task_id=task_id,
            **kwargs,
        )

        # Start the tasks asynchronously
        results = []
        if chord_tasks:
            workflow_chord = chord(chord_tasks, chord_callback)
            promise_chord = workflow_chord.apply_async()
            results.extend(promise_chord.get())

        if group_tasks:
            workflow_group = group(group_tasks)
            promise_group = workflow_group.apply_async()
            results.extend(promise_group.get())

        if chain_tasks:
            workflow_chain = chain(chain_tasks)
            promise_chain = workflow_chain.apply_async()
            results.extend(promise_chain.get())

        return results

    async def get_chord_tasks(  # type: ignore
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

    async def get_group_tasks(  # type: ignore
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

    async def get_chain_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Run tasks with chain."""
        chain_tasks: list[celery.Signature] = []
        return chain_tasks
