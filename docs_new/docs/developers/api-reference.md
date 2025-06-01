# API Reference

This comprehensive API reference provides detailed documentation for all QDrant Loader classes, methods, and interfaces. Whether you're integrating QDrant Loader into your application or extending its functionality, this reference covers everything you need to know about the programmatic interface.

## 🎯 Quick API Overview

### Core Classes

```python
from qdrant_loader import QDrantLoader
from qdrant_loader.config import Config
from qdrant_loader.models import Document, SearchResult, LoadResult
from qdrant_loader.connectors import LocalConnector, GitConnector
from qdrant_loader.search import SemanticSearch, HierarchySearch
```

### Basic Usage Pattern

```python
# Initialize loader
config = Config.from_file("config.yaml")
loader = QDrantLoader(config)

# Load documents
result = loader.load_source("local", path="./docs")

# Search documents
results = loader.search("machine learning", limit=5)
```

## 📚 Core API Classes

### QDrantLoader

**Main entry point for all QDrant Loader operations.**

```python
class QDrantLoader:
    """Primary interface for QDrant Loader functionality."""
    
    def __init__(self, config: Config, monitor: Optional[PerformanceMonitor] = None):
        """Initialize QDrant Loader with configuration.
        
        Args:
            config: Configuration object
            monitor: Optional performance monitor
        """
```

#### Methods

##### `load_source(source_type: str, **kwargs) -> LoadResult`

Load documents from a specified data source.

**Parameters:**

- `source_type` (str): Type of data source ('local', 'git', 'confluence', 'jira')
- `**kwargs`: Source-specific parameters

**Returns:** `LoadResult` object with operation details

**Example:**

```python
# Load from local directory
result = loader.load_source(
    source_type="local",
    path="./documents",
    include_patterns=["*.md", "*.txt"],
    exclude_patterns=["*.tmp"]
)

# Load from Git repository
result = loader.load_source(
    source_type="git",
    url="https://github.com/user/repo.git",
    branch="main",
    path_filter="docs/"
)

# Load from Confluence
result = loader.load_source(
    source_type="confluence",
    space_key="DOCS",
    include_attachments=True
)
```

##### `search(query: str, **kwargs) -> List[SearchResult]`

Search documents using semantic similarity.

**Parameters:**

- `query` (str): Search query text
- `collection_name` (str, optional): Target collection name
- `limit` (int, optional): Maximum results to return (default: 10)
- `threshold` (float, optional): Similarity threshold (default: 0.7)
- `filters` (dict, optional): Metadata filters

**Returns:** List of `SearchResult` objects

**Example:**

```python
# Basic search
results = loader.search("machine learning concepts")

# Advanced search with filters
results = loader.search(
    query="API documentation",
    collection_name="tech_docs",
    limit=20,
    threshold=0.8,
    filters={"content_type": "documentation", "language": "python"}
)

# Process results
for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Title: {result.metadata.get('title', 'Untitled')}")
    print(f"Content: {result.content[:200]}...")
    print(f"Source: {result.metadata.get('source_url', 'Unknown')}")
    print("---")
```

##### `hierarchy_search(query: str, **kwargs) -> HierarchySearchResult`

Search with document hierarchy awareness.

**Parameters:**

- `query` (str): Search query
- `depth` (int, optional): Maximum hierarchy depth
- `parent_title` (str, optional): Filter by parent document
- `organize_by_hierarchy` (bool, optional): Group results by structure

**Returns:** `HierarchySearchResult` with structured results

**Example:**

```python
# Search with hierarchy context
result = loader.hierarchy_search(
    query="installation guide",
    depth=2,
    organize_by_hierarchy=True
)

# Access hierarchical results
for section in result.sections:
    print(f"Section: {section.title}")
    for doc in section.documents:
        print(f"  - {doc.title} (depth: {doc.depth})")
```

##### `attachment_search(query: str, **kwargs) -> List[AttachmentSearchResult]`

Search file attachments with content extraction.

**Parameters:**

- `query` (str): Search query
- `file_types` (List[str], optional): Filter by file types
- `include_parent_context` (bool, optional): Include parent document context

**Returns:** List of `AttachmentSearchResult` objects

**Example:**

```python
# Search attachments
results = loader.attachment_search(
    query="architecture diagram",
    file_types=["pdf", "png", "jpg"],
    include_parent_context=True
)

# Process attachment results
for result in results:
    print(f"File: {result.filename}")
    print(f"Type: {result.file_type}")
    print(f"Size: {result.file_size}")
    print(f"Parent: {result.parent_document}")
```

##### `create_collection(name: str, **kwargs) -> bool`

Create a new document collection.

**Parameters:**

- `name` (str): Collection name
- `vector_size` (int, optional): Vector dimension size
- `distance_metric` (str, optional): Distance metric ('cosine', 'euclidean', 'dot')

**Returns:** Success boolean

**Example:**

```python
# Create collection with custom settings
success = loader.create_collection(
    name="product_docs",
    vector_size=1536,
    distance_metric="cosine"
)
```

##### `delete_collection(name: str) -> bool`

Delete a document collection.

**Parameters:**

- `name` (str): Collection name to delete

**Returns:** Success boolean

##### `list_collections() -> List[CollectionInfo]`

List all available collections.

**Returns:** List of `CollectionInfo` objects

**Example:**

```python
collections = loader.list_collections()
for collection in collections:
    print(f"Name: {collection.name}")
    print(f"Documents: {collection.document_count}")
    print(f"Size: {collection.size_bytes}")
```

##### `get_status(collection_name: str = None) -> StatusInfo`

Get system or collection status information.

**Parameters:**

- `collection_name` (str, optional): Specific collection to check

**Returns:** `StatusInfo` object

**Example:**

```python
# System status
status = loader.get_status()
print(f"QDrant connected: {status.qdrant_connected}")
print(f"Collections: {status.total_collections}")

# Collection-specific status
status = loader.get_status("my_docs")
print(f"Documents: {status.document_count}")
print(f"Last updated: {status.last_updated}")
```

### Config

**Configuration management class.**

```python
class Config:
    """Configuration management for QDrant Loader."""
    
    def __init__(self, config_dict: dict):
        """Initialize configuration from dictionary."""
```

#### Class Methods

##### `from_file(file_path: str) -> Config`

Load configuration from YAML file.

**Parameters:**

- `file_path` (str): Path to configuration file

**Returns:** `Config` instance

**Example:**

```python
config = Config.from_file("qdrant-loader.yaml")
```

##### `from_dict(config_dict: dict) -> Config`

Create configuration from dictionary.

**Parameters:**

- `config_dict` (dict): Configuration dictionary

**Returns:** `Config` instance

**Example:**

```python
config_dict = {
    "qdrant": {
        "url": "http://localhost:6333",
        "api_key": "your-key"
    },
    "openai": {
        "api_key": "your-openai-key"
    }
}
config = Config.from_dict(config_dict)
```

##### `from_env() -> Config`

Create configuration from environment variables.

**Returns:** `Config` instance

**Example:**

```python
# Requires environment variables like QDRANT_URL, OPENAI_API_KEY
config = Config.from_env()
```

#### Instance Methods

##### `validate() -> ValidationResult`

Validate configuration completeness and correctness.

**Returns:** `ValidationResult` with validation details

**Example:**

```python
result = config.validate()
if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")
```

##### `to_dict() -> dict`

Convert configuration to dictionary.

**Returns:** Configuration as dictionary

##### `save(file_path: str) -> None`

Save configuration to YAML file.

**Parameters:**

- `file_path` (str): Output file path

**Example:**

```python
config.save("updated-config.yaml")
```

## 📊 Data Models

### Document

**Represents a source document with content and metadata.**

```python
@dataclass
class Document:
    """Document data model."""
    
    content: str
    metadata: Dict[str, Any]
    id: Optional[str] = None
    source_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Example:**

```python
document = Document(
    content="This is the document content...",
    metadata={
        "title": "API Documentation",
        "author": "John Doe",
        "file_path": "/docs/api.md",
        "content_type": "documentation"
    },
    source_type="local"
)
```

### ProcessedChunk

**Represents a processed document chunk with embeddings.**

```python
@dataclass
class ProcessedChunk:
    """Processed document chunk with embeddings."""
    
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    chunk_index: int
    parent_document_id: str
    chunk_size: int
    overlap_size: int = 0
```

### SearchResult

**Represents a search result with relevance score.**

```python
@dataclass
class SearchResult:
    """Search result data model."""
    
    content: str
    score: float
    metadata: Dict[str, Any]
    chunk_id: str
    document_id: str
    highlights: Optional[List[str]] = None
```

**Example Usage:**

```python
results = loader.search("machine learning")
for result in results:
    print(f"Relevance: {result.score:.3f}")
    print(f"Content: {result.content}")
    print(f"Source: {result.metadata.get('source_url')}")
    
    # Access highlights if available
    if result.highlights:
        print("Highlights:")
        for highlight in result.highlights:
            print(f"  - {highlight}")
```

### LoadResult

**Represents the result of a data loading operation.**

```python
@dataclass
class LoadResult:
    """Load operation result."""
    
    success: bool
    documents_processed: int
    chunks_created: int
    errors: List[str]
    warnings: List[str]
    processing_time: float
    collection_name: str
    source_info: Dict[str, Any]
```

**Example Usage:**

```python
result = loader.load_source("local", path="./docs")

print(f"Success: {result.success}")
print(f"Documents processed: {result.documents_processed}")
print(f"Chunks created: {result.chunks_created}")
print(f"Processing time: {result.processing_time:.2f}s")

if result.errors:
    print("Errors encountered:")
    for error in result.errors:
        print(f"  - {error}")
```

### HierarchySearchResult

**Represents hierarchical search results with document structure.**

```python
@dataclass
class HierarchySearchResult:
    """Hierarchical search result."""
    
    query: str
    total_results: int
    sections: List[HierarchySection]
    processing_time: float
    
@dataclass
class HierarchySection:
    """Hierarchical section with documents."""
    
    title: str
    depth: int
    documents: List[HierarchyDocument]
    parent_section: Optional[str] = None
    
@dataclass
class HierarchyDocument:
    """Document within hierarchy context."""
    
    title: str
    content: str
    score: float
    depth: int
    path: List[str]  # Breadcrumb path
    metadata: Dict[str, Any]
```

### AttachmentSearchResult

**Represents file attachment search results.**

```python
@dataclass
class AttachmentSearchResult:
    """Attachment search result."""
    
    filename: str
    file_type: str
    file_size: int
    content: str
    score: float
    metadata: Dict[str, Any]
    parent_document: Optional[str] = None
    download_url: Optional[str] = None
    extracted_text: Optional[str] = None
```

## 🔌 Connector APIs

### BaseConnector

**Abstract base class for data source connectors.**

```python
class BaseConnector(ABC):
    """Base connector interface."""
    
    def __init__(self, config: dict):
        self.config = config
    
    @abstractmethod
    def fetch_documents(self) -> Iterator[Document]:
        """Fetch documents from data source."""
        pass
    
    @abstractmethod
    def supports_incremental(self) -> bool:
        """Check if incremental updates are supported."""
        pass
    
    def validate_config(self) -> bool:
        """Validate connector configuration."""
        return True
```

### LocalConnector

**File system connector for local documents.**

```python
class LocalConnector(BaseConnector):
    """Local file system connector."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.path = config["path"]
        self.include_patterns = config.get("include_patterns", ["*"])
        self.exclude_patterns = config.get("exclude_patterns", [])
        self.recursive = config.get("recursive", True)
```

**Configuration:**

```python
local_config = {
    "path": "./documents",
    "include_patterns": ["*.md", "*.txt", "*.pdf"],
    "exclude_patterns": ["*.tmp", "*.log"],
    "recursive": True,
    "follow_symlinks": False,
    "max_file_size": "10MB"
}

connector = LocalConnector(local_config)
```

### GitConnector

**Git repository connector.**

```python
class GitConnector(BaseConnector):
    """Git repository connector."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.url = config["url"]
        self.branch = config.get("branch", "main")
        self.path_filter = config.get("path_filter")
        self.auth_token = config.get("auth_token")
```

**Configuration:**

```python
git_config = {
    "url": "https://github.com/user/repo.git",
    "branch": "main",
    "path_filter": "docs/",
    "auth_token": "ghp_your_token",
    "clone_depth": 1,
    "include_patterns": ["*.md"],
    "exclude_patterns": [".git/**"]
}

connector = GitConnector(git_config)
```

### ConfluenceConnector

**Atlassian Confluence connector.**

```python
class ConfluenceConnector(BaseConnector):
    """Confluence connector."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config["base_url"]
        self.username = config["username"]
        self.api_token = config["api_token"]
        self.space_key = config.get("space_key")
```

**Configuration:**

```python
confluence_config = {
    "base_url": "https://company.atlassian.net",
    "username": "user@company.com",
    "api_token": "your_api_token",
    "space_key": "DOCS",
    "include_attachments": True,
    "page_limit": 1000,
    "content_types": ["page", "blogpost"]
}

connector = ConfluenceConnector(confluence_config)
```

## 🔍 Search APIs

### SemanticSearch

**Vector similarity-based search.**

```python
class SemanticSearch:
    """Semantic search implementation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.qdrant_client = QdrantClient(config.qdrant.url)
        self.embedding_provider = EmbeddingProvider(config)
    
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute semantic search."""
        pass
```

**Usage:**

```python
search_engine = SemanticSearch(config)

results = search_engine.search(
    query="machine learning algorithms",
    collection_name="tech_docs",
    limit=10,
    threshold=0.75,
    filters={"category": "tutorial"}
)
```

### HierarchySearch

**Structure-aware document search.**

```python
class HierarchySearch:
    """Hierarchy-aware search implementation."""
    
    def search(self, query: str, **kwargs) -> HierarchySearchResult:
        """Execute hierarchy search."""
        pass
    
    def get_document_path(self, document_id: str) -> List[str]:
        """Get hierarchical path for document."""
        pass
    
    def get_children(self, parent_id: str) -> List[Document]:
        """Get child documents."""
        pass
```

**Usage:**

```python
hierarchy_search = HierarchySearch(config)

result = hierarchy_search.search(
    query="API endpoints",
    depth=3,
    organize_by_hierarchy=True,
    parent_title="Developer Guide"
)

# Navigate hierarchy
for section in result.sections:
    print(f"Section: {section.title} (depth: {section.depth})")
    for doc in section.documents:
        path = " > ".join(doc.path)
        print(f"  {path}: {doc.title}")
```

## ⚙️ Processing APIs

### TextProcessor

**Text processing and chunking.**

```python
class TextProcessor:
    """Text processing utilities."""
    
    def __init__(self, config: ProcessingConfig):
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.chunking_strategy = config.chunking_strategy
    
    def process_text(self, text: str, metadata: dict) -> List[ProcessedChunk]:
        """Process text into chunks."""
        pass
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        pass
    
    def extract_metadata(self, text: str) -> dict:
        """Extract metadata from text."""
        pass
```

**Usage:**

```python
processor_config = ProcessingConfig(
    chunk_size=1000,
    chunk_overlap=200,
    chunking_strategy="semantic"
)

processor = TextProcessor(processor_config)

chunks = processor.process_text(
    text="Long document content...",
    metadata={"title": "Document Title", "author": "Author"}
)

for chunk in chunks:
    print(f"Chunk {chunk.chunk_index}: {len(chunk.content)} chars")
```

### EmbeddingProvider

**Embedding generation interface.**

```python
class EmbeddingProvider:
    """Embedding generation provider."""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = config.openai.model
        self.api_key = config.openai.api_key
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
```

**Usage:**

```python
embedding_provider = EmbeddingProvider(config)

# Single embedding
embedding = embedding_provider.generate_embedding("Sample text")
print(f"Embedding dimension: {len(embedding)}")

# Batch embeddings
texts = ["Text 1", "Text 2", "Text 3"]
embeddings = embedding_provider.generate_embeddings_batch(texts)
print(f"Generated {len(embeddings)} embeddings")
```

## 🔧 Utility APIs

### CollectionManager

**QDrant collection management.**

```python
class CollectionManager:
    """QDrant collection management utilities."""
    
    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client
    
    def create_collection(self, name: str, vector_size: int, **kwargs) -> bool:
        """Create new collection."""
        pass
    
    def delete_collection(self, name: str) -> bool:
        """Delete collection."""
        pass
    
    def optimize_collection(self, name: str) -> bool:
        """Optimize collection performance."""
        pass
    
    def backup_collection(self, name: str, output_path: str) -> bool:
        """Backup collection data."""
        pass
    
    def restore_collection(self, name: str, backup_path: str) -> bool:
        """Restore collection from backup."""
        pass
```

### CacheManager

**Caching utilities for performance optimization.**

```python
class CacheManager:
    """Cache management for embeddings and processed content."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_backend = self._initialize_backend()
    
    def cache_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache embedding for text."""
        pass
    
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Retrieve cached embedding."""
        pass
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        pass
```

## 🚨 Exception Classes

### QDrantLoaderError

**Base exception class.**

```python
class QDrantLoaderError(Exception):
    """Base exception for QDrant Loader."""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code
        self.timestamp = datetime.now()
```

### ConnectionError

**Connection-related errors.**

```python
class ConnectionError(QDrantLoaderError):
    """Connection-related errors."""
    pass
```

### AuthenticationError

**Authentication failures.**

```python
class AuthenticationError(QDrantLoaderError):
    """Authentication-related errors."""
    pass
```

### ConfigurationError

**Configuration problems.**

```python
class ConfigurationError(QDrantLoaderError):
    """Configuration-related errors."""
    pass
```

### ProcessingError

**Document processing errors.**

```python
class ProcessingError(QDrantLoaderError):
    """Document processing errors."""
    pass
```

**Exception Handling Example:**

```python
from qdrant_loader.exceptions import (
    QDrantLoaderError,
    ConnectionError,
    AuthenticationError,
    ConfigurationError
)

try:
    loader = QDrantLoader(config)
    result = loader.load_source("local", path="./docs")
except ConnectionError as e:
    print(f"Connection failed: {e}")
    print(f"Error code: {e.error_code}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except QDrantLoaderError as e:
    print(f"General error: {e}")
```

## 📈 Performance APIs

### PerformanceMonitor

**Performance monitoring and metrics collection.**

```python
class PerformanceMonitor:
    """Performance monitoring utilities."""
    
    def __init__(self):
        self.metrics = {}
        self.timers = {}
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        pass
    
    def end_timer(self, operation: str) -> float:
        """End timer and return duration."""
        pass
    
    def record_metric(self, name: str, value: float) -> None:
        """Record a custom metric."""
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        pass
```

**Usage:**

```python
monitor = PerformanceMonitor()
loader = QDrantLoader(config, monitor=monitor)

# Monitor will automatically track operations
result = loader.load_source("local", path="./docs")

# Get performance metrics
metrics = monitor.get_metrics()
print(f"Total processing time: {metrics['total_time']}")
print(f"Documents per second: {metrics['throughput']}")
print(f"Memory usage: {metrics['memory_usage']}")
```

## 🔗 Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from qdrant_loader import QDrantLoader
from qdrant_loader.exceptions import QDrantLoaderError

app = FastAPI()
loader = QDrantLoader.from_config("config.yaml")

@app.post("/search")
async def search_documents(query: str, limit: int = 10):
    """Search documents endpoint."""
    try:
        results = loader.search(query, limit=limit)
        return {
            "query": query,
            "results": [
                {
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata
                }
                for r in results
            ]
        }
    except QDrantLoaderError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/load")
async def load_documents(source_type: str, **kwargs):
    """Load documents endpoint."""
    try:
        result = loader.load_source(source_type, **kwargs)
        return {
            "success": result.success,
            "documents_processed": result.documents_processed,
            "processing_time": result.processing_time
        }
    except QDrantLoaderError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Async Usage

```python
import asyncio
from qdrant_loader.async_loader import AsyncQDrantLoader

async def async_example():
    """Example of async usage."""
    loader = AsyncQDrantLoader(config)
    
    # Async loading
    result = await loader.load_source_async("git", url="https://github.com/user/repo.git")
    
    # Async search
    results = await loader.search_async("machine learning")
    
    return results

# Run async example
results = asyncio.run(async_example())
```

## 🔗 Related Documentation

- **[Architecture Guide](./architecture.md)** - System design and components
- **[Extending Guide](./extending.md)** - Building custom components
- **[Testing Guide](./testing.md)** - Testing strategies and tools
- **[Configuration Reference](../users/configuration/config-file-reference.md)** - Configuration options
- **[CLI Reference](../users/cli/commands-reference.md)** - Command-line interface

---

**Ready to integrate?** Use this API reference alongside the [Architecture Guide](./architecture.md) to understand the system design, or check the [Extending Guide](./extending.md) to build custom components using these APIs.
