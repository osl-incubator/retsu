"""Configuration used by pytest."""

from __future__ import annotations

import os
import subprocess
import time

from typing import Generator

import pytest


@pytest.fixture(autouse=True, scope="session")
def setup() -> Generator[None, None, None]:
    """Set up the services needed by the tests."""
    try:
        # # Run the `sugar build` command
        # subprocess.run(["sugar", "build"], check=True)
        # # Run the `sugar ext restart --options -d` command
        # subprocess.run(
        #     ["sugar", "ext", "restart", "--options", "-d"], check=True
        # )
        # # Sleep for 5 seconds
        # time.sleep(5)

        # Change directory to `tests/`
        os.chdir("tests/")

        # Start the Celery worker
        celery_process = subprocess.Popen(
            ["celery", "-A", "celery_tasks", "worker", "--loglevel=debug"]
        )

        time.sleep(5)

        # Change directory back to the original
        os.chdir("..")

        yield

    finally:
        # Teardown: Terminate the Celery worker
        celery_process.terminate()
        celery_process.wait()
        # subprocess.run(["sugar", "ext", "stop"], check=True)
