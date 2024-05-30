"""Tests for retsu package."""

from retsu import SerialTask


class MyTask(SerialTask):
    def task(self, *args, task_id: str, **kwargs) -> None:  # type: ignore
        a = kwargs.pop("a", 0)
        b = kwargs.pop("b", 0)
        return a + b


class TestManager:
    # @classmethod
    # def class_setup(cls) -> None:
    #     self.task_manager = TaskManager()

    # @classmethod
    # def class_teardown(cls) -> None:
    #     self.task_manager.stop
    ...


class TestSerialTask:
    """TestSerialTask."""

    def test_serial(self):
        task = MyTask()
        task.start()

        results: dict[str, int] = {}

        for i in range(10):
            task_id = task.request(a=i, b=i)
            results[task_id] = i + i

        for task_id, expected in results.items():
            result = task.result.get(task_id, timeout=2)
            assert (
                result == expected
            ), f"Expected Result: {expected}, Actual Result: {result}"

        task.stop()
