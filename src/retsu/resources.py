"""Resource and capacity data models."""

from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, Mapping, Union

from retsu.exceptions import ResourceEstimationError

ResourceValue = Union[float, int, Callable[..., Union[float, int]]]


@dataclass(frozen=True)
class CapacityDefinition:
    """A configured resource or concurrency capacity."""

    name: str
    capacity: float
    kind: Literal["resource", "concurrency"]
    unit: str = ""
    description: str = ""


@dataclass(frozen=True)
class ResourceRequest:
    """Concrete resource and concurrency amounts for one lease."""

    resources: Dict[str, float]
    concurrency: Dict[str, float]

    def __post_init__(self) -> None:
        """Normalize and validate the request."""
        object.__setattr__(
            self, "resources", self._normalize(self.resources, "resource")
        )
        object.__setattr__(
            self,
            "concurrency",
            self._normalize(self.concurrency, "concurrency"),
        )

    @staticmethod
    def _normalize(
        values: Mapping[str, Union[float, int]], kind: str
    ) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for name, raw_value in values.items():
            if not isinstance(name, str) or not name:
                raise ValueError(f"{kind} names must be non-empty strings")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
            if value < 0:
                raise ValueError(f"{name} must be positive")
            if value == 0:
                continue
            normalized[name] = value
        return normalized

    @property
    def empty(self) -> bool:
        """Return whether the request asks for no capacity."""
        return not self.resources and not self.concurrency


@dataclass(frozen=True)
class ResourceSpec:
    """Static or dynamic resource requirements."""

    resources: Mapping[str, ResourceValue]
    concurrency: Mapping[str, ResourceValue]

    def evaluate(self, *args: Any, **kwargs: Any) -> ResourceRequest:
        """Evaluate the spec using the wrapped function arguments."""
        return ResourceRequest(
            resources=self._evaluate_mapping(self.resources, *args, **kwargs),
            concurrency=self._evaluate_mapping(
                self.concurrency, *args, **kwargs
            ),
        )

    @staticmethod
    def _evaluate_mapping(
        spec: Mapping[str, ResourceValue], *args: Any, **kwargs: Any
    ) -> Dict[str, float]:
        values: Dict[str, float] = {}
        for name, raw_value in spec.items():
            try:
                value = (
                    raw_value(*args, **kwargs)
                    if callable(raw_value)
                    else raw_value
                )
            except Exception as exc:
                raise ResourceEstimationError(
                    f"Could not estimate resource {name}"
                ) from exc
            values[name] = float(value)
        return values


@dataclass(frozen=True)
class AcquireResult:
    """Result returned by backend acquire calls."""

    acquired: bool
    lease_id: str = ""
    reason: str = ""
    blocked_by: str = ""
    retry_after_seconds: float = 0


@dataclass(frozen=True)
class UsageItem:
    """Usage and capacity for one resource."""

    used: float
    capacity: float

    @property
    def available(self) -> float:
        """Return currently available capacity."""
        return max(self.capacity - self.used, 0)


@dataclass(frozen=True)
class UsageSnapshot:
    """Usage snapshot for all resource kinds."""

    resources: Dict[str, UsageItem]
    concurrency: Dict[str, UsageItem]


@dataclass(frozen=True)
class CleanupResult:
    """Result returned by lease cleanup."""

    expired_lease_ids: list[str]
