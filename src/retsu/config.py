"""Global configuration for Retsu."""

from __future__ import annotations

import os

from dataclasses import dataclass
from typing import Literal, Optional

from retsu.backends.base import Backend
from retsu.backends.memory import MemoryBackend
from retsu.backends.redis import RedisBackend


@dataclass
class RetsuConfig:
    """Runtime configuration."""

    backend: str = "redis"
    redis_url: Optional[str] = None
    namespace: str = "default"
    default_ttl_seconds: int = 300
    default_acquire_timeout_seconds: Optional[float] = 60
    default_heartbeat_interval_seconds: float = 30
    default_wait_strategy: Literal["block", "fail", "retry"] = "block"


_config = RetsuConfig(
    redis_url=os.getenv("RETSU_REDIS_URL"),
    namespace=os.getenv("RETSU_NAMESPACE", "default"),
)
_backend: Optional[Backend] = None


def configure(
    backend: str = "redis",
    redis_url: Optional[str] = None,
    namespace: str = "default",
    default_ttl_seconds: int = 300,
    default_acquire_timeout_seconds: Optional[float] = 60,
    default_heartbeat_interval_seconds: float = 30,
    default_wait_strategy: Literal["block", "fail", "retry"] = "block",
) -> RetsuConfig:
    """Configure the process-global Retsu runtime."""
    global _backend, _config
    _config = RetsuConfig(
        backend=backend,
        redis_url=redis_url,
        namespace=namespace,
        default_ttl_seconds=default_ttl_seconds,
        default_acquire_timeout_seconds=default_acquire_timeout_seconds,
        default_heartbeat_interval_seconds=(
            default_heartbeat_interval_seconds
        ),
        default_wait_strategy=default_wait_strategy,
    )
    _backend = None
    return _config


def get_config() -> RetsuConfig:
    """Return the current process-global configuration."""
    return _config


def set_backend(backend: Backend) -> None:
    """Set an explicit backend object."""
    global _backend
    _backend = backend


def get_backend() -> Backend:
    """Return the configured backend, creating it lazily."""
    global _backend
    if _backend is not None:
        return _backend
    if _config.backend == "memory":
        _backend = MemoryBackend()
    elif _config.backend == "redis":
        _backend = RedisBackend(
            redis_url=_config.redis_url,
            namespace=_config.namespace,
        )
    else:
        raise ValueError(f"Unsupported Retsu backend: {_config.backend}")
    return _backend
