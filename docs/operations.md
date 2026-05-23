# Operations

This guide covers the practical details of running Retsu with Redis/Valkey,
observing capacity, sizing leases, and troubleshooting common failures.

## Backend selection

Retsu defaults to the Redis backend:

```python
retsu.configure(backend="redis")
```

Use memory only when process-local state is correct:

```python
retsu.configure(backend="memory")
```

The memory backend is useful for tests and notebooks, but it does not coordinate
between processes.

## Redis/Valkey configuration

The most explicit configuration is:

```python
retsu.configure(
    backend="redis",
    redis_url="redis://localhost:6379/0",
    namespace="production",
)
```

If you rely on environment variables and do not call `configure()` yourself,
Retsu reads these values during import:

```bash
export RETSU_REDIS_URL=redis://localhost:6379/0
export RETSU_NAMESPACE=production
```

If `RETSU_REDIS_URL` is absent, the Redis backend uses the queue helper
variables:

```bash
export RETSU_REDIS_HOST=localhost
export RETSU_REDIS_PORT=6379
export RETSU_REDIS_DB=0
```

Use a distinct `RETSU_NAMESPACE` per environment, test run, or tenant boundary
that needs isolated accounting.

## Capacity bootstrap

Define capacities before workers start executing guarded code:

```python
def configure_retsu() -> None:
    retsu.configure(
        backend="redis",
        redis_url=os.environ["RETSU_REDIS_URL"],
        namespace=os.getenv("RETSU_NAMESPACE", "production"),
    )
    retsu.define_resource("memory_mb", 64_000)
    retsu.define_resource("gpu", 4)
    retsu.define_concurrency("billing-api", 5)
    retsu.define_concurrency("tenant:acme", 1)
```

Capacity definitions are idempotent in normal startup flows. Redefining a
capacity changes the stored capacity without resetting current usage.

## CLI operations

The `retsu` command uses the same backend configuration flags as the Python API:

```bash
retsu --redis-url redis://localhost:6379/0 --namespace production usage
```

Available commands:

```bash
retsu resource memory_mb 64000
retsu concurrency billing-api 5
retsu usage
retsu leases
retsu cleanup
```

Examples with explicit Redis flags:

```bash
retsu --redis-url redis://localhost:6379/0 resource gpu 4
retsu --redis-url redis://localhost:6379/0 concurrency billing-api 5
retsu --redis-url redis://localhost:6379/0 usage
```

## Observability

Use `get_usage()` for metrics and dashboards:

```python
usage = retsu.get_usage()
for name, item in usage.resources.items():
    emit_metric(f"retsu.resource.{name}.used", item.used)
    emit_metric(f"retsu.resource.{name}.available", item.available)
```

Use `list_leases()` for debugging active reservations:

```python
for lease in retsu.list_leases():
    print(lease.id, lease.job_id, lease.owner_id, lease.expires_at)
```

`get_usage()` and `list_leases()` clean expired leases before returning data, so
snapshots should not include expired reservations.

## Lease TTL sizing

Defaults:

| Setting | Default |
| --- | --- |
| `default_ttl_seconds` | `300` |
| `default_acquire_timeout_seconds` | `60` |
| `default_heartbeat_interval_seconds` | `30` |
| `default_wait_strategy` | `block` |

Guidance:

- Make the heartbeat interval comfortably smaller than the TTL.
- Make the TTL long enough to tolerate short pauses, GC, or temporary Redis
  latency.
- Make the acquire timeout match caller expectations. A web request may need a
  short timeout; a batch worker may tolerate a long one.
- Use `cleanup_expired_leases()` or `retsu cleanup` as a safe maintenance action
  if you suspect a worker died while holding leases.

## Redis keys

Redis keys are scoped by namespace:

```text
retsu:{namespace}:capacity:resources
retsu:{namespace}:capacity:concurrency
retsu:{namespace}:usage:resources
retsu:{namespace}:usage:concurrency
retsu:{namespace}:leases
retsu:{namespace}:lease:{lease_id}
retsu:{namespace}:job:{job_id}
```

Avoid deleting broad Redis patterns manually. For tests and controlled tools,
use backend namespace cleanup helpers rather than deleting unrelated keys.

## Security and serialization

Admission-mode args, kwargs, and results are serialized with `pickle`. Treat
those blobs as trusted-process data. Do not expose admission job storage as a
way for untrusted users to submit arbitrary payloads.

Redis should be protected like other application infrastructure: enable network
controls, authentication where appropriate, and environment-specific namespaces.

## Troubleshooting

### `ResourceDefinitionMissing`

The job requested a resource or concurrency name that was not defined in the
current backend namespace.

Check:

```bash
retsu usage
```

Then define the missing capacity during startup or with the CLI.

### Capacity never becomes available

Check active leases:

```bash
retsu leases
retsu cleanup
retsu usage
```

If usage drops after cleanup, a worker likely disappeared and the lease expired.
Consider whether the TTL is too long for your failure-recovery expectations.

### Blocking calls time out

A `ResourceAcquireTimeout` means the `block` strategy waited longer than
`acquire_timeout_seconds`. Either increase capacity, reduce request size,
increase timeout, or switch to `fail`/`retry` and handle backpressure at the
caller.

### Memory backend behaves differently in production

The memory backend coordinates only inside one process. Use Redis/Valkey for
multi-process workers, web applications with multiple processes, Celery, Ray, or
multiple hosts.

## Production checklist

- [ ] Set a deliberate Redis/Valkey namespace.
- [ ] Define every resource and concurrency capacity during startup.
- [ ] Use Redis/Valkey, not memory, for multi-process coordination.
- [ ] Size TTL and heartbeat values for your workload.
- [ ] Export usage metrics for important capacities.
- [ ] Alert on unexpected long-lived leases or sustained zero availability.
- [ ] Keep admission-mode payloads restricted to trusted producers.
- [ ] Test failure paths that raise inside guarded code and executor code.
