.PHONY: help install install-dev test test-loader test-mcp test-coverage lint format clean build publish-loader publish-mcp docs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install both packages in development mode
	pip install -e packages/qdrant-loader
	pip install -e packages/qdrant-loader-mcp-server

install-dev: ## Install both packages with development dependencies
	pip install -e packages/qdrant-loader[dev]
	pip install -e packages/qdrant-loader-mcp-server[dev]

test: ## Run all tests
	pytest packages/

test-loader: ## Run tests for qdrant-loader package only
	pytest packages/qdrant-loader/tests/

test-mcp: ## Run tests for mcp-server package only
	pytest packages/qdrant-loader-mcp-server/tests/

test-coverage: ## Run tests with coverage report
	pytest packages/ --cov=packages --cov-report=html --cov-report=term-missing

lint: ## Run linting on all packages
	ruff check packages/
	mypy packages/

format: ## Format code in all packages
	black packages/
	isort packages/
	ruff check --fix packages/

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf packages/*/dist/
	rm -rf packages/*/build/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/

build: ## Build both packages
	cd packages/qdrant-loader && python -m build
	cd packages/qdrant-loader-mcp-server && python -m build

build-loader: ## Build qdrant-loader package only
	cd packages/qdrant-loader && python -m build

build-mcp: ## Build mcp-server package only
	cd packages/qdrant-loader-mcp-server && python -m build

publish-loader: build-loader ## Publish qdrant-loader to PyPI
	cd packages/qdrant-loader && python -m twine upload dist/*

publish-mcp: build-mcp ## Publish mcp-server to PyPI
	cd packages/qdrant-loader-mcp-server && python -m twine upload dist/*

docs: ## Generate documentation
	@echo "Documentation generation not yet implemented"

setup-dev: ## Set up development environment
	python3.12 -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # On macOS/Linux"
	@echo "  venv\\Scripts\\activate     # On Windows"
	@echo "Then run: make install-dev"

check: lint test ## Run all checks (lint + test)

profile-pyspy:
	@echo "Running py-spy..."
	python -m qdrant_loader.cli.cli ingest --source-type=localfile & \
	PID=$$!; sleep 2; py-spy record -o profile.svg --pid $$PID; kill $$PID; echo "Flamegraph saved to profile.svg"

profile-cprofile:
	@echo "Running cProfile..."
	python -m qdrant_loader.cli.cli ingest --source-type=localfile --profile
	@echo "Opening SnakeViz..."
	snakeviz profile.out

metrics:
	@echo "Starting Prometheus metrics endpoint (to be implemented)"
	# TODO: Implement metrics endpoint and start it here

# Docker commands
docker-build: ## Build all Docker images
	docker-compose build

docker-build-loader: ## Build qdrant-loader Docker image only
	docker-compose build qdrant-loader

docker-build-mcp: ## Build MCP server Docker image only
	docker-compose build mcp-server

docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-up-logs: ## Start all services and show logs
	docker-compose up

docker-down: ## Stop all Docker services
	docker-compose down

docker-down-volumes: ## Stop all services and remove volumes
	docker-compose down -v

docker-logs: ## Show logs for all services
	docker-compose logs -f

docker-logs-loader: ## Show logs for qdrant-loader service
	docker-compose logs -f qdrant-loader

docker-logs-mcp: ## Show logs for MCP server service
	docker-compose logs -f mcp-server

docker-logs-qdrant: ## Show logs for QDrant service
	docker-compose logs -f qdrant

docker-logs-neo4j: ## Show logs for Neo4j service
	docker-compose logs -f neo4j

docker-restart: ## Restart all services
	docker-compose restart

docker-restart-loader: ## Restart qdrant-loader service
	docker-compose restart qdrant-loader

docker-restart-mcp: ## Restart MCP server service
	docker-compose restart mcp-server

docker-status: ## Show status of all services
	docker-compose ps

docker-clean: ## Clean up Docker resources
	docker-compose down -v --remove-orphans
	docker system prune -f

docker-clean-cache: ## Clean Docker build cache (forces full rebuild)
	docker builder prune -f
	docker buildx prune -f

docker-build-no-cache: ## Build all Docker images without cache
	docker-compose build --no-cache

docker-build-dev: ## Build with development optimizations (uses cache)
	DOCKER_BUILDKIT=1 docker-compose build

docker-shell-loader: ## Open shell in qdrant-loader container
	docker-compose exec qdrant-loader /bin/bash

docker-shell-mcp: ## Open shell in MCP server container
	docker-compose exec mcp-server /bin/bash

docker-shell-neo4j: ## Open shell in Neo4j container
	docker-compose exec neo4j /bin/bash

docker-dev: docker-build docker-up-dev ## Build and start development environment with live code mounting

docker-up-dev: ## Start development environment with live code mounting (like pip install -e)
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

docker-up-dev-logs: ## Start development environment and show logs
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-down-dev: ## Stop development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

docker-restart-dev: ## Restart development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart

docker-logs-dev: ## Show logs for development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

docker-shell-loader-dev: ## Open shell in qdrant-loader development container
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec qdrant-loader /bin/bash

docker-shell-mcp-dev: ## Open shell in MCP server development container
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec mcp-server /bin/bash

docker-reload-dev: ## Reload packages in development containers (re-run pip install -e)
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec qdrant-loader pip install -e .
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec mcp-server pip install -e .

# Environment management
env-setup: ## Set up environment configuration from template
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo "Created .env from template. Please edit it with your configuration."; \
	else \
		echo ".env already exists. Use 'make env-reset' to recreate from template."; \
	fi

env-reset: ## Reset environment configuration from template
	cp .env.template .env
	@echo "Reset .env from template. Please edit it with your configuration."

env-validate: ## Validate environment configuration
	@echo "Validating Docker Compose configuration..."
	docker-compose config > /dev/null && echo "✅ Docker Compose configuration is valid" || echo "❌ Docker Compose configuration has errors"

env-check: ## Check current environment variables
	@echo "Current environment configuration:"
	@if [ -f .env ]; then \
		echo "📄 .env file exists"; \
		grep -v "^#" .env | grep -v "^$$" | head -10; \
		echo "... (showing first 10 non-comment lines)"; \
	else \
		echo "❌ .env file not found. Run 'make env-setup' first."; \
	fi

# Resource monitoring
docker-stats: ## Show Docker container resource usage
	docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

docker-top: ## Show processes running in containers
	@echo "=== QDrant Container Processes ==="
	-docker exec qdrant-db ps aux
	@echo "\n=== Neo4j Container Processes ==="
	-docker exec neo4j-db ps aux
	@echo "\n=== QDrant Loader Container Processes ==="
	-docker exec qdrant-loader-app ps aux
	@echo "\n=== MCP Server Container Processes ==="
	-docker exec qdrant-loader-mcp-server ps aux

docker-inspect-resources: ## Inspect resource limits for all containers
	@echo "=== Container Resource Limits ==="
	@for container in qdrant-db neo4j-db qdrant-loader-app qdrant-loader-mcp-server; do \
		echo "--- $$container ---"; \
		docker inspect $$container --format '{{.HostConfig.Memory}} bytes memory limit' 2>/dev/null || echo "Container not running"; \
		docker inspect $$container --format '{{.HostConfig.NanoCpus}} nanocpus limit' 2>/dev/null || echo "Container not running"; \
		echo ""; \
	done 