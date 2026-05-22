# AI Skill: Retsu Contributor Guide

This file is the shared operating manual for AI contributors working in
`retsu`. Use it to keep implementation style, review standards, and delivery
quality consistent across different agents.

## When To Use This Skill

Use this guidance for any change inside the Retsu repository:

- resource or concurrency-control behavior
- backend changes, especially Redis/Valkey Lua-script accounting
- lease, heartbeat, cleanup, and owner-safety behavior
- admission scheduler, executors, job state, or job handle APIs
- Celery, Ray, Django, or CLI integrations
- docs, examples, packaging, release, CI, typing, lint, and tests

## Core Objectives

1. Preserve resource-safety guarantees: never over-allocate configured capacity.
2. Keep lease lifecycle behavior predictable: acquire, renew, release, expire,
   and cleanup must leave usage accounting consistent.
3. Keep optional integrations optional and lightweight at import time.
4. Keep public API, docs, examples, and tests synchronized.
5. Keep code quality gates green: tests, coverage, mypy, ruff, and pre-commit.
6. Make minimal, targeted edits with clear intent.

## Project Snapshot

- Package: `retsu`
- Runtime: Python `>=3.10,<4`
- Purpose: lightweight resource and concurrency control for Python background
  jobs.
- Main modes:
  - Guard mode: protect a function or critical section with resource leases.
  - Admission mode: submit jobs, acquire resources, then dispatch through an
    executor.
- Default backend: Redis/Valkey via `redis`.
- Local/test backend: in-memory backend.
- Optional integrations: Celery, Django, Ray.
- Docs stack: Quarto.
- Automation: Makim plus pre-commit.

## Repository Layout

- `src/retsu/`: package implementation.
- `src/retsu/backends/`: backend protocol plus memory and Redis backends.
- `src/retsu/executors/`: admission-mode executor protocol and local/Ray
  executors.
- `src/retsu/integrations/`: Celery and Ray guard helpers.
- `src/retsu/plugins/`: framework plugins such as Django app config support.
- `src/retsu/cli/`: `retsu` command line interface.
- `tests/`: pytest coverage for memory-only and Redis-backed behavior.
- `examples/`: runnable examples and supporting README files.
- `docs/`: Quarto documentation.
- `containers/`: Valkey and optional worker container definitions.
- `conda/dev.yaml`: development environment.
- `.makim.yaml`: local task runner definitions.
- `.github/workflows/`: CI, documentation, and release workflows.

## Architecture And Responsibilities

### Public API Surface

`src/retsu/__init__.py` re-exports the public API. When adding or removing a
public object:

- update `__all__` and imports intentionally;
- preserve `src/retsu/py.typed` support;
- update `docs/api/references.md` and examples when user-facing behavior
  changes;
- avoid exposing backend internals unless they are meant to be stable.

### Configuration

`src/retsu/config.py` owns process-global runtime configuration.

- `configure()` resets the cached backend.
- `get_backend()` lazily creates the configured backend.
- Supported backend names are currently `redis` and `memory`.
- Redis configuration may come from `RETSU_REDIS_URL`, `RETSU_NAMESPACE`, or the
  queue helper environment variables `RETSU_REDIS_HOST`, `RETSU_REDIS_PORT`, and
  `RETSU_REDIS_DB`.

### Backend Boundary

`src/retsu/backends/base.py` defines the backend protocol. Backend
implementations own storage, atomic accounting, lease persistence, and job
persistence.

- Keep `MemoryBackend` and `RedisBackend` behavior aligned.
- New backend features must be represented in the protocol and covered in both
  generic behavior tests and backend-specific tests where possible.
- Redis capacity acquisition/release/renewal is intentionally implemented with
  Lua scripts for atomicity. Do not replace atomic Redis operations with
  read-modify-write Python sequences.
- Redis keys must remain namespace-scoped under `retsu:{namespace}:...`.
- `flush_namespace()` is a test/helper capability; avoid broad key deletion.

### Resource And Lease Model

`src/retsu/resources.py`, `src/retsu/leases.py`, and `src/retsu/task.py` define
resource requests, lease behavior, and the public guard APIs.

Preserve these invariants:

- Resource and concurrency names must be non-empty strings.
- Requested values must be finite and non-negative; zero-value requests are
  ignored.
- Undefined capacity requests raise `ResourceDefinitionMissing`.
- A successful acquire returns one lease id and increments usage exactly once.
- Release and cleanup subtract usage exactly once and never allow negative
  usage.
- Renew and release must respect owner ids when an owner is supplied.
- Expired leases are cleaned before usage snapshots and capacity acquisition.
- Guard/context-manager paths release leases in `finally`, including exception
  paths.
- Heartbeat threads must be daemonized and stopped when the guarded section
  exits.
- Wait strategies must keep their current semantics:
  - `block`: wait until capacity is available or timeout expires;
  - `fail`: raise `ResourceUnavailable` immediately;
  - `retry`: raise `ResourceUnavailable` so integrations such as Celery can
    trigger their retry flow.

### Admission Mode

`submit()`, `JobHandle`, `Scheduler`, backend job methods, and executors make up
admission mode.

Preserve these invariants:

- `submit()` stores a `JobRecord` with serialized args/kwargs and an evaluated
  resource/concurrency request.
- Local execution uses `_LOCAL_FUNCTIONS` for in-process functions.
- Schedulers must acquire capacity before dispatching a job.
- Dispatch failures must release acquired leases and mark the job failed.
- Executors must release leases after success or failure.
- Job state timestamps should be set consistently when transitioning to leased,
  running, and terminal states.
- `JobHandle.result()` must return successful results, raise on failed or
  cancelled jobs, and honor timeouts.

`pickle` is currently used for admission-mode payloads and results. Treat these
payloads as trusted-process data unless a task explicitly changes the security
model; do not claim that serialized job storage is safe for untrusted inputs.

### Optional Integrations

Celery, Django, and Ray support should not make the base package expensive or
surprising to import.

- Prefer lazy imports for optional runtime dependencies where practical.
- Keep integration-specific behavior inside `integrations/`, `executors/`, or
  `plugins/` rather than leaking framework assumptions into core APIs.
- Celery retry behavior should continue to convert retry-style resource denial
  into `task.retry(...)`.
- Ray helpers should guard work with the same lease semantics as core guard
  mode.

### CLI

`src/retsu/cli/main.py` provides the `retsu` console script.

- Keep CLI output stable unless the task explicitly changes it.
- Return integer exit codes from `main()`.
- Add tests for new commands and user-facing errors.

## Behavior Rules You Must Preserve

Current Retsu behavior includes:

- Resources and concurrency limits are defined separately.
- Capacity values are floats internally.
- Resource/concurrency requests may be static values or callables evaluated with
  the wrapped function arguments.
- Estimator failures are wrapped in `ResourceEstimationError` before acquiring a
  lease.
- Memory backend is thread-safe and suitable for no-service tests.
- Redis backend uses Valkey/Redis hashes, sorted sets, and Lua scripts to keep
  capacity accounting atomic.
- `get_usage()` reports used, capacity, and available values for configured
  capacities.
- `cleanup_expired_leases()` returns expired lease ids and restores usage.
- `limit(name, slots=1)` is a convenience context manager for concurrency.
- `guard(...)` preserves wrapped function metadata via `functools.wraps`.
- Default config uses the Redis backend, namespace `default`, TTL `300`, acquire
  timeout `60`, heartbeat interval `30`, and wait strategy `block`.

If you change any of these behaviors, update tests, docs, examples, and CLI/API
references in the same change.

## Code Style And Standards

### Design Principles

- Prefer small, focused changes over broad refactors.
- Keep resource-safety paths explicit and easy to audit.
- Use guard clauses and early returns where they reduce nesting.
- Avoid obvious comments; comment non-trivial concurrency, Redis, or lifecycle
  decisions.
- Do not update unrelated files just to clean up style.

### Python Style

- Use the `src` layout and import through `retsu`, not local path hacks.
- Use 4-space indentation for Python.
- Use explicit type annotations for new and changed code.
- Keep line length at 79 characters (`ruff`).
- Ruff is configured for pycodestyle, pyflakes, pydocstyle, pyupgrade-style
  checks, Ruff rules, and import ordering.
- Pydocstyle convention is NumPy, but current docstrings are concise one-line or
  short standard docstrings. Keep new public docstrings clear and consistent.
- Mypy is strict (`check_untyped_defs = true`, `strict = true`). Avoid `Any` and
  `type: ignore` unless the boundary truly requires it; narrow ignores to a
  specific error code when possible.
- Keep `py.typed` in the package.

### YAML And Automation

- Never use heredocs inside YAML files in this repository.
- This applies to CI and automation configs such as `.github/workflows/*.yaml`
  and `.makim.yaml`.
- In YAML-backed task/config files, prefer plain shell commands or direct
  command invocations over embedded `<<EOF` / `<<'PY'` blocks.

### Error Handling

- Use existing Retsu exception types for user-facing resource errors:
  `RetsuError`, `ResourceDefinitionMissing`, `ResourceUnavailable`,
  `ResourceAcquireTimeout`, `ResourceEstimationError`,
  `RetsuBackendUnavailable`, and `JobNotFound`.
- Do not raise generic `Exception` for new expected error paths.
- Keep exception messages explicit enough for tests and users to diagnose the
  missing resource, unavailable capacity, or unsupported configuration.

## Tooling And Commands

Environment setup:

```bash
mamba env create --file conda/dev.yaml
conda activate retsu
poetry install
```

High-value local commands:

```bash
# Fast memory-only tests that do not need Redis/Valkey
pytest -q -m no_services

# Full unit suite with coverage; starts Valkey through Makim/Sugar
makim tests.unit

# Redis backend only, after starting services
makim tests.setup
pytest -q tests/test_redis_backend.py
makim tests.teardown

# Lint, typing, and security/dead-code hooks
ruff format src tests
ruff check src tests
mypy .
pre-commit run --all-files
makim tests.linter

# Package and docs
poetry build
makim docs.build
```

Notes:

- `makim tests.unit` runs `pytest` with `--cov=retsu`, terminal missing report,
  and `--cov-fail-under=90`.
- `tests/conftest.py` skips Redis setup only when all selected tests are marked
  `no_services`.
- Valkey is defined in `containers/compose.yaml` and managed through
  `containers-sugar`/`compose-go` tasks.

## CI Contract

GitHub Actions currently run:

- branch freshness check on pull requests;
- conda environment creation from `conda/dev.yaml`;
- `poetry install`;
- `makim tests.unit`;
- `makim tests.linter` via pre-commit;
- documentation build in the docs workflow;
- semantic-release dry run on pull requests and pushes to `main`.

Do not rely on a local change that bypasses these commands. If you cannot run a
required check locally, report the blocker and the exact command that remains
unverified.

## Documentation Contract

When user-facing behavior changes, update documentation in the same PR:

- `README.md` for high-level usage and project positioning;
- `docs/index.md` for website overview;
- `docs/installation.md` if installation, extras, or dependency behavior
  changes;
- `docs/api/references.md` for public API changes;
- `examples/` when adding or changing usage patterns.

Quarto builds into `build/`; do not commit generated docs output unless the task
explicitly asks for it.

## Testing Contract

- Prefer targeted tests near changed behavior.
- Use `pytest.mark.no_services` for tests that use `MemoryBackend` and do not
  need Redis/Valkey.
- Use `pytest.mark.redis` for Redis backend integration coverage.
- For backend changes, add or update tests for both memory behavior and Redis
  behavior when the feature applies to both.
- For concurrency/resource changes, test acquire denial, release, cleanup, and
  no-over-allocation behavior.
- For scheduler or executor changes, test success, failure, status transitions,
  result retrieval, and lease release.
- For CLI changes, test return codes and output.
- Keep coverage at or above the configured threshold.

## Examples Contract

- Keep `examples/` runnable and synchronized with docs.
- Do not invent APIs in examples that are not implemented in `src/retsu`.
- Example changes should prefer the public `retsu` package API rather than
  backend internals.
- If an example requires external services, document startup commands and
  environment variables clearly.

## Change Playbooks

### Adding Or Changing Backend Behavior

1. Update the `Backend` protocol if the contract changes.
2. Update `MemoryBackend` first for clear semantics.
3. Update `RedisBackend` using atomic Redis operations or Lua scripts.
4. Add memory-only tests and Redis tests.
5. Update docs/API references if public behavior changes.

### Adding Or Changing Public APIs

1. Implement behavior in the smallest appropriate module.
2. Re-export intentionally from `src/retsu/__init__.py` if public.
3. Update type annotations, docstrings, and `__all__`.
4. Add tests for success and failure paths.
5. Update `docs/api/references.md`, README/docs examples, and changelog-related
   notes if needed.

### Changing Guard Or Lease Behavior

1. Preserve `finally` release behavior and heartbeat shutdown.
2. Verify timeout, fail, retry, and block strategies.
3. Test exception paths and expired lease cleanup.
4. Confirm usage accounting returns to zero after release/failure.

### Changing Admission Scheduling

1. Keep capacity acquisition before dispatch.
2. Keep status transitions and timestamps consistent.
3. Ensure every dispatch path releases leases.
4. Test `JobHandle.status()`, `result()`, `metadata()`, and `cancel()` when
   affected.
5. Avoid changing serialization or trusted-data assumptions without an explicit
   design update.

### Adding Or Changing Integrations

1. Keep framework-specific imports and behavior isolated.
2. Preserve core lease semantics and exception behavior.
3. Add tests with light fakes/mocks when external runtimes are heavy.
4. Document required optional extras and environment setup.

### Changing CLI Behavior

1. Update `src/retsu/cli/main.py` with stable parsing and explicit exit codes.
2. Add tests around command output and return values.
3. Update docs or examples for user-facing command changes.

## Contributor Workflow Expectations

1. Inspect local files before planning or editing.
2. Make minimal focused changes.
3. Add or update tests for behavior changes.
4. Run targeted checks first, then broader quality checks when practical.
5. Keep docs/examples in sync with behavior.
6. Use conventional commits in PR titles; releases use semantic-release and
   squash-merge.

## PR Review Checklist For AI Agents

Before final output, verify:

- [ ] behavior change is covered by tests;
- [ ] memory and Redis behavior remain aligned where applicable;
- [ ] resource accounting cannot over-allocate or go negative;
- [ ] leases are released on success, failure, and cleanup paths;
- [ ] optional integrations remain optional/lazy where practical;
- [ ] public API changes are reflected in `__init__.py`, docs, and examples;
- [ ] `mypy` passes for touched code or blockers are reported;
- [ ] `ruff` and pre-commit hooks pass or blockers are reported;
- [ ] no unrelated refactors or formatting churn were introduced;
- [ ] error messages are explicit and actionable.

## Non-Goals / Avoid

- Do not weaken atomicity in Redis/Valkey accounting.
- Do not bypass lease ownership checks.
- Do not add framework-specific assumptions to core modules.
- Do not make optional dependencies mandatory without a documented packaging
  change.
- Do not lower coverage or remove tests to make a change pass.
- Do not commit generated caches, coverage output, build artifacts, or
  `__pycache__` directories.
- Do not use heredocs in YAML workflows or Makim configuration.
