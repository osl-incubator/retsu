# Concepts

Retsu is intentionally small. Understanding the few core concepts makes the API
predictable and helps you design safe capacity policies.

## Capacities

A capacity is a named limit stored in the backend.

```python
retsu.define_resource("memory_mb", 16_000)
retsu.define_concurrency("vendor-api", 5)
```

Retsu keeps two kinds of capacity separate:

- **Resources** are quantitative amounts. They are useful for memory, GPU
  fractions, license seats, token budgets, or any other value where a job may
  need more than one unit.
- **Concurrency limits** are named slot counts. They are useful for per-service,
  per-tenant, or per-critical-section limits.

Both kinds use floating-point values internally. Names must be non-empty
strings. Capacity values must be non-negative. A request for an undefined name
raises `ResourceDefinitionMissing`.

## Requests

A request is the concrete capacity needed by one lease.

```python
request = retsu.ResourceRequest(
    resources={"memory_mb": 256},
    concurrency={"vendor-api": 1},
)
```

Guard APIs usually build the request for you from a `ResourceSpec`. Values can
be static numbers or callables evaluated with the wrapped function arguments:

```python
@retsu.guard(resources={"memory_mb": lambda batch: batch.estimated_mb})
def process(batch):
    ...
```

Estimator failures are wrapped in `ResourceEstimationError` before any lease is
acquired. Zero-valued requests are ignored. Negative or non-finite values are
rejected.

## Leases

A lease is a time-limited reservation of a request. On successful acquire:

1. Retsu verifies every requested name exists.
2. Retsu checks whether `used + requested <= capacity` for every item.
3. Usage is incremented.
4. A lease record is stored with an owner id and expiry time.

When the lease is released or cleaned up after expiry, usage is decremented once
and clamped so it cannot go below zero.

Guard decorators and context managers release leases in `finally` blocks. They
also run a daemon heartbeat thread that renews the lease while user code is
running.

## Owners

Each lease has an owner id. Guard mode uses a process-stable owner id based on
the host name and process id. Admission-mode schedulers use their own owner id.

Release and renewal operations include the owner id. If an owner is supplied and
it does not match the lease owner, the backend leaves the lease untouched. This
prevents one worker from accidentally releasing another worker's reservation.

## Wait strategies

Wait strategies control what happens when capacity is currently full.

| Strategy | Behavior |
| --- | --- |
| `block` | Keep trying until capacity is available or the acquire timeout expires. This is the default. |
| `fail` | Raise `ResourceUnavailable` immediately. |
| `retry` | Raise `ResourceUnavailable` immediately so an integration can schedule a retry. Celery uses this path. |

If `block` waits longer than `acquire_timeout_seconds`, Retsu raises
`ResourceAcquireTimeout`.

## Backends

### Memory backend

The memory backend is thread-safe and service-free. Use it for tests, notebooks,
local scripts, and single-process tools.

```python
retsu.configure(backend="memory")
```

Memory state is process-local. It does not coordinate across processes.

### Redis/Valkey backend

The Redis backend is the default. It stores capacity, usage, leases, and
admission jobs under namespace-scoped keys:

```text
retsu:{namespace}:capacity:resources
retsu:{namespace}:capacity:concurrency
retsu:{namespace}:usage:resources
retsu:{namespace}:usage:concurrency
retsu:{namespace}:leases
retsu:{namespace}:lease:{lease_id}
retsu:{namespace}:job:{job_id}
```

Acquisition, release, and renewal use Lua scripts for atomic accounting. Do not
replace those paths with application-side read-modify-write sequences.

## Usage snapshots and cleanup

`get_usage()` returns configured capacity, used capacity, and available capacity
for every resource and concurrency definition:

```python
snapshot = retsu.get_usage()
print(snapshot.resources["memory_mb"].available)
```

Retsu cleans expired leases before acquisition and before usage snapshots. You
can also call `cleanup_expired_leases()` directly or use the CLI `cleanup`
command as an operational maintenance action.

## Job lifecycle in admission mode

Admission mode uses persisted `JobRecord` objects. A typical successful job
moves through these statuses:

```text
queued -> leased -> dispatched -> running -> succeeded
```

If capacity is unavailable during a scheduler pass, the job becomes
`waiting_for_resources` and can be considered again later. Dispatch failures and
runtime exceptions mark the job `failed`, and executors release the lease in a
`finally` path.

## Safety boundaries

Retsu protects capacity accounting. It does not make the guarded work itself
idempotent, transactional, or safe for untrusted input. Admission-mode payloads
and results are serialized with `pickle`, so treat them as trusted-process data.
