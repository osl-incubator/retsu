"""Redis backend for Retsu."""

from __future__ import annotations

import json

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis

from retsu.exceptions import JobNotFound, ResourceDefinitionMissing
from retsu.queues import get_redis_queue_config
from retsu.resources import (
    AcquireResult,
    CleanupResult,
    ResourceRequest,
    UsageItem,
    UsageSnapshot,
)
from retsu.state import JobRecord, JobStatus, LeaseRecord

ACQUIRE_SCRIPT = """
local cap_res = KEYS[1]
local cap_con = KEYS[2]
local use_res = KEYS[3]
local use_con = KEYS[4]
local leases = KEYS[5]
local lease_prefix = KEYS[6]

local lease_id = ARGV[1]
local job_id = ARGV[2]
local owner_id = ARGV[3]
local ttl_seconds = tonumber(ARGV[4])
local now = tonumber(ARGV[5])
local resources_json = ARGV[6]
local concurrency_json = ARGV[7]

local function subtract_mapping(usage_key, mapping_json)
  local mapping = cjson.decode(mapping_json)
  for name, amount in pairs(mapping) do
    local current = tonumber(redis.call("HGET", usage_key, name) or "0")
    local next_value = current - tonumber(amount)
    if next_value < 0 then
      next_value = 0
    end
    redis.call("HSET", usage_key, name, next_value)
  end
end

local expired = redis.call("ZRANGEBYSCORE", leases, "-inf", now)
for _, expired_id in ipairs(expired) do
  local key = lease_prefix .. expired_id
  local existing_resources = redis.call("HGET", key, "resources_json")
  local existing_concurrency = redis.call("HGET", key, "concurrency_json")
  if existing_resources then
    subtract_mapping(use_res, existing_resources)
  end
  if existing_concurrency then
    subtract_mapping(use_con, existing_concurrency)
  end
  redis.call("DEL", key)
  redis.call("ZREM", leases, expired_id)
end

local resources = cjson.decode(resources_json)
local concurrency = cjson.decode(concurrency_json)

for name, amount in pairs(resources) do
  local capacity = redis.call("HGET", cap_res, name)
  if not capacity then
    return {0, "missing", name, 0}
  end
  local used = tonumber(redis.call("HGET", use_res, name) or "0")
  if used + tonumber(amount) > tonumber(capacity) then
    return {0, "insufficient_resource", name, 1}
  end
end

for name, amount in pairs(concurrency) do
  local capacity = redis.call("HGET", cap_con, name)
  if not capacity then
    return {0, "missing", name, 0}
  end
  local used = tonumber(redis.call("HGET", use_con, name) or "0")
  if used + tonumber(amount) > tonumber(capacity) then
    return {0, "insufficient_concurrency", name, 1}
  end
end

for name, amount in pairs(resources) do
  redis.call("HINCRBYFLOAT", use_res, name, amount)
end
for name, amount in pairs(concurrency) do
  redis.call("HINCRBYFLOAT", use_con, name, amount)
end

local expires_at = now + ttl_seconds
redis.call(
  "HSET",
  lease_prefix .. lease_id,
  "id", lease_id,
  "job_id", job_id,
  "owner_id", owner_id,
  "resources_json", resources_json,
  "concurrency_json", concurrency_json,
  "created_at", now,
  "renewed_at", now,
  "expires_at", expires_at
)
redis.call("ZADD", leases, expires_at, lease_id)
return {1, lease_id, "", 0}
"""


RELEASE_SCRIPT = """
local use_res = KEYS[1]
local use_con = KEYS[2]
local leases = KEYS[3]
local lease_key = KEYS[4]
local lease_id = ARGV[1]
local owner_id = ARGV[2]

local existing_owner = redis.call("HGET", lease_key, "owner_id")
if not existing_owner then
  return {0, "missing"}
end
if owner_id ~= "" and existing_owner ~= owner_id then
  return {0, "owner_mismatch"}
end

local function subtract_mapping(usage_key, mapping_json)
  local mapping = cjson.decode(mapping_json)
  for name, amount in pairs(mapping) do
    local current = tonumber(redis.call("HGET", usage_key, name) or "0")
    local next_value = current - tonumber(amount)
    if next_value < 0 then
      next_value = 0
    end
    redis.call("HSET", usage_key, name, next_value)
  end
end

local resources_json = redis.call("HGET", lease_key, "resources_json")
local concurrency_json = redis.call("HGET", lease_key, "concurrency_json")
if resources_json then
  subtract_mapping(use_res, resources_json)
end
if concurrency_json then
  subtract_mapping(use_con, concurrency_json)
end
redis.call("DEL", lease_key)
redis.call("ZREM", leases, lease_id)
return {1, "released"}
"""


RENEW_SCRIPT = """
local leases = KEYS[1]
local lease_key = KEYS[2]
local lease_id = ARGV[1]
local owner_id = ARGV[2]
local ttl_seconds = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local existing_owner = redis.call("HGET", lease_key, "owner_id")
if not existing_owner then
  return {0, "missing"}
end
if owner_id ~= "" and existing_owner ~= owner_id then
  return {0, "owner_mismatch"}
end
local expires_at = now + ttl_seconds
redis.call("HSET", lease_key, "renewed_at", now, "expires_at", expires_at)
redis.call("ZADD", leases, expires_at, lease_id)
return {1, "renewed"}
"""


class RedisBackend:
    """Redis-backed atomic lease backend."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        namespace: str = "default",
        client: Optional[redis.Redis] = None,
    ) -> None:
        """Initialize the backend."""
        self.namespace = namespace
        if client is not None:
            self.client = client
        elif redis_url:
            self.client = redis.Redis.from_url(
                redis_url, decode_responses=False
            )
        else:
            self.client = redis.Redis(
                **get_redis_queue_config(),  # type: ignore[arg-type]
                decode_responses=False,
            )

    def _key(self, suffix: str) -> str:
        return f"retsu:{self.namespace}:{suffix}"

    @property
    def _capacity_resources_key(self) -> str:
        return self._key("capacity:resources")

    @property
    def _capacity_concurrency_key(self) -> str:
        return self._key("capacity:concurrency")

    @property
    def _usage_resources_key(self) -> str:
        return self._key("usage:resources")

    @property
    def _usage_concurrency_key(self) -> str:
        return self._key("usage:concurrency")

    @property
    def _leases_key(self) -> str:
        return self._key("leases")

    @property
    def _lease_prefix(self) -> str:
        return self._key("lease:")

    def _lease_key(self, lease_id: str) -> str:
        return f"{self._lease_prefix}{lease_id}"

    def _job_key(self, job_id: str) -> str:
        return self._key(f"job:{job_id}")

    def define_resource(self, name: str, capacity: float) -> None:
        """Define a quantitative resource."""
        self._define(
            self._capacity_resources_key,
            self._usage_resources_key,
            name,
            capacity,
        )

    def define_concurrency(self, name: str, capacity: float) -> None:
        """Define a named concurrency limit."""
        self._define(
            self._capacity_concurrency_key,
            self._usage_concurrency_key,
            name,
            capacity,
        )

    def _define(
        self,
        capacity_key: str,
        usage_key: str,
        name: str,
        capacity: float,
    ) -> None:
        if not name:
            raise ValueError("capacity name must be non-empty")
        if capacity < 0:
            raise ValueError(f"{name} capacity must be positive")
        pipe = self.client.pipeline()
        pipe.hset(capacity_key, name, float(capacity))
        pipe.hsetnx(usage_key, name, 0)
        pipe.execute()

    def acquire(
        self,
        job_id: str,
        owner_id: str,
        request: ResourceRequest,
        ttl_seconds: int,
    ) -> AcquireResult:
        """Try to acquire capacity atomically."""
        lease_id = uuid4().hex
        result = self.client.eval(
            ACQUIRE_SCRIPT,
            6,
            self._capacity_resources_key,
            self._capacity_concurrency_key,
            self._usage_resources_key,
            self._usage_concurrency_key,
            self._leases_key,
            self._lease_prefix,
            lease_id,
            job_id,
            owner_id,
            ttl_seconds,
            datetime.now(timezone.utc).timestamp(),
            json.dumps(request.resources),
            json.dumps(request.concurrency),
        )
        values = list(result)  # type: ignore[arg-type]
        acquired = bool(int(values[0]))
        reason = self._decode(values[1])
        blocked_by = self._decode(values[2])
        retry_after = float(values[3] or 0)
        if not acquired and reason == "missing":
            raise ResourceDefinitionMissing(blocked_by)
        return AcquireResult(
            acquired=acquired,
            lease_id=reason if acquired else "",
            reason="" if acquired else reason,
            blocked_by=blocked_by,
            retry_after_seconds=retry_after,
        )

    def release(self, lease_id: str, owner_id: str) -> None:
        """Release an active lease."""
        self.client.eval(
            RELEASE_SCRIPT,
            4,
            self._usage_resources_key,
            self._usage_concurrency_key,
            self._leases_key,
            self._lease_key(lease_id),
            lease_id,
            owner_id,
        )

    def renew(
        self, lease_id: str, owner_id: str, ttl_seconds: int
    ) -> None:
        """Renew an active lease."""
        self.client.eval(
            RENEW_SCRIPT,
            2,
            self._leases_key,
            self._lease_key(lease_id),
            lease_id,
            owner_id,
            ttl_seconds,
            datetime.now(timezone.utc).timestamp(),
        )

    def get_usage(self) -> UsageSnapshot:
        """Return current usage."""
        self.cleanup_expired_leases()
        resource_capacity = self._hgetall_float(self._capacity_resources_key)
        concurrency_capacity = self._hgetall_float(
            self._capacity_concurrency_key
        )
        resource_usage = self._hgetall_float(self._usage_resources_key)
        concurrency_usage = self._hgetall_float(self._usage_concurrency_key)
        return UsageSnapshot(
            resources={
                name: UsageItem(
                    used=resource_usage.get(name, 0),
                    capacity=capacity,
                )
                for name, capacity in resource_capacity.items()
            },
            concurrency={
                name: UsageItem(
                    used=concurrency_usage.get(name, 0),
                    capacity=capacity,
                )
                for name, capacity in concurrency_capacity.items()
            },
        )

    def list_leases(self) -> List[LeaseRecord]:
        """List active leases."""
        self.cleanup_expired_leases()
        lease_ids = self.client.zrange(self._leases_key, 0, -1)
        records = []
        for raw_id in lease_ids:
            lease = self.get_lease(self._decode(raw_id))
            if lease is not None:
                records.append(lease)
        return records

    def get_lease(self, lease_id: str) -> Optional[LeaseRecord]:
        """Get one active lease."""
        data = self.client.hgetall(self._lease_key(lease_id))
        if not data:
            return None
        return self._decode_lease(data)

    def cleanup_expired_leases(self) -> CleanupResult:
        """Release expired leases."""
        now = datetime.now(timezone.utc).timestamp()
        expired_raw = self.client.zrangebyscore(self._leases_key, "-inf", now)
        expired = [self._decode(lease_id) for lease_id in expired_raw]
        for lease_id in expired:
            self.release(lease_id, owner_id="")
        return CleanupResult(expired_lease_ids=expired)

    def create_job(self, job: JobRecord) -> None:
        """Create a persisted job."""
        self.client.hset(self._job_key(job.id), mapping=self._encode_job(job))

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
        result_blob: Optional[bytes] = None,
    ) -> None:
        """Update a job status."""
        key = self._job_key(job_id)
        if not self.client.exists(key):
            raise JobNotFound(job_id)
        now = datetime.now(timezone.utc)
        updates: Dict[str, Any] = {
            "status": status.value,
            "updated_at": now.timestamp(),
        }
        if status == JobStatus.LEASED:
            updates["leased_at"] = now.timestamp()
        elif status == JobStatus.RUNNING:
            updates["started_at"] = now.timestamp()
        elif status in (
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ):
            updates["finished_at"] = now.timestamp()
        if error is not None:
            updates["error"] = error
        if result_blob is not None:
            updates["result_blob"] = result_blob
        self.client.hset(key, mapping=updates)

    def get_job(self, job_id: str) -> JobRecord:
        """Load one job."""
        data = self.client.hgetall(self._job_key(job_id))
        if not data:
            raise JobNotFound(job_id)
        return self._decode_job(data)

    def list_queued_jobs(self, limit: int = 100) -> List[JobRecord]:
        """List queued and waiting jobs."""
        jobs = []
        for key in self.client.scan_iter(self._key("job:*")):
            job = self._decode_job(self.client.hgetall(key))
            if job.status in (
                JobStatus.QUEUED,
                JobStatus.WAITING_FOR_RESOURCES,
            ):
                jobs.append(job)
        jobs.sort(key=lambda job: (-job.priority, job.created_at))
        return jobs[:limit]

    def flush_namespace(self) -> None:
        """Delete all keys in this backend namespace."""
        keys = list(self.client.scan_iter(self._key("*")))
        if keys:
            self.client.delete(*keys)

    @staticmethod
    def _decode(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf8")
        return str(value)

    def _hgetall_float(self, key: str) -> Dict[str, float]:
        return {
            self._decode(name): float(value)
            for name, value in self.client.hgetall(key).items()
        }

    def _decode_lease(self, data: Dict[bytes, bytes]) -> LeaseRecord:
        decoded = {self._decode(k): v for k, v in data.items()}
        return LeaseRecord(
            id=self._decode(decoded["id"]),
            job_id=self._decode(decoded["job_id"]),
            owner_id=self._decode(decoded["owner_id"]),
            resources=json.loads(self._decode(decoded["resources_json"])),
            concurrency=json.loads(
                self._decode(decoded["concurrency_json"])
            ),
            created_at=self._datetime_from_timestamp(decoded["created_at"]),
            renewed_at=self._datetime_from_timestamp(decoded["renewed_at"]),
            expires_at=self._datetime_from_timestamp(decoded["expires_at"]),
        )

    def _encode_job(self, job: JobRecord) -> Dict[str, Any]:
        return {
            "id": job.id,
            "task_name": job.task_name,
            "status": job.status.value,
            "args_blob": job.args_blob or b"",
            "kwargs_blob": job.kwargs_blob or b"",
            "resources_json": json.dumps(job.resources),
            "concurrency_json": json.dumps(job.concurrency),
            "executor": job.executor,
            "queue": job.queue or "",
            "priority": job.priority,
            "attempt": job.attempt,
            "max_attempts": job.max_attempts,
            "created_at": job.created_at.timestamp(),
            "updated_at": job.updated_at.timestamp(),
            "leased_at": self._optional_timestamp(job.leased_at),
            "started_at": self._optional_timestamp(job.started_at),
            "finished_at": self._optional_timestamp(job.finished_at),
            "heartbeat_at": self._optional_timestamp(job.heartbeat_at),
            "error": job.error or "",
            "result_blob": job.result_blob or b"",
        }

    def _decode_job(self, data: Dict[bytes, bytes]) -> JobRecord:
        decoded = {self._decode(k): v for k, v in data.items()}

        def text(name: str) -> str:
            return self._decode(decoded.get(name, b""))

        return JobRecord(
            id=text("id"),
            task_name=text("task_name"),
            status=JobStatus(text("status")),
            args_blob=self._optional_blob(decoded.get("args_blob")),
            kwargs_blob=self._optional_blob(decoded.get("kwargs_blob")),
            resources=json.loads(text("resources_json") or "{}"),
            concurrency=json.loads(text("concurrency_json") or "{}"),
            executor=text("executor"),
            queue=text("queue") or None,
            priority=int(float(text("priority") or 0)),
            attempt=int(float(text("attempt") or 0)),
            max_attempts=int(float(text("max_attempts") or 1)),
            created_at=self._datetime_from_timestamp(decoded["created_at"]),
            updated_at=self._datetime_from_timestamp(decoded["updated_at"]),
            leased_at=self._optional_datetime(decoded.get("leased_at")),
            started_at=self._optional_datetime(decoded.get("started_at")),
            finished_at=self._optional_datetime(decoded.get("finished_at")),
            heartbeat_at=self._optional_datetime(decoded.get("heartbeat_at")),
            error=text("error") or None,
            result_blob=self._optional_blob(decoded.get("result_blob")),
        )

    @staticmethod
    def _optional_timestamp(value: Optional[datetime]) -> str:
        if value is None:
            return ""
        return str(value.timestamp())

    def _optional_datetime(self, value: Optional[bytes]) -> Optional[datetime]:
        if value is None or self._decode(value) == "":
            return None
        return self._datetime_from_timestamp(value)

    def _datetime_from_timestamp(self, value: Any) -> datetime:
        return datetime.fromtimestamp(float(self._decode(value)), timezone.utc)

    @staticmethod
    def _optional_blob(value: Optional[bytes]) -> Optional[bytes]:
        if not value:
            return None
        return value
