"""Tests for retsu package."""

from __future__ import annotations

from typing import Generator

import pytest

from retsu.celery import SerialCeleryTask

from .celery_tasks import task_sum


class MyResultTask(SerialCeleryTask):
    """Task for the test."""

    def get_chord_tasks(self, *args, **kwargs) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        x = kwargs.get("x")
        y = kwargs.get("y")
        task_id = kwargs.get("task_id")
        return (
            [task_sum.s(x, y, task_id)],
            None,
        )


class MyTimestampTask(SerialCeleryTask):
    """Task for the test."""

    def get_chord_tasks(self, *args, **kwargs) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        seconds = kwargs.get("seconds")
        task_id = kwargs.get("task_id")
        return (
            [task_sum.s(x, y, task_id, task_id)],
            None,
        )


@pytest.fixture
def task_result() -> Generator[Task, None, None]:
    """Create a fixture for MyResultTask."""
    task = MyResultTask()
    task.start()
    yield task
    task.stop()


@pytest.fixture
def task_timestamp() -> Generator[Task, None, None]:
    """Create a fixture for MyResultTask."""
    task = MyTimestampTask()
    task.start()
    yield task
    task.stop()


class TestSerialTask:
    """TestSerialTask."""

    def test_serial_result(self, task_result: Task) -> None:
        """Run simple test for a serial task."""
        results: dict[str, int] = {}

        task = task_result

        for i in range(10):
            task_id = task.request(a=i, b=i)
            results[task_id] = i + i

        for task_id, expected in results.items():
            result = task.result.get(task_id, timeout=2)
            assert (
                result == expected
            ), f"Expected Result: {expected}, Actual Result: {result}"

    def test_serial_timestamp(self, task_timestamp: Task) -> None:
        """Run simple test for a serial task."""
        results: list[tuple[str, int]] = []

        task = task_timestamp

        for sleep_time in range(5, 1, -1):
            task_id = task.request(sleep=sleep_time)
            results.append((task_id, 0))

        # gather results
        for i, (task_id, _) in enumerate(results):
            results[i] = (task_id, task.result.get(task_id, timeout=10))

        # check results
        previous_timestamp = results[0][1]
        for _, current_timestamp in results[1:]:
            assert current_timestamp > previous_timestamp, (
                f"Previous timestamp: {previous_timestamp}, "
                f"Current timestamp: {current_timestamp}"
            )
            previous_timestamp = current_timestamp
