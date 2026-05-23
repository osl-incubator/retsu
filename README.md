# Retsu

Retsu is a lightweight resource and concurrency control layer for Python
background jobs. It lets you describe the capacity your system has, describe
what each unit of work needs, and run that work only while a lease for the
required capacity is active.

Use Retsu when a queue, worker pool, or distributed executor needs one more
safety layer:

- limit calls to a fragile API without serializing unrelated work;
- cap GPU, memory, license-seat, tenant, or database pressure across workers;
- block, fail fast, or hand control back to Celery retry when capacity is full;
- release capacity predictably after success, failure, timeout, or lease expiry;
- use Redis/Valkey for atomic cross-process accounting, or memory for local
  tests and small single-process tools.

Documentation: <https://osl-incubator.github.io/retsu>

License: BSD 3-Clause

## Install

```bash
pip install retsu
```

Optional integrations are installed only when you ask for them:

```bash
pip install "retsu[celery]"
pip install "retsu[ray]"
pip install "retsu[django]"
```

Retsu supports Python `>=3.10,<4`.

## A 60-second example

The memory backend is perfect for local development and tests:

```python
import retsu

retsu.configure(backend="memory")
retsu.define_resource("memory_mb", 1_000)
retsu.define_concurrency("image-api", 2)

@retsu.guard(
    resources={"memory_mb": lambda image: image.size_mb},
    concurrency={"image-api": 1},
)
def transform(image):
    return image.resize()
```

When `transform()` is called, Retsu evaluates the request, acquires capacity,
renews the lease while the function runs, and releases the lease in a `finally`
path. If the request cannot fit, the configured wait strategy decides whether
Retsu blocks, raises immediately, or lets an integration retry later.

## Core ideas

| Concept | Meaning |
| --- | --- |
| Resource | A named quantitative capacity such as `memory_mb`, `gpu`, or `tokens_per_second`. |
| Concurrency | A named slot limit such as `vendor-api`, `tenant:acme`, or `db-writer`. |
| Request | The amount of each resource/concurrency a job needs. Requests can be static numbers or callables evaluated from function arguments. |
| Lease | A time-limited reservation. Usage is incremented once on acquire and decremented once on release or cleanup. |
| Backend | Storage and atomic accounting. Redis/Valkey is the default backend; memory is available for tests and local tools. |

## Guard mode

Guard mode protects a function or critical section you execute yourself:

```python
import retsu

retsu.configure(backend="redis", redis_url="redis://localhost:6379/0")
retsu.define_concurrency("billing-api", 5)

@retsu.guard(concurrency={"billing-api": 1}, wait_strategy="fail")
def charge_invoice(invoice_id: str) -> None:
    call_billing_provider(invoice_id)
```

You can also guard a block:

```python
with retsu.limit("billing-api", slots=1):
    call_billing_provider(invoice_id)
```

## Admission mode

Admission mode stores jobs, lets a scheduler acquire resources before dispatch,
and returns a handle for status/result access:

```python
import retsu

retsu.configure(backend="memory")
retsu.define_resource("cpu", 2)
retsu.define_concurrency("reports", 1)

def build_report(report_id: str) -> str:
    return f"built {report_id}"

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

The local executor runs admitted jobs in daemon threads. A Ray executor is also
available for Ray-backed dispatch.

## Redis/Valkey in production

Redis/Valkey is the default backend because it provides shared, atomic capacity
accounting across processes. Configure it explicitly:

```python
import retsu

retsu.configure(
    backend="redis",
    redis_url="redis://localhost:6379/0",
    namespace="production",
    default_ttl_seconds=300,
    default_acquire_timeout_seconds=60,
)
```

Or configure through environment variables before the application imports
Retsu:

```bash
export RETSU_REDIS_URL=redis://localhost:6379/0
export RETSU_NAMESPACE=production
```

If `RETSU_REDIS_URL` is not provided, Retsu uses `RETSU_REDIS_HOST`,
`RETSU_REDIS_PORT`, and `RETSU_REDIS_DB`.

## Command line

The `retsu` command can define capacities and inspect Redis/Valkey state:

```bash
retsu --redis-url redis://localhost:6379/0 resource memory_mb 16000
retsu --redis-url redis://localhost:6379/0 concurrency image-api 4
retsu --redis-url redis://localhost:6379/0 usage
retsu --redis-url redis://localhost:6379/0 leases
retsu --redis-url redis://localhost:6379/0 cleanup
```

## Development

```bash
mamba env create --file conda/dev.yaml
conda activate retsu
poetry install
pytest -q -m no_services
```

For the full Redis-backed suite, start the Valkey service through the project
automation and run the unit task:

```bash
makim tests.unit
```

See the contributor guide for the full quality gate.
