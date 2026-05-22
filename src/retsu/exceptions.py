"""Exceptions raised by Retsu APIs."""

from __future__ import annotations

from typing import Optional


class RetsuError(Exception):
    """Base exception for Retsu errors."""


class ResourceDefinitionMissing(RetsuError):
    """Raised when a request references an undefined capacity."""

    def __init__(self, name: str) -> None:
        """Initialize the exception."""
        self.name = name
        super().__init__(f"Resource or concurrency definition missing: {name}")


class ResourceUnavailable(RetsuError):
    """Raised when requested resources are currently unavailable."""

    def __init__(
        self,
        blocked_by: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Initialize the exception."""
        self.blocked_by = blocked_by
        self.retry_after_seconds = retry_after_seconds
        self.reason = reason
        message = "Requested resources are unavailable"
        if blocked_by:
            message = f"{message}: {blocked_by}"
        super().__init__(message)


class ResourceAcquireTimeout(ResourceUnavailable):
    """Raised when waiting for resources times out."""


class ResourceEstimationError(RetsuError):
    """Raised when a dynamic resource estimator fails."""


class RetsuBackendUnavailable(RetsuError):
    """Raised when the configured backend cannot be reached."""


class JobNotFound(RetsuError):
    """Raised when a job cannot be found."""
