# Backend Agent Guide

This file defines how coding agents should work in `hcmis-backend`.
Follow these rules before making changes.

## Scope

- Applies to everything under this backend directory.
- Prioritize safe, incremental changes over broad rewrites.
- Keep behavior stable unless the task explicitly asks for a breaking change.

## Stack And Runtime

- Python `>=3.11`
- FastAPI
- SQLAlchemy (async)
- Alembic (schema migrations)
- PostgreSQL (Docker)
- Redis (Docker)
- Tooling: `uv`, `ruff`, `ty`

## Current Service Contracts

- API entrypoint: `app.main:app`
- Auth endpoint: `POST /auth/register`
- Auth endpoint: `POST /auth/login`
- Auth endpoint: `GET /auth/me`
- Health endpoint: `GET /health`

## Project Layout

- `app/main.py`: FastAPI app wiring + lifespan
- `app/core/config.py`: environment settings
- `app/core/security.py`: password hashing + JWT creation
- `app/api/routes/`: route modules
- `app/api/deps.py`: dependency providers (`get_current_user`, etc.)
- `app/models/`: SQLAlchemy models
- `app/schemas/`: Pydantic request/response schemas
- `app/db/`: SQLAlchemy base/session and DB client wiring
- `migrations/`: Alembic env + revision files
- `alembic.ini`: Alembic config

## Environment Requirements

- Required file: `.env` (copy from `.env.example` when missing)
- Default Postgres host mapping: `localhost:5432`
- Default Redis host mapping: `localhost:6380`
- Never commit secrets from `.env`.

## Local Commands

- Install deps: `uv sync --dev`
- Run API: `uv run uvicorn app.main:app --reload`
- Lint: `uv run ruff check`
- Format fix (if needed): `uv run ruff check --fix`
- Type check: `uv run ty check`
- Lint (Make): `make ruff`
- Format fix (Make): `make ruff-fix`
- Type check (Make): `make ty`
- Lint + type check (Make): `make check`
- Migrate DB: `uv run alembic upgrade head`
- New migration: `uv run alembic revision --autogenerate -m "message"`
- Rollback one migration: `uv run alembic downgrade -1`
- Start infra: `docker compose up -d`

## Container Notes

- Compose service `postgres` maps to host `5432`
- Compose service `redis` maps to host `6380`
- If ports are occupied, update `docker-compose.yml` and corresponding `.env` URLs together.

## Database And Migration Rules

- Use Alembic for all schema changes.
- Do not rely on `Base.metadata.create_all()` for production schema management.
- Each schema change must include a migration file.
- Keep migrations reversible when feasible (`upgrade` + `downgrade`).
- Prefer additive changes for compatibility when possible.
- Alembic revision IDs must stay short enough for the `alembic_version.version_num` column.
- Do not use long descriptive revision IDs like full snake_case sentences.
- Keep `revision` values within 32 characters, and prefer compact IDs such as `0037_req_cancel_ot_status`.
- Before finalizing a new migration, run `uv run alembic upgrade head` to catch revision metadata issues, not just SQL issues.

## Auth And Security Rules

- Passwords must be hashed, never stored or logged in plaintext.
- JWT secret must come from env in non-local deployments.
- Avoid leaking auth internals in error responses.
- Keep token payload minimal (`sub`, expiry, and required claims only).

## API Change Rules

- Preserve response models and status codes unless explicitly requested otherwise.
- Update schemas and docs/examples when changing request/response contracts.
- Add new routes under `app/api/routes/` and wire them in `app/main.py`.
- Keep business logic out of route handlers when it grows; extract service modules.

## Code Quality Expectations

- New code should be typed.
- Keep modules focused and small.
- Prefer explicit names over clever abstractions.
- Handle external dependency failures (DB/Redis) with clear errors.
- Avoid introducing new dependencies unless justified by clear value.

## Engineering Principles

- KISS: choose the simplest design that fully solves the requirement.
- DRY: avoid duplicated logic; extract shared code only after a real repeat appears.
- YAGNI: do not add speculative features, abstractions, or config knobs.
- SOLID (pragmatic): keep boundaries clear, especially between API, business logic, and data access.
- Single responsibility: each module should have one primary reason to change.
- Explicit over implicit: make auth, data flow, and failure paths easy to trace.
- Fail fast with context: return actionable errors, avoid silent fallback behavior.
- Backward compatibility first: prefer additive API and schema changes.

## Testing Expectations

- For non-trivial behavior changes, add or update tests.
- At minimum, run lint and type checks before finalizing work.
- If tests are unavailable, state what was verified manually.

## Agent Workflow

1. Read the relevant files before editing.
2. Make the smallest change that satisfies the request.
3. Run quality checks (`ruff`, `ty`, and migration command if DB changed).
4. Summarize changed files and operational impact.
5. Call out any follow-up work or residual risk.

## Lean Ctx Tooling Preference

- Prefer `lean_ctx` MCP tools for discovery and inspection work whenever possible.
- Default command-to-tool mapping:
- `ctx_tree` for directory/file discovery instead of broad `ls`/`find`.
- `ctx_search` for code/text lookup instead of `grep`/manual scanning.
- `ctx_read` and `ctx_multi_read` for file reads (use compact modes when full content is unnecessary).
- `ctx_shell` for command execution when command output inspection is needed.
- Use cache-aware workflows (`ctx_cache`, `ctx_metrics`) to reduce repeated context and token usage during iterative edits.
- Fall back to raw shell commands only when `lean_ctx` cannot perform the needed task.

## Do Not

- Do not hardcode secrets.
- Do not bypass Alembic for schema changes.
- Do not silently change ports or env keys without updating docs.
- Do not introduce breaking API changes without explicit direction.
- Do not revert user changes unrelated to the task.

## Definition Of Done

- Code compiles and runs.
- Lint/type checks pass.
- Migrations apply cleanly when schema changes exist.
- Documentation is aligned with behavior.
