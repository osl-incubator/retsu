# API Reference

Retsu's stable user-facing API is re-exported from the `retsu` package. Backend
classes and plugin helpers are available from their module paths when you need
advanced integration points.

## Configuration

### `retsu.configure(...) -> RetsuConfig`

```python
retsu.configure(
    backend="redis",
    redis_url=None,
    namespace="default",
    default_ttl_seconds=300,
    default_acquire_timeout_seconds=60,
    default_heartbeat_interval_seconds=30,
    default_wait_strategy="block",
)
```

Set process-global Retsu configuration and reset the cached backend. Supported
backend names are `"redis"` and `"memory"`.

Important behavior:

- the backend is created lazily by `get_backend()`;
- calling `configure()` discards the cached backend object;
- `default_wait_strategy` must be `"block"`, `"fail"`, or `"retry"`;
- `default_acquire_timeout_seconds=None` allows blocking acquires to wait
  indefinitely.

### `retsu.get_config() -> RetsuConfig`

Return the current process-global configuration dataclass.

### `retsu.get_backend() -> Backend`

Return the configured backend, creating it if needed. The Redis backend uses
`redis_url` if supplied; otherwise it uses the Redis environment helper values.

### `retsu.set_backend(backend) -> None`

Set an explicit backend object. This is most useful in tests or advanced
applications that construct their own backend instance.

```python
from retsu.backends.memory import MemoryBackend

retsu.set_backend(MemoryBackend())
```

## Capacity management

### `retsu.define_resource(name: str, capacity: float) -> None`

Define or update a named quantitative resource.

```python
retsu.define_resource("memory_mb", 64_000)
retsu.define_resource("gpu", 4)
```

### `retsu.define_concurrency(name: str, capacity: float) -> None`

Define or update a named concurrency limit.

```python
retsu.define_concurrency("billing-api", 5)
retsu.define_concurrency("tenant:acme", 1)
```

### `retsu.get_usage() -> UsageSnapshot`

Return current used, capacity, and available values for all configured
capacities. Expired leases are cleaned before the snapshot is returned.

```python
usage = retsu.get_usage()
item = usage.concurrency["billing-api"]
print(item.used, item.capacity, item.available)
```

### `retsu.list_leases() -> list[LeaseRecord]`

Return active leases after cleaning expired leases.

### `retsu.cleanup_expired_leases() -> CleanupResult`

Release all expired leases and return their ids.

```python
expired = retsu.cleanup_expired_leases().expired_lease_ids
```

## Guard mode

### `retsu.guard(...)`

```python
retsu.guard(
    resources=None,
    concurrency=None,
    ttl_seconds=None,
    acquire_timeout_seconds=None,
    wait_strategy=None,
)
```

Return a decorator that acquires capacity before calling the wrapped function.
`resources` and `concurrency` are mappings of names to either numbers or
callables evaluated with the wrapped function arguments.

```python
@retsu.guard(
    resources={"memory_mb": lambda batch: batch.estimated_mb},
    concurrency={"imports": 1},
)
def import_batch(batch):
    ...
```

Raises:

- `ResourceDefinitionMissing` for undefined capacity names;
- `ResourceUnavailable` when the selected strategy fails fast;
- `ResourceAcquireTimeout` when blocking acquisition times out;
- `ResourceEstimationError` when a dynamic estimator raises.

### `retsu.acquire(...)`

Context manager that acquires capacity for a critical section.

```python
with retsu.acquire(resources={"memory_mb": 512}, concurrency={"exports": 1}):
    export_file()
```

The yielded object is a `Lease`.

### `retsu.limit(name: str, slots: float = 1, ...)`

Convenience context manager for one named concurrency limit.

```python
with retsu.limit("billing-api", slots=1):
    call_billing_api()
```

### `retsu.acquire_with_policy(...) -> Lease`

Lower-level API used by guard mode. It accepts an already evaluated
`ResourceRequest` plus explicit `job_id` and `owner_id`.

```python
lease = retsu.acquire_with_policy(
    job_id="manual-job",
    owner_id="worker-1",
    request=retsu.ResourceRequest(resources={}, concurrency={"api": 1}),
)
try:
    do_work()
finally:
    lease.release()
```

## Admission mode

### `retsu.submit(...) -> JobHandle`

```python
retsu.submit(
    func,
    args=(),
    kwargs=None,
    resources=None,
    concurrency=None,
    executor="local",
    queue=None,
    priority=0,
    max_attempts=1,
)
```

Create a queued admission job and return a handle. The resource request is
evaluated at submit time. Args, kwargs, and results are serialized with
`pickle`, so treat admission payloads as trusted-process data.

```python
handle = retsu.submit(
    build_report,
    args=("weekly",),
    resources={"cpu": 1},
    concurrency={"reports": 1},
    priority=10,
)
```

### `retsu.Scheduler(...)`

```python
scheduler = retsu.Scheduler()
scheduler.run_once(limit=100)
```

`run_once()` cleans expired leases, considers queued/waiting jobs, acquires
capacity, and dispatches admitted jobs through an executor. The default executor
is local. Jobs with `executor="ray"` create a Ray executor on demand.

Constructor arguments:

- `backend`: explicit backend, otherwise `retsu.get_backend()`;
- `executors`: mapping of executor names to executor objects;
- `owner_id`: explicit owner id for acquired leases.

### `retsu.JobHandle`

Returned by `submit()`.

| Method | Behavior |
| --- | --- |
| `status()` | Return the current `JobStatus`. |
| `result(timeout=None)` | Wait for success and return the unpickled result. Raise for failure, cancellation, or timeout. |
| `metadata()` | Return a dictionary of job metadata. |
| `cancel()` | Mark the job cancelled. |

## Integrations

### `retsu.celery_guard(task, ..., wait_strategy="retry")`

Context manager for bound Celery tasks. With `wait_strategy="retry"`, capacity
denial is converted into `task.retry(countdown=...)`.

```python
@app.task(bind=True)
def render(self, document_id: str) -> None:
    with retsu.celery_guard(self, concurrency={"render": 1}):
        render_document(document_id)
```

### `retsu.ray_guard(...)`

Context manager for guarded sections inside Ray tasks.

```python
@ray.remote
def train(model_id: str) -> str:
    with retsu.ray_guard(resources={"gpu": 1}):
        return run_training(model_id)
```

### `retsu.ray_task(..., **ray_options)`

Decorator that wraps a function with Retsu guard mode and then applies
`ray.remote`.

```python
@retsu.ray_task(resources={"gpu": 1}, num_gpus=1)
def train(model_id: str) -> str:
    return run_training(model_id)
```

### `retsu.plugins.django.create_app_config(manager, app_name="myapp")`

Django plugin helper for manager-style integrations. Import from the module path
rather than `retsu`:

```python
from retsu.plugins.django import create_app_config
```

## Data models

### `ResourceRequest`

Concrete request for one lease.

```python
request = retsu.ResourceRequest(
    resources={"memory_mb": 512},
    concurrency={"api": 1},
)
```

Validation rules:

- names must be non-empty strings;
- values must be finite and non-negative;
- zero values are ignored;
- values are normalized to floats.

### `ResourceSpec`

Static or dynamic resource requirements. `evaluate(*args, **kwargs)` returns a
`ResourceRequest`.

### `AcquireResult`

Backend acquire result:

| Field | Meaning |
| --- | --- |
| `acquired` | Whether capacity was acquired. |
| `lease_id` | New lease id when acquired. |
| `reason` | Backend reason when not acquired. |
| `blocked_by` | Capacity name that blocked acquisition. |
| `retry_after_seconds` | Suggested retry delay. |

### `UsageSnapshot` and `UsageItem`

`UsageSnapshot.resources` and `UsageSnapshot.concurrency` map names to
`UsageItem` objects. `UsageItem.available` is `max(capacity - used, 0)`.

### `CleanupResult`

Contains `expired_lease_ids`.

### `LeaseRecord`

Persisted lease metadata: id, job id, owner id, resource request, concurrency
request, creation time, renewal time, and expiry time.

### `JobRecord` and `JobStatus`

Admission-mode job metadata and status enum. Common statuses include `queued`,
`waiting_for_resources`, `leased`, `dispatched`, `running`, `succeeded`,
`failed`, and `cancelled`.

### `CapacityDefinition`

Dataclass representing a named capacity definition. It is exported for typed
integrations that need to describe capacity metadata.

## Backends and executors

Advanced users can import implementations directly:

```python
from retsu.backends.memory import MemoryBackend
from retsu.backends.redis import RedisBackend
from retsu.executors.local import LocalExecutor
from retsu.executors.ray import RayExecutor
```

Backend implementations follow the protocol in `retsu.backends.base.Backend`.
Custom executors should implement `dispatch(job, lease_id, owner_id)` and must
release the lease on every success and failure path.

## Exceptions

| Exception | Meaning |
| --- | --- |
| `RetsuError` | Base class for Retsu errors. |
| `ResourceDefinitionMissing` | A request referenced an undefined resource or concurrency name. |
| `ResourceUnavailable` | Capacity is full and the wait strategy failed fast. |
| `ResourceAcquireTimeout` | Blocking acquisition exceeded the configured timeout. |
| `ResourceEstimationError` | A dynamic request estimator raised before acquisition. |
| `RetsuBackendUnavailable` | Backend connectivity/configuration error type for integrations. |
| `JobNotFound` | A backend job lookup failed. Import from `retsu.exceptions`. |

## Version metadata

```python
retsu.__version__
retsu.__author__
retsu.__email__
```
