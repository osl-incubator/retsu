"""Plugin for integrating with django."""

from django.apps import AppConfig
from django.core.signals import request_finished

from retsu.core import TaskManager


def create_app_config(
    manager: TaskManager, app_name: str = "myapp"
) -> AppConfig:
    """Create a django app config class."""

    class RetsuAppConfig(AppConfig):
        """RetsuAppConfig class."""

        name = app_name

        def ready(self) -> None:
            """Start the task manager when the django app is ready."""
            manager.start()
            request_finished.connect(self.stop_multiprocessing)

        def stop_multiprocessing(self, **kwargs) -> None:
            manager.stop()

    return RetsuAppConfig
