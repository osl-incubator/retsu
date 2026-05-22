"""Lease object and heartbeat support."""

from __future__ import annotations

import threading

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from retsu.backends.base import Backend
from retsu.resources import ResourceRequest


@dataclass
class Lease:
    """An acquired capacity lease."""

    id: str
    job_id: str
    owner_id: str
    request: ResourceRequest
    backend: Backend
    ttl_seconds: int

    def renew(self) -> None:
        """Renew the lease."""
        self.backend.renew(self.id, self.owner_id, self.ttl_seconds)

    def release(self) -> None:
        """Release the lease."""
        self.backend.release(self.id, self.owner_id)

    @contextmanager
    def heartbeat(self, interval_seconds: float) -> Iterator[None]:
        """Renew the lease periodically while the context is active."""
        stop = threading.Event()

        def run() -> None:
            while not stop.wait(interval_seconds):
                self.renew()

        thread = threading.Thread(
            target=run,
            name=f"retsu-heartbeat-{self.id}",
            daemon=True,
        )
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=max(interval_seconds, 0.1))
