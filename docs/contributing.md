# Contributing

Thank you for improving Retsu. The project is small, but it protects important
resource-safety guarantees, so changes should be focused, tested, and easy to
audit.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/retsu/` | Public APIs, configuration, leases, resources, scheduling, and state models. |
| `src/retsu/backends/` | Backend protocol plus memory and Redis/Valkey implementations. |
| `src/retsu/executors/` | Admission-mode executor protocol and local/Ray executors. |
| `src/retsu/integrations/` | Celery and Ray guard helpers. |
| `src/retsu/plugins/` | Framework plugins such as Django app config support. |
| `src/retsu/cli/` | `retsu` command line interface. |
| `tests/` | Memory-only and Redis-backed tests. |
| `docs/` | Quarto documentation. |
| `examples/` | Usage examples and example notes. |
| `containers/` | Valkey and optional worker container definitions. |

The package uses the `src` layout. Import package code as `retsu`, not through
local path hacks.

## Development setup

```bash
git clone https://github.com/osl-incubator/retsu.git
cd retsu
mamba env create --file conda/dev.yaml
conda activate retsu
poetry install
pre-commit install
```

Conda also works if Mamba is not installed:

```bash
conda env create --file conda/dev.yaml
conda activate retsu
poetry install
```

## High-value commands

Fast service-free tests:

```bash
pytest -q -m no_services
```

Full unit suite with Redis/Valkey managed by project automation:

```bash
makim tests.unit
```

Redis backend only, after starting services:

```bash
makim tests.setup
pytest -q tests/test_redis_backend.py
makim tests.teardown
```

Linting, typing, and pre-commit checks:

```bash
ruff format src tests
ruff check src tests
mypy .
pre-commit run --all-files
makim tests.linter
```

Documentation build:

```bash
makim docs.build
```

## Design priorities

1. Never over-allocate configured capacity.
2. Release leases exactly once on success, failure, timeout, and cleanup paths.
3. Keep memory and Redis/Valkey behavior aligned.
4. Keep Redis capacity accounting atomic; do not replace Lua-scripted acquire or
   release paths with Python read-modify-write sequences.
5. Keep optional integrations optional at import time.
6. Update docs, examples, and API references for user-facing behavior changes.
7. Prefer small targeted edits over broad refactors.

## Testing expectations

- Add or update tests near the behavior you change.
- Mark service-free tests with `pytest.mark.no_services`.
- Mark Redis/Valkey integration tests with `pytest.mark.redis`.
- For backend behavior, cover both memory and Redis where the feature applies.
- For scheduler/executor behavior, test status transitions, result handling,
  failure handling, and lease release.
- For CLI behavior, test return codes and user-facing output.

## Documentation expectations

Update documentation in the same change when behavior changes:

- `README.md` for high-level positioning and quick examples;
- `docs/index.md` for the website overview;
- topic pages such as `guard-mode.md`, `admission-mode.md`, and
  `operations.md` for workflow details;
- `docs/api/references.md` for public API changes;
- `examples/` when example usage changes.

Do not commit generated Quarto output from `build/` unless a task explicitly
asks for it.

## Style

- Python line length is 79 characters.
- Mypy is strict; avoid unnecessary `Any` and broad `type: ignore` comments.
- Ruff handles formatting, import order, pycodestyle, pyflakes, pydocstyle, and
  pyupgrade-style checks.
- Use existing Retsu exception types for expected user-facing errors.
- Do not use heredocs inside YAML-backed configuration files.

## Pull request checklist

Before opening a PR, verify:

- [ ] tests cover the behavior change;
- [ ] resource accounting cannot over-allocate or go negative;
- [ ] leases release on success, failure, and cleanup paths;
- [ ] memory and Redis behavior remain aligned where applicable;
- [ ] optional dependencies remain optional;
- [ ] public API changes are reflected in docs and examples;
- [ ] `ruff`, `mypy`, and relevant tests pass, or blockers are clearly stated.

## Commit messages and releases

Retsu uses semantic-release. Pull request titles should follow conventional
commit style because squash-merge titles drive release notes:

```text
fix: release leases after dispatch failure
feat: add scheduler queue filtering
chore: update development dependencies
```

Use `!` for breaking changes:

```text
feat!: change admission result serialization format
```
