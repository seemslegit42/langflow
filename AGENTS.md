# AGENTS.md

Langflow is a visual AI workflow builder. Python/FastAPI backend + React 19/TypeScript frontend + lightweight `lfx` executor. Monorepo managed by `uv` workspaces and `make`.

## Prerequisites

- Python 3.10–3.14, `uv >=0.4`, Node >=20.19.0 (22.12 LTS recommended), npm >=10.9, `make`
- Always use `uv run <cmd>` for Python (ensures venv + pre-commit hooks). Bare `python`/`pytest` will miss deps.
- Sub-package tests need their dev group: `uv sync --group dev --package langflow-base` (same for `lfx`). Top-level `uv sync` alone leaves `fakeredis` etc. uninstalled.

## Commands

```bash
make init                # install backend+frontend deps + pre-commit hooks (first setup)
make run_cli             # build frontend + run on :7860 (quick run from source)
make run_clic            # clean frontend build then run (use when frontend stale)
make backend             # dev FastAPI on :7860 (hot reload)
make frontend            # Vite dev on :3000 (run alongside backend)

# component dev — prebuilt index is default; dynamic loading only with LFX_DEV:
LFX_DEV=1 make backend
LFX_DEV=openai,anthropic make backend  # load only listed modules (faster)
# without LFX_DEV, rebuild index after component changes:
uv run python scripts/build_component_index.py

make format_backend      # ruff check --fix + ruff format
make format_frontend     # biome check --write (src/frontend/biome.json)
make format              # both
make lint                # currently stub — prints "No type checker configured. See PR #12448"
uv run mypy --namespace-packages -p langflow  # manual typecheck (CI runs mypy matrix 3.10–3.14)

make unit_tests                    # pytest src/backend/tests/unit, parallel (-n auto), skips api_key_required
make unit_tests async=false        # sequential
uv run pytest src/backend/tests/unit/test_foo.py -v        # single file
uv run pytest src/backend/tests/unit/test_foo.py::test_bar # single test
make test_frontend                 # Jest unit tests
make tests_frontend                # Playwright e2e

make alembic-revision message="Add X"  # cd src/backend/base/langflow && alembic revision --autogenerate
make alembic-upgrade               # upgrade head
make alembic-downgrade             # downgrade -1
make patch v=1.12.1               # bump version in pyproject.toml, src/backend/base/pyproject.toml, lfx, frontend
```

## Monorepo Structure

```
src/backend/base/langflow/  → langflow-base (API, services, graph engine, components, alembic)
src/frontend/               → React + Vite + Zustand + @xyflow/react + Tailwind
src/lfx/                    → lfx package (shared execution primitives, `lfx serve`/`lfx run`)
src/langflow-core/          → provider-free distribution (owns `langflow` CLI)
src/bundles/*/              → curated provider integrations (lfx-openai, lfx-anthropic, etc.)
src/backend/tests/          → backend tests (unit + integration)
```

Dependency direction: `langflow → langflow-core → langflow-base → lfx`. Bundles only via `langflow` (not `langflow-core`). Workspace members declared in root `pyproject.toml` `[tool.uv.workspace]`.

Entrypoints: `langflow` CLI via `langflow-core`, `lfx` CLI via `src/lfx/src/lfx/__main__.py`, FastAPI app in `src/backend/base/langflow/`.

## Quirks & Gotchas

- **Pre-commit** runs ruff, biome, `detect-secrets` (.secrets.baseline), migration validators, component-env-writes check on `git commit`. Must commit with `uv run git commit ...`. To avoid an extra cycle: `make format_backend` before staging, then `uv run git commit`.
- **Generated artifacts**: `src/lfx/src/lfx/_assets/component_index.json` is built by `scripts/build_component_index.py` and enables fast startup (~10ms). Starter projects in `src/backend/base/langflow/initial_setup/starter_projects/*.json` are reformatted on `langflow run` — don't treat as dirty.
- **Lockfiles**: `uv.lock` and `src/frontend/package-lock.json` change on `make` targets; don't commit them. Use `git update-index --assume-unchanged uv.lock src/frontend/package-lock.json` to ignore locally.
- **`make lint` is currently a no-op** (typecheck disabled, PR #12448). Don't rely on it for verification.
- **Env loading**: `make backend` runs `scripts/setup/setup_env.sh` and reads `.env` (see `.env.example` for `LANGFLOW_DATABASE_URL`, `LANGFLOW_CONFIG_DIR`). Backend kill step uses `lsof -t -i:7860`.
- **Frontend proxy** is `http://localhost:7860` (vite.config.mts). Dev needs both terminals (backend :7860 + frontend :3000).

## Migrations

- Alembic lives in `src/backend/base/langflow/alembic/` (versions + `env.py` + `migration_validator.py`).
- Pre-commit validates every migration file has `Phase: EXPAND|MIGRATE|CONTRACT` header and enforces bare-name uniqueness + append-only for `src/lfx/src/lfx/extension/migration/migration_table.json` and `BUNDLE_API.md` changelog gate.
- Create with `make alembic-revision message="..."`, never hand-edit `versions/` without the validator.

## Testing Notes

- Markers: `@pytest.mark.api_key_required` (needs external keys), `@pytest.mark.no_blockbuster`, `real_services` (needs `LANGFLOW_TEST_DATABASE_URI` + `LANGFLOW_TEST_REDIS_URL`).
- DB tests (`test_database.py`) can fail in parallel batch but pass individually — rerun that file sequentially if flaky.
- Prefer real integrations over mocking (project convention). Graph tests: build graph → `.set()` edges → `async_start` + iterate → validate results.
- Frontend `make test_frontend` = Jest, `make tests_frontend` = Playwright. CI path-filters jobs (python/frontend/docs/components) and skips draft PRs; `fast-track` label skips tests.

## Authorization (RBAC) — condensed

- Pluggable; default off (`LANGFLOW_AUTHZ_ENABLED=false`). OSS ships `BaseAuthorizationService` (in `lfx`) + pass-through `LangflowAuthorizationService` + `authz_*`/`casbin_rule` schema + guards in `langflow.services.authorization.guards` (`ensure_flow_permission`, `ensure_project_permission`, etc.).
- Register via `lfx.services` entry-point `authorization_service` in `lfx.toml`. Enforces `(subject=user:{uuid}, domain=project:{uuid}→workspace:{uuid}→*, object=flow:{uuid}|..., action=read/write/create/delete/execute/deploy)`.
- Cross-user fetch gated by `supports_cross_user_fetch()` (OSS = false, preserves owner-scoped queries). Share CRUD at `/api/v1/authz/shares`, audit at `GET /api/v1/authz/audit` (superuser, max 200). System roles `viewer/developer/admin` seeded in migration `7c8d9e0f1a2b`.

## Workflow

- PRs target the active `release-X.Y.Z` branch, not `main` (see CONTRIBUTING.md). Title must be conventional-commit and not end with `...`/`…` (CI rejects). Reference issues (`Fixes #1234`).
- CI concurrency cancels in-progress on same ref; nightly `.devN` publish health gates merges.
