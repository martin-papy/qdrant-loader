.PHONY: help install install-dev test test-loader test-mcp test-core test-coverage lint format clean build publish-loader publish-mcp docs quality quality-all

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

test-core: ## Run tests for qdrant-loader-core package only
	pytest packages/qdrant-loader-core/tests/

test-coverage: ## Run tests with coverage report
	pytest packages/ --cov=packages --cov-report=html --cov-report=term-missing

quality: ## Run quality gates (import cycles, module sizes) for qdrant-loader
	cd packages/qdrant-loader && pytest -q tests/unit/quality -v

quality-all: ## Run quality gates for all packages (currently qdrant-loader and qdrant-loader-core)
	cd packages/qdrant-loader && pytest -q tests/unit/quality -v
	cd packages/qdrant-loader-core && pytest -q tests/unit/quality -v
	# Add additional per-package quality directories here if/when created

lint: ## Run linting on all packages
	ruff check .
	# TODO: Add mypy check for all packages
	# mypy -p qdrant_loader -p qdrant_loader_core -p qdrant_loader_mcp_server

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
	python website/build.py --output website/site --templates website/templates

setup-dev: ## Set up development environment
	python3.12 -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # On macOS/Linux"
	@echo "  venv\\Scripts\\activate     # On Windows"
	@echo "Then run: make install-dev"

check: lint quality test ## Run all checks (lint + quality + test)

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