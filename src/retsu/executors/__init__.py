"""Admission-mode executors."""

from retsu.executors.local import LocalExecutor
from retsu.executors.ray import RayExecutor

__all__ = ["LocalExecutor", "RayExecutor"]
