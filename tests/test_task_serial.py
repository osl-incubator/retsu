"""Tests for retsu package."""

from __future__ import annotations

from datetime import datetime
from time import sleep
from typing import Any, Generator

import pytest

from retsu import Process, SingleProcess


class MyResultTask(SingleProcess):
    """Process for the test."""

    def task(self, *args, task_id: str, **kwargs) -> Any:  # type: ignore
        """Return the sum of the given 2 numbers."""
        a = kwargs.pop("a", 0)
        b = kwargs.pop("b", 0)
        result = a + b
        return result


class MyTimestampTask(SingleProcess):
    """Process for the test."""

    def task(self, *args, task_id: str, **kwargs) -> Any:  # type: ignore
        """Sleep the given seconds, and return the current timestamp."""
        sleep_time = kwargs.pop("sleep", 0)
        sleep(sleep_time)
        return datetime.now().timestamp()


@pytest.fixture
def task_result() -> Generator[Process, None, None]:
    """Create a fixture for MyResultTask."""
    task = MyResultTask()
    task.start()
    yield task
    task.stop()


@pytest.fixture
def task_timestamp() -> Generator[Process, None, None]:
    """Create a fixture for MyResultTask."""
    task = MyTimestampTask()
    task.start()
    yield task
    task.stop()


class TestSingleProcess:
    """TestSingleProcess."""

    def test_serial_result(self, task_result: Process) -> None:
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

    def test_serial_timestamp(self, task_timestamp: Process) -> None:
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
