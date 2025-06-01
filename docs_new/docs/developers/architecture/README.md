# Architecture Overview

This section provides a comprehensive overview of QDrant Loader's architecture, including system design principles, component interactions, and data flow patterns.

## 🎯 Design Principles

QDrant Loader is built on several key architectural principles:

### 1. **Modularity and Extensibility**

- **Connector-based architecture** - Easy to add new data source connectors
- **Clear interfaces** - Well-defined interfaces between components
- **Separation of concerns** - Each component has a single responsibility

### 2. **Scalability and Performance**

- **Asynchronous processing** - Non-blocking I/O for better throughput
- **Batch processing** - Efficient handling of large datasets
- **Configurable concurrency** - Adjustable parallelism based on resources

### 3. **Reliability and Robustness**

- **Error handling** - Graceful degradation and retry mechanisms
- **State management** - Persistent tracking of processing state
- **Incremental updates** - Only process changed content

### 4. **Developer Experience**

- **Clear CLI interface** - Intuitive command-line operations
- **Comprehensive testing** - Unit, integration, and performance tests
- **Rich documentation** - Detailed guides and examples

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        QDrant Loader                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    CLI      │  │ MCP Server  │  │   Config    │             │
│  │ Interface   │  │             │  │  Manager    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Core Pipeline                            │   │
│  │                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │   Data      │  │    File     │  │   Content   │     │   │
│  │  │ Connectors  │  │ Converters  │  │ Processors  │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  │         │                 │                 │          │   │
│  │         └─────────────────┼─────────────────┘          │   │
│  │                           │                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ Embedding   │  │   State     │  │   QDrant    │     │   │
│  │  │  Service    │  │ Manager     │  │  Manager    │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                    │
└───────────────────────────┼────────────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────────────┐
│                External Services                               │
├───────────────────────────┼────────────────────────────────────┤
│                           │                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   QDrant    │  │   OpenAI    │  │    Data     │             │
│  │  Database   │  │     API     │  │   Sources   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Layers

#### 1. **Interface Layer**

- **CLI Interface** - Command-line tool for data ingestion and management
- **MCP Server** - Model Context Protocol server for AI tool integration
- **Config Manager** - Configuration loading, validation, and environment variables

#### 2. **Core Pipeline**

- **Data Connectors** - Fetch content from various data sources
- **File Converters** - Convert files to text using MarkItDown and custom processors
- **Content Processors** - Chunk text, extract metadata, and prepare for vectorization
- **Embedding Service** - Generate embeddings using OpenAI API
- **State Manager** - Track processing state and handle incremental updates
- **QDrant Manager** - Manage vector storage and collection operations

#### 3. **External Services**

- **QDrant Database** - Vector storage and similarity search
- **OpenAI API** - Embedding generation and AI services
- **Data Sources** - Git repositories, Confluence, JIRA, local files, web content

## 🔧 Core Components

### Data Source Connectors

**Purpose**: Fetch content from various external sources

**Key Features**:

- Unified interface for all data sources
- Authentication handling
- Rate limiting and retry logic
- Incremental update support
- Metadata extraction

**Supported Sources**:

- Git repositories (GitHub, GitLab, Bitbucket)
- Confluence (Cloud and Data Center)
- JIRA (Cloud and Data Center)
- Local file systems
- Public documentation websites

### File Converters

**Purpose**: Convert various file formats to text

**Key Features**:

- 20+ file format support via MarkItDown
- Custom conversion pipelines
- Metadata preservation
- Error handling for corrupted files
- Configurable conversion options

**Supported Formats**:

- Documents: PDF, DOCX, PPTX, XLSX
- Images: PNG, JPEG, GIF (with OCR)
- Archives: ZIP, TAR, 7Z
- Data: JSON, CSV, XML, YAML
- Audio: MP3, WAV (transcription)

### Content Processors

**Purpose**: Process and prepare content for vectorization

**Key Features**:

- Text chunking with configurable sizes
- Metadata extraction and enrichment
- Content deduplication
- Language detection
- Custom processing pipelines

### Embedding Service

**Purpose**: Generate embeddings using OpenAI API

**Key Features**:

- OpenAI API integration
- Batch processing for efficiency
- Error handling and retries
- Configurable embedding models
- Rate limiting compliance

### State Manager

**Purpose**: Track processing state and enable incremental updates

**Key Features**:

- SQLite-based state storage
- Content change detection
- Processing history tracking
- Rollback capabilities
- Concurrent access handling

### QDrant Manager

**Purpose**: Manage vector storage and collection operations

**Key Features**:

- Collection creation and management
- Vector upsert operations
- Search and filtering
- Metadata handling
- Performance optimization

## 📊 Data Flow

### Ingestion Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Data      │───▶│    File     │───▶│   Content   │───▶│ Embedding   │
│ Connector   │    │ Converter   │    │ Processor   │    │  Service    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Raw Data   │    │    Text     │    │   Chunks    │    │  Vectors    │
│ + Metadata  │    │ + Metadata  │    │ + Metadata  │    │ + Metadata  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                 │
                                                                 ▼
                                                        ┌─────────────┐
                                                        │   QDrant    │
                                                        │  Manager    │
                                                        └─────────────┘
                                                                 │
                                                                 ▼
                                                        ┌─────────────┐
                                                        │   QDrant    │
                                                        │  Database   │
                                                        └─────────────┘
```

### Search Pipeline (MCP Server)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Query    │───▶│ Embedding   │───▶│   QDrant    │───▶│   Results   │
│   (Text)    │    │  Service    │    │   Search    │    │ + Metadata  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ User Query  │    │ Query Vector│    │ Similarity  │    │ Ranked      │
│             │    │             │    │ Scores      │    │ Results     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## 🔌 Connector System

### Connector Architecture

QDrant Loader uses a connector-based architecture for extensibility:

```python
# Base connector interface
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
from qdrant_loader.core import Document

class BaseConnector(ABC):
    """Base class for all data source connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def fetch_documents(self) -> AsyncIterator[Document]:
        """Fetch documents from the data source."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to the data source."""
        pass

# Example connector implementation
class GitConnector(BaseConnector):
    """Git repository connector."""
    
    async def fetch_documents(self) -> AsyncIterator[Document]:
        """Fetch documents from Git repository."""
        # Implementation here
        pass
    
    async def test_connection(self) -> bool:
        """Test Git repository access."""
        # Implementation here
        return True
```

### Connector Registration

```python
# Connector registry in config system
CONNECTOR_REGISTRY = {
    "git": "qdrant_loader.connectors.git.GitConnector",
    "confluence": "qdrant_loader.connectors.confluence.ConfluenceConnector",
    "jira": "qdrant_loader.connectors.jira.JiraConnector",
    "localfile": "qdrant_loader.connectors.localfile.LocalFileConnector",
    "publicdocs": "qdrant_loader.connectors.publicdocs.PublicDocsConnector",
}
```

## 🔄 State Management

### State Storage

QDrant Loader uses SQLite for state management:

```sql
-- Documents table
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    last_modified TIMESTAMP,
    processed_at TIMESTAMP,
    metadata JSON
);

-- Processing state table
CREATE TABLE processing_state (
    source_type TEXT,
    source_id TEXT,
    last_processed TIMESTAMP,
    status TEXT,
    error_message TEXT,
    PRIMARY KEY (source_type, source_id)
);
```

### Incremental Updates

```python
class StateManager:
    def is_content_changed(self, document: Document) -> bool:
        """Check if content has changed since last processing."""
        stored_hash = self.get_content_hash(document.id)
        current_hash = self.calculate_hash(document.content)
        return stored_hash != current_hash
    
    def mark_processed(self, document: Document) -> None:
        """Mark document as processed."""
        self.update_document_state(
            document.id,
            content_hash=self.calculate_hash(document.content),
            processed_at=datetime.utcnow()
        )
```

## 🚀 Performance Considerations

### Asynchronous Processing

```python
import asyncio
from typing import List

class AsyncProcessor:
    def __init__(self, max_concurrency: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_documents(self, documents: List[Document]) -> List[ProcessedDocument]:
        """Process documents concurrently."""
        tasks = [self.process_document(doc) for doc in documents]
        return await asyncio.gather(*tasks)
    
    async def process_document(self, document: Document) -> ProcessedDocument:
        """Process a single document."""
        async with self.semaphore:
            # Process document
            return await self._process_single(document)
```

### Batch Processing

```python
class BatchProcessor:
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
    
    def process_in_batches(self, documents: List[Document]) -> Iterator[List[ProcessedDocument]]:
        """Process documents in batches."""
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            yield self.process_batch(batch)
```

## 🔒 Security Architecture

### Authentication Flow

```python
class AuthManager:
    def __init__(self):
        self.credentials = {}
    
    def authenticate(self, source_type: str, credentials: Dict[str, str]) -> bool:
        """Authenticate with data source."""
        authenticator = self.get_authenticator(source_type)
        return authenticator.validate(credentials)
    
    def get_authenticated_client(self, source_type: str):
        """Get authenticated client for data source."""
        credentials = self.get_credentials(source_type)
        return self.create_client(source_type, credentials)
```

### Data Privacy

- **Credential management** - Secure storage of API keys and tokens
- **Data encryption** - Optional encryption for sensitive content
- **Access control** - Permission-based access to data sources
- **Audit logging** - Track data access and processing

## 📚 Related Documentation

- **[Core Components](./core-components.md)** - Detailed component documentation
- **[Data Flow](./data-flow.md)** - In-depth data flow analysis
- **[Connector System](./connector-system.md)** - Connector development guide
- **[CLI Documentation](../cli/)** - Command-line interface
- **[Extension Guide](../extending/)** - How to extend functionality

## 🔄 Architecture Evolution

### Current State (v0.4.x)

- Monolithic core with connector extensions
- SQLite-based state management
- Asynchronous processing with async I/O
- Single-node deployment

### Future Roadmap (v1.x+)

- **Enhanced connectors** - More data source integrations
- **Improved performance** - Better parallel processing
- **Advanced search** - Enhanced MCP server capabilities
- **Deployment options** - Docker images and deployment scripts
- **Monitoring and observability** - Metrics, tracing, and alerting

---

**Ready to dive deeper?** Explore the [Core Components](./core-components.md) for detailed component documentation or check out the [Connector System](./connector-system.md) to learn about extending QDrant Loader.
