# Testing Guide

This guide provides comprehensive testing strategies and tools for QDrant Loader development. Whether you're contributing to the core project or developing custom extensions, this guide covers all aspects of testing from unit tests to integration tests.

## 🎯 Testing Overview

QDrant Loader uses a multi-layered testing approach with pytest as the primary testing framework:

- **Unit Tests** - Test individual components in isolation
- **Integration Tests** - Test component interactions and workflows
- **End-to-End Tests** - Test complete CLI scenarios
- **Coverage Reporting** - Track test coverage across packages

### Testing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Testing Framework (pytest)              │
├─────────────────────────────────────────────────────────────┤
│  Unit Tests     │ Integration Tests │ E2E Tests             │
│  ┌───────────┐  │  ┌─────────────┐  │  ┌─────────────────┐  │
│  │ Core      │  │  │ File Conv.  │  │  │ CLI Commands    │  │
│  │ Connectors│  │  │ Pipelines   │  │  │ Workspace Mode  │  │
│  │ Config    │  │  │ Workflows   │  │  │ MCP Server      │  │
│  │ Utils     │  │  │ Connectors  │  │  │ Full Scenarios  │  │
│  └───────────┘  │  └─────────────┘  │  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Coverage       │ CI/CD Testing     │ Multi-Package       │
│  ┌───────────┐  │  ┌─────────────┐  │  ┌─────────────────┐  │
│  │ HTML/XML  │  │  │ GitHub      │  │  │ Actions     │  │
│  │ Reports   │  │  │ Actions     │  │  │ Multi-OS    │  │
│  │ Artifacts │  │  │ Multi-OS    │  │  │ Separate Tests  │  │
│  └───────────┘  │  └─────────────┘  │  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🧪 Unit Testing

### Test Structure

The project follows a structured approach to unit testing with clear separation by module:

```
packages/qdrant-loader/tests/
├── unit/
│   ├── cli/                    # CLI command tests
│   ├── config/                 # Configuration tests
│   ├── connectors/             # Data source connector tests
│   ├── core/                   # Core functionality tests
│   │   ├── chunking/
│   │   ├── embedding/
│   │   ├── file_conversion/
│   │   ├── monitoring/
│   │   ├── pipeline/
│   │   ├── state/
│   │   └── text_processing/
│   └── utils/                  # Utility function tests
├── integration/                # Integration tests
├── fixtures/                   # Test fixtures and data
├── conftest.py                # Pytest configuration
└── config.test.yaml           # Test configuration
```

### Example Unit Test Pattern

```python
# tests/unit/core/test_qdrant_manager.py
"""Tests for QdrantManager."""

from unittest.mock import AsyncMock, Mock, patch
import pytest
from qdrant_client.http import models
from qdrant_loader.config import Settings
from qdrant_loader.core.qdrant_manager import QdrantConnectionError, QdrantManager

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
            patch("qdrant_loader.core.qdrant_manager.get_settings", return_value=mock_settings),
            patch("qdrant_loader.core.qdrant_manager.get_global_config", return_value=mock_global_config),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager()
            
            assert manager.settings == mock_settings
            assert manager.collection_name == "test_collection"
    
    @pytest.mark.asyncio
    async def test_upsert_points_success(self, mock_settings, mock_qdrant_client):
        """Test successful point upsert."""
        with patch("qdrant_loader.core.qdrant_manager.get_global_config"):
            manager = QdrantManager(mock_settings)
            manager.client = mock_qdrant_client
            
            points = [{"id": "1", "vector": [0.1] * 384, "payload": {"text": "test"}}]
            
            await manager.upsert_points(points)
            
            mock_qdrant_client.upsert.assert_called_once()
```

### Testing Async Code

The project extensively uses async patterns, and tests properly handle async functionality:

```python
@pytest.mark.asyncio
async def test_async_processing(self):
    """Test async document processing."""
    pipeline = AsyncIngestionPipeline(settings, qdrant_manager)
    
    result = await pipeline.process_documents(project_id="test")
    
    assert result is not None
    # Verify async cleanup
    await pipeline.cleanup()
```

### Mocking External Dependencies

Tests properly mock external services and dependencies:

```python
@patch('qdrant_loader.connectors.git.GitRepoConnector._clone_repository')
@patch('qdrant_loader.connectors.git.GitRepoConnector._get_file_content')
def test_git_connector_processing(self, mock_get_content, mock_clone):
    """Test Git repository connector."""
    mock_clone.return_value = None
    mock_get_content.return_value = "test content"
    
    connector = GitRepoConnector(config)
    documents = connector.fetch_documents()
    
    assert len(documents) > 0
    mock_clone.assert_called_once()
```

## 🔗 Integration Testing

### Testing Component Interactions

Integration tests verify that components work together correctly:

```python
# tests/integration/test_file_conversion_integration.py
"""Integration tests for file conversion functionality."""

import pytest
from pathlib import Path
from qdrant_loader.core.file_conversion.file_converter import FileConverter

class TestFileConversionIntegration:
    """Integration tests for file conversion."""
    
    @pytest.mark.asyncio
    async def test_pdf_conversion_workflow(self, temp_pdf_file):
        """Test complete PDF conversion workflow."""
        converter = FileConverter()
        
        result = await converter.convert_file(temp_pdf_file)
        
        assert result.success
        assert result.content is not None
        assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_office_document_conversion(self, temp_docx_file):
        """Test Office document conversion."""
        converter = FileConverter()
        
        result = await converter.convert_file(temp_docx_file)
        
        assert result.success
        assert "document content" in result.content.lower()
```

### Testing CLI Commands

Integration tests verify CLI command functionality:

```python
def test_init_command_workspace_mode(self, temp_workspace):
    """Test init command in workspace mode."""
    result = subprocess.run([
        "qdrant-loader", "--workspace", str(temp_workspace), "init"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    assert "Collection initialized" in result.stdout

def test_ingest_command_with_project_filter(self, temp_workspace):
    """Test ingest command with project filtering."""
    result = subprocess.run([
        "qdrant-loader", "--workspace", str(temp_workspace), 
        "ingest", "--project", "test-project"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    assert "Processing project: test-project" in result.stdout
```

## 🚀 End-to-End Testing

### CLI Testing

E2E tests verify complete user workflows:

```python
class TestCLIWorkflows:
    """End-to-end tests for CLI workflows."""
    
    def test_complete_workspace_workflow(self, temp_workspace):
        """Test complete workspace setup and ingestion workflow."""
        workspace_dir = temp_workspace
        
        # Step 1: Initialize workspace
        result = subprocess.run([
            "qdrant-loader", "--workspace", str(workspace_dir), "init"
        ], capture_output=True, text=True)
        assert result.returncode == 0
        
        # Step 2: Run ingestion
        result = subprocess.run([
            "qdrant-loader", "--workspace", str(workspace_dir), "ingest"
        ], capture_output=True, text=True)
        assert result.returncode == 0
        
        # Step 3: Check project status
        result = subprocess.run([
            "qdrant-loader", "--workspace", str(workspace_dir), 
            "project", "status"
        ], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Project Status" in result.stdout
```

### MCP Server Testing

E2E tests for MCP server functionality are handled in the separate `qdrant-loader-mcp-server` package:

```python
def test_mcp_server_search_integration(self):
    """Test MCP server search functionality."""
    # MCP server tests are in packages/qdrant-loader-mcp-server/tests/
    # They test the complete search workflow through the MCP interface
```

## 🔧 Test Configuration and Setup

### pytest Configuration

```ini
# packages/qdrant-loader/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
filterwarnings =
    ignore::DeprecationWarning:pydantic.*
    ignore::DeprecationWarning:spacy.*
    ignore::UserWarning:structlog.*
    ignore::bs4.XMLParsedAsHTMLWarning
    ignore:unclosed transport.*:ResourceWarning
    ignore:coroutine.*was never awaited:RuntimeWarning
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
asyncio_default_fixture_loop_scope = function
```

### Test Dependencies

The project uses these testing dependencies (defined in `pyproject.toml`):

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "pytest-asyncio>=0.21.0",
    "pytest-xdist>=3.0.0",
    "pytest-timeout>=2.1.0",
    # Additional development dependencies
]
```

### Test Environment Setup

Tests use environment templates for configuration:

```bash
# tests/.env.test.template
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key_here
QDRANT_COLLECTION_NAME=test_collection
OPENAI_API_KEY=your_openai_key_here
STATE_DB_PATH=:memory:
```

```yaml
# tests/config.test.template.yaml
global_config:
  qdrant:
    url: ${QDRANT_URL}
    api_key: ${QDRANT_API_KEY}
    collection_name: ${QDRANT_COLLECTION_NAME}
  
  embedding:
    provider: openai
    api_key: ${OPENAI_API_KEY}
    model: text-embedding-3-small
    vector_size: 1536

projects:
  test-project:
    name: "Test Project"
    sources:
      local-docs:
        type: local_files
        config:
          base_url: "file://./tests/fixtures/sample_docs"
          include_paths: ["**/*.md", "**/*.txt"]
```

## 🔄 CI/CD Integration

### GitHub Actions Workflow

The project uses GitHub Actions for automated testing:

```yaml
# .github/workflows/test.yml
name: Test and Coverage

on:
  push:
    branches: [ main, develop, feature/*, bugfix/*, release/* ]
  pull_request:
    branches: [ main, develop, feature/*, bugfix/*, release/* ]

jobs:
  test-loader:
    name: Test QDrant Loader
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e packages/qdrant-loader[dev]
      
      - name: Run tests and generate coverage
        run: |
          cd packages/qdrant-loader
          python -m pytest tests/ --cov=src --cov-report=xml --cov-report=html -v
      
      - name: Upload coverage artifacts
        uses: actions/upload-artifact@v4
        with:
          name: coverage-loader-${{ github.run_id }}
          path: |
            htmlcov
            coverage.xml

  test-mcp-server:
    name: Test MCP Server
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e packages/qdrant-loader[dev]
          pip install -e packages/qdrant-loader-mcp-server[dev]
      
      - name: Run MCP server tests
        run: |
          cd packages/qdrant-loader-mcp-server
          python -m pytest tests/ --cov=src --cov-report=xml --cov-report=html -v
```

## 🏃‍♂️ Running Tests

### Local Development

```bash
# Run all tests for qdrant-loader package
cd packages/qdrant-loader
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v                    # Unit tests only
python -m pytest tests/integration/ -v             # Integration tests only
python -m pytest -m "not slow" -v                  # Skip slow tests

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Run tests for MCP server package
cd packages/qdrant-loader-mcp-server
python -m pytest tests/ -v
```

### Test Environment Setup

```bash
# Set up test environment
cd packages/qdrant-loader
cp tests/.env.test.template tests/.env.test
cp tests/config.test.template.yaml tests/config.test.yaml

# Edit the files with your test credentials
# Then run tests
python -m pytest tests/ -v
```

### Parallel Testing

```bash
# Run tests in parallel (requires pytest-xdist)
python -m pytest tests/ -n auto -v
```

## 📊 Coverage Reporting

The project maintains test coverage tracking:

- **HTML Reports**: Generated in `htmlcov/` directory
- **XML Reports**: Generated as `coverage.xml` for CI/CD
- **Terminal Reports**: Displayed during test runs
- **Coverage Artifacts**: Uploaded in GitHub Actions for review

### Coverage Targets

- **Unit Tests**: Aim for >80% coverage on core modules
- **Integration Tests**: Focus on critical workflows
- **E2E Tests**: Cover main user scenarios

## 🔗 Related Documentation

- **[Architecture Guide](./architecture.md)** - System design and components
- **[Extending Guide](./extending.md)** - Custom extension development
- **[Deployment Guide](./deployment.md)** - Production deployment
- **[CLI Reference](../users/cli-reference/README.md)** - Command-line interface

---

**Ready to test QDrant Loader?** Start with unit tests for your components, add integration tests for workflows, and use the existing test patterns as examples.

**Need help with test setup?** Check the test configuration files and GitHub Actions workflow for complete setup examples.
