# Testing Guide

This section provides comprehensive testing documentation for QDrant Loader, covering unit testing, integration testing, performance testing, and quality assurance practices.

## 🎯 Testing Overview

QDrant Loader follows a comprehensive testing strategy to ensure reliability, performance, and maintainability:

### 🧪 Testing Philosophy

1. **Test-Driven Development** - Write tests before implementing features
2. **Comprehensive Coverage** - Aim for 85%+ test coverage
3. **Fast Feedback** - Quick unit tests for rapid development
4. **Real-World Testing** - Integration tests with actual services
5. **Performance Validation** - Regular performance benchmarking

### 📚 Testing Categories

- **[Unit Testing](./unit-testing.md)** - Testing individual components in isolation
- **[Integration Testing](./integration-testing.md)** - Testing component interactions and end-to-end workflows
- **[Performance Testing](./performance-testing.md)** - Load testing, benchmarking, and performance validation
- **[Quality Assurance](./quality-assurance.md)** - Code quality, review processes, and standards

## 🚀 Quick Start

### Test Environment Setup

```bash
# Clone the repository
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install dependencies including test dependencies
poetry install --with dev

# Activate virtual environment
poetry shell

# Run all tests
pytest

# Run with coverage
pytest --cov=qdrant_loader --cov-report=html
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Performance tests
pytest tests/performance/

# Specific test file
pytest tests/unit/test_sources.py

# Specific test function
pytest tests/unit/test_sources.py::test_git_source_fetch_documents
```

## 🧪 Testing Framework

### Core Testing Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| **pytest** | Test runner and framework | Main testing framework |
| **pytest-asyncio** | Async test support | Testing async functions |
| **pytest-cov** | Coverage reporting | Code coverage analysis |
| **pytest-mock** | Mocking utilities | Mock external dependencies |
| **pytest-benchmark** | Performance testing | Benchmark test execution |
| **factory-boy** | Test data generation | Create test fixtures |

### Test Configuration

```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=qdrant_loader
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=85
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    slow: Slow running tests
asyncio_mode = auto
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_sources.py      # Data source tests
│   ├── test_converters.py   # File converter tests
│   ├── test_processors.py   # Content processor tests
│   └── test_vector.py       # Vector engine tests
├── integration/             # Integration tests
│   ├── test_full_pipeline.py
│   ├── test_mcp_server.py
│   └── test_cli.py
├── performance/             # Performance tests
│   ├── test_ingestion_speed.py
│   └── test_search_performance.py
└── fixtures/                # Test data and fixtures
    ├── sample_documents/
    └── test_configs/
```

## 🔧 Test Fixtures and Utilities

### Common Fixtures

```python
# conftest.py
import pytest
import tempfile
import asyncio
from pathlib import Path
from qdrant_loader.config import Config
from qdrant_loader import QDrantLoader

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        yield workspace

@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        qdrant_url="memory://test",
        collection_name="test_collection",
        sources=[],
        chunk_size=500,
        batch_size=10
    )

@pytest.fixture
async def qdrant_loader(test_config):
    """Create a QDrant Loader instance for testing."""
    loader = QDrantLoader(test_config)
    await loader.initialize()
    yield loader
    await loader.cleanup()

@pytest.fixture
def sample_documents():
    """Generate sample documents for testing."""
    from qdrant_loader.types import Document
    return [
        Document(
            id="doc_1",
            title="Test Document 1",
            content="This is test content for document 1",
            metadata={"source": "test"},
            source_type="test",
            source_id="1"
        ),
        Document(
            id="doc_2",
            title="Test Document 2",
            content="This is test content for document 2",
            metadata={"source": "test"},
            source_type="test",
            source_id="2"
        )
    ]
```

### Mock Utilities

```python
# tests/utils/mocks.py
from unittest.mock import AsyncMock, MagicMock
from typing import List, AsyncIterator
from qdrant_loader.types import Document

class MockDataSource:
    """Mock data source for testing."""
    
    def __init__(self, documents: List[Document]):
        self.documents = documents
    
    async def fetch_documents(self) -> AsyncIterator[Document]:
        """Yield mock documents."""
        for doc in self.documents:
            yield doc
    
    async def test_connection(self) -> bool:
        """Mock connection test."""
        return True

class MockVectorEngine:
    """Mock vector engine for testing."""
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return mock embeddings."""
        return [[0.1, 0.2, 0.3] for _ in texts]
    
    async def search(self, query_vector: List[float], limit: int = 10):
        """Return mock search results."""
        return []

def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.embeddings.create.return_value.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3])
    ]
    return client
```

## 🧪 Unit Testing Patterns

### Testing Data Sources

```python
# tests/unit/test_sources.py
import pytest
from unittest.mock import patch, AsyncMock
from qdrant_loader.sources import GitSource

@pytest.mark.asyncio
async def test_git_source_fetch_documents():
    """Test Git source document fetching."""
    config = {
        "url": "https://github.com/test/repo.git",
        "branch": "main",
        "include_patterns": ["**/*.md"]
    }
    
    source = GitSource(config)
    
    # Mock git operations
    with patch('qdrant_loader.sources.git.Repo') as mock_repo:
        mock_repo.clone_from.return_value = mock_repo
        mock_repo.iter_tree_files.return_value = [
            "README.md", "docs/guide.md"
        ]
        
        documents = []
        async for doc in source.fetch_documents():
            documents.append(doc)
        
        assert len(documents) == 2
        assert all(doc.source_type == "git" for doc in documents)

@pytest.mark.asyncio
async def test_git_source_connection_test():
    """Test Git source connection testing."""
    config = {"url": "https://github.com/test/repo.git"}
    source = GitSource(config)
    
    with patch('qdrant_loader.sources.git.git.cmd.Git') as mock_git:
        mock_git.return_value.ls_remote.return_value = "refs/heads/main"
        
        result = await source.test_connection()
        assert result is True
```

### Testing File Converters

```python
# tests/unit/test_converters.py
import pytest
import tempfile
from pathlib import Path
from qdrant_loader.converters import PDFConverter

def test_pdf_converter_can_convert():
    """Test PDF converter file type detection."""
    converter = PDFConverter()
    
    assert converter.can_convert("document.pdf") is True
    assert converter.can_convert("document.txt") is False
    assert converter.can_convert("document.PDF") is True

@pytest.mark.asyncio
async def test_pdf_converter_convert():
    """Test PDF conversion to text."""
    converter = PDFConverter()
    
    # Create a test PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        # Write minimal PDF content
        temp_file.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        temp_path = temp_file.name
    
    try:
        with patch('qdrant_loader.converters.pdf.PyPDF2') as mock_pdf:
            mock_pdf.PdfReader.return_value.pages = [
                MagicMock(extract_text=lambda: "Test PDF content")
            ]
            
            result = await converter.convert(temp_path)
            assert "Test PDF content" in result
    finally:
        Path(temp_path).unlink()
```

### Testing Vector Operations

```python
# tests/unit/test_vector.py
import pytest
from unittest.mock import patch, AsyncMock
from qdrant_loader.vector import VectorEngine

@pytest.mark.asyncio
async def test_vector_engine_embed_texts():
    """Test text embedding generation."""
    engine = VectorEngine(model_name="text-embedding-ada-002")
    
    with patch('openai.OpenAI') as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6])
        ]
        
        texts = ["Hello world", "Test text"]
        embeddings = await engine.embed_texts(texts)
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]

@pytest.mark.asyncio
async def test_vector_engine_batch_processing():
    """Test batch embedding processing."""
    engine = VectorEngine(model_name="text-embedding-ada-002", batch_size=2)
    
    with patch.object(engine, 'embed_texts') as mock_embed:
        mock_embed.side_effect = [
            [[0.1, 0.2], [0.3, 0.4]],  # First batch
            [[0.5, 0.6]]               # Second batch
        ]
        
        texts = ["text1", "text2", "text3"]
        all_embeddings = []
        
        async for batch_embeddings in engine.embed_batch(texts):
            all_embeddings.extend(batch_embeddings)
        
        assert len(all_embeddings) == 3
        assert mock_embed.call_count == 2
```

## 🔗 Integration Testing

### Full Pipeline Testing

```python
# tests/integration/test_full_pipeline.py
import pytest
from qdrant_loader import QDrantLoader
from qdrant_loader.config import Config

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_ingestion_pipeline(temp_workspace, sample_documents):
    """Test complete ingestion pipeline."""
    # Create test configuration
    config = Config(
        qdrant_url="memory://test",
        collection_name="test_docs",
        sources=[{
            "type": "test",
            "documents": sample_documents
        }]
    )
    
    # Initialize loader
    loader = QDrantLoader(config)
    await loader.initialize()
    
    try:
        # Run ingestion
        result = await loader.ingest()
        
        # Verify results
        assert result.processed_count == len(sample_documents)
        assert result.error_count == 0
        
        # Test search functionality
        search_results = await loader.search("test content")
        assert len(search_results.results) > 0
        
    finally:
        await loader.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_incremental_updates(temp_workspace):
    """Test incremental update functionality."""
    config = Config(
        qdrant_url="memory://test",
        collection_name="test_docs",
        sources=[{"type": "test"}]
    )
    
    loader = QDrantLoader(config)
    await loader.initialize()
    
    try:
        # First ingestion
        result1 = await loader.ingest()
        
        # Second ingestion (should skip unchanged documents)
        result2 = await loader.ingest()
        
        assert result2.skipped_count > 0
        
    finally:
        await loader.cleanup()
```

### MCP Server Testing

```python
# tests/integration/test_mcp_server.py
import pytest
import asyncio
from qdrant_loader_mcp_server import MCPServer

@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_search_tools(temp_workspace):
    """Test MCP server search functionality."""
    server = MCPServer(
        name="test-server",
        version="1.0.0",
        workspace_path=str(temp_workspace)
    )
    
    # Start server
    await server.start()
    
    try:
        # Test search tool
        result = await server.execute_tool(
            "search",
            {"query": "test query", "limit": 5}
        )
        
        assert "results" in result
        assert isinstance(result["results"], list)
        
    finally:
        await server.stop()
```

## 📊 Performance Testing

### Benchmarking

```python
# tests/performance/test_ingestion_speed.py
import pytest
import time
from qdrant_loader import QDrantLoader

@pytest.mark.performance
@pytest.mark.asyncio
async def test_ingestion_performance(benchmark, large_document_set):
    """Benchmark ingestion performance."""
    config = create_test_config()
    loader = QDrantLoader(config)
    
    async def run_ingestion():
        await loader.initialize()
        try:
            result = await loader.ingest()
            return result
        finally:
            await loader.cleanup()
    
    # Benchmark the ingestion
    result = await benchmark(run_ingestion)
    
    # Performance assertions
    assert result.processed_count > 0
    assert benchmark.stats.mean < 10.0  # Should complete in under 10 seconds

@pytest.mark.performance
def test_memory_usage(memory_profiler):
    """Test memory usage during processing."""
    with memory_profiler:
        # Run memory-intensive operations
        loader = QDrantLoader(config)
        # ... processing logic
    
    # Assert memory usage is within acceptable limits
    assert memory_profiler.peak_memory < 1024  # MB
```

### Load Testing

```python
# tests/performance/test_concurrent_processing.py
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_search_performance():
    """Test search performance under concurrent load."""
    loader = QDrantLoader(config)
    await loader.initialize()
    
    async def search_task(query):
        return await loader.search(f"query {query}")
    
    # Run concurrent searches
    tasks = [search_task(i) for i in range(100)]
    start_time = time.time()
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Performance assertions
    assert len(results) == 100
    assert duration < 30.0  # Should complete in under 30 seconds
    assert all(len(r.results) >= 0 for r in results)
```

## 🔍 Quality Assurance

### Code Quality Checks

```bash
# Run all quality checks
make quality-check

# Individual checks
black --check .                    # Code formatting
isort --check-only .               # Import sorting
ruff check .                       # Linting
mypy .                            # Type checking
pytest --cov=qdrant_loader        # Test coverage
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.8

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.270
    hooks:
      - id: ruff

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install --with dev
    
    - name: Run tests
      run: |
        poetry run pytest --cov=qdrant_loader --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 📚 Testing Documentation

### Detailed Testing Guides

- **[Unit Testing](./unit-testing.md)** - Comprehensive unit testing strategies
- **[Integration Testing](./integration-testing.md)** - End-to-end testing approaches
- **[Performance Testing](./performance-testing.md)** - Load testing and benchmarking
- **[Quality Assurance](./quality-assurance.md)** - Code quality and review processes

### Best Practices

1. **Write tests first** - Follow TDD principles
2. **Test behavior, not implementation** - Focus on what, not how
3. **Use descriptive test names** - Make test purpose clear
4. **Keep tests independent** - No test should depend on another
5. **Mock external dependencies** - Isolate units under test
6. **Test edge cases** - Include error conditions and boundary values

### Testing Checklist

- [ ] Unit tests for all new functionality
- [ ] Integration tests for user workflows
- [ ] Performance tests for critical paths
- [ ] Error handling and edge cases covered
- [ ] Mocks for external dependencies
- [ ] Test data cleanup
- [ ] Documentation updated

## 🆘 Getting Help

### Testing Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report testing issues
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask testing questions
- **[Testing Examples](https://github.com/martin-papy/qdrant-loader/tree/main/tests)** - Reference implementations

### Contributing Tests

- **[Contributing Guide](../../CONTRIBUTING.md)** - How to contribute tests
- **[Test Standards](./quality-assurance.md)** - Testing quality standards
- **[Code Review Process](./quality-assurance.md#code-review)** - Review guidelines

---

**Ready to write tests?** Start with [Unit Testing](./unit-testing.md) for component-level testing or check out [Integration Testing](./integration-testing.md) for end-to-end testing strategies.
