# Extension Guide

This section provides comprehensive guides for extending QDrant Loader with new functionality. Whether you want to add support for new data sources, file formats, or search capabilities, you'll find the patterns and examples you need here.

## 🎯 Extension Overview

QDrant Loader is designed to be highly extensible through a plugin-based architecture. You can extend the system in several ways:

### 🔌 Extension Types

- **[Data Source Connectors](./data-source-connectors.md)** - Add support for new data sources
- **[File Converters](./file-converters.md)** - Support new file formats and conversion methods
- **[Search Tools](./search-tools.md)** - Extend MCP server with new search capabilities
- **[Custom Processors](./custom-processors.md)** - Add custom content processing logic

### 🏗️ Extension Architecture

QDrant Loader uses a plugin-based architecture with well-defined interfaces:

```
┌─────────────────────────────────────────────────────────────┐
│                    QDrant Loader Core                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Plugin    │  │   Plugin    │  │   Plugin    │         │
│  │  Registry   │  │ Interface   │  │  Manager    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    Plugin Ecosystem                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    Data     │  │    File     │  │   Search    │         │
│  │   Source    │  │ Converter   │  │    Tool     │         │
│  │  Plugins    │  │  Plugins    │  │  Plugins    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install in development mode
poetry install

# Activate virtual environment
poetry shell

# Run tests to ensure everything works
pytest
```

### Creating Your First Extension

Let's create a simple data source connector:

```python
# my_extension/custom_source.py
from typing import AsyncIterator, Dict, Any
from qdrant_loader.plugins import DataSourcePlugin
from qdrant_loader.types import Document

class CustomDataSource(DataSourcePlugin):
    """Example custom data source."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url")
        self.api_key = config.get("api_key")
    
    async def fetch_documents(self) -> AsyncIterator[Document]:
        """Fetch documents from the custom API."""
        # Your implementation here
        yield Document(
            id="example_1",
            title="Example Document",
            content="This is example content",
            metadata={"source": "custom_api"},
            source_type="custom",
            source_id="example_1"
        )
    
    async def test_connection(self) -> bool:
        """Test connection to the data source."""
        # Test your API connection
        return True
```

### Registering Your Extension

```python
# my_extension/__init__.py
from qdrant_loader.plugins import register_plugin
from .custom_source import CustomDataSource

# Register your plugin
register_plugin("custom", CustomDataSource)
```

### Using Your Extension

```yaml
# config.yaml
sources:
  custom:
    - api_url: "https://api.example.com"
      api_key: "your_api_key"
```

## 🔧 Plugin Development Patterns

### Base Plugin Interface

All plugins inherit from a base plugin class:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePlugin(ABC):
    """Base class for all plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up plugin-specific logging."""
        import logging
        return logging.getLogger(f"qdrant_loader.plugins.{self.__class__.__name__}")
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass
```

### Configuration Validation

```python
from pydantic import BaseModel, validator

class CustomSourceConfig(BaseModel):
    """Configuration schema for custom data source."""
    api_url: str
    api_key: str
    timeout: int = 30
    max_retries: int = 3
    
    @validator('api_url')
    def validate_api_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('API URL must start with http:// or https://')
        return v

class CustomDataSource(DataSourcePlugin):
    def __init__(self, config: Dict[str, Any]):
        # Validate configuration
        self.config_obj = CustomSourceConfig(**config)
        super().__init__(config)
```

### Error Handling

```python
from qdrant_loader.exceptions import DataSourceError

class CustomDataSource(DataSourcePlugin):
    async def fetch_documents(self) -> AsyncIterator[Document]:
        try:
            # Your implementation
            pass
        except Exception as e:
            raise DataSourceError(
                f"Failed to fetch documents from {self.api_url}: {e}",
                source_type="custom",
                source_id=self.api_url
            ) from e
```

### Async Best Practices

```python
import asyncio
import aiohttp
from typing import List

class CustomDataSource(DataSourcePlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.session = None
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrency
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config_obj.timeout)
        )
    
    async def cleanup(self) -> None:
        """Clean up HTTP session."""
        if self.session:
            await self.session.close()
    
    async def fetch_documents(self) -> AsyncIterator[Document]:
        """Fetch documents with proper async handling."""
        async with self.semaphore:
            async with self.session.get(self.api_url) as response:
                data = await response.json()
                for item in data:
                    yield self._create_document(item)
```

## 📚 Extension Types

### Data Source Connectors

Connect to new data sources like databases, APIs, or file systems:

```python
class DatabaseSource(DataSourcePlugin):
    """Connect to SQL databases."""
    
    async def fetch_documents(self) -> AsyncIterator[Document]:
        async with self.get_db_connection() as conn:
            async for row in conn.execute("SELECT * FROM documents"):
                yield Document(
                    id=str(row['id']),
                    title=row['title'],
                    content=row['content'],
                    metadata={"table": "documents"},
                    source_type="database",
                    source_id=str(row['id'])
                )
```

### File Converters

Add support for new file formats:

```python
class CustomFileConverter(ConverterPlugin):
    """Convert custom file format to text."""
    
    def can_convert(self, file_path: str) -> bool:
        """Check if this converter can handle the file."""
        return file_path.endswith('.custom')
    
    async def convert(self, file_path: str) -> str:
        """Convert file to text."""
        # Your conversion logic
        with open(file_path, 'rb') as f:
            content = f.read()
            return self._parse_custom_format(content)
    
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from the file."""
        return {
            "format": "custom",
            "size": os.path.getsize(file_path),
            "converter": "custom_converter"
        }
```

### Search Tools

Extend MCP server with new search capabilities:

```python
from qdrant_loader_mcp_server.tools import SearchTool

class SemanticSearchTool(SearchTool):
    """Advanced semantic search tool."""
    
    name = "semantic_search"
    description = "Perform semantic search with advanced filtering"
    
    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute semantic search."""
        filters = kwargs.get('filters', {})
        limit = kwargs.get('limit', 10)
        
        # Your search logic
        results = await self.search_engine.semantic_search(
            query=query,
            filters=filters,
            limit=limit
        )
        
        return {
            "query": query,
            "results": [self._format_result(r) for r in results],
            "total": len(results)
        }
```

## 🧪 Testing Extensions

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock, patch
from my_extension.custom_source import CustomDataSource

@pytest.mark.asyncio
async def test_custom_source_fetch_documents():
    """Test document fetching."""
    config = {
        "api_url": "https://api.example.com",
        "api_key": "test_key"
    }
    
    source = CustomDataSource(config)
    
    # Mock the API response
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {"id": "1", "title": "Test", "content": "Test content"}
        ]
        mock_get.return_value.__aenter__.return_value = mock_response
        
        documents = []
        async for doc in source.fetch_documents():
            documents.append(doc)
        
        assert len(documents) == 1
        assert documents[0].title == "Test"
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_custom_source_integration():
    """Test full integration with QDrant Loader."""
    from qdrant_loader import QDrantLoader
    from qdrant_loader.config import Config
    
    config = Config(
        qdrant_url="memory://test",
        collection_name="test",
        sources=[{
            "type": "custom",
            "api_url": "https://api.example.com",
            "api_key": "test_key"
        }]
    )
    
    loader = QDrantLoader(config)
    result = await loader.ingest()
    
    assert result.processed_count > 0
```

## 📦 Packaging Extensions

### Creating a Package

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="qdrant-loader-custom-extension",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "qdrant-loader>=1.0.0",
        "aiohttp>=3.8.0",
        "pydantic>=1.10.0"
    ],
    entry_points={
        "qdrant_loader.plugins": [
            "custom = my_extension:CustomDataSource"
        ]
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Custom data source for QDrant Loader",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/qdrant-loader-custom-extension",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
```

### Plugin Discovery

```python
# my_extension/__init__.py
from qdrant_loader.plugins import register_plugin
from .custom_source import CustomDataSource

def load_plugin():
    """Load and register the plugin."""
    register_plugin("custom", CustomDataSource)

# Auto-register when imported
load_plugin()
```

## 🔍 Advanced Patterns

### Plugin Composition

```python
class CompositeDataSource(DataSourcePlugin):
    """Combine multiple data sources."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.sources = []
        for source_config in config.get("sources", []):
            source_type = source_config["type"]
            source_class = get_plugin_class(source_type)
            self.sources.append(source_class(source_config))
    
    async def fetch_documents(self) -> AsyncIterator[Document]:
        """Fetch from all configured sources."""
        for source in self.sources:
            async for document in source.fetch_documents():
                yield document
```

### Middleware Pattern

```python
class ProcessingMiddleware:
    """Middleware for document processing."""
    
    def __init__(self, next_processor):
        self.next_processor = next_processor
    
    async def process(self, document: Document) -> Document:
        """Process document with middleware chain."""
        # Pre-processing
        document = await self.pre_process(document)
        
        # Call next processor
        document = await self.next_processor.process(document)
        
        # Post-processing
        document = await self.post_process(document)
        
        return document
    
    async def pre_process(self, document: Document) -> Document:
        """Override in subclasses."""
        return document
    
    async def post_process(self, document: Document) -> Document:
        """Override in subclasses."""
        return document
```

### Configuration Inheritance

```python
class BaseAPISource(DataSourcePlugin):
    """Base class for API-based sources."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config["base_url"]
        self.api_key = config["api_key"]
        self.session = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session with common settings."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        self.session = aiohttp.ClientSession(headers=headers)

class GitHubSource(BaseAPISource):
    """GitHub-specific implementation."""
    
    async def fetch_documents(self) -> AsyncIterator[Document]:
        """Fetch from GitHub API."""
        async with self.session.get(f"{self.base_url}/repos") as response:
            # GitHub-specific logic
            pass
```

## 📚 Extension Documentation

### Detailed Guides

- **[Data Source Connectors](./data-source-connectors.md)** - Complete guide to creating data source plugins
- **[File Converters](./file-converters.md)** - Adding support for new file formats
- **[Search Tools](./search-tools.md)** - Extending MCP server search capabilities
- **[Custom Processors](./custom-processors.md)** - Building custom content processors

### Best Practices

1. **Follow the plugin interface** - Implement all required methods
2. **Validate configuration** - Use Pydantic for robust config validation
3. **Handle errors gracefully** - Provide meaningful error messages
4. **Use async/await properly** - Follow async best practices
5. **Write comprehensive tests** - Unit and integration tests
6. **Document your extension** - Clear documentation and examples

### Performance Considerations

1. **Use connection pooling** - Reuse HTTP connections
2. **Implement rate limiting** - Respect API limits
3. **Batch operations** - Process multiple items together
4. **Cache when appropriate** - Avoid redundant operations
5. **Monitor resource usage** - Memory and CPU optimization

## 🆘 Getting Help

### Development Support

- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask development questions
- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report bugs or request features
- **[Contributing Guide](../../CONTRIBUTING.md)** - Contribution guidelines

### Community Extensions

- **[Extension Registry](https://github.com/martin-papy/qdrant-loader/wiki/Extensions)** - Community-maintained extensions
- **[Example Extensions](https://github.com/martin-papy/qdrant-loader/tree/main/examples/extensions)** - Reference implementations

---

**Ready to extend QDrant Loader?** Choose the type of extension you want to create and dive into the detailed guides. Start with [Data Source Connectors](./data-source-connectors.md) for adding new data sources or [File Converters](./file-converters.md) for new file format support.
