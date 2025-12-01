.PHONY: dev down logs logs-api logs-web logs-worker build test lint format db-migrate db-revision db-downgrade clean help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

# Default target
.DEFAULT_GOAL := help

## Development
dev: ## Start all services in development mode
	@echo "$(CYAN)Starting development environment...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)Services started!$(RESET)"
	@echo ""
	@echo "  Frontend:    http://localhost:3001"
	@echo "  API:         http://localhost:8000"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo "  MailHog:     http://localhost:8025"
	@echo "  Flower:      http://localhost:5555"
	@echo ""

down: ## Stop all services
	@echo "$(CYAN)Stopping services...$(RESET)"
	docker compose down

restart: ## Restart all services
	@echo "$(CYAN)Restarting services...$(RESET)"
	docker compose restart

rebuild: ## Rebuild and restart all services
	@echo "$(CYAN)Rebuilding services...$(RESET)"
	docker compose up -d --build

## Logs
logs: ## View logs for all services
	docker compose logs -f

logs-api: ## View API logs
	docker compose logs -f api

logs-web: ## View frontend logs
	docker compose logs -f web

logs-worker: ## View worker logs
	docker compose logs -f worker

## Database
db-migrate: ## Run database migrations
	@echo "$(CYAN)Running database migrations...$(RESET)"
	docker compose exec api alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(RESET)"

db-revision: ## Create a new migration (usage: make db-revision name="migration_name")
	@echo "$(CYAN)Creating new migration...$(RESET)"
	docker compose exec api alembic revision --autogenerate -m "$(name)"

db-downgrade: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(RESET)"
	docker compose exec api alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "$(YELLOW)Resetting database...$(RESET)"
	docker compose down -v
	docker compose up -d postgres redis
	@sleep 5
	docker compose up -d api
	@sleep 3
	docker compose exec api alembic upgrade head

## Testing
test: ## Run all tests
	@echo "$(CYAN)Running all tests...$(RESET)"
	$(MAKE) test-api
	$(MAKE) test-web

test-api: ## Run backend tests
	@echo "$(CYAN)Running backend tests...$(RESET)"
	docker compose exec api pytest -v

test-web: ## Run frontend tests
	@echo "$(CYAN)Running frontend tests...$(RESET)"
	docker compose exec web npm test

test-coverage: ## Run tests with coverage
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	docker compose exec api pytest --cov=src --cov-report=html

## Code Quality
lint: ## Run linters
	@echo "$(CYAN)Running linters...$(RESET)"
	docker compose exec api ruff check src
	docker compose exec web npm run lint

format: ## Format code
	@echo "$(CYAN)Formatting code...$(RESET)"
	docker compose exec api ruff format src
	docker compose exec web npm run format

typecheck: ## Run type checking
	@echo "$(CYAN)Running type checks...$(RESET)"
	docker compose exec api mypy src
	docker compose exec web npm run typecheck

## Build
build: ## Build production images
	@echo "$(CYAN)Building production images...$(RESET)"
	docker compose -f docker-compose.prod.yml build

build-api: ## Build API image only
	docker compose build api

build-web: ## Build frontend image only
	docker compose build web

build-worker: ## Build worker image only
	docker compose build worker

## Shell Access
shell-api: ## Open shell in API container
	docker compose exec api bash

shell-web: ## Open shell in frontend container
	docker compose exec web sh

shell-db: ## Open PostgreSQL shell
	docker compose exec postgres psql -U postgres -d app

shell-redis: ## Open Redis CLI
	docker compose exec redis redis-cli

## Utilities
clean: ## Clean up containers, volumes, and cache
	@echo "$(YELLOW)Cleaning up...$(RESET)"
	docker compose down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)Cleanup complete!$(RESET)"

status: ## Show status of all services
	docker compose ps

health: ## Check health of all services
	@echo "$(CYAN)Checking service health...$(RESET)"
	@curl -s http://localhost:8000/health | jq . || echo "API not responding"
	@curl -s http://localhost:8000/health/detailed | jq . || echo "API detailed health not responding"

## Help
help: ## Show this help message
	@echo "$(CYAN)App Boilerplate - Available Commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""
