"""Tests for retsu package."""

from __future__ import annotations

import celery
import pytest

from retsu.asyncio.celery import CeleryAsyncProcess
from retsu.asyncio.core import AsyncProcess

from .celery_tasks import task_sleep, task_sum


class MyResultTask(CeleryAsyncProcess):
    """Async Process for the test."""

    async def get_group_tasks(self, *args, **kwargs) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        x = kwargs.get("x")
        y = kwargs.get("y")
        task_id = kwargs.get("task_id")
        return [task_sum.s(x, y, task_id)]


class MyTimestampTask(CeleryAsyncProcess):
    """Async Process for the test."""

    async def get_group_tasks(self, *args, **kwargs) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        seconds = kwargs.get("seconds")
        task_id = kwargs.get("task_id")
        return [task_sleep.s(seconds, task_id)]


@pytest.fixture
async def task_result() -> AsyncProcess:
    """Create a fixture for MyResultTask."""
    process = MyResultTask(workers=2)
    await process.start()
    yield process
    await process.stop()


@pytest.fixture
async def task_timestamp() -> AsyncProcess:
    """Create a fixture for MyTimestampTask."""
    process = MyTimestampTask(workers=5)
    await process.start()
    yield process
    await process.stop()


@pytest.mark.asyncio
class TestMultiCeleryAsyncProcess:
    """TestMultiCeleryAsyncProcess."""

    async def test_multi_async_result(self, task_result: AsyncProcess) -> None:
        """Run simple test for a multi-process."""
        results: dict[str, int] = {}

        async for process in task_result:
            for i in range(10):
                task_id = await process.request(x=i, y=i)
                results[task_id] = i + i

            for task_id, expected in results.items():
                result = await process.result.get(task_id, timeout=10)
                assert (
                    result[0] == expected
                ), f"Expected Result: {expected}, Actual Result: {result}"


# note: it is not working as expected
# async def test_multi_async_timestamp(
#      self, task_timestamp: AsyncProcess
# ) -> None:
#     """Run simple test for a multi-process."""
#     results: list[tuple[str, int]] = []

#     async for process in task_timestamp:
#         for sleep_time in range(5, 1, -1):
#             task_id = await process.request(seconds=sleep_time * 1.5)
#             results.append((task_id, 0))

#         # Gather results
#         for i, (task_id, _) in enumerate(results):
#             results[i] = (
#               task_id, await process.result.get(task_id, timeout=10))
#         # Check results
#         previous_timestamp = results[0][1]
#         for _, current_timestamp in results[1:]:
#             assert current_timestamp < previous_timestamp, (
#                 f"Previous timestamp: {previous_timestamp}, "
#                 f"Current timestamp: {current_timestamp}"
#             )
#             previous_timestamp = current_timestamp
