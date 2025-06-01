# Testing Guide

This guide provides comprehensive testing strategies and tools for QDrant Loader development. Whether you're contributing to the core project or developing custom extensions, this guide covers all aspects of testing from unit tests to performance benchmarks.

## 🎯 Testing Overview

QDrant Loader uses a multi-layered testing approach:

- **Unit Tests** - Test individual components in isolation
- **Integration Tests** - Test component interactions and workflows
- **End-to-End Tests** - Test complete user scenarios
- **Performance Tests** - Benchmark and validate performance
- **Security Tests** - Validate security measures
- **Compatibility Tests** - Test across different environments

### Testing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Testing Framework                        │
├─────────────────────────────────────────────────────────────┤
│  Unit Tests     │ Integration Tests │ E2E Tests             │
│  ┌───────────┐  │  ┌─────────────┐  │  ┌─────────────────┐  │
│  │ Components│  │  │ Workflows   │  │  │ User Scenarios  │  │
│  │ Functions │  │  │ APIs        │  │  │ CLI Commands    │  │
│  │ Classes   │  │  │ Connectors  │  │  │ MCP Server      │  │
│  └───────────┘  │  └─────────────┘  │  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Performance    │ Security Tests    │ Compatibility       │
│  ┌───────────┐  │  ┌─────────────┐  │  ┌─────────────────┐  │
│  │ Benchmarks│  │  │ Auth Tests  │  │  │ Python Versions │  │
│  │ Load Tests│  │  │ Input Valid │  │  │ OS Platforms    │  │
│  │ Memory    │  │  │ Permissions │  │  │ Dependencies    │  │
│  └───────────┘  │  └─────────────┘  │  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🧪 Unit Testing

### Test Structure

```python
# tests/unit/test_document_processor.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from qdrant_loader.processors import DocumentProcessor
from qdrant_loader.models import Document

class TestDocumentProcessor:
    """Unit tests for DocumentProcessor."""
    
    @pytest.fixture
    def processor_config(self):
        """Test configuration for processor."""
        return {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "enable_metadata_extraction": True
        }
    
    @pytest.fixture
    def processor(self, processor_config):
        """Processor instance for testing."""
        return DocumentProcessor(processor_config)
    
    def test_initialization(self, processor):
        """Test processor initialization."""
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
        assert processor.enable_metadata_extraction is True
    
    def test_process_text_document(self, processor):
        """Test processing of text documents."""
        content = "This is a test document with some content."
        
        result = processor.process_text(content)
        
        assert isinstance(result, Document)
        assert result.content == content
        assert "word_count" in result.metadata
        assert result.metadata["word_count"] == 9
    
    @patch('qdrant_loader.processors.extract_metadata')
    def test_metadata_extraction(self, mock_extract, processor):
        """Test metadata extraction functionality."""
        mock_extract.return_value = {"language": "en", "sentiment": 0.5}
        
        content = "Test content for metadata extraction."
        result = processor.process_text(content)
        
        mock_extract.assert_called_once_with(content)
        assert result.metadata["language"] == "en"
        assert result.metadata["sentiment"] == 0.5
    
    def test_chunking_large_document(self, processor):
        """Test chunking of large documents."""
        # Create content larger than chunk_size
        large_content = "word " * 300  # 1500 characters
        
        chunks = processor.create_chunks(large_content)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= processor.chunk_size for chunk in chunks)
    
    def test_error_handling(self, processor):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            processor.process_text(None)
        
        with pytest.raises(TypeError):
            processor.process_text(123)
```

### Mocking External Dependencies

```python
# tests/unit/test_qdrant_connector.py
import pytest
from unittest.mock import Mock, patch
from qdrant_loader.connectors import QDrantConnector
from qdrant_client.models import VectorParams, Distance

class TestQDrantConnector:
    """Unit tests for QDrant connector."""
    
    @pytest.fixture
    def connector_config(self):
        return {
            "url": "http://localhost:6333",
            "collection_name": "test_collection",
            "vector_size": 384
        }
    
    @patch('qdrant_loader.connectors.QdrantClient')
    def test_connection_initialization(self, mock_client, connector_config):
        """Test QDrant client initialization."""
        connector = QDrantConnector(connector_config)
        
        mock_client.assert_called_once_with(
            url="http://localhost:6333"
        )
        assert connector.collection_name == "test_collection"
    
    @patch('qdrant_loader.connectors.QdrantClient')
    def test_collection_creation(self, mock_client, connector_config):
        """Test collection creation."""
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        connector = QDrantConnector(connector_config)
        connector.create_collection()
        
        mock_instance.create_collection.assert_called_once()
    
    @patch('qdrant_loader.connectors.QdrantClient')
    def test_document_insertion(self, mock_client, connector_config):
        """Test document insertion."""
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        connector = QDrantConnector(connector_config)
        
        documents = [
            {"id": "1", "vector": [0.1] * 384, "payload": {"text": "test"}}
        ]
        
        connector.insert_documents(documents)
        
        mock_instance.upsert.assert_called_once()
```

### Testing Async Code

```python
# tests/unit/test_async_processor.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from qdrant_loader.processors import AsyncDocumentProcessor

class TestAsyncDocumentProcessor:
    """Unit tests for async document processor."""
    
    @pytest.fixture
    def processor(self):
        return AsyncDocumentProcessor()
    
    @pytest.mark.asyncio
    async def test_async_processing(self, processor):
        """Test async document processing."""
        content = "Test document content"
        
        result = await processor.process_async(content)
        
        assert result.content == content
        assert "processing_time" in result.metadata
    
    @pytest.mark.asyncio
    @patch('qdrant_loader.processors.async_extract_metadata')
    async def test_async_metadata_extraction(self, mock_extract, processor):
        """Test async metadata extraction."""
        mock_extract.return_value = {"language": "en"}
        
        content = "Test content"
        result = await processor.process_async(content)
        
        mock_extract.assert_called_once_with(content)
        assert result.metadata["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processor):
        """Test concurrent processing of multiple documents."""
        contents = [f"Document {i}" for i in range(5)]
        
        tasks = [processor.process_async(content) for content in contents]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(isinstance(result, Document) for result in results)
```

## 🔗 Integration Testing

### Testing Component Interactions

```python
# tests/integration/test_loader_workflow.py
import pytest
import tempfile
import os
from qdrant_loader import QDrantLoader
from qdrant_loader.config import Config

class TestLoaderWorkflow:
    """Integration tests for QDrant Loader workflows."""
    
    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = {
                "doc1.txt": "This is the first test document.",
                "doc2.txt": "This is the second test document.",
                "doc3.md": "# Test Markdown\n\nThis is markdown content."
            }
            
            for filename, content in test_files.items():
                with open(os.path.join(temp_dir, filename), 'w') as f:
                    f.write(content)
            
            yield temp_dir
    
    @pytest.fixture
    def test_config(self, temp_directory):
        """Test configuration for integration tests."""
        return Config.from_dict({
            "qdrant": {
                "url": "http://localhost:6333",
                "collection_name": "test_integration"
            },
            "data_sources": {
                "local_files": {
                    "connector_type": "local",
                    "path": temp_directory,
                    "file_patterns": ["*.txt", "*.md"]
                }
            },
            "processing": {
                "chunk_size": 500,
                "enable_metadata_extraction": True
            }
        })
    
    def test_complete_loading_workflow(self, test_config):
        """Test complete document loading workflow."""
        loader = QDrantLoader(test_config)
        
        # Load documents
        result = loader.load_source("local_files")
        
        assert result.success is True
        assert result.documents_processed > 0
        assert result.documents_loaded > 0
    
    def test_search_workflow(self, test_config):
        """Test search workflow after loading."""
        loader = QDrantLoader(test_config)
        
        # Load documents first
        loader.load_source("local_files")
        
        # Search for documents
        results = loader.search("test document", limit=5)
        
        assert len(results) > 0
        assert all(result.score > 0 for result in results)
        assert all("test" in result.content.lower() for result in results)
    
    def test_incremental_update_workflow(self, test_config, temp_directory):
        """Test incremental update workflow."""
        loader = QDrantLoader(test_config)
        
        # Initial load
        initial_result = loader.load_source("local_files")
        initial_count = initial_result.documents_loaded
        
        # Add new file
        new_file_path = os.path.join(temp_directory, "doc4.txt")
        with open(new_file_path, 'w') as f:
            f.write("This is a new test document.")
        
        # Incremental update
        update_result = loader.update_source("local_files")
        
        assert update_result.success is True
        assert update_result.documents_loaded > 0
        
        # Verify new document is searchable
        results = loader.search("new test document")
        assert len(results) > 0
```

### Testing API Endpoints

```python
# tests/integration/test_mcp_server.py
import pytest
import json
from unittest.mock import patch
from qdrant_loader.mcp_server import MCPServer

class TestMCPServer:
    """Integration tests for MCP server."""
    
    @pytest.fixture
    def mcp_server(self):
        """MCP server instance for testing."""
        config = {
            "qdrant": {"url": "http://localhost:6333"},
            "server": {"port": 8000}
        }
        return MCPServer(config)
    
    def test_semantic_search_endpoint(self, mcp_server):
        """Test semantic search endpoint."""
        # Mock request
        request_data = {
            "method": "search",
            "params": {
                "query": "test query",
                "limit": 5
            }
        }
        
        with patch.object(mcp_server, 'search') as mock_search:
            mock_search.return_value = [
                {"content": "Test result", "score": 0.9}
            ]
            
            response = mcp_server.handle_request(request_data)
            
            assert response["success"] is True
            assert len(response["results"]) == 1
            mock_search.assert_called_once_with("test query", limit=5)
    
    def test_hierarchy_search_endpoint(self, mcp_server):
        """Test hierarchy search endpoint."""
        request_data = {
            "method": "hierarchy_search",
            "params": {
                "query": "documentation",
                "organize_by_hierarchy": True
            }
        }
        
        with patch.object(mcp_server, 'hierarchy_search') as mock_search:
            mock_search.return_value = {
                "results": [],
                "hierarchy": {}
            }
            
            response = mcp_server.handle_request(request_data)
            
            assert response["success"] is True
            assert "hierarchy" in response
```

## 🚀 End-to-End Testing

### CLI Testing

```python
# tests/e2e/test_cli_commands.py
import pytest
import subprocess
import tempfile
import os
import json

class TestCLICommands:
    """End-to-end tests for CLI commands."""
    
    @pytest.fixture
    def test_workspace(self):
        """Create test workspace with sample data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            docs_dir = os.path.join(temp_dir, "docs")
            os.makedirs(docs_dir)
            
            with open(os.path.join(docs_dir, "test.txt"), 'w') as f:
                f.write("This is a test document for CLI testing.")
            
            # Create config file
            config = {
                "qdrant": {"url": "http://localhost:6333"},
                "data_sources": {
                    "docs": {
                        "connector_type": "local",
                        "path": docs_dir
                    }
                }
            }
            
            config_path = os.path.join(temp_dir, "config.yaml")
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            yield temp_dir, config_path
    
    def test_load_command(self, test_workspace):
        """Test qdrant-loader load command."""
        workspace_dir, config_path = test_workspace
        
        result = subprocess.run([
            "qdrant-loader", "load",
            "--config", config_path,
            "--source", "docs"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Successfully loaded" in result.stdout
    
    def test_search_command(self, test_workspace):
        """Test qdrant-loader search command."""
        workspace_dir, config_path = test_workspace
        
        # First load data
        subprocess.run([
            "qdrant-loader", "load",
            "--config", config_path,
            "--source", "docs"
        ])
        
        # Then search
        result = subprocess.run([
            "qdrant-loader", "search",
            "--config", config_path,
            "--query", "test document",
            "--limit", "5"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "test document" in result.stdout.lower()
    
    def test_status_command(self, test_workspace):
        """Test qdrant-loader status command."""
        workspace_dir, config_path = test_workspace
        
        result = subprocess.run([
            "qdrant-loader", "status",
            "--config", config_path
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Collection" in result.stdout
```

### MCP Server E2E Testing

```python
# tests/e2e/test_mcp_integration.py
import pytest
import requests
import json
import time
import subprocess
import signal
import os

class TestMCPIntegration:
    """End-to-end tests for MCP server integration."""
    
    @pytest.fixture
    def mcp_server_process(self):
        """Start MCP server for testing."""
        # Start server process
        process = subprocess.Popen([
            "qdrant-loader-mcp-server",
            "--port", "8001",
            "--config", "test_config.yaml"
        ])
        
        # Wait for server to start
        time.sleep(2)
        
        yield process
        
        # Cleanup
        process.send_signal(signal.SIGTERM)
        process.wait()
    
    def test_server_health_check(self, mcp_server_process):
        """Test MCP server health check."""
        response = requests.get("http://localhost:8001/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_semantic_search_integration(self, mcp_server_process):
        """Test semantic search through MCP server."""
        search_request = {
            "method": "search",
            "params": {
                "query": "test query",
                "limit": 5
            }
        }
        
        response = requests.post(
            "http://localhost:8001/search",
            json=search_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
```

## ⚡ Performance Testing

### Benchmark Tests

```python
# tests/performance/test_benchmarks.py
import pytest
import time
import psutil
import os
from qdrant_loader import QDrantLoader
from qdrant_loader.config import Config

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.fixture
    def large_dataset_config(self):
        """Configuration for large dataset testing."""
        return Config.from_dict({
            "qdrant": {"url": "http://localhost:6333"},
            "data_sources": {
                "large_docs": {
                    "connector_type": "local",
                    "path": "/path/to/large/dataset"
                }
            },
            "processing": {
                "batch_size": 100,
                "parallel_workers": 4
            }
        })
    
    def test_loading_performance(self, large_dataset_config):
        """Test document loading performance."""
        loader = QDrantLoader(large_dataset_config)
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        result = loader.load_source("large_docs")
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        loading_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Performance assertions
        assert loading_time < 300  # Should complete within 5 minutes
        assert memory_used < 1024 * 1024 * 1024  # Should use less than 1GB
        assert result.documents_processed > 0
        
        # Log performance metrics
        print(f"Loading time: {loading_time:.2f}s")
        print(f"Memory used: {memory_used / 1024 / 1024:.2f}MB")
        print(f"Documents/second: {result.documents_processed / loading_time:.2f}")
    
    def test_search_performance(self, large_dataset_config):
        """Test search performance."""
        loader = QDrantLoader(large_dataset_config)
        
        # Ensure data is loaded
        loader.load_source("large_docs")
        
        # Test search performance
        queries = [
            "machine learning algorithms",
            "data processing techniques",
            "performance optimization",
            "system architecture",
            "database design patterns"
        ]
        
        search_times = []
        
        for query in queries:
            start_time = time.time()
            results = loader.search(query, limit=10)
            end_time = time.time()
            
            search_time = end_time - start_time
            search_times.append(search_time)
            
            # Assertions
            assert len(results) > 0
            assert search_time < 1.0  # Should complete within 1 second
        
        avg_search_time = sum(search_times) / len(search_times)
        print(f"Average search time: {avg_search_time:.3f}s")
        
        assert avg_search_time < 0.5  # Average should be under 500ms
    
    @pytest.mark.stress
    def test_concurrent_search_performance(self, large_dataset_config):
        """Test concurrent search performance."""
        import concurrent.futures
        import threading
        
        loader = QDrantLoader(large_dataset_config)
        loader.load_source("large_docs")
        
        def search_worker(query_id):
            """Worker function for concurrent searches."""
            query = f"test query {query_id}"
            start_time = time.time()
            results = loader.search(query, limit=5)
            end_time = time.time()
            return end_time - start_time, len(results)
        
        # Run concurrent searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(search_worker, i) for i in range(50)]
            results = [future.result() for future in futures]
        
        search_times = [result[0] for result in results]
        result_counts = [result[1] for result in results]
        
        # Performance assertions
        assert all(time < 2.0 for time in search_times)  # All searches under 2s
        assert all(count > 0 for count in result_counts)  # All searches return results
        
        avg_time = sum(search_times) / len(search_times)
        print(f"Concurrent search average time: {avg_time:.3f}s")
```

### Memory and Resource Testing

```python
# tests/performance/test_resource_usage.py
import pytest
import psutil
import gc
import tracemalloc
from qdrant_loader import QDrantLoader

class TestResourceUsage:
    """Test resource usage and memory management."""
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        tracemalloc.start()
        
        loader = QDrantLoader(test_config)
        
        # Baseline memory
        gc.collect()
        baseline_memory = psutil.Process().memory_info().rss
        
        # Perform repeated operations
        for i in range(100):
            # Load and search operations
            loader.search(f"test query {i}", limit=5)
            
            if i % 10 == 0:
                gc.collect()
        
        # Final memory check
        gc.collect()
        final_memory = psutil.Process().memory_info().rss
        memory_growth = final_memory - baseline_memory
        
        # Memory growth should be minimal
        assert memory_growth < 50 * 1024 * 1024  # Less than 50MB growth
        
        # Get memory trace
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"Memory growth: {memory_growth / 1024 / 1024:.2f}MB")
        print(f"Peak memory usage: {peak / 1024 / 1024:.2f}MB")
    
    def test_file_handle_management(self):
        """Test proper file handle management."""
        initial_handles = len(psutil.Process().open_files())
        
        loader = QDrantLoader(test_config)
        
        # Perform file operations
        for i in range(50):
            loader.load_source("local_files")
        
        final_handles = len(psutil.Process().open_files())
        handle_growth = final_handles - initial_handles
        
        # File handle growth should be minimal
        assert handle_growth < 10
        
        print(f"File handle growth: {handle_growth}")
```

## 🔒 Security Testing

### Input Validation Tests

```python
# tests/security/test_input_validation.py
import pytest
from qdrant_loader import QDrantLoader
from qdrant_loader.exceptions import ValidationError

class TestInputValidation:
    """Test input validation and security measures."""
    
    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks."""
        loader = QDrantLoader(test_config)
        
        malicious_queries = [
            "'; DROP TABLE documents; --",
            "' OR '1'='1",
            "'; DELETE FROM collections; --"
        ]
        
        for query in malicious_queries:
            # Should not raise exceptions or cause damage
            results = loader.search(query)
            assert isinstance(results, list)
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM"
        ]
        
        for path in malicious_paths:
            with pytest.raises(ValidationError):
                config = Config.from_dict({
                    "data_sources": {
                        "malicious": {
                            "connector_type": "local",
                            "path": path
                        }
                    }
                })
    
    def test_command_injection_prevention(self):
        """Test prevention of command injection."""
        malicious_commands = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& del C:\\*.*",
            "`whoami`"
        ]
        
        for command in malicious_commands:
            # Should sanitize input and not execute commands
            results = loader.search(command)
            assert isinstance(results, list)
```

## 🔧 Test Configuration and Setup

### pytest Configuration

```ini
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra
    --strict-markers
    --strict-config
    --cov=qdrant_loader
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    stress: Stress tests
    security: Security tests
    slow: Slow running tests
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
```

### Test Dependencies

```txt
# requirements-test.txt
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-asyncio>=0.21.0
pytest-xdist>=3.0.0
pytest-benchmark>=4.0.0
pytest-timeout>=2.1.0
pytest-html>=3.1.0
pytest-json-report>=1.5.0

# Mocking and fixtures
factory-boy>=3.2.0
faker>=18.0.0
responses>=0.23.0
httpx>=0.24.0

# Performance testing
psutil>=5.9.0
memory-profiler>=0.60.0

# Security testing
bandit>=1.7.0
safety>=2.3.0
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: pytest tests/unit -v --cov=qdrant_loader
    
    - name: Run integration tests
      run: pytest tests/integration -v
    
    - name: Run security tests
      run: |
        bandit -r qdrant_loader/
        safety check
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 🔗 Related Documentation

- **[API Reference](./api-reference.md)** - Complete API documentation
- **[Extending Guide](./extending.md)** - Custom extension development
- **[Architecture Guide](./architecture.md)** - System design and components
- **[Deployment Guide](./deployment.md)** - Production deployment

---

**Ready to test QDrant Loader?** Start with unit tests for your components, add integration tests for workflows, and use the performance testing framework to validate scalability.

**Need help with CI/CD?** Check the [Deployment Guide](./deployment.md) for comprehensive CI/CD pipeline configurations.
