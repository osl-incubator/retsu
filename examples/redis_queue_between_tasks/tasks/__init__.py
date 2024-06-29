"""Tasks for the example."""

from retsu import ProcessManager

from .parallel import MyMultiProcess1
from .serial import MySingleProcess1


class MyProcessManager(ProcessManager):
    """MyProcessManager."""

    def __init__(self) -> None:
        """Create a list of retsu tasks."""
        self.tasks = {
            "serial": MySingleProcess1(),
            "parallel": MyMultiProcess1(workers=2),
        }
