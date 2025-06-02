# Architecture Guide

This guide provides a comprehensive overview of QDrant Loader's architecture, including system design, component interactions, data flow, and technical implementation details. Understanding this architecture is essential for developers who want to extend, integrate, or contribute to QDrant Loader.

## 🏗️ System Overview

QDrant Loader is designed as a modular, workspace-oriented system for ingesting, processing, and searching documents using vector embeddings. The architecture follows modern software design principles including separation of concerns, async processing patterns, and multi-project workspace support.

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              QDrant Loader System                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                User Interfaces                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                           │
│  │     CLI     │ │ MCP Server  │ │   Workspace │                           │
│  │ Interface   │ │  Interface  │ │    Mode     │                           │
│  └─────────────┘ └─────────────┘ └─────────────┘                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Core Processing Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Project   │ │ Async       │ │   QDrant    │ │    State    │          │
│  │  Manager    │ │ Ingestion   │ │  Manager    │ │  Manager    │          │
│  │             │ │  Pipeline   │ │             │ │             │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────────────────────┤
│                               Connector Architecture                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │    Git      │ │ Confluence  │ │    JIRA     │ │ Local Files │          │
│  │ Connector   │ │ Connector   │ │ Connector   │ │ Connector   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│  ┌─────────────┐                                                           │
│  │ Public Docs │                                                           │
│  │ Connector   │                                                           │
│  └─────────────┘                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Storage & External APIs                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   QDrant    │ │   OpenAI    │ │   SQLite    │ │ MarkItDown  │          │
│  │  Database   │ │ Embeddings  │ │ State DB    │ │File Convert │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. Project Manager

**Purpose**: Manages multi-project workspace configurations and project contexts.

**Key Responsibilities**:

- Project discovery from configuration files
- Project validation and metadata management
- Project context injection into documents
- Multi-project collection management

**Implementation**:

```python
class ProjectManager:
    def __init__(self, projects_config: ProjectsConfig, global_collection_name: str):
        self.projects_config = projects_config
        self.global_collection_name = global_collection_name
        self._project_contexts: Dict[str, ProjectContext] = {}
    
    async def initialize(self, session: AsyncSession) -> None:
        """Initialize and discover projects from configuration."""
        await self._discover_projects(session)
    
    def get_project_context(self, project_id: str) -> Optional[ProjectContext]:
        """Get project context for metadata injection."""
        return self._project_contexts.get(project_id)
```

### 2. Async Ingestion Pipeline

**Purpose**: Orchestrates the entire document processing workflow using async patterns.

**Processing Stages**:

1. **Document Fetching** - Retrieve documents from connectors
2. **File Conversion** - Convert files using MarkItDown
3. **Text Processing** - Clean and normalize content
4. **Chunking** - Split documents into optimal-sized pieces
5. **Embedding Generation** - Create vector embeddings via OpenAI
6. **QDrant Storage** - Store vectors and metadata

**Pipeline Architecture**:

```python
class AsyncIngestionPipeline:
    def __init__(self, settings: Settings, qdrant_manager: QdrantManager, 
                 state_manager: StateManager, max_chunk_workers: int = 10,
                 max_embed_workers: int = 4, max_upsert_workers: int = 4):
        self.settings = settings
        self.qdrant_manager = qdrant_manager
        self.state_manager = state_manager
        self.project_manager = ProjectManager(...)
        self.orchestrator = PipelineOrchestrator(...)
    
    async def process_documents(self, project_id: str = None, 
                              source_type: str = None) -> List[Document]:
        """Process documents through the async pipeline."""
        return await self.orchestrator.process_documents(
            project_id=project_id, source_type=source_type
        )
```

### 3. QDrant Manager

**Purpose**: Manages QDrant vector database operations and collection lifecycle.

**Key Features**:

- Collection creation and configuration
- Vector storage and retrieval
- Batch upsert operations
- Collection optimization

**Implementation**:

```python
class QdrantManager:
    def __init__(self, config: QdrantConfig):
        self.client = QdrantClient(url=config.url, api_key=config.api_key)
        self.config = config
    
    async def ensure_collection_exists(self, collection_name: str, 
                                     vector_size: int = 1536) -> bool:
        """Ensure collection exists with proper configuration."""
        # Implementation handles collection creation and validation
    
    async def upsert_documents(self, collection_name: str, 
                             documents: List[Document]) -> None:
        """Batch upsert documents to QDrant."""
        # Implementation handles batch operations
```

### 4. State Manager

**Purpose**: Manages processing state and tracks document changes using SQLite.

**Key Features**:

- Document state tracking
- Incremental processing support
- Processing metrics and history
- Database schema management

## 🔌 Connector Architecture

### Base Connector Interface

All data source connectors implement the `BaseConnector` abstract class:

```python
class BaseConnector(ABC):
    """Base class for all connectors."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialized = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._initialized = True
        return self
    
    @abstractmethod
    async def get_documents(self) -> List[Document]:
        """Get documents from the source."""
        pass
```

### Connector Implementations

- **GitConnector** - Git repository processing with branch and path filtering
- **ConfluenceConnector** - Atlassian Confluence space integration
- **JiraConnector** - Atlassian Jira project integration  
- **LocalFileConnector** - Local file system processing
- **PublicDocsConnector** - Public documentation websites

Each connector handles:

- Authentication and connection management
- Content fetching and pagination
- File attachment downloading
- Incremental updates and change detection

## 📊 Data Flow Architecture

### Document Processing Flow

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Data      │    │    File     │    │   Text      │    │  Chunking   │
│   Source    │───▶│ Conversion  │───▶│ Processing  │───▶│ & Metadata  │
│ Connector   │    │(MarkItDown) │    │             │    │ Extraction  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                   │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│   QDrant    │    │  OpenAI     │    │ Project     │              │
│   Storage   │◀───│ Embedding   │◀───│ Context     │◀─────────────┘
│             │    │ Generation  │    │ Injection   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Search Flow (MCP Server)

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    MCP      │    │   Query     │    │  OpenAI     │    │   Vector    │
│   Client    │───▶│ Processing  │───▶│ Embedding   │───▶│   Search    │
│             │    │             │    │ Generation  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                   │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│   Search    │    │   Result    │    │  Ranking &  │              │
│  Results    │◀───│ Formatting  │◀───│  Filtering  │◀─────────────┘
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 🏛️ Design Patterns

### 1. Async Context Manager Pattern

Used for resource management in connectors:

```python
async with connector_class(config) as connector:
    documents = await connector.get_documents()
```

### 2. Factory Pattern

Used for creating pipeline components:

```python
class PipelineComponentsFactory:
    def create_components(self, settings: Settings, config: PipelineConfig,
                         qdrant_manager: QdrantManager) -> PipelineComponents:
        return PipelineComponents(
            chunker=self._create_chunker(settings),
            embedder=self._create_embedder(settings),
            upserter=self._create_upserter(qdrant_manager)
        )
```

### 3. Strategy Pattern

Used for different chunking strategies:

```python
class ChunkingStrategy(ABC):
    @abstractmethod
    async def chunk_document(self, document: Document) -> List[Chunk]:
        pass

# Implementations: MarkdownStrategy, CodeStrategy, HTMLStrategy, etc.
```

### 4. Observer Pattern

Used for monitoring and metrics collection:

```python
class IngestionMonitor:
    def start_operation(self, operation_name: str, metadata: Dict = None):
        """Start tracking an operation."""
        
    def end_operation(self, operation_name: str, success: bool = True):
        """End tracking and record metrics."""
```

## 🔄 Concurrency and Parallelism

### Async Processing Architecture

QDrant Loader uses asyncio for I/O-bound operations and thread pools for CPU-bound tasks:

```python
class PipelineOrchestrator:
    async def process_documents(self) -> List[Document]:
        """Process documents with controlled concurrency."""
        
        # Fetch documents concurrently from all connectors
        connector_tasks = [
            self._process_connector(connector) 
            for connector in connectors
        ]
        
        # Process with semaphore-controlled concurrency
        async with asyncio.Semaphore(max_concurrent_sources):
            results = await asyncio.gather(*connector_tasks)
        
        return results
```

### Resource Management

```python
class ResourceManager:
    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._active_tasks: Set[asyncio.Task] = set()
    
    def register_signal_handlers(self):
        """Register SIGINT/SIGTERM handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
```

## 💾 Storage Architecture

### QDrant Integration

```python
class QdrantManager:
    async def create_collection(self, collection_name: str, vector_size: int):
        """Create optimized collection for document storage."""
        await self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            ),
            optimizers_config=OptimizersConfig(
                default_segment_number=2,
                max_segment_size=20000
            )
        )
```

### State Management with SQLite

```python
class StateManager:
    def __init__(self, config: StateManagementConfig):
        self.database_url = f"sqlite+aiosqlite:///{config.state_db_path}"
        self._engine = create_async_engine(self.database_url)
        self._session_factory = async_sessionmaker(self._engine)
    
    async def track_document_state(self, document: Document, 
                                 state: ProcessingState):
        """Track document processing state."""
        async with self._session_factory() as session:
            # Implementation tracks state changes
```

## 🔧 Configuration Architecture

### Workspace-Based Configuration

QDrant Loader supports workspace mode for organized multi-project configurations:

```text
workspace/
├── config.yaml          # Main configuration
├── .env                 # Environment variables
├── data/               # State and cache data
├── logs/               # Application logs
└── metrics/            # Performance metrics
```

### Multi-Project Configuration Structure

```yaml
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  project1:
    display_name: "Documentation Project"
    sources:
      confluence:
        - base_url: "https://company.atlassian.net"
          space_key: "DOCS"
      git:
        - base_url: "https://github.com/company/docs"
          branch: "main"
```

## 🔗 Integration Architecture

### MCP Server Integration

The MCP (Model Context Protocol) server provides search capabilities to AI assistants:

```python
class SearchEngine:
    def __init__(self):
        self.qdrant_client = None
        self.embedding_service = None
        self.hybrid_search: HybridSearchEngine | None = None
    
    async def semantic_search(self, query: str, limit: int = 10,
                            project_filter: str = None) -> SearchResults:
        """Execute semantic search with optional project filtering."""
        
    async def hierarchy_search(self, query: str, organize_by_hierarchy: bool = True,
                             hierarchy_filter: Dict = None) -> SearchResults:
        """Execute hierarchy-aware search."""
```

### CLI Architecture

The CLI uses Click framework with async command support:

```python
@cli.command()
@option("--workspace", type=ClickPath(path_type=Path))
@option("--project", type=str)
@option("--source-type", type=str)
@async_command
async def ingest(workspace: Path, project: str, source_type: str):
    """Ingest documents from configured sources."""
    # Implementation handles workspace setup and pipeline execution
```

## 📈 Performance Architecture

### Optimization Strategies

1. **Async I/O** - Non-blocking operations for network requests
2. **Batch Processing** - Group operations for efficiency
3. **Controlled Concurrency** - Semaphores prevent resource exhaustion
4. **Incremental Processing** - Only process changed documents
5. **Memory Management** - Stream processing for large datasets

### Performance Monitoring

```python
class IngestionMonitor:
    def __init__(self, metrics_dir: str):
        self.metrics_dir = Path(metrics_dir)
        self.operations: Dict[str, OperationMetrics] = {}
    
    def start_operation(self, operation_id: str, metadata: Dict = None):
        """Start tracking an operation with metadata."""
        
    def record_document_processed(self, operation_id: str, doc_size: int,
                                processing_time: float):
        """Record document processing metrics."""
```

## 🧪 Testing Architecture

### Test Structure

The testing architecture mirrors the modular design:

- **Unit Tests** - Individual component testing
- **Integration Tests** - Component interaction testing  
- **End-to-End Tests** - Full pipeline testing
- **Performance Tests** - Load and stress testing

```python
# Example test structure
class TestAsyncIngestionPipeline:
    async def test_document_processing_with_project_filter(self):
        """Test pipeline with project-specific filtering."""
        
    async def test_concurrent_connector_processing(self):
        """Test concurrent processing of multiple connectors."""
```

## 📊 Monitoring and Observability

### Metrics Collection

```python
class PrometheusMetrics:
    def __init__(self):
        self.document_counter = Counter('documents_processed_total')
        self.processing_time = Histogram('processing_time_seconds')
        self.error_counter = Counter('processing_errors_total')
    
    def start_metrics_server(self, port: int = 8000):
        """Start Prometheus metrics server."""
```

### Logging Architecture

```python
class LoggingConfig:
    @staticmethod
    def setup(level: str = "INFO", format: str = "console", 
             file: str = None):
        """Setup structured logging with JSON output."""
        
    @staticmethod
    def get_logger(name: str) -> Logger:
        """Get configured logger instance."""
```

## 🔗 Related Documentation

- **[CLI Reference](../users/cli-reference/README.md)** - Command-line interface documentation
- **[Configuration Guide](../users/configuration/README.md)** - Configuration options and examples
- **[Extending Guide](./extending.md)** - How to extend the architecture
- **[Testing Guide](./testing.md)** - Testing strategies and frameworks
- **[Deployment Guide](./deployment.md)** - Production deployment architecture

---

**Understanding the architecture?** Continue with the [Extending Guide](./extending.md) to learn how to build on this architecture, or check the [Testing Guide](./testing.md) for development practices.
