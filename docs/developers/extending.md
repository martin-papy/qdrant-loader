# Extending QDrant Loader

This guide provides instructions for extending QDrant Loader with custom functionality. QDrant Loader is designed with a modular architecture that allows for extension through custom connectors and configuration.

## 🎯 Extension Overview

QDrant Loader currently supports extension through:

- **Custom Data Source Connectors** - Add support for new data sources by implementing the BaseConnector interface
- **Configuration Extensions** - Extend configuration options for existing connectors
- **File Conversion Extensions** - Leverage the MarkItDown library for additional file format support

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QDrant Loader CLI                        │
├─────────────────────────────────────────────────────────────┤
│                  Project Manager                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Config    │ │   State     │ │ Monitoring  │          │
│  │ Management  │ │ Management  │ │             │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                Async Ingestion Pipeline                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Connectors  │ │   Chunking  │ │ Embeddings  │          │
│  │             │ │             │ │             │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │    File     │ │   QDrant    │ │    State    │          │
│  │ Conversion  │ │   Manager   │ │   Tracking  │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Custom Data Source Connectors

### Creating a Custom Connector

Data source connectors fetch documents from external systems. All connectors must implement the `BaseConnector` interface:

```python
from abc import ABC, abstractmethod
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.document import Document

class BaseConnector(ABC):
    """Base class for all connectors."""

    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._initialized = False

    @abstractmethod
    async def get_documents(self) -> list[Document]:
        """Get documents from the source."""
        pass
```

### Example Custom Connector Implementation

Here's an example of implementing a custom connector for a REST API:

```python
import httpx
from typing import Any
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

class CustomAPIConnector(BaseConnector):
    """Connector for custom REST API data source."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        # Access configuration through config.config dict
        self.api_url = config.config["api_url"]
        self.api_key = config.config.get("api_key")
        self.batch_size = config.config.get("batch_size", 100)
        
    async def get_documents(self) -> list[Document]:
        """Fetch documents from the custom API."""
        documents = []
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/documents",
                    headers=headers,
                    params={"limit": self.batch_size}
                )
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("documents", []):
                    document = self._convert_to_document(item)
                    if document:
                        documents.append(document)
                        
            except httpx.RequestError as e:
                logger.error(f"API request failed: {e}")
                raise
        
        return documents
    
    def _convert_to_document(self, api_item: dict[str, Any]) -> Document:
        """Convert API response item to Document."""
        return Document(
            title=api_item.get("title", "Untitled"),
            content_type="text/plain",
            content=api_item["content"],
            metadata={
                "api_id": api_item["id"],
                "author": api_item.get("author"),
                "created_at": api_item.get("created_at"),
                "tags": api_item.get("tags", []),
            },
            source_type="custom_api",
            source=self.config.config["api_url"],
            url=f"{self.api_url}/documents/{api_item['id']}"
        )
```

### Integrating Custom Connectors

To integrate a custom connector into QDrant Loader:

1. **Create the connector class** implementing `BaseConnector`
2. **Add configuration support** by extending the source configuration
3. **Register the connector** in your project's connector factory

Example connector factory extension:

```python
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.config.source_config import SourceConfig

def create_connector(source_type: str, config: SourceConfig) -> BaseConnector:
    """Factory function to create connectors."""
    
    if source_type == "custom_api":
        from .custom_api import CustomAPIConnector
        return CustomAPIConnector(config)
    elif source_type == "confluence":
        from qdrant_loader.connectors.confluence import ConfluenceConnector
        return ConfluenceConnector(config)
    # ... other existing connectors
    else:
        raise ValueError(f"Unknown source type: {source_type}")
```

## 📄 Document Model

The `Document` model is the core data structure used throughout QDrant Loader:

```python
class Document(BaseModel):
    """Document model with enhanced metadata support."""

    id: str                           # Auto-generated from source info
    title: str                        # Document title
    content_type: str                 # MIME type or content type
    content: str                      # Main document content
    metadata: dict[str, Any]          # Additional metadata
    content_hash: str                 # Auto-generated content hash
    source_type: str                  # Type of source (e.g., "confluence")
    source: str                       # Source identifier
    url: str                          # Document URL
    is_deleted: bool = False          # Deletion flag
    created_at: datetime              # Creation timestamp
    updated_at: datetime              # Last update timestamp
```

Key features of the Document model:

- **Automatic ID generation** based on source_type, source, and url
- **Content hashing** for change detection
- **Hierarchical metadata** support for parent/child relationships
- **Breadcrumb navigation** support
- **Deletion tracking** for incremental updates

## 🔧 Configuration Extensions

### Custom Source Configuration

To add configuration options for custom connectors, extend the source configuration:

```yaml
# workspace.yml
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  - name: "custom-api-project"
    sources:
      - source_type: "custom_api"
        config:
          api_url: "https://api.example.com"
          api_key: "${CUSTOM_API_KEY}"
          batch_size: 50
          include_metadata: true
          custom_headers:
            User-Agent: "QDrant-Loader/1.0"
```

### Environment Variable Support

QDrant Loader supports environment variable substitution in configuration:

```bash
# .env file
CUSTOM_API_KEY=your_api_key_here
CUSTOM_API_URL=https://api.example.com
```

## 📁 File Conversion Extensions

QDrant Loader uses the MarkItDown library for file conversion. You can extend file conversion capabilities by:

### 1. Configuring MarkItDown Options

```yaml
global_config:
  file_conversion:
    max_file_size: 50000000  # 50MB
    conversion_timeout: 300   # 5 minutes
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o-mini"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"
```

### 2. Supporting Additional File Types

MarkItDown supports many file formats out of the box:

- Office documents (Word, Excel, PowerPoint)
- PDF files
- Images (with OCR capabilities)
- Audio files (with transcription)
- Archive files (ZIP, etc.)
- Code files
- And many more

## 🔍 Development Workflow

### Setting Up Development Environment

1. **Clone the repository**:

```bash
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader
```

2. **Install in development mode**:

```bash
cd packages/qdrant-loader
pip install -e ".[dev]"
```

3. **Run tests**:

```bash
pytest
```

### Testing Custom Connectors

Create tests for your custom connectors:

```python
import pytest
from unittest.mock import AsyncMock, patch
from your_connector import CustomAPIConnector
from qdrant_loader.config.source_config import SourceConfig

@pytest.mark.asyncio
async def test_custom_api_connector():
    """Test custom API connector."""
    config = SourceConfig(
        source_type="custom_api",
        config={
            "api_url": "https://api.example.com",
            "api_key": "test_key",
            "batch_size": 10
        }
    )
    
    connector = CustomAPIConnector(config)
    
    with patch("httpx.AsyncClient") as mock_client:
        # Mock API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "documents": [
                {
                    "id": "1",
                    "title": "Test Document",
                    "content": "Test content",
                    "author": "Test Author"
                }
            ]
        }
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        async with connector:
            documents = await connector.get_documents()
            
        assert len(documents) == 1
        assert documents[0].title == "Test Document"
        assert documents[0].content == "Test content"
```

## 🚀 Deployment Considerations

### Custom Connector Deployment

When deploying custom connectors:

1. **Package your connector** as a separate Python package
2. **Install alongside QDrant Loader**:

```bash
pip install qdrant-loader your-custom-connector
```

3. **Configure your workspace** to use the custom connector
4. **Test thoroughly** in your target environment

### Performance Considerations

- **Implement async operations** for I/O-bound tasks
- **Use appropriate batch sizes** for API calls
- **Implement proper error handling** and retry logic
- **Monitor memory usage** for large document sets
- **Use connection pooling** for HTTP clients

## 📚 Best Practices

### Connector Development

1. **Follow async patterns** - Use async/await for I/O operations
2. **Implement proper logging** - Use the QDrant Loader logging system
3. **Handle errors gracefully** - Implement retry logic and proper error handling
4. **Validate configuration** - Check required configuration parameters
5. **Document your connector** - Provide clear usage examples
6. **Write comprehensive tests** - Cover both success and failure scenarios

### Configuration Management

1. **Use environment variables** for sensitive data
2. **Provide sensible defaults** for optional configuration
3. **Validate configuration** at startup
4. **Document all options** clearly

### Performance Optimization

1. **Batch operations** when possible
2. **Implement connection pooling** for HTTP clients
3. **Use appropriate timeouts** for external services
4. **Monitor resource usage** during development
5. **Profile your connector** under realistic loads

## 🔗 Related Documentation

- [Architecture Overview](./architecture.md) - Understanding QDrant Loader's architecture
- [Configuration Reference](../users/configuration/config-file-reference.md) - Configuration options
- [Testing Guide](./testing.md) - Testing strategies and tools
- [Deployment Guide](./deployment.md) - Deployment best practices

## 📞 Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/martin-papy/qdrant-loader/issues)
- **Documentation**: [Browse the full documentation](https://github.com/martin-papy/qdrant-loader#readme)
- **Examples**: Check the existing connectors in `packages/qdrant-loader/src/qdrant_loader/connectors/`
