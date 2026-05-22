"""Retsu."""

from importlib import metadata as importlib_metadata

from retsu.config import (
    configure,
    get_backend,
    get_config,
    set_backend,
)
from retsu.exceptions import (
    ResourceAcquireTimeout,
    ResourceDefinitionMissing,
    ResourceEstimationError,
    ResourceUnavailable,
    RetsuBackendUnavailable,
    RetsuError,
)
from retsu.executors.ray import RayExecutor
from retsu.integrations.celery import celery_guard
from retsu.integrations.ray import ray_guard, ray_task
from retsu.resources import (
    AcquireResult,
    CapacityDefinition,
    CleanupResult,
    ResourceRequest,
    ResourceSpec,
    UsageItem,
    UsageSnapshot,
)
from retsu.scheduler import Scheduler
from retsu.state import (
    JobRecord,
    JobStatus,
    LeaseRecord,
)
from retsu.task import (
    JobHandle,
    acquire,
    acquire_with_policy,
    cleanup_expired_leases,
    define_concurrency,
    define_resource,
    get_usage,
    guard,
    limit,
    list_leases,
    submit,
)


def get_version() -> str:
    """Return the program version."""
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "0.4.0"  # semantic-release


version = get_version()

__version__ = version
__author__ = "Ivan Ogasawara"
__email__ = "ivan.ogasawara@gmail.com"

__all__ = [
    "AcquireResult",
    "CapacityDefinition",
    "CleanupResult",
    "JobHandle",
    "JobRecord",
    "JobStatus",
    "LeaseRecord",
    "RayExecutor",
    "ResourceAcquireTimeout",
    "ResourceDefinitionMissing",
    "ResourceEstimationError",
    "ResourceRequest",
    "ResourceSpec",
    "ResourceUnavailable",
    "RetsuBackendUnavailable",
    "RetsuError",
    "Scheduler",
    "UsageItem",
    "UsageSnapshot",
    "__author__",
    "__email__",
    "__version__",
    "acquire",
    "acquire_with_policy",
    "celery_guard",
    "cleanup_expired_leases",
    "configure",
    "define_concurrency",
    "define_resource",
    "get_backend",
    "get_config",
    "get_usage",
    "guard",
    "limit",
    "list_leases",
    "ray_guard",
    "ray_task",
    "set_backend",
    "submit",
]
