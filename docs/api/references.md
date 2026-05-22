# API Reference

Retsu exposes a small public API from the `retsu` package.

## Configuration

- `retsu.configure`
- `retsu.get_config`
- `retsu.get_backend`
- `retsu.set_backend`

## Capacity Definitions

- `retsu.define_resource`
- `retsu.define_concurrency`
- `retsu.get_usage`
- `retsu.list_leases`
- `retsu.cleanup_expired_leases`

## Guard Mode

- `retsu.guard`
- `retsu.acquire`
- `retsu.limit`
- `retsu.celery_guard`
- `retsu.ray_guard`
- `retsu.ray_task`

## Admission Mode

- `retsu.submit`
- `retsu.JobHandle`
- `retsu.Scheduler`

## Core Models

- `retsu.ResourceSpec`
- `retsu.ResourceRequest`
- `retsu.AcquireResult`
- `retsu.UsageSnapshot`
- `retsu.UsageItem`
- `retsu.JobRecord`
- `retsu.JobStatus`
- `retsu.LeaseRecord`

## Exceptions

- `retsu.RetsuError`
- `retsu.ResourceUnavailable`
- `retsu.ResourceAcquireTimeout`
- `retsu.ResourceDefinitionMissing`
- `retsu.ResourceEstimationError`
- `retsu.RetsuBackendUnavailable`
