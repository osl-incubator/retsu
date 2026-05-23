# Integrations

Retsu keeps framework-specific behavior outside the core APIs. Optional
integrations add convenience around Celery, Ray, and Django without making those
packages mandatory for basic use.

## Optional dependencies

```bash
pip install "retsu[celery]"
pip install "retsu[ray]"
pip install "retsu[django]"
```

The base package installs Redis support because Redis/Valkey is the default
backend.

## Celery

Use `celery_guard()` inside a bound Celery task when capacity denial should use
Celery's retry mechanism:

```python
import retsu

from celery import Celery

app = Celery(__name__)

retsu.configure(backend="redis", redis_url="redis://localhost:6379/0")
retsu.define_concurrency("pdf-render", 2)


@app.task(bind=True)
def render_pdf(self, document_id: str) -> None:
    with retsu.celery_guard(
        self,
        concurrency={"pdf-render": 1},
        wait_strategy="retry",
    ):
        render_document(document_id)
```

When `wait_strategy="retry"`, `celery_guard()` catches
`ResourceUnavailable` and raises `task.retry(countdown=...)`. For `fail` or
`block`, it preserves the core Retsu behavior.

Recommended Celery pattern:

1. configure Retsu when the worker starts;
2. define capacities once per namespace;
3. wrap the smallest section that needs the scarce capacity;
4. use Celery retry options for backoff, max retries, and dead-letter behavior.

## Ray guard helpers

Use `ray_guard()` when a Ray task already exists and only a section needs Retsu
capacity:

```python
import ray
import retsu

retsu.configure(backend="redis", redis_url="redis://localhost:6379/0")
retsu.define_resource("gpu-memory", 1)


@ray.remote
def train_one(model_id: str) -> str:
    with retsu.ray_guard(resources={"gpu-memory": 1}):
        return train(model_id)
```

Use `ray_task()` when you want one decorator to create a Ray remote function and
wrap it with Retsu guard mode:

```python
@retsu.ray_task(resources={"gpu-memory": 1}, num_gpus=1)
def train_one(model_id: str) -> str:
    return train(model_id)
```

The keyword arguments after the Retsu parameters are passed to `ray.remote`.
Ray controls cluster placement; Retsu controls your named application capacity.

## Ray executor for admission mode

Admission jobs can request the Ray executor:

```python
handle = retsu.submit(
    train,
    args=("model-a",),
    resources={"gpu-memory": 1},
    executor="ray",
)
retsu.Scheduler().run_once()
```

The scheduler acquires Retsu capacity first, then dispatches the function to
Ray. A local daemon thread waits for `ray.get()` and releases the lease when the
Ray task finishes or fails.

## Django

Most Django applications should configure Retsu in application startup code and
then use the public guard or admission APIs from views, tasks, or management
commands.

The package also includes `retsu.plugins.django.create_app_config()` for
manager-style integrations that need `start()` on app readiness and `stop()` on
`request_finished`:

```python
from retsu.plugins.django import create_app_config

RetsuAppConfig = create_app_config(manager, app_name="myapp")
```

This helper expects the supplied manager object to expose `start()` and
`stop()` methods. Import it only in Django projects that install the `django`
extra.

## Integration checklist

- Keep Retsu configuration and capacity bootstrap close to worker startup.
- Use Redis/Valkey for any integration that runs in multiple processes.
- Keep framework imports out of modules that should remain lightweight.
- Match wait strategy to the framework: `retry` for Celery retry flows, `fail`
  for request/response paths, and `block` for worker paths where waiting is
  acceptable.
- Treat Retsu capacity as one layer of protection; still configure executor
  worker counts, Celery retry limits, and Ray resource options appropriately.
