"""Local thread executor for admission mode."""

from __future__ import annotations

import pickle
import threading

from retsu.backends.base import Backend
from retsu.state import JobRecord, JobStatus
from retsu.task import _LOCAL_FUNCTIONS


class LocalExecutor:
    """Run admitted jobs in local daemon threads."""

    name = "local"

    def __init__(self, backend: Backend) -> None:
        """Initialize the executor."""
        self.backend = backend

    def dispatch(self, job: JobRecord, lease_id: str, owner_id: str) -> None:
        """Dispatch a job in a local thread."""
        thread = threading.Thread(
            target=self._run,
            args=(job, lease_id, owner_id),
            name=f"retsu-local-{job.id}",
            daemon=True,
        )
        thread.start()

    def _run(self, job: JobRecord, lease_id: str, owner_id: str) -> None:
        try:
            self.backend.update_job_status(job.id, JobStatus.RUNNING)
            func = _LOCAL_FUNCTIONS[job.id]
            result = func(*job.args, **job.kwargs)
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
