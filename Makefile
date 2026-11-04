.PHONY: dev-backend lint typecheck test

BACKEND := cd backend &&

dev-backend:
	$(BACKEND) uv run uvicorn webhooks.main:create_app --factory --reload --port 8000

lint:
	$(BACKEND) uv run ruff check . && uv run ruff format --check .

typecheck:
	$(BACKEND) uv run pyright

test:
	$(BACKEND) uv run pytest
