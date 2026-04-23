# 📝 Architecture Overview

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

- **CLI Interface** - Command-line tool for data ingestion and management (`setup`, `init`, `ingest`, `config`, `project list|status|validate`)
- **MCP Server** - Separate package (`qdrant-loader-mcp-server`) for AI tool integration
- **Config Manager** - Multi-project configuration loading, validation, and environment variables

#### 2. **Core Pipeline**

- **Data Connectors** - Fetch content from various data sources using BaseConnector interface
- **File Converters** - Convert files to text using MarkItDown library
- **Content Processors** - Chunk text, extract metadata, and prepare for vectorization
- **LLM Service** - Generate embeddings using configurable LLM providers (OpenAI, Azure OpenAI, Ollama)
- **State Manager** - SQLite-based tracking of processing state and incremental updates
- **QDrant Manager** - Manage vector storage and collection operations

#### 3. **External Services**

- **QDrant Database** - Vector storage and similarity search
- **LLM APIs** - Embedding generation via provider-agnostic interface (OpenAI, Azure OpenAI, Ollama)
- **Data Sources** - Git repositories, Confluence, Jira, local files, web content

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
- Confluence and PublicDocs expose `requests_per_minute` in config (defaults: Confluence 60 RPM, PublicDocs 120 RPM).

**Interface (simplified)**:

- Interface definition: [BaseConnector](../../../packages/qdrant-loader/src/qdrant_loader/connectors/base.py#L16)
- Required connector method: [BaseConnector.get_documents](../../../packages/qdrant-loader/src/qdrant_loader/connectors/base.py#L47)

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

### LLM Service

**Purpose**: Generate embeddings using configurable LLM providers

**Key Features**:

- Provider-agnostic interface (OpenAI, Azure OpenAI, Ollama)
- Configurable embedding models (text-embedding-3-small, text-embedding-ada-002, etc.)
- Batch processing for efficiency
- Error handling and retries
- Rate limiting compliance
- Unified configuration via `global.llm.*`

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

## 🧪 Data Flow

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

QDrant Loader uses a connector-based architecture for extensibility. Connectors are resolved through the connector factory in the pipeline orchestrator:

Implementation citation: [PipelineOrchestrator._collect_documents_from_sources](../../../packages/qdrant-loader/src/qdrant_loader/core/pipeline/orchestrator.py#L278)

### Available Connectors

- **GitConnector** - Git repository processing with file filtering
- **ConfluenceConnector** - Confluence space content and attachments
- **JiraConnector** - Jira project issues and attachments
- **LocalFileConnector** - Local file system processing
- **PublicDocsConnector** - Web-based documentation crawling

## 🔄 State Management

### State Storage

QDrant Loader uses SQLite with SQLAlchemy for state management:

- State manager class: [StateManager](../../../packages/qdrant-loader/src/qdrant_loader/core/state/state_manager.py#L29)
- Initialization flow: [StateManager.initialize](../../../packages/qdrant-loader/src/qdrant_loader/core/state/state_manager.py#L74)

### Incremental Updates

Implementation citation: [StateManager.update_document_state](../../../packages/qdrant-loader/src/qdrant_loader/core/state/state_manager.py#L314)

## 🚀 Performance Considerations

### Asynchronous Processing

The entire pipeline is built on async/await patterns:

- Pipeline entry point: [AsyncIngestionPipeline.process_documents](../../../packages/qdrant-loader/src/qdrant_loader/core/async_ingestion_pipeline.py#L182)

### Batch Processing

Implementation citation: [QdrantManager.upsert_points](../../../packages/qdrant-loader/src/qdrant_loader/core/qdrant_manager.py#L212)

## 🔒 Security Architecture

### Authentication Flow

Each connector handles its own authentication:

Implementation citation: [ConfluenceConnector._setup_authentication](../../../packages/qdrant-loader/src/qdrant_loader/connectors/confluence/connector.py#L114)

### Data Privacy

- **Credential management** - Environment variables and secure configuration
- **State isolation** - Project-based data separation
- **Access control** - Per-source authentication
- **Local processing** - No data sent to external services except for LLM embedding generation

## 📚 Related Documentation

- **[CLI Reference](../../users/cli-reference/)** - Command-line interface
- **[Configuration Guide](../../users/configuration/)** - Configuration options
- **[Extending Guide](../extending/)** - How to extend functionality
- **[Testing Guide](../testing/)** - Testing framework and patterns

## 🔄 Architecture Evolution

### Current Capabilities

- Multi-project workspace support
- SQLite-based state management with async support
- Asynchronous processing with async I/O
- Separate MCP server package
- MarkItDown-based file conversion

### Roadmap Priorities

- **Enhanced connectors** - More data source integrations
- **Improved performance** - Better parallel processing and caching
- **Advanced search** - Enhanced MCP server capabilities
- **Deployment options** - Container images and deployment scripts
- **Monitoring and observability** - Enhanced metrics and logging

For version-specific milestones and release status, see the project [CHANGELOG](../../../CHANGELOG.md).

---

**Ready to dive deeper?** Explore the [CLI Reference](../../users/cli-reference/) for command-line usage or check out the [Extending Guide](../extending/) to learn about extending QDrant Loader.
