.PHONY: help install install-dev test test-loader test-mcp test-core test-coverage lint format clean clean-python clean-build build build-loader build-mcp publish-loader publish-mcp docs quality quality-all setup-dev check profile-pyspy profile-cprofile metrics

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install both packages in development mode
	uv sync --all-packages

install-dev: ## Install both packages with development dependencies
	uv sync --all-packages --all-extras

test: ## Run all tests
	uv run pytest packages/

test-loader: ## Run tests for qdrant-loader package only
	uv run pytest packages/qdrant-loader/tests/

test-mcp: ## Run tests for mcp-server package only
	uv run pytest packages/qdrant-loader-mcp-server/tests/

test-core: ## Run tests for qdrant-loader-core package only
	uv run pytest packages/qdrant-loader-core/tests/

test-coverage: ## Run tests with coverage report
	uv run pytest packages/ --cov=packages --cov-report=html --cov-report=term-missing

quality: ## Run quality gates (import cycles, module sizes) for qdrant-loader
	cd packages/qdrant-loader && uv run pytest -q tests/unit/quality -v

quality-all: ## Run quality gates for all packages (currently qdrant-loader and qdrant-loader-core)
	cd packages/qdrant-loader && uv run pytest -q tests/unit/quality -v
	cd packages/qdrant-loader-core && uv run pytest -q tests/unit/quality -v
	# Add additional per-package quality directories here if/when created

lint: ## Run linting on all packages
	uv run ruff check --fix .

format: ## Format code in all packages
	uv run black .
	uv run isort .
	uv run ruff check --fix .

clean-python: ## Clean Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

clean-build: ## Clean build and test artifacts
	rm -rf dist/ packages/*/dist/ packages/*/build/
	rm -rf htmlcov/ .coverage .pytest_cache/

clean: clean-python clean-build ## Clean all build and cache artifacts

build: ## Build both packages
	rm -rf packages/qdrant-loader/dist/ packages/qdrant-loader-mcp-server/dist/
	cd packages/qdrant-loader && uv build --out-dir dist/
	cd packages/qdrant-loader-mcp-server && uv build --out-dir dist/

build-loader: ## Build qdrant-loader package only
	rm -rf packages/qdrant-loader/dist/
	cd packages/qdrant-loader && uv build --out-dir dist/

build-mcp: ## Build mcp-server package only
	rm -rf packages/qdrant-loader-mcp-server/dist/
	cd packages/qdrant-loader-mcp-server && uv build --out-dir dist/

publish-loader: build-loader ## Publish qdrant-loader to PyPI
	uv publish packages/qdrant-loader/dist/qdrant_loader-*

publish-mcp: build-mcp ## Publish mcp-server to PyPI
	uv publish packages/qdrant-loader-mcp-server/dist/qdrant_loader_mcp_server-*

docs: ## Generate documentation
	uv run python website/build.py --output site --templates website/templates --base-url "http://127.0.0.1:3000/site/"

setup-dev: ## Set up development environment
	uv sync --all-packages --all-extras
	@echo "Virtual environment ready at .venv"
	@echo "Run commands with: uv run <command>"
	@echo "Or activate manually: source .venv/bin/activate (macOS/Linux)"
	@echo "  .venv\\Scripts\\activate (Windows)"

check: lint quality test ## Run all checks (lint + quality + test)

profile-pyspy:
	@echo "Running py-spy..."
	uv run python -m qdrant_loader.cli.cli ingest --source-type=localfile & \
	PID=$$!; sleep 2; uv run py-spy record -o profile.svg --pid $$PID; kill $$PID; echo "Flamegraph saved to profile.svg"

profile-cprofile:
	@echo "Running cProfile..."
	uv run python -m qdrant_loader.cli.cli ingest --source-type=localfile --profile
	@echo "Opening SnakeViz..."
	uv run snakeviz profile.out

metrics:
	@echo "Starting Prometheus metrics endpoint (to be implemented)"
	# TODO: Implement metrics endpoint and start it here 