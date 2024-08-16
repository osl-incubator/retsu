"""Tests for retsu package."""

from __future__ import annotations

from typing import Generator

import celery
import pytest

from retsu import Process
from retsu.celery import SingleCeleryProcess

from .celery_tasks import task_sleep, task_sum


class MyResultTask(SingleCeleryProcess):
    """Process for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        x = kwargs.get("x")
        y = kwargs.get("y")
        task_id = kwargs.get("task_id")
        return [task_sum.s(x, y, task_id)]


class MyTimestampTask(SingleCeleryProcess):
    """Process for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        seconds = kwargs.get("seconds")
        task_id = kwargs.get("task_id")
        return [task_sleep.s(seconds, task_id)]


@pytest.fixture
def task_result() -> Generator[Process, None, None]:
    """Create a fixture for MyResultTask."""
    process = MyResultTask()
    process.start()
    yield process
    process.stop()


@pytest.fixture
def task_timestamp() -> Generator[Process, None, None]:
    """Create a fixture for MyResultTask."""
    process = MyTimestampTask()
    process.start()
    yield process
    process.stop()


class TestSingleCeleryProcess:
    """TestSingleCeleryProcess."""

    def test_serial_result(self, task_result: Process) -> None:
        """Run simple test for a serial process."""
        results: dict[str, int] = {}

        process = task_result

        for i in range(10):
            task_id = process.request(x=i, y=i)
            results[task_id] = i + i

        for task_id, expected in results.items():
            result = process.result.get(task_id, timeout=10)[0]
            assert (
                result == expected
            ), f"Expected Result: {expected}, Actual Result: {result}"

    def test_serial_timestamp(self, task_timestamp: Process) -> None:
        """Run simple test for a serial process."""
        results: list[tuple[str, int]] = []

        process = task_timestamp

        for sleep_time in range(5, 1, -1):
            task_id = process.request(seconds=sleep_time)
            results.append((task_id, 0))

        # gather results
        for i, (task_id, _) in enumerate(results):
            results[i] = (task_id, process.result.get(task_id, timeout=10))

        # check results
        previous_timestamp = results[0][1]
        for _, current_timestamp in results[1:]:
            assert current_timestamp > previous_timestamp, (
                f"Previous timestamp: {previous_timestamp}, "
                f"Current timestamp: {current_timestamp}"
            )
            previous_timestamp = current_timestamp
