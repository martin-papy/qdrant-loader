.PHONY: help install install-dev test test-loader test-mcp test-coverage lint format clean build publish-loader publish-mcp analyze

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development setup
install: ## Install both packages in development mode
	pip install -e packages/qdrant-loader
	pip install -e packages/qdrant-loader-mcp-server

install-dev: ## Install both packages with development dependencies
	pip install -e packages/qdrant-loader[dev]
	pip install -e packages/qdrant-loader-mcp-server[dev]

setup-dev: ## Set up development environment
	python3.12 -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # On macOS/Linux"
	@echo "  venv\\Scripts\\activate     # On Windows"
	@echo "Then run: make install-dev"

# Testing
test-all: ## Run all tests
	pytest tests/ -v
	cd packages/qdrant-loader && pytest tests/ -v
	cd packages/qdrant-loader-mcp-server && pytest tests/ -v

test-loader: ## Run tests for qdrant-loader package only
	cd packages/qdrant-loader && pytest tests/ -v

test-mcp: ## Run tests for mcp-server package only
	cd packages/qdrant-loader-mcp-server && pytest tests/ -v

test-web: ## Run tests for website only
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ --cov=packages --cov-report=html --cov-report=term-missing
	cd packages/qdrant-loader && pytest tests/ --cov=qdrant_loader --cov-report=html --cov-report=term-missing
	cd packages/qdrant-loader-mcp-server && pytest tests/ --cov=qdrant_loader_mcp_server --cov-report=html --cov-report=term-missing

# Code quality
lint: ## Run linting on all packages
	ruff check packages/
	mypy packages/

format: ## Format code in all packages
	black packages/
	isort packages/
	ruff check --fix packages/

analyze: lint ## Run comprehensive static analysis
	@echo "Running security analysis with Bandit..."
	bandit -r packages/
	@echo "Running complexity analysis with Radon..."
	radon cc packages/ -a -s
	@echo "Running dead code analysis with Vulture..."
	vulture packages/ --min-confidence 80

check: lint test ## Run all checks (lint + test)

# Build
build: ## Build both packages
	pip install -e ".[docs]"
	cd packages/qdrant-loader && pip install .
	cd packages/qdrant-loader-mcp-server && pip install .

build-dev: ## Build both packages with development dependencies
	pip install -e ".[dev,docs]"
	cd packages/qdrant-loader && pip install -e ".[dev]"
	cd packages/qdrant-loader-mcp-server && pip install -e ".[dev]"

build-loader: ## Build qdrant-loader package only
	cd packages/qdrant-loader && python -m build

build-mcp: ## Build mcp-server package only
	cd packages/qdrant-loader-mcp-server && python -m build

# Cleanup
clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf packages/*/dist/
	rm -rf packages/*/build/
	rm -rf htmlcov*
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf coverage*

# Docker commands
docker-up: ## Start all services (production mode)
	docker-compose up -d

docker-up-dev: ## Start development environment with live code mounting
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-restart: ## Restart all Docker services
	docker-compose restart

docker-logs: ## Show logs for all services
	docker-compose logs -f

docker-status: ## Show status of all containers
	docker-compose ps

docker-clean: ## Clean up Docker resources (removes volumes)
	docker-compose down -v --remove-orphans
	docker system prune -f

docker-build: ## Build Docker images for production
	docker-compose build

docker-build-dev: ## Build Docker images for development
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

# Docker interaction commands
docker-shell-loader: ## Open bash shell in qdrant-loader container
	docker exec -it qdrant-loader /bin/bash

docker-shell-mcp: ## Open bash shell in mcp-server container
	docker exec -it qdrant-loader-mcp-server /bin/bash

docker-shell-neo4j: ## Open bash shell in neo4j container
	docker exec -it neo4j-db /bin/bash

docker-shell-qdrant: ## Open bash shell in qdrant container
	docker exec -it qdrant-db /bin/bash

docker-exec-loader: ## Execute command in qdrant-loader container (usage: make docker-exec-loader CMD="your command")
	docker exec -it qdrant-loader $(CMD)

docker-exec-mcp: ## Execute command in mcp-server container (usage: make docker-exec-mcp CMD="your command")
	docker exec -it qdrant-loader-mcp-server $(CMD)

docker-logs-loader: ## Show logs for qdrant-loader container only
	docker-compose logs -f qdrant-loader

docker-logs-mcp: ## Show logs for mcp-server container only
	docker-compose logs -f qdrant-loader-mcp-server

docker-logs-neo4j: ## Show logs for neo4j container only
	docker-compose logs -f neo4j

docker-logs-qdrant: ## Show logs for qdrant container only
	docker-compose logs -f qdrant 