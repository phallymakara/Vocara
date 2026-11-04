.PHONY: help dev test lint format typecheck migrate sync docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make dev         - Start Vocara API server with reload via uv"
	@echo "  make sync        - Sync and install dependencies using uv"
	@echo "  make test        - Run test suite with pytest via uv"
	@echo "  make lint        - Run ruff linter via uv"
	@echo "  make format      - Format code using ruff via uv"
	@echo "  make typecheck   - Run type checks with mypy via uv"
	@echo "  make migrate     - Run database migrations via uv"
	@echo "  make docker-up   - Start local services via docker-compose"
	@echo "  make docker-down - Stop local services"

sync:
	cd backend && uv sync --all-extras

dev:
	cd backend && uv run vocara

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest -v tests/

lint:
	cd backend && uv run ruff check src/ tests/

format:
	cd backend && uv run ruff format src/ tests/
	cd backend && uv run ruff check --fix src/ tests/

typecheck:
	cd backend && uv run mypy src/

migrate:
	cd backend && uv run alembic upgrade head

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
