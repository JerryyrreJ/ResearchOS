.PHONY: sync lint test migrate api contracts verify

sync:
	uv sync --dev

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest

migrate:
	uv run alembic upgrade head

api:
	uv run uvicorn researchos.api.main:app --reload

contracts:
	uv run python scripts/export_openapi.py

verify: lint test contracts

