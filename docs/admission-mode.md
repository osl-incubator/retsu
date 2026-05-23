# Admission mode

Admission mode is Retsu's resource-aware dispatch path. Instead of immediately
running a guarded function, you submit a job, let a scheduler acquire capacity,
and dispatch the job only after the lease exists.

Use admission mode when:

- jobs should wait in Retsu state until capacity is available;
- a scheduler should decide when to dispatch queued work;
- callers need a `JobHandle` for status, metadata, cancellation, and result
  access;
- you want the same resource accounting for local threads or Ray dispatch.

## Minimal local example

```python
import retsu

retsu.configure(backend="memory")
retsu.define_resource("cpu", 2)
retsu.define_concurrency("reports", 1)


def build_report(name: str) -> str:
    return f"built {name}"


handle = retsu.submit(
    build_report,
    args=("weekly",),
    resources={"cpu": 1},
    concurrency={"reports": 1},
)

scheduler = retsu.Scheduler()
scheduler.run_once()

print(handle.result(timeout=5))
```

The default local executor runs admitted jobs in daemon threads.

## Components

### `submit()`

`submit()` evaluates the resource request immediately, serializes args and
kwargs, stores a `JobRecord`, and returns a `JobHandle`.

```python
handle = retsu.submit(
    func,
    args=("customer-42",),
    kwargs={"force": True},
    resources={"memory_mb": 256},
    concurrency={"customer-sync": 1},
    executor="local",
    priority=10,
)
```

The local executor also stores the submitted Python callable in a process-local
function registry. That means local admission execution is currently best suited
for scheduler loops running in the same process as submission, or for tests and
single-process services.

### `Scheduler`

The scheduler performs one admission pass with `run_once()`:

1. cleanup expired leases;
2. load queued and waiting jobs;
3. try to acquire each job's requested capacity;
4. mark unavailable jobs as `waiting_for_resources`;
5. mark admitted jobs as `leased` and `dispatched`;
6. call the configured executor.

```python
scheduler = retsu.Scheduler()
scheduler.run_once(limit=100)
```

A service can call `run_once()` in a loop:

```python
import signal
import time

stop = False


def request_stop(*_: object) -> None:
    global stop
    stop = True


signal.signal(signal.SIGTERM, request_stop)
scheduler = retsu.Scheduler()

while not stop:
    scheduler.run_once(limit=100)
    time.sleep(0.5)
```

### Executors

Retsu includes two executor implementations:

| Executor | Name | Behavior |
| --- | --- | --- |
| `LocalExecutor` | `local` | Runs jobs in local daemon threads and releases the lease after success or failure. |
| `RayExecutor` | `ray` | Dispatches jobs to Ray and tracks completion in a local daemon thread. |

`Scheduler()` registers the local executor by default. If a job asks for
`executor="ray"`, the scheduler creates a `RayExecutor` on demand.

### `JobHandle`

The handle returned by `submit()` exposes:

```python
handle.status()       # current JobStatus
handle.result(10)     # wait up to 10 seconds, then return or raise
handle.metadata()     # serializable job metadata
handle.cancel()       # mark the job cancelled
```

`result()` returns the unpickled result for succeeded jobs. It raises
`RuntimeError` for failed or cancelled jobs and `TimeoutError` if the timeout
expires before a terminal state.

## Job statuses

Common statuses are:

| Status | Meaning |
| --- | --- |
| `queued` | The job has been submitted and is eligible for scheduling. |
| `waiting_for_resources` | A scheduler pass could not acquire capacity. |
| `leased` | Capacity was acquired. |
| `dispatched` | The executor was called. |
| `running` | The executor started executing the callable. |
| `succeeded` | The callable returned successfully. |
| `failed` | Dispatch or execution raised an exception. |
| `cancelled` | The job was marked cancelled. |

Timestamps such as `leased_at`, `started_at`, and `finished_at` are updated as
jobs move through these states.

## Priorities and fairness

Queued jobs are sorted by descending `priority`, then by creation time. A higher
priority value is considered first during each scheduler pass.

```python
high = retsu.submit(expensive_job, priority=100)
normal = retsu.submit(expensive_job, priority=0)
```

Retsu does not currently implement aging, weighted fairness, or per-queue
scheduler filters. If you use the `queue` field, treat it as metadata unless you
provide custom scheduler logic.

## Ray dispatch

```python
handle = retsu.submit(
    train_model,
    args=("model-a",),
    resources={"gpu": 1},
    executor="ray",
)

retsu.Scheduler().run_once()
```

Ray still controls Ray cluster placement. Retsu controls the application-level
capacity definitions you declare in its backend.

## Reliability notes

- Dispatch failures release the acquired lease and mark the job failed.
- Executors release leases after success and after exceptions.
- Admission payloads and results use `pickle`; treat them as trusted-process
  data, not untrusted user input.
- Local admission mode is intentionally lightweight. For durable, multi-worker
  task distribution, pair Retsu guard mode with Celery/Ray or build a custom
  executor around the backend protocol.
