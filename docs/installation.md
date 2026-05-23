# Installation

Retsu supports Python `>=3.10,<4` and uses Redis/Valkey as its default shared
backend. The memory backend is included for local development, notebooks, and
service-free tests.

## Package install

```bash
pip install retsu
```

Verify the package imports:

```bash
python -c "import retsu; print(retsu.__version__)"
```

## Optional integrations

Install only the framework integrations you use:

```bash
pip install "retsu[celery]"
pip install "retsu[ray]"
pip install "retsu[django]"
```

You can combine extras:

```bash
pip install "retsu[celery,ray]"
```

## Redis or Valkey

For production-style multi-process coordination, run Redis or Valkey and point
Retsu at it:

```python
import retsu

retsu.configure(
    backend="redis",
    redis_url="redis://localhost:6379/0",
    namespace="my-app",
)
```

You can also configure the default Redis backend with environment variables
before your application imports Retsu:

```bash
export RETSU_REDIS_URL=redis://localhost:6379/0
export RETSU_NAMESPACE=my-app
```

If `RETSU_REDIS_URL` is not set, Retsu falls back to host/port/db variables:

```bash
export RETSU_REDIS_HOST=localhost
export RETSU_REDIS_PORT=6379
export RETSU_REDIS_DB=0
```

## Local-only install without Redis service

No Redis service is required for the memory backend:

```python
import retsu

retsu.configure(backend="memory")
retsu.define_concurrency("local-demo", 1)
```

Use this backend for unit tests and examples that do not need cross-process
coordination.

## Install from source

Clone the repository and install development dependencies:

```bash
git clone https://github.com/osl-incubator/retsu.git
cd retsu
mamba env create --file conda/dev.yaml
conda activate retsu
poetry install
```

If you use Conda instead of Mamba:

```bash
conda env create --file conda/dev.yaml
conda activate retsu
poetry install
```

## Run checks from a checkout

Fast tests that do not require services:

```bash
pytest -q -m no_services
```

Full unit suite with Redis/Valkey managed by the project automation:

```bash
makim tests.unit
```

Linting, typing, and pre-commit checks:

```bash
ruff format src tests
ruff check src tests
mypy .
pre-commit run --all-files
```

Documentation build:

```bash
makim docs.build
```

## Common installation issues

### Redis connection refused

Either start Redis/Valkey, set the correct `RETSU_REDIS_URL`, or use
`retsu.configure(backend="memory")` for local examples.

### Optional integration import errors

Install the matching extra. For example, `retsu.ray_task()` requires Ray:

```bash
pip install "retsu[ray]"
```

### Different environments share usage unexpectedly

Set a unique `RETSU_NAMESPACE` per environment:

```bash
export RETSU_NAMESPACE=staging
```
