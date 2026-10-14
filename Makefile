.PHONY: help up down backend-install frontend-install backend frontend test lint fmt

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

up: ## Run the full stack in Docker (http://localhost:8080)
	docker compose up --build

down: ## Stop the Docker stack
	docker compose down

backend-install: ## Create the backend venv and install dependencies
	cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

frontend-install: ## Install frontend dependencies
	cd frontend && npm ci

backend: ## Run the Django dev server on :8000
	cd backend && DJANGO_DEBUG=true .venv/bin/python manage.py createcachetable && \
	DJANGO_DEBUG=true .venv/bin/python manage.py runserver 8000

frontend: ## Run the Vite dev server on :5173
	cd frontend && npm run dev

test: ## Run backend and frontend tests
	cd backend && .venv/bin/python -m pytest -q
	cd frontend && npm test

lint: ## Lint and type-check everything
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint && npm run typecheck && npx prettier --check .

fmt: ## Auto-format everything
	cd backend && .venv/bin/ruff check --fix . && .venv/bin/ruff format .
	cd frontend && npx prettier --write .
