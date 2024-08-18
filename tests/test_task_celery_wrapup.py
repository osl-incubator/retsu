"""Test celery tasks with a wrapup."""

from __future__ import annotations

from celery import Task, group

from .celery_tasks import task_get_time


def test_task_get_time() -> None:
    """Test task_get_time."""
    results: dict[int, float] = {}
    tasks: list[Task] = []

    for i in range(1, 11):
        promise = group([task_get_time.s(request_id=i)])
        breakpoint()
        tasks.append(promise.apply_async())

    for task in tasks:
        task_id, result = task.get(timeout=10)
        results[task_id] = result

    diffs = (
        (0, 0),  # 0, 0
        (0, 1),  # 0, 1
        (1, 2),  # 1, 2
        (0, 1),  # 2, 3
        (1, 2),  # 3, 4
        (0, 1),  # 4, 5
        (1, 2),  # 5, 6
        (0, 1),  # 6, 7
        (1, 2),  # 7, 8
        (0, 1),  # 8, 9
    )

    previous_time = results[0]
    for i in sorted(results.keys()):
        result = results[i]
        current_time = result
        assert current_time - previous_time > diffs[i][0]
        assert current_time - previous_time < diffs[i][1]
        previous_time = current_time
