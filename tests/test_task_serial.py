"""Tests for retsu package."""

from retsu import SerialTask


class MyTask(SerialTask):
    """Task for the test."""

    def task(self, *args, task_id: str, **kwargs) -> None:  # type: ignore
        """Task that sum the given 2 numbers."""
        a = kwargs.pop("a", 0)
        b = kwargs.pop("b", 0)
        return a + b


class SetupTask:
    """Setup the task workflow for the test."""

    @classmethod
    def setup_class(cls) -> None:
        """Set the class configuration for the test."""
        cls.task = MyTask()
        cls.task.start()

    @classmethod
    def teardown_class(cls) -> None:
        """Set the class teardown step for the test."""
        cls.task.stop()


class TestSerialTask(SetupTask):
    """TestSerialTask."""

    def test_serial_simple(self):
        """Run simple test for a serial task."""
        results: dict[str, int] = {}

        for i in range(10):
            task_id = self.task.request(a=i, b=i)
            results[task_id] = i + i

        for task_id, expected in results.items():
            result = self.task.result.get(task_id, timeout=2)
            assert (
                result == expected
            ), f"Expected Result: {expected}, Actual Result: {result}"
