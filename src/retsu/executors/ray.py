"""Ray executor for admission mode."""

from __future__ import annotations

import pickle
import threading

from importlib import import_module
from typing import Any, cast

from retsu.backends.base import Backend
from retsu.state import JobRecord, JobStatus
from retsu.task import _LOCAL_FUNCTIONS


class RayExecutor:
    """Dispatch admitted jobs to Ray."""

    name = "ray"

    def __init__(self, backend: Backend, ray_module: Any = None) -> None:
        """Initialize the executor."""
        self.backend = backend
        self.ray = ray_module or import_module("ray")

    def dispatch(self, job: JobRecord, lease_id: str, owner_id: str) -> None:
        """Dispatch a job to Ray and track completion in a local thread."""
        self.backend.update_job_status(job.id, JobStatus.RUNNING)
        func = _LOCAL_FUNCTIONS[job.id]
        remote_target = cast(
            Any,
            func
            if callable(getattr(func, "remote", None))
            else self.ray.remote(func),
        )
        object_ref = remote_target.remote(*job.args, **job.kwargs)
        thread = threading.Thread(
            target=self._wait_for_result,
            args=(job, lease_id, owner_id, object_ref),
            name=f"retsu-ray-{job.id}",
            daemon=True,
        )
        thread.start()

    def _wait_for_result(
        self,
        job: JobRecord,
        lease_id: str,
        owner_id: str,
        object_ref: Any,
    ) -> None:
        try:
            result = self.ray.get(object_ref)
            self.backend.update_job_status(
                job.id,
                JobStatus.SUCCEEDED,
                result_blob=pickle.dumps(result),
            )
        except Exception as exc:
            self.backend.update_job_status(
                job.id,
                JobStatus.FAILED,
                error=str(exc),
            )
        finally:
            self.backend.release(lease_id, owner_id)
