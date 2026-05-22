"""Executor protocol for admission mode."""

from __future__ import annotations

from typing import Protocol

from retsu.state import JobRecord


class Executor(Protocol):
    """Dispatches admitted jobs."""

    name: str

    def dispatch(
        self, job: JobRecord, lease_id: str, owner_id: str
    ) -> None:
        """Dispatch a leased job."""

