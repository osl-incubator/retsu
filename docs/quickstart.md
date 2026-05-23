# Quickstart

This page gets you from a new environment to resource-aware execution in a few
minutes. The examples use the memory backend first so you can run them without
Redis or Valkey.

## Install

```bash
pip install retsu
```

For development from a checkout:

```bash
mamba env create --file conda/dev.yaml
conda activate retsu
poetry install
```

## Local guard example

Create a file named `quickstart.py`:

```python
from dataclasses import dataclass

import retsu


@dataclass
class Image:
    id: str
    size_mb: int


retsu.configure(backend="memory")
retsu.define_resource("memory_mb", 512)
retsu.define_concurrency("image-transform", 2)


@retsu.guard(
    resources={"memory_mb": lambda image: image.size_mb},
    concurrency={"image-transform": 1},
)
def transform(image: Image) -> str:
    return f"transformed {image.id}"


print(transform(Image(id="hero", size_mb=128)))
print(retsu.get_usage().resources["memory_mb"].used)
```

Run it:

```bash
python quickstart.py
```

The final usage value is `0` because the lease is released after `transform()`
returns.

## What happened?

1. `configure(backend="memory")` selected a local, thread-safe backend.
2. `define_resource()` and `define_concurrency()` registered capacity.
3. The `guard()` decorator built a request from the function arguments.
4. Retsu acquired a lease before calling `transform()`.
5. A heartbeat renewed the lease while the function was running.
6. The lease was released in a `finally` path.

## Try an unavailable capacity

```python
import retsu

retsu.configure(backend="memory")
retsu.define_concurrency("api", 1)

held = retsu.acquire_with_policy(
    job_id="manual",
    owner_id="quickstart",
    request=retsu.ResourceRequest(resources={}, concurrency={"api": 1}),
)

try:
    with retsu.limit("api", wait_strategy="fail"):
        print("will not run")
except retsu.ResourceUnavailable as exc:
    print(f"blocked by {exc.blocked_by}")
finally:
    held.release()
```

`wait_strategy="fail"` raises `ResourceUnavailable` immediately instead of
waiting for the held lease to release.

## Move to Redis or Valkey

Use Redis/Valkey when multiple processes need shared accounting:

```python
import retsu

retsu.configure(
    backend="redis",
    redis_url="redis://localhost:6379/0",
    namespace="quickstart",
)
retsu.define_resource("memory_mb", 4096)
retsu.define_concurrency("image-transform", 4)
```

Capacity definitions live in the selected backend namespace. Define them during
application startup or through the CLI before workers begin accepting work.

## Admission-mode quickstart

Admission mode stores a job first, then dispatches it only after the scheduler
gets a lease:

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

print(handle.status())
print(handle.result(timeout=5))
print(handle.metadata())
```

For a long-running service, call `run_once()` from your own loop or scheduler
process:

```python
import time

scheduler = retsu.Scheduler()

while True:
    scheduler.run_once(limit=100)
    time.sleep(0.5)
```

## Next steps

- Read [concepts](concepts.md) for the resource and lease model.
- Use [guard mode](guard-mode.md) if your work is already dispatched elsewhere.
- Use [admission mode](admission-mode.md) for resource-aware job dispatch.
- Review [operations](operations.md) before sharing Redis/Valkey state in
  production.
