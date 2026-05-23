# Retsu examples

This directory contains example material for Retsu. The current public API is
best demonstrated in the documentation pages:

- [Quickstart](../docs/quickstart.md)
- [Guard mode](../docs/guard-mode.md)
- [Admission mode](../docs/admission-mode.md)
- [Integrations](../docs/integrations.md)

## Service-free local example

```python
import retsu

retsu.configure(backend="memory")
retsu.define_concurrency("api", 1)

with retsu.limit("api"):
    print("only one protected section can run at a time")
```

## Local admission example

```python
import retsu

retsu.configure(backend="memory")
retsu.define_resource("cpu", 2)


def double(value: int) -> int:
    return value * 2


handle = retsu.submit(double, args=(21,), resources={"cpu": 1})
retsu.Scheduler().run_once()
print(handle.result(timeout=5))
```

## Existing subdirectories

`redis_queue_between_tasks/` is a legacy Celery/Flask example from an earlier
Retsu API. It remains in the repository for historical context while the modern
documentation focuses on the current guard, admission, Celery, and Ray APIs.
