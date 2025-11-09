COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: dev down seed fmt fmt-frontend fmt-backend test test-frontend test-backend

dev:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

seed:
	python3 infra/seed/seed.py

fmt: fmt-frontend fmt-backend

fmt-frontend:
	cd frontend && npm run fmt --if-present

fmt-backend:
	cd backend && ruff format || true

test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm run test -- --run
