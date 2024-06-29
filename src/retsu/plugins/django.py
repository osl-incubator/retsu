"""Plugin for integrating with django."""

from __future__ import annotations

from typing import Type

from django.apps import AppConfig
from django.core.signals import request_finished

from retsu.core import ProcessManager


def create_app_config(
    manager: ProcessManager, app_name: str = "myapp"
) -> Type[AppConfig]:
    """Create a django app config class."""

    class RetsuAppConfig(AppConfig):
        """RetsuAppConfig class."""

        name = app_name

        def ready(self) -> None:
            """Start the task manager when the django app is ready."""
            manager.start()
            request_finished.connect(self.stop_multiprocessing)

        def stop_multiprocessing(self, **kwargs) -> None:  # type: ignore
            assert kwargs is not None
            manager.stop()

    return RetsuAppConfig
