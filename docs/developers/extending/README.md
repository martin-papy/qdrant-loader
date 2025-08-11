# Extension Guide
This guide provides instructions for extending QDrant Loader with custom functionality. QDrant Loader is designed with a modular architecture that allows for extension through custom connectors and configuration.
## 🎯 Extension Overview
QDrant Loader currently supports extension through:
- **Custom Data Source Connectors** - Add support for new data sources by implementing the BaseConnector interface
- **Configuration Extensions** - Extend configuration options for existing connectors
- **File Conversion Extensions** - Leverage the MarkItDown library for additional file format support
### Current Architecture
```
┌─────────────────────────────────────────────────────────────┐
│ QDrant Loader CLI │
├─────────────────────────────────────────────────────────────┤
│ Project Manager │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ Config │ │ State │ │ Monitoring │ │
│ │ Management │ │ Management │ │ │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Async Ingestion Pipeline │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ Connectors │ │ Chunking │ │ Embeddings │ │
│ │ │ │ │ │ │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ File │ │ QDrant │ │ State │ │
│ │ Conversion │ │ Manager │ │ Tracking │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```
## 🚀 Development Environment Setup
### Prerequisites
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
## 📊 Custom Data Source Connectors
### Creating a Custom Connector
Data source connectors fetch documents from external systems. All connectors must implement the `BaseConnector` interface:
```python
from abc import ABC, abstractmethod
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.document import Document
class BaseConnector(ABC): """Base class for all connectors.""" def __init__(self, config: SourceConfig): self.config = config self._initialized = False async def __aenter__(self): """Async context manager entry.""" self._initialized = True return self async def __aexit__(self, exc_type, exc_val, exc_tb): """Async context manager exit.""" self._initialized = False @abstractmethod async def get_documents(self) -> list[Document]: """Get documents from the source.""" pass
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
class CustomAPIConnector(BaseConnector): """Connector for custom REST API data source.""" def __init__(self, config: SourceConfig): super().__init__(config) # Access configuration through config.config dict self.api_url = config.config["api_url"] self.api_key = config.config.get("api_key") self.batch_size = config.config.get("batch_size", 100) async def get_documents(self) -> list[Document]: """Fetch documents from the custom API.""" documents = [] headers = {} if self.api_key: headers["Authorization"] = f"Bearer {self.api_key}" async with httpx.AsyncClient() as client: try: response = await client.get( f"{self.api_url}/documents", headers=headers, params={"limit": self.batch_size} ) response.raise_for_status() data = response.json() for item in data.get("documents", []): document = self._convert_to_document(item) if document: documents.append(document) except httpx.RequestError as e: logger.error(f"API request failed: {e}") raise return documents def _convert_to_document(self, api_item: dict[str, Any]) -> Document: """Convert API response item to Document.""" return Document( title=api_item.get("title", "Untitled"), content_type="text/plain", content=api_item["content"], metadata={ "api_id": api_item["id"], "author": api_item.get("author"), "created_at": api_item.get("created_at"), "tags": api_item.get("tags", []), }, source_type="custom_api", source=self.config.source, url=f"{self.api_url}/documents/{api_item['id']}" )
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
def create_connector(source_type: str, config: SourceConfig) -> BaseConnector: """Factory function to create connectors.""" if source_type == "custom_api": from .custom_api import CustomAPIConnector return CustomAPIConnector(config) elif source_type == "confluence": from qdrant_loader.connectors.confluence import ConfluenceConnector return ConfluenceConnector(config) # ... other existing connectors else: raise ValueError(f"Unknown source type: {source_type}")
```
## 📄 Document Model
The `Document` model is the core data structure used throughout QDrant Loader. It uses Pydantic BaseModel:
```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime, UTC
class Document(BaseModel): """Document model with enhanced metadata support.""" id: str # Auto-generated from source_type, source, and url title: str content_type: str content: str metadata: dict[str, Any] = Field(default_factory=dict) content_hash: str # Auto-generated hash of content source_type: str source: str url: str is_deleted: bool = False created_at: datetime = Field(default_factory=lambda: datetime.now(UTC)) updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```
### Document Creation Best Practices
1. **Provide meaningful titles** - Use descriptive titles that help with search
2. **Set appropriate content_type** - Use MIME types when possible
3. **Include rich metadata** - Add author, creation date, tags, etc.
4. **Use consistent source_type** - Follow naming conventions
5. **Provide URLs when available** - Enable linking back to original content
### Document Creation Example
```python
# The Document constructor automatically generates id and content_hash
document = Document( title="API Documentation", content_type="text/markdown", content="# API Reference\n\nThis is the API documentation...", metadata={ "author": "John Doe", "version": "1.0", "tags": ["api", "documentation"], "last_modified": "2024-01-15T10:30:00Z" }, source_type="custom_api", source="my-api-docs", url="https://api.example.com/docs/reference"
)
```
## 🔧 Configuration Extensions
### Custom Configuration Classes
Create configuration classes for your custom connectors by extending `SourceConfig`:
```python
from pydantic import BaseModel, field_validator
from typing import Optional, List
from qdrant_loader.config.source_config import SourceConfig
class CustomAPIConfig(SourceConfig): """Configuration for custom API connector.""" api_key: Optional[str] = None batch_size: int = 100 timeout: int = 30 max_retries: int = 3 include_tags: List[str] = [] exclude_tags: List[str] = [] @field_validator('batch_size') @classmethod def validate_batch_size(cls, v): if v < 1 or v > 1000: raise ValueError('Batch size must be between 1 and 1000') return v
```
### Configuration Usage
```yaml
# config.yaml
global: qdrant: url: "${QDRANT_URL}" api_key: "${QDRANT_API_KEY}" collection_name: "my-collection"
projects: my-project: display_name: "My Custom API Project" description: "Project using custom API connector" sources: custom_api: my-api-source: base_url: "https://api.example.com" api_key: "${API_KEY}" batch_size: 50 timeout: 60 include_tags: ["published", "public"] exclude_tags: ["draft", "private"]
```
## 🔄 File Conversion Extensions
QDrant Loader uses the MarkItDown library for file conversion. You can extend file conversion capabilities by:
### 1. Leveraging MarkItDown Features
```python
from qdrant_loader.core.file_conversion import FileConverter, FileConversionConfig
# Configure file conversion
config = FileConversionConfig( enable_llm_descriptions=True, llm_model="gpt-4o-mini", max_file_size=50 * 1024 * 1024, # 50MB conversion_timeout=300 # 5 minutes
)
converter = FileConverter(config)
```
### 2. Custom File Processing
```python
class CustomFileProcessor: """Custom file processor for specific formats.""" def __init__(self, converter: FileConverter): self.converter = converter async def process_custom_format(self, file_path: str) -> str: """Process custom file format.""" if file_path.endswith('.custom'): # Custom processing logic with open(file_path, 'rb') as f: content = f.read() return self._parse_custom_format(content) else: # Fall back to MarkItDown return await self.converter.convert_file(file_path) def _parse_custom_format(self, content: bytes) -> str: """Parse custom file format.""" # Your custom parsing logic here return content.decode('utf-8')
```
## 🧪 Testing Custom Extensions
### Unit Testing
```python
import pytest
from unittest.mock import AsyncMock, patch
from your_extension.custom_api import CustomAPIConnector
from qdrant_loader.config.source_config import SourceConfig
@pytest.mark.asyncio
async def test_custom_connector_fetch_documents(): """Test document fetching.""" config = SourceConfig( source_type="custom_api", source="test-source", base_url="https://api.example.com", config={ "api_url": "https://api.example.com", "api_key": "test_key" } ) connector = CustomAPIConnector(config) # Mock the API response with patch('httpx.AsyncClient.get') as mock_get: mock_response = AsyncMock() mock_response.json.return_value = { "documents": [ {"id": "1", "title": "Test", "content": "Test content"} ] } mock_response.raise_for_status.return_value = None mock_get.return_value.__aenter__.return_value = mock_response documents = await connector.get_documents() assert len(documents) == 1 assert documents[0].title == "Test" assert documents[0].content == "Test content"
```
### Integration Testing
```python
@pytest.mark.asyncio
async def test_custom_connector_integration(): """Test full integration with QDrant Loader.""" from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline from qdrant_loader.config import Settings # Load test configuration settings = Settings.from_yaml("test_config.yaml") # Create pipeline with custom connector pipeline = AsyncIngestionPipeline(settings) result = await pipeline.process_documents(project_id="test-project") assert len(result) > 0
```
## 📦 Packaging Extensions
### Creating a Package
```toml
# pyproject.toml
[project]
name = "qdrant-loader-custom-extension"
version = "1.0.0"
dependencies = [ "qdrant-loader>=1.0.0", "httpx>=0.24.0", "pydantic>=2.0.0"
]
[project.entry-points."qdrant_loader.connectors"]
custom_api = "my_extension.custom_api:CustomAPIConnector"
```
### Distribution
```bash
# Build package
python -m build
# Install locally for testing
pip install -e .
# Publish to PyPI
python -m twine upload dist/*
```
## 🔍 Advanced Patterns
### Error Handling
```python
from qdrant_loader.connectors.exceptions import ConnectorError
class CustomAPIConnector(BaseConnector): async def get_documents(self) -> list[Document]: try: # Your implementation pass except httpx.RequestError as e: raise ConnectorError( f"Failed to fetch documents from {self.api_url}: {e}" ) from e except Exception as e: logger.error(f"Unexpected error: {e}") raise
```
### Async Best Practices
```python
import asyncio
from typing import List
class CustomAPIConnector(BaseConnector): def __init__(self, config: SourceConfig): super().__init__(config) self.session = None self.semaphore = asyncio.Semaphore(10) # Limit concurrency async def __aenter__(self): """Initialize HTTP session.""" await super().__aenter__() self.session = httpx.AsyncClient( timeout=httpx.Timeout(self.config.config.get("timeout", 30)) ) return self async def __aexit__(self, exc_type, exc_val, exc_tb): """Clean up HTTP session.""" if self.session: await self.session.aclose() await super().__aexit__(exc_type, exc_val, exc_tb) async def get_documents(self) -> list[Document]: """Fetch documents with proper async handling.""" async with self.semaphore: response = await self.session.get(f"{self.api_url}/documents") response.raise_for_status() data = response.json() return [self._convert_to_document(item) for item in data["documents"]]
```
### Configuration Inheritance
```python
class BaseAPIConnector(BaseConnector): """Base class for API-based connectors.""" def __init__(self, config: SourceConfig): super().__init__(config) self.base_url = str(config.base_url) self.api_key = config.config.get("api_key") self.session = None async def __aenter__(self): """Initialize HTTP session with common settings.""" await super().__aenter__() headers = {} if self.api_key: headers["Authorization"] = f"Bearer {self.api_key}" self.session = httpx.AsyncClient(headers=headers) return self
class GitHubConnector(BaseAPIConnector): """GitHub-specific implementation.""" async def get_documents(self) -> list[Document]: """Fetch from GitHub API.""" response = await self.session.get(f"{self.base_url}/repos") # GitHub-specific logic pass
```
## 📚 Available Connectors
QDrant Loader includes several built-in connectors you can reference:
- **GitConnector** - Git repository processing with branch and path filtering
- **ConfluenceConnector** - Atlassian Confluence space integration
- **JiraConnector** - Atlassian Jira project integration
- **LocalFileConnector** - Local file system processing
- **PublicDocsConnector** - Public documentation websites
Each connector demonstrates different patterns and can serve as examples for your custom implementations.
## 🆘 Getting Help
### Development Support
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask development questions
- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report bugs or request features
- **[Contributing Guide](../../CONTRIBUTING.md)** - Contribution guidelines
### Related Documentation
- **[Architecture Overview](../architecture/)** - System design and components
- **[Configuration Reference](../../users/configuration/)** - Configuration options
---
**Ready to extend QDrant Loader?** Start by implementing a custom connector using the BaseConnector interface and follow the patterns shown in the existing connectors.
