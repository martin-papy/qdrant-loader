# Testing Guide

This section provides comprehensive testing documentation for QDrant Loader, covering unit testing, integration testing, and quality assurance practices.

## 🎯 Testing Overview

QDrant Loader follows a comprehensive testing strategy to ensure reliability, performance, and maintainability:

### 🧪 Testing Philosophy

1. **Test-Driven Development** - Write tests before implementing features
2. **Comprehensive Coverage** - Aim for 85%+ test coverage
3. **Fast Feedback** - Quick unit tests for rapid development
4. **Real-World Testing** - Integration tests with actual services
5. **Performance Validation** - Regular performance benchmarking

### 📚 Testing Categories

- **Unit Testing** - Testing individual components in isolation
- **Integration Testing** - Testing component interactions and end-to-end workflows
- **Quality Assurance** - Code quality, review processes, and standards

## 🚀 Quick Start

### Test Environment Setup

```bash
# Clone the repository
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# Install packages in editable mode (workspace layout)
pip install -e packages/qdrant-loader
# Optional: MCP server if testing integration
pip install -e packages/qdrant-loader-mcp-server

# Install test tools
pip install pytest pytest-asyncio pytest-cov pytest-mock requests-mock responses

# Run all tests (verbose)
pytest -v

# Run with coverage per package (HTML reports under respective directories)
# Test qdrant-loader package
cd packages/qdrant-loader
pytest -v --cov=src --cov-report=html

# Test qdrant-loader-mcp-server package
cd ../qdrant-loader-mcp-server
pytest -v --cov=src --cov-report=html

# Test website (from project root)
cd ../..
export PYTHONPATH="${PYTHONPATH}:$(pwd)/website"
pytest tests/ --cov=website --cov-report=html
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/
# Integration tests only
pytest tests/integration/
# Specific test file
pytest tests/unit/core/test_qdrant_manager.py
# Specific test function
pytest tests/unit/core/test_qdrant_manager.py::TestQdrantManager::test_initialization_default_settings
```

## 🧪 Testing Framework

### Core Testing Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| **pytest** | Test runner and framework | Main testing framework |
| **pytest-asyncio** | Async test support | Testing async functions |
| **pytest-cov** | Coverage reporting | Code coverage analysis |
| **pytest-mock** | Mocking utilities | Mock external dependencies |
| **requests-mock** | HTTP mocking | Mock external HTTP calls |
| **pytest-timeout** | Test timeouts | Prevent hanging tests |

### Test Configuration

Key settings live in `pyproject.toml` under `[tool.pytest.ini_options]` and coverage settings under `[tool.coverage.*]`.

### Test Structure

```text
tests/
├── __init__.py
├── conftest.py # Shared fixtures and configuration
├── test_cleanup.py
├── test_favicon_generation.py
├── test_link_checker.py
├── test_website_build_comprehensive.py
├── test_website_build_edge_cases.py
└── test_website_build.py
```

## 🔧 Test Fixtures and Utilities

### Common Fixtures

```python
# conftest.py
import pytest
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_loader.config import get_settings, initialize_config


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Create necessary directories
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Load test configuration
    config_path = Path("tests/config.test.yaml")
    env_path = Path("tests/.env.test")
    
    # Load environment variables first
    load_dotenv(env_path, override=True)
    
    # Initialize config using the same function as CLI
    initialize_config(config_path)
    
    yield
    
    # Clean up after all tests
    if data_dir.exists():
        shutil.rmtree(data_dir)


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings."""
    settings = get_settings()
    return settings


@pytest.fixture(scope="session")
def test_global_config():
    """Get test configuration."""
    config = get_settings().global_config
    return config


@pytest.fixture(scope="session")
def qdrant_client(test_global_config):
    """Create and return a Qdrant client for testing."""
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    yield client
    
    # Cleanup: Delete test collection after tests
    collection_name = os.getenv("QDRANT_COLLECTION_NAME")
    if collection_name:
        client.delete_collection(collection_name)


@pytest.fixture(scope="function")
def clean_collection(qdrant_client):
    """Ensure the test collection is empty before each test."""
    collection_name = os.getenv("QDRANT_COLLECTION_NAME")
    
    if collection_name:
        qdrant_client.delete_collection(collection_name)
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "size": 1536,
                "distance": "Cosine",
            },  # OpenAI embedding size
        )
```

### Mock Utilities

```python
# tests/utils.py
from unittest.mock import Mock
from typing import List
from qdrant_loader.core.document import Document


def create_mock_qdrant_client():
    """Create a mock QdrantClient."""
    client = Mock()
    
    # Configure mock methods
    client.get_collections.return_value = Mock(collections=[])
    client.create_collection = Mock()
    client.create_payload_index = Mock()
    client.upsert = Mock()
    client.search.return_value = []
    client.delete_collection = Mock()
    client.delete = Mock()
    
    return client


def create_mock_settings():
    """Create mock settings for testing."""
    from qdrant_loader.config import Settings
    
    settings = Mock(spec=Settings)
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_api_key = None
    settings.qdrant_collection_name = "test_collection"
    
    return settings
```

## 🧪 Unit Testing Patterns

### Testing Core Components

```python
# tests/unit/core/test_qdrant_manager.py
import pytest
from unittest.mock import Mock, patch
from qdrant_loader.config import Settings
from qdrant_loader.core.qdrant_manager import QdrantManager, QdrantConnectionError


class TestQdrantManager:
    """Test cases for QdrantManager."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.qdrant_url = "http://localhost:6333"
        settings.qdrant_api_key = None
        settings.qdrant_collection_name = "test_collection"
        return settings
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock QdrantClient for testing."""
        client = Mock()
        client.get_collections.return_value = Mock(collections=[])
        client.create_collection = Mock()
        client.upsert = Mock()
        client.search.return_value = []
        return client
    
    def test_initialization_default_settings(self, mock_settings, mock_global_config):
        """Test QdrantManager initialization with default settings."""
        with (
            patch(
                "qdrant_loader.core.qdrant_manager.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "qdrant_loader.core.qdrant_manager.get_global_config",
                return_value=mock_global_config,
            ),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager()
            assert manager.settings == mock_settings
            assert manager.collection_name == "test_collection"
    
    @pytest.mark.asyncio
    async def test_upsert_points_success(self, mock_settings, mock_qdrant_client):
        """Test successful point upsert."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)
            manager.client = mock_qdrant_client
            
            points = [
                {"id": "1", "vector": [0.1, 0.2, 0.3], "payload": {"text": "test"}}
            ]
            
            await manager.upsert_points(points)
            mock_qdrant_client.upsert.assert_called_once()
```

### Testing CLI Commands

```python
# tests/unit/cli/test_cli.py
import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
from qdrant_loader.cli.cli import cli


class TestCliCommands:
    """Test CLI command functionality."""
    
    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()
    
    @patch("qdrant_loader.cli.cli._setup_logging")
    @patch("qdrant_loader.cli.cli._load_config_with_workspace")
    @patch("qdrant_loader.cli.cli._check_settings")
    @patch("qdrant_loader.cli.cli.QdrantManager")
    @patch("qdrant_loader.cli.cli.AsyncIngestionPipeline")
    def test_ingest_command_success(
        self,
        mock_pipeline_class,
        mock_qdrant_manager,
        mock_check_settings,
        mock_load_config_with_workspace,
        mock_setup_logging,
    ):
        """Test successful ingest command."""
        # Setup mocks
        mock_pipeline = Mock()
        mock_pipeline.initialize = Mock()
        mock_pipeline.process_documents = Mock(return_value=[])
        mock_pipeline.cleanup = Mock()
        mock_pipeline_class.return_value = mock_pipeline
        
        # Run command
        result = self.runner.invoke(cli, ["ingest"])
        
        # Verify success
        assert result.exit_code == 0
        mock_pipeline.initialize.assert_called_once()
        mock_pipeline.process_documents.assert_called_once()
        mock_pipeline.cleanup.assert_called_once()
```

### Testing Document Processing

```python
# tests/unit/core/test_document.py
import pytest
from qdrant_loader.core.document import Document


def test_document_creation():
    """Test document creation with auto-generated fields."""
    doc = Document(
        title="Test Document",
        content_type="text/plain",
        content="This is test content",
        metadata={"author": "test"},
        source_type="test",
        source="test_source",
        url="http://example.com/doc1"
    )
    
    assert doc.title == "Test Document"
    assert doc.content == "This is test content"
    assert doc.source_type == "test"
    assert doc.id is not None  # Auto-generated
    assert doc.content_hash is not None  # Auto-generated


def test_document_id_consistency():
    """Test that document IDs are consistent for same inputs."""
    doc1 = Document(
        title="Test",
        content_type="text/plain",
        content="Content",
        source_type="test",
        source="source",
        url="http://example.com"
    )
    
    doc2 = Document(
        title="Test",
        content_type="text/plain",
        content="Content",
        source_type="test",
        source="source",
        url="http://example.com"
    )
    
    assert doc1.id == doc2.id
```

## 🔗 Integration Testing

### Full Pipeline Testing

```python
# tests/integration/test_full_pipeline.py
import pytest
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.config import Settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_ingestion_pipeline(test_settings):
    """Test complete ingestion pipeline."""
    # Create QdrantManager
    qdrant_manager = QdrantManager(test_settings)
    
    # Initialize pipeline
    pipeline = AsyncIngestionPipeline(
        settings=test_settings,
        qdrant_manager=qdrant_manager
    )
    
    try:
        # Initialize pipeline
        await pipeline.initialize()
        
        # Run ingestion for a specific project
        documents = await pipeline.process_documents(project_id="test-project")
        
        # Verify results
        assert isinstance(documents, list)
    finally:
        await pipeline.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cli_integration(tmp_path):
    """Test CLI integration."""
    from qdrant_loader.cli.cli import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    
    # Test init command
    result = runner.invoke(cli, [
        '--workspace', str(tmp_path),
        'init'
    ])
    
    assert result.exit_code == 0
```

## 📊 Performance Testing

### Benchmarking

```python
# tests/performance/test_ingestion_speed.py
import pytest
import time
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline


@pytest.mark.performance
@pytest.mark.asyncio
async def test_ingestion_performance(test_settings):
    """Benchmark ingestion performance."""
    pipeline = AsyncIngestionPipeline(settings=test_settings)
    
    start_time = time.time()
    
    try:
        await pipeline.initialize()
        documents = await pipeline.process_documents(project_id="test-project")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 30.0  # Should complete in under 30 seconds
        assert isinstance(documents, list)
    finally:
        await pipeline.cleanup()
```

## 🔍 Quality Assurance

### Code Quality Checks

```bash
# Run all quality checks
make test
make lint
make format-check
# Individual checks
ruff check . # Linting
ruff format --check . # Code formatting
mypy . # Type checking
# Per-package test coverage
cd packages/qdrant-loader && pytest --cov=src
cd packages/qdrant-loader-mcp-server && pytest --cov=src
```

### Package-specific quality gates: qdrant-loader-core

- Import cycle and module size guards are under `packages/qdrant-loader-core/tests/unit/quality/`.
- Keep refactored modules within target sizes (<300–400 lines) unless explicitly exempted in tests.
- Prefer thin entrypoints and shared helpers to avoid duplication.

### Continuous Integration

The project uses GitHub Actions for CI/CD:

```yaml
# .github/workflows/test.yml
name: Test and Coverage

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install Poetry
        uses: snok/install-poetry@v1
      
      - name: Install dependencies
        run: poetry install --with dev
      
      - name: Run tests
        run: poetry run pytest --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## 📚 Testing Best Practices

### Guidelines

1. **Write tests first** - Follow TDD principles
2. **Test behavior, not implementation** - Focus on what, not how
3. **Use descriptive test names** - Make test purpose clear
4. **Keep tests independent** - No test should depend on another
5. **Mock external dependencies** - Isolate units under test
6. **Test edge cases** - Include error conditions and boundary values

### Testing Checklist

- [ ] Unit tests for all new functionality
- [ ] Integration tests for user workflows
- [ ] Error handling and edge cases covered
- [ ] Mocks for external dependencies
- [ ] Test data cleanup
- [ ] Documentation updated

### Common Patterns

```python
# Async testing
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None

# Exception testing
def test_exception_handling():
    with pytest.raises(ValueError, match="Expected error message"):
        function_that_should_raise()

# Parametrized testing
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
])
def test_multiple_inputs(input, expected):
    assert process_input(input) == expected

# Mocking with patch
@patch("module.external_function")
def test_with_mock(mock_function):
    mock_function.return_value = "mocked_result"
    result = function_under_test()
    assert result == "expected_result"
```

## 🆘 Getting Help

### Testing Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report testing issues
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask testing questions
- **[Test Examples](https://github.com/martin-papy/qdrant-loader/tree/main/packages/qdrant-loader/tests)** - Reference implementations

### Contributing Tests

- **[Contributing Guide](../../CONTRIBUTING.md)** - How to contribute tests
- **[Development Setup](../README.md)** - Development environment setup

---
**Ready to write tests?** Start with unit tests for individual components or check out the existing test suite for patterns and examples.
