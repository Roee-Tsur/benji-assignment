.PHONY: dev dev-backend dev-frontend gen-api lint typecheck test

BACKEND := cd backend &&
FRONTEND := cd frontend &&

# Backend on :8000, dashboard on :3000 (proxying /api to the backend).
dev:
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	$(BACKEND) uv run uvicorn webhooks.main:create_app --factory --reload --port 8000

dev-frontend:
	$(FRONTEND) pnpm dev

# Regenerate the frontend's API types after a backend schema change.
gen-api:
	$(FRONTEND) pnpm gen:api

lint:
	$(BACKEND) uv run ruff check . && uv run ruff format --check .
	$(FRONTEND) pnpm lint

typecheck:
	$(BACKEND) uv run pyright
	$(FRONTEND) pnpm typecheck

test:
	$(BACKEND) uv run pytest
	$(FRONTEND) pnpm test
