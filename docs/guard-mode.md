# Guard mode

Guard mode is the simplest way to use Retsu. You keep your existing execution
model and wrap the code that must not run unless capacity is available.

Use guard mode for:

- Celery tasks that should retry when a shared limit is full;
- local functions that need a Redis-backed cross-process semaphore;
- critical sections that use scarce external resources;
- Ray tasks that need Retsu capacity in addition to Ray placement resources.

## Decorate a function

```python
import retsu

retsu.configure(backend="memory")
retsu.define_concurrency("vendor-api", 2)


@retsu.guard(concurrency={"vendor-api": 1})
def sync_order(order_id: str) -> None:
    push_order_to_vendor(order_id)
```

The wrapper preserves the function metadata with `functools.wraps`. Retsu
acquires capacity before calling your function and releases it whether the
function returns or raises.

## Guard a critical section

Use `acquire()` when only part of a function needs protection:

```python
with retsu.acquire(resources={"memory_mb": 512}, concurrency={"exports": 1}):
    export_large_file()
```

Use `limit()` for the common case of one named concurrency limit:

```python
with retsu.limit("exports", slots=1):
    export_large_file()
```

Both APIs return a `Lease` object from the context manager if you need the lease
id for logs:

```python
with retsu.limit("exports") as lease:
    logger.info("running export under lease %s", lease.id)
    export_large_file()
```

## Static and dynamic requests

Requests can be static:

```python
@retsu.guard(resources={"gpu": 1}, concurrency={"training": 1})
def train(model_id: str) -> None:
    ...
```

They can also be dynamic. Callable values receive the wrapped function's
arguments:

```python
@retsu.guard(
    resources={"memory_mb": lambda records: max(128, len(records) * 2)},
)
def import_records(records: list[dict[str, object]]) -> None:
    ...
```

If a dynamic estimator raises, Retsu raises `ResourceEstimationError` and does
not acquire a lease.

## Wait policy examples

### Block until capacity is available

```python
@retsu.guard(concurrency={"reports": 1}, wait_strategy="block")
def build_report(report_id: str) -> None:
    ...
```

`block` is the default. It retries until capacity is available or the acquire
timeout expires.

### Fail fast

```python
try:
    with retsu.limit("reports", wait_strategy="fail"):
        build_report_now()
except retsu.ResourceUnavailable as exc:
    return {"status": "busy", "blocked_by": exc.blocked_by}
```

Use `fail` for request/response paths where waiting would be worse than telling
the caller to try again.

### Retry in an integration

```python
@app.task(bind=True)
def build_report(self, report_id: str) -> None:
    with retsu.celery_guard(
        self,
        concurrency={"reports": 1},
        wait_strategy="retry",
    ):
        render_report(report_id)
```

`celery_guard()` converts `ResourceUnavailable` into `task.retry(...)` when the
strategy is `retry`.

## TTLs and heartbeat

Every lease has a TTL. Guard mode starts a daemon heartbeat thread and renews
the lease while the guarded code is active. If the worker process crashes, the
heartbeat stops and the lease eventually expires. Expired leases are cleaned up
before capacity acquisition and usage snapshots.

Tune these values together:

```python
retsu.configure(
    backend="redis",
    redis_url="redis://localhost:6379/0",
    default_ttl_seconds=300,
    default_heartbeat_interval_seconds=30,
    default_acquire_timeout_seconds=60,
)
```

Choose a TTL long enough to tolerate normal heartbeat delays, and an acquire
timeout that matches how long callers are willing to wait.

## Exceptions to handle

| Exception | Typical cause |
| --- | --- |
| `ResourceDefinitionMissing` | A request referenced a capacity that was never defined. |
| `ResourceUnavailable` | Capacity is full and the policy is `fail` or `retry`. |
| `ResourceAcquireTimeout` | Capacity stayed full until the blocking acquire timed out. |
| `ResourceEstimationError` | A dynamic resource estimator raised an exception. |

## Good guard-mode practices

- Define capacities during process startup, before tasks begin running.
- Use clear names that match operational dashboards or limits.
- Keep guarded sections as small as practical.
- Prefer dynamic estimates when input size materially changes resource needs.
- Use `wait_strategy="retry"` for Celery tasks that should return to the queue.
- Set namespaces deliberately when multiple environments share Redis/Valkey.

## Avoid

- Guarding code that can block forever without a suitable TTL/heartbeat setup.
- Using the memory backend when multiple processes need shared accounting.
- Catching broad exceptions around guarded code and forgetting that the work may
  have partially completed.
- Treating a Retsu lease as a database transaction. It controls admission; it
  does not roll back side effects.
