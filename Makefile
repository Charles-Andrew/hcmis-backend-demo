UV_CACHE_DIR ?= /tmp/uv-cache
DOCKER_CONFIG ?= /tmp/hcmis-docker-config
COMPOSE ?= docker compose
POSTGRES_SERVICE ?= postgres
REDIS_SERVICE ?= redis
POSTGRES_HOST_PORT ?= 15432
REDIS_HOST_PORT ?= 16379
DATABASE_URL ?= postgresql+asyncpg://hcmis:hcmis@localhost:$(POSTGRES_HOST_PORT)/hcmis
REDIS_URL ?= redis://localhost:$(REDIS_HOST_PORT)/0
FASTAPI_APP ?= app/main.py

.PHONY: ruff ty check test docker-config up wait-postgres wait-redis migrate dev db-clear seed-initial seed-performance-questionnaires reset-and-seed

ruff:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check

ty:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ty check

check: ruff ty

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run pytest

docker-config:
	@mkdir -p $(DOCKER_CONFIG)
	@printf '{}' > $(DOCKER_CONFIG)/config.json

up: docker-config
	POSTGRES_HOST_PORT=$(POSTGRES_HOST_PORT) REDIS_HOST_PORT=$(REDIS_HOST_PORT) DOCKER_CONFIG=$(DOCKER_CONFIG) $(COMPOSE) up -d $(POSTGRES_SERVICE) $(REDIS_SERVICE)

wait-postgres:
	until DOCKER_CONFIG=$(DOCKER_CONFIG) $(COMPOSE) exec -T $(POSTGRES_SERVICE) pg_isready -U hcmis -d hcmis >/dev/null 2>&1; do sleep 1; done

wait-redis:
	until DOCKER_CONFIG=$(DOCKER_CONFIG) $(COMPOSE) exec -T $(REDIS_SERVICE) redis-cli ping >/dev/null 2>&1; do sleep 1; done

migrate:
	DATABASE_URL=$(DATABASE_URL) REDIS_URL=$(REDIS_URL) UV_CACHE_DIR=$(UV_CACHE_DIR) uv run alembic upgrade head

dev: docker-config up wait-postgres wait-redis migrate
	DATABASE_URL=$(DATABASE_URL) REDIS_URL=$(REDIS_URL) UV_CACHE_DIR=$(UV_CACHE_DIR) uv run fastapi dev $(FASTAPI_APP) --host 0.0.0.0 --port 8000

db-clear:
	DATABASE_URL=$(DATABASE_URL) REDIS_URL=$(REDIS_URL) UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m app.scripts.clear_db_data

seed-initial:
	DATABASE_URL=$(DATABASE_URL) REDIS_URL=$(REDIS_URL) UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m app.scripts.seed_initial_data

seed-performance-questionnaires:
	DATABASE_URL=$(DATABASE_URL) REDIS_URL=$(REDIS_URL) UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m app.scripts.import_performance_questionnaires

reset-and-seed: db-clear seed-initial seed-performance-questionnaires
