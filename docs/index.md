![Retsu logo](images/logo.png)

# Retsu

Retsu is a resource and concurrency control layer for Python background jobs.
It sits beside Celery, Ray, local worker threads, or your own scheduler and
answers one operational question before work starts:

> Is there enough configured capacity available to run this job safely right
> now?

If the answer is yes, Retsu creates a lease and accounts for the capacity. If
not, it can block, fail fast, or let an integration retry later. Leases are
released explicitly when work exits and are also protected by time-to-live based
cleanup if a worker disappears.

## Why use it?

Queues and executors decide *where* work runs. They usually do not understand
all of the external limits your application depends on:

- one SaaS API allows only five concurrent exports;
- a tenant should never run more than one expensive rebuild at a time;
- a worker host has enough CPU threads but not enough GPU memory;
- a licensed solver has a fixed number of seats;
- a batch job needs to reserve memory before it starts, not after it crashes.

Retsu turns those limits into named capacities and applies them consistently
across guarded functions and admission-mode scheduling.

## What Retsu provides

| Area | What you get |
| --- | --- |
| Resource definitions | Named quantitative capacity such as `memory_mb`, `gpu`, or `license_seats`. |
| Concurrency definitions | Named slot limits such as `billing-api`, `tenant:42`, or `reports`. |
| Guard mode | Decorators and context managers that acquire a lease before entering user code. |
| Admission mode | `submit()`, `Scheduler`, executors, and `JobHandle` for resource-aware dispatch. |
| Backends | Redis/Valkey for shared atomic accounting; memory for tests and local tools. |
| Integrations | Celery retry-friendly guards and Ray guard/task helpers. |
| Operations | Usage snapshots, active lease listing, cleanup of expired leases, and a small CLI. |

## The mental model

```text
Define capacity  ->  Evaluate request  ->  Acquire lease  ->  Run work
       ^                    |                    |               |
       |                    |                    v               v
   resources and       static values or      usage increments  release in
   concurrency         callables from        atomically        finally path
                       function args
```

A successful acquire creates exactly one lease. Usage is incremented once for
that lease and decremented once when the lease is released or expires. Redis and
Valkey accounting is implemented with Lua scripts so capacity checks and usage
updates happen atomically.

## Choose a workflow

:::: {.grid}
::: {.g-col-12 .g-col-md-6}
### Guard mode

Use when you already have an execution system and only need to protect a
function or critical section.

```python
@retsu.guard(concurrency={"vendor-api": 1})
def sync_customer(customer_id: str) -> None:
    push_to_vendor(customer_id)
```

[Learn guard mode](guard-mode.md)
:::

::: {.g-col-12 .g-col-md-6}
### Admission mode

Use when jobs should be stored first, admitted only after capacity is acquired,
and then dispatched by a scheduler.

```python
handle = retsu.submit(render, args=("scene-42",), resources={"gpu": 1})
retsu.Scheduler().run_once()
result = handle.result(timeout=30)
```

[Learn admission mode](admission-mode.md)
:::
::::

## When Retsu is a good fit

Retsu is a good fit when capacity is an application-level concern and the
resource cannot be expressed cleanly as a worker-pool size. Examples include
external API quotas, tenant locks, GPU fractions, memory reservations, and
licensed software seats.

Retsu is not a replacement for a durable task queue, a general distributed lock
service, or a full autoscaler. It complements those tools by making admission
resource-aware.

## Start here

1. Follow the [quickstart](quickstart.md) for a copy-paste local example.
2. Read [concepts](concepts.md) to understand resources, leases, and wait
   policies.
3. Use [guard mode](guard-mode.md) for protected functions and critical
   sections.
4. Use [admission mode](admission-mode.md) when work should be scheduled after
   capacity is acquired.
5. Review [operations](operations.md) before using Redis/Valkey in production.
