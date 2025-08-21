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
- **Comprehensive testing** - Unit, integration, and end-to-end tests
- **Rich documentation** - Detailed guides and examples

## 🏗️ System Architecture

### High-Level Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│ QDrant Loader │
├─────────────────────────────────────────────────────────────────┤
│ │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ CLI │ │ MCP Server │ │ Config │ │
│ │ Interface │ │ (Separate) │ │ Manager │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ │
│ │ │ │ │
│ └─────────────────┼─────────────────┘ │
│ │ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Async Ingestion Pipeline │ │
│ │ │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │ │
│ │ │ Data │ │ File │ │ Content │ │ │
│ │ │ Connectors │ │ Converters │ │ Processors │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ │ │
│ │ │ │ │ │ │
│ │ └─────────────────┼─────────────────┘ │ │
│ │ │ │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │ │
│ │ │ Embedding │ │ State │ │ QDrant │ │ │
│ │ │ Service │ │ Manager │ │ Manager │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│ │ │
└───────────────────────────┼────────────────────────────────────┘ │
┌───────────────────────────┼────────────────────────────────────┐
│ External Services │
├───────────────────────────┼────────────────────────────────────┤
│ │ │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ QDrant │ │ OpenAI │ │ Data │ │
│ │ Database │ │ API │ │ Sources │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ │
│ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Layers

#### 1. **Interface Layer**

- **CLI Interface** - Command-line tool for data ingestion and management (`init`, `ingest`, `config`, `project`)
- **MCP Server** - Separate package (`qdrant-loader-mcp-server`) for AI tool integration
- **Config Manager** - Multi-project configuration loading, validation, and environment variables

#### 2. **Core Pipeline**

- **Data Connectors** - Fetch content from various data sources using BaseConnector interface
- **File Converters** - Convert files to text using MarkItDown library
- **Content Processors** - Chunk text, extract metadata, and prepare for vectorization
- **Embedding Service** - Generate embeddings using OpenAI API
- **State Manager** - SQLite-based tracking of processing state and incremental updates
- **QDrant Manager** - Manage vector storage and collection operations

#### 3. **External Services**

- **QDrant Database** - Vector storage and similarity search
- **OpenAI API** - Embedding generation (text-embedding-3-small)
- **Data Sources** - Git repositories, Confluence, JIRA, local files, web content

## 🔧 Core Components

### Data Source Connectors

**Purpose**: Fetch content from external systems via a common abstraction

**Key Features**:

- Unified `BaseConnector` interface for all sources
- Per-source authentication and validation
- Retry-aware HTTP and rate limiting (where relevant)
- Shared HTTP utilities under `qdrant_loader.connectors.shared.http`:
  - `RateLimiter` for per-interval throttling
  - `request_with_policy` / `aiohttp_request_with_policy` for consistent retries + jitter + optional rate limiting
- Incremental updates via state tracking
- Rich metadata on every `Document`

**Supported Sources**: Git, Confluence, Jira, Local Files, Public Docs

Implementation notes:
- Jira uses `request_with_policy` with project-configured `requests_per_minute`.
- Confluence and PublicDocs use a conservative default limiter; can be surfaced in config later.

**Interface (simplified)**:

```python
from abc import ABC, abstractmethod
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import FileConversionConfig

class BaseConnector(ABC):
    def __init__(self, config: SourceConfig): ...
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
    def set_file_conversion_config(self, cfg: FileConversionConfig) -> None: ...
    @abstractmethod
    async def get_documents(self) -> list[Document]: ...
```

### File Converters

**Purpose**: Convert various file formats to text using MarkItDown

**Key Features**:

- 20+ file format support via MarkItDown library
- Optional LLM-enhanced descriptions
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
- Content deduplication via hashing
- Document ID generation
- Async processing pipelines

Refactoring highlights (Large Files):
- Markdown strategy split into `splitters/{base,standard,excel,fallback}.py` with facade `section_splitter.py`.
- Code strategy modularized (`parser/*`, `metadata/*`, `processor/*`); orchestrators remain thin.

### Embedding Service

**Purpose**: Generate embeddings using OpenAI API

**Key Features**:

- OpenAI API integration (text-embedding-3-small)
- Batch processing for efficiency
- Error handling and retries
- Configurable embedding models
- Rate limiting compliance

### State Manager

**Purpose**: Track processing state and enable incremental updates

**Key Features**:

- SQLite + SQLAlchemy async engine
- Content hashing for change detection
- Ingestion history and per-document state
- Project-aware queries and updates

Implementation: `qdrant_loader/core/state/state_manager.py`

### QDrant Manager

**Purpose**: Manage vector storage and collection operations

**Key Features**:

- Collection creation and management
- Vector upsert operations with batching
- Search and filtering capabilities
- Metadata handling
- Connection management with retry logic

## 📊 Data Flow

### Ingestion Pipeline

```text
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Data │───▶│ File │───▶│ Content │───▶│ Embedding │
│ Connector │ │ Converter │ │ Processor │ │ Service │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │ │ │ │ ▼ ▼ ▼ ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Raw Data │ │ Text │ │ Chunks │ │ Vectors │
│ + Metadata │ │ + Metadata │ │ + Metadata │ │ + Metadata │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │ ▼ ┌─────────────┐ │ QDrant │ │ Manager │ └─────────────┘ │ ▼ ┌─────────────┐ │ QDrant │ │ Database │ └─────────────┘
```

### Search Pipeline (MCP Server)

```text
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Query │───▶│ Embedding │───▶│ QDrant │───▶│ Results │
│ (Text) │ │ Service │ │ Search │ │ + Metadata │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │ │ │ │ ▼ ▼ ▼ ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ User Query │ │ Query Vector│ │ Similarity │ │ Ranked │
│ │ │ │ │ Scores │ │ Results │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## 🔌 Connector System

### Connector Architecture

QDrant Loader uses a connector-based architecture for extensibility. Connectors are instantiated directly in the pipeline orchestrator:

```python
# Actual connector instantiation in PipelineOrchestrator
async def _collect_documents_from_sources(
    self, filtered_config: SourcesConfig, project_id: str | None = None
) -> list[Document]:
    """Collect documents from all configured sources."""
    documents = []
    
    # Process each source type with direct connector instantiation
    if filtered_config.confluence:
        confluence_docs = await self.components.source_processor.process_source_type(
            filtered_config.confluence, ConfluenceConnector, "Confluence"
        )
        documents.extend(confluence_docs)
    
    if filtered_config.git:
        git_docs = await self.components.source_processor.process_source_type(
            filtered_config.git, GitConnector, "Git"
        )
        documents.extend(git_docs)
    
    if filtered_config.jira:
        jira_docs = await self.components.source_processor.process_source_type(
            filtered_config.jira, JiraConnector, "Jira"
        )
        documents.extend(jira_docs)
    
    if filtered_config.publicdocs:
        publicdocs_docs = await self.components.source_processor.process_source_type(
            filtered_config.publicdocs, PublicDocsConnector, "PublicDocs"
        )
        documents.extend(publicdocs_docs)
    
    if filtered_config.localfile:
        localfile_docs = await self.components.source_processor.process_source_type(
            filtered_config.localfile, LocalFileConnector, "LocalFile"
        )
        documents.extend(localfile_docs)
    
    return documents
```

### Available Connectors

- **GitConnector** - Git repository processing with file filtering
- **ConfluenceConnector** - Confluence space content and attachments
- **JiraConnector** - JIRA project issues and attachments
- **LocalFileConnector** - Local file system processing
- **PublicDocsConnector** - Web-based documentation crawling

## 🔄 State Management

### State Storage

QDrant Loader uses SQLite with SQLAlchemy for state management:

```python
class StateManager:
    """Manages state for document ingestion."""
    
    def __init__(self, config: StateManagementConfig):
        self.config = config
        self._engine = None
        self._session_factory = None
    
    async def initialize(self):
        """Initialize the database schema and connection."""
        db_url = self.config.database_path
        if not db_url.startswith("sqlite:///"):
            db_url = f"sqlite:///{db_url}"
        
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
        self._session_factory = async_sessionmaker(bind=self._engine)
        
        # Initialize schema
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
```

### Incremental Updates

```python
async def update_document_state(
    self, document: Document, project_id: str | None = None
) -> DocumentStateRecord:
    """Update document state for change detection."""
    content_hash = hashlib.sha256(document.content.encode()).hexdigest()
    
    # Check if document exists and has changed
    existing = await self.get_document_state_record(
        document.source_type, document.source, document.id, project_id
    )
    
    if existing and existing.content_hash == content_hash:
        # No changes detected
        return existing
    
    # Update or create new state record
    # ... implementation details
```

## 🚀 Performance Considerations

### Asynchronous Processing

The entire pipeline is built on async/await patterns:

```python
class AsyncIngestionPipeline:
    """Main async ingestion pipeline."""
    
    async def process_documents(
        self,
        project_id: str | None = None,
        source_type: str | None = None,
        source: str | None = None,
    ) -> None:
        """Process documents asynchronously."""
        # Async document collection and processing
        async with self.state_manager:
            documents = await self.orchestrator.process_documents(
                project_id=project_id,
                source_type=source_type,
                source=source,
            )
```

### Batch Processing

```python
class QdrantManager:
    """Manages QDrant operations with batching."""
    
    async def upsert_points(self, points: list[dict]) -> None:
        """Upsert points in batches."""
        batch_size = self.batch_size  # Configurable batch size
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            await self._upsert_batch(batch)
```

## 🔒 Security Architecture

### Authentication Flow

Each connector handles its own authentication:

```python
class ConfluenceConnector(BaseConnector):
    """Confluence connector with authentication."""
    
    def _setup_authentication(self):
        """Set up authentication based on deployment type."""
        if self.config.deployment_type == ConfluenceDeploymentType.CLOUD:
            self.session.auth = HTTPBasicAuth(self.config.email, self.config.token)
        else:
            self.session.headers.update({"Authorization": f"Bearer {self.config.token}"})
```

### Data Privacy

- **Credential management** - Environment variables and secure configuration
- **State isolation** - Project-based data separation
- **Access control** - Per-source authentication
- **Local processing** - No data sent to external services except for embeddings

## 📚 Related Documentation

- **[CLI Reference](../../users/cli-reference/)** - Command-line interface
- **[Configuration Guide](../../users/configuration/)** - Configuration options
- **[Extending Guide](../extending/)** - How to extend functionality
- **[Testing Guide](../testing/)** - Testing framework and patterns

## 🔄 Architecture Evolution

### Current State (v0.4.x)

- Multi-project workspace support
- SQLite-based state management with async support
- Asynchronous processing with async I/O
- Separate MCP server package
- MarkItDown-based file conversion

### Future Roadmap (v1.x+)

- **Enhanced connectors** - More data source integrations
- **Improved performance** - Better parallel processing and caching
- **Advanced search** - Enhanced MCP server capabilities
- **Deployment options** - Container images and deployment scripts
- **Monitoring and observability** - Enhanced metrics and logging

---
**Ready to dive deeper?** Explore the [CLI Reference](../../users/cli-reference/README.md) for command-line usage or check out the [Extending Guide](../extending.md) to learn about extending QDrant Loader.
