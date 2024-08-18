"""Test celery tasks with a wrapup."""

from __future__ import annotations

import time

from celery import Task

from .celery_tasks import (
    task_random_get_time,
    task_sequence_get_time,
)


def test_task_random_get_time() -> None:
    """Test task_random_get_time."""
    results: dict[int, float] = {}
    tasks: list[Task] = []
    start_time = time.time()

    for i in range(10):
        task_promise = task_random_get_time.s(
            request_id=i, start_time=start_time
        )
        tasks.append(task_promise.apply_async())

    for i in range(10):
        task = tasks[i]
        task_id, result = task.get(timeout=10)
        assert i == task_id
        results[task_id] = result

    previous_time = results[0]
    previous_id = 0
    tol = 0.2
    for i in range(10):
        current_time = results[i]
        diff = abs(current_time - previous_time)
        # print(
        #     f"task {previous_id}-{i}, diff: {diff}, "
        #     f"expected: {diff_expected}"
        # )
        assert diff - tol < 5, f"[EE] Task {previous_id}-{i}"
        previous_time = current_time
        previous_id = i


def test_task_sequence_get_time() -> None:
    """Test task_sequence_get_time."""
    results: dict[int, float] = {}
    tasks: list[Task] = []
    start_time = time.time()

    for i in range(10):
        task_promise = task_sequence_get_time.s(
            request_id=i, start_time=start_time
        )
        tasks.append(task_promise.apply_async())

    for i in range(10):
        task = tasks[i]
        task_id, result = task.get(timeout=10)
        assert i == task_id
        results[task_id] = result

    diffs = (
        0,  # 0 -> 0
        0,  # 0 -> 1
        1,  # 1 -> 2
        0,  # 2 -> 3
        1,  # 3 -> 4
        0,  # 4 -> 5
        1,  # 5 -> 6
        0,  # 6 -> 7
        1,  # 7 -> 8
        0,  # 8 -> 9
    )

    previous_time = results[0]
    previous_id = 0
    tol = 0.2
    for i in range(10):
        current_time = results[i]
        diff = current_time - previous_time
        diff_expected = diffs[i]
        # print(
        #     f"task {previous_id}-{i}, diff: {diff}, "
        #     f"expected: {diff_expected}"
        # )
        assert diff >= diff_expected - tol, f"[EE] Task {previous_id}-{i}"
        assert diff <= diff_expected + tol, f"[EE] Task {previous_id}-{i}"
        previous_time = current_time
        previous_id = i
