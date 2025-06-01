# Architecture Guide

This guide provides a comprehensive overview of QDrant Loader's architecture, including system design, component interactions, data flow, and technical implementation details. Understanding this architecture is essential for developers who want to extend, integrate, or contribute to QDrant Loader.

## 🏗️ System Overview

QDrant Loader is designed as a modular, extensible system for ingesting, processing, and searching documents using vector embeddings. The architecture follows modern software design principles including separation of concerns, plugin-based extensibility, and scalable processing patterns.

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              QDrant Loader System                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                User Interfaces                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │     CLI     │ │ Python API  │ │ MCP Server  │ │   Web UI    │          │
│  │ Interface   │ │  Interface  │ │  Interface  │ │ (Optional)  │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Core Processing Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Loader    │ │ Processor   │ │   Search    │ │ Collection  │          │
│  │  Manager    │ │  Pipeline   │ │   Engine    │ │  Manager    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────────────────────┤
│                               Plugin Architecture                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │    Data     │ │    File     │ │   Search    │ │ Embedding   │          │
│  │ Connectors  │ │ Processors  │ │  Providers  │ │  Providers  │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Storage & External APIs                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   QDrant    │ │   OpenAI    │ │    Local    │ │   External  │          │
│  │  Database   │ │ Embeddings  │ │    Cache    │ │    APIs     │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. Loader Manager

**Purpose**: Orchestrates the entire data loading process from source to vector storage.

**Key Responsibilities**:

- Coordinate data source connectors
- Manage processing pipeline
- Handle error recovery and retries
- Track processing progress and metrics

**Implementation**:

```python
class LoaderManager:
    def __init__(self, config: Config):
        self.config = config
        self.connectors = self._initialize_connectors()
        self.processors = self._initialize_processors()
        self.search_engine = SearchEngine(config)
    
    def load_source(self, source_type: str, **kwargs) -> LoadResult:
        """Main entry point for loading data from any source."""
        connector = self.connectors[source_type]
        documents = connector.fetch_documents(**kwargs)
        
        processed_docs = self._process_documents(documents)
        result = self._store_documents(processed_docs)
        
        return result
```

### 2. Processor Pipeline

**Purpose**: Transforms raw documents into searchable chunks with embeddings.

**Processing Stages**:

1. **Document Parsing** - Extract text from various file formats
2. **Content Cleaning** - Remove noise, normalize text
3. **Chunking** - Split documents into optimal-sized pieces
4. **Metadata Extraction** - Extract and enrich document metadata
5. **Embedding Generation** - Create vector embeddings
6. **Quality Validation** - Ensure processed content meets standards

**Pipeline Architecture**:

```python
class ProcessorPipeline:
    def __init__(self, config: Config):
        self.stages = [
            DocumentParser(config),
            ContentCleaner(config),
            TextChunker(config),
            MetadataExtractor(config),
            EmbeddingGenerator(config),
            QualityValidator(config)
        ]
    
    def process(self, document: Document) -> List[ProcessedChunk]:
        """Process document through all pipeline stages."""
        current_data = document
        
        for stage in self.stages:
            current_data = stage.process(current_data)
            
        return current_data
```

### 3. Search Engine

**Purpose**: Provides intelligent search capabilities across processed documents.

**Search Types**:

- **Semantic Search** - Vector similarity-based search
- **Hierarchy Search** - Structure-aware document navigation
- **Attachment Search** - Specialized file attachment search
- **Hybrid Search** - Combination of multiple search methods

**Search Architecture**:

```python
class SearchEngine:
    def __init__(self, config: Config):
        self.qdrant_client = QdrantClient(config.qdrant.url)
        self.embedding_provider = EmbeddingProvider(config)
        self.search_providers = {
            'semantic': SemanticSearchProvider(config),
            'hierarchy': HierarchySearchProvider(config),
            'attachment': AttachmentSearchProvider(config)
        }
    
    def search(self, query: str, search_type: str = 'semantic', **kwargs) -> SearchResults:
        """Execute search using specified provider."""
        provider = self.search_providers[search_type]
        return provider.search(query, **kwargs)
```

### 4. Collection Manager

**Purpose**: Manages QDrant collections and their configurations.

**Key Features**:

- Collection lifecycle management
- Schema validation and migration
- Performance optimization
- Backup and restore operations

## 🔌 Plugin Architecture

### Plugin System Design

QDrant Loader uses a plugin-based architecture that allows easy extension without modifying core code. Plugins are discovered automatically and registered at runtime.

```python
class PluginManager:
    def __init__(self):
        self.plugins = {}
        self._discover_plugins()
    
    def _discover_plugins(self):
        """Automatically discover and register plugins."""
        for entry_point in pkg_resources.iter_entry_points('qdrant_loader.plugins'):
            plugin_class = entry_point.load()
            self.plugins[entry_point.name] = plugin_class()
    
    def get_plugin(self, plugin_type: str, name: str):
        """Get specific plugin instance."""
        return self.plugins.get(f"{plugin_type}.{name}")
```

### Data Source Connectors

**Base Interface**:

```python
class BaseConnector(ABC):
    """Base class for all data source connectors."""
    
    def __init__(self, config: dict):
        self.config = config
    
    @abstractmethod
    def fetch_documents(self) -> Iterator[Document]:
        """Fetch documents from the data source."""
        pass
    
    @abstractmethod
    def supports_incremental(self) -> bool:
        """Whether connector supports incremental updates."""
        pass
    
    def validate_config(self) -> bool:
        """Validate connector configuration."""
        return True
```

**Connector Implementations**:

- **LocalConnector** - File system access
- **GitConnector** - Git repository processing
- **ConfluenceConnector** - Atlassian Confluence integration
- **JiraConnector** - Atlassian Jira integration
- **WebConnector** - Web scraping and crawling

### File Processors

**Base Interface**:

```python
class BaseProcessor(ABC):
    """Base class for file processors."""
    
    supported_extensions: List[str] = []
    
    @abstractmethod
    def process_file(self, file_path: str) -> Document:
        """Process file and extract content."""
        pass
    
    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """Check if processor can handle file type."""
        pass
```

**Processor Implementations**:

- **TextProcessor** - Plain text files (.txt, .md, .rst)
- **PDFProcessor** - PDF documents
- **OfficeProcessor** - Microsoft Office documents
- **CodeProcessor** - Source code files
- **ImageProcessor** - Image files with OCR
- **ArchiveProcessor** - Compressed archives

### Search Providers

**Base Interface**:

```python
class BaseSearchProvider(ABC):
    """Base class for search providers."""
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> SearchResults:
        """Execute search query."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> SearchCapabilities:
        """Get provider capabilities."""
        pass
```

## 📊 Data Flow Architecture

### Document Processing Flow

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Data      │    │    File     │    │   Content   │    │  Chunking   │
│   Source    │───▶│ Processing  │───▶│  Cleaning   │───▶│ & Metadata  │
│ Connector   │    │             │    │             │    │ Extraction  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                   │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│   QDrant    │    │  Embedding  │    │ Validation  │              │
│   Storage   │◀───│ Generation  │◀───│ & Quality   │◀─────────────┘
│             │    │             │    │   Control   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Search Flow

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    User     │    │   Query     │    │  Embedding  │    │   Vector    │
│   Query     │───▶│ Processing  │───▶│ Generation  │───▶│   Search    │
│             │    │             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                   │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│   Search    │    │   Result    │    │  Ranking &  │              │
│  Results    │◀───│ Formatting  │◀───│  Filtering  │◀─────────────┘
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 🏛️ Design Patterns

### 1. Strategy Pattern

Used for pluggable components like connectors and processors:

```python
class ProcessingStrategy:
    def __init__(self, processor_type: str):
        self.processor = ProcessorFactory.create(processor_type)
    
    def process(self, document: Document) -> ProcessedDocument:
        return self.processor.process(document)
```

### 2. Observer Pattern

Used for progress tracking and event handling:

```python
class LoadingObserver(ABC):
    @abstractmethod
    def on_document_processed(self, document: Document):
        pass
    
    @abstractmethod
    def on_batch_completed(self, batch_info: BatchInfo):
        pass

class LoaderManager:
    def __init__(self):
        self.observers: List[LoadingObserver] = []
    
    def add_observer(self, observer: LoadingObserver):
        self.observers.append(observer)
    
    def notify_document_processed(self, document: Document):
        for observer in self.observers:
            observer.on_document_processed(document)
```

### 3. Factory Pattern

Used for creating components based on configuration:

```python
class ConnectorFactory:
    @staticmethod
    def create(connector_type: str, config: dict) -> BaseConnector:
        connectors = {
            'local': LocalConnector,
            'git': GitConnector,
            'confluence': ConfluenceConnector,
            'jira': JiraConnector
        }
        
        if connector_type not in connectors:
            raise ValueError(f"Unknown connector type: {connector_type}")
        
        return connectors[connector_type](config)
```

### 4. Command Pattern

Used for CLI operations and API actions:

```python
class LoadCommand:
    def __init__(self, loader: LoaderManager, source_type: str, **kwargs):
        self.loader = loader
        self.source_type = source_type
        self.kwargs = kwargs
    
    def execute(self) -> LoadResult:
        return self.loader.load_source(self.source_type, **self.kwargs)
    
    def undo(self):
        # Implementation for rollback
        pass
```

## 🔄 Concurrency and Parallelism

### Processing Parallelism

QDrant Loader uses multiple levels of parallelism for optimal performance:

```python
class ParallelProcessor:
    def __init__(self, config: Config):
        self.max_workers = config.processing.max_workers
        self.batch_size = config.processing.batch_size
    
    def process_documents(self, documents: List[Document]) -> List[ProcessedDocument]:
        """Process documents in parallel batches."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Process in batches to manage memory
            batches = self._create_batches(documents, self.batch_size)
            
            futures = []
            for batch in batches:
                future = executor.submit(self._process_batch, batch)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                results.extend(future.result())
            
            return results
```

### Async Operations

For I/O-bound operations, async/await patterns are used:

```python
class AsyncConnector:
    async def fetch_documents_async(self) -> AsyncIterator[Document]:
        """Asynchronously fetch documents."""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in self.urls:
                task = self._fetch_document(session, url)
                tasks.append(task)
            
            for coro in asyncio.as_completed(tasks):
                document = await coro
                yield document
```

## 💾 Storage Architecture

### QDrant Integration

```python
class QDrantStorage:
    def __init__(self, config: QDrantConfig):
        self.client = QdrantClient(
            url=config.url,
            api_key=config.api_key,
            timeout=config.timeout
        )
        self.collection_config = config.collection_config
    
    def create_collection(self, collection_name: str, vector_size: int):
        """Create optimized collection for document storage."""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            ),
            optimizers_config=OptimizersConfig(
                default_segment_number=2,
                max_segment_size=20000,
                memmap_threshold=50000
            ),
            hnsw_config=HnswConfig(
                m=16,
                ef_construct=100,
                full_scan_threshold=10000
            )
        )
```

### Caching Strategy

```python
class CacheManager:
    def __init__(self, config: CacheConfig):
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db
        )
        self.ttl = config.default_ttl
    
    def cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding with content hash as key."""
        key = hashlib.sha256(text.encode()).hexdigest()
        self.redis_client.setex(
            key,
            self.ttl,
            json.dumps(embedding)
        )
    
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Retrieve cached embedding."""
        key = hashlib.sha256(text.encode()).hexdigest()
        cached = self.redis_client.get(key)
        return json.loads(cached) if cached else None
```

## 🔒 Security Architecture

### Authentication and Authorization

```python
class SecurityManager:
    def __init__(self, config: SecurityConfig):
        self.auth_providers = self._initialize_auth_providers(config)
        self.access_control = AccessControlManager(config)
    
    def authenticate_request(self, request: Request) -> AuthResult:
        """Authenticate incoming request."""
        for provider in self.auth_providers:
            result = provider.authenticate(request)
            if result.success:
                return result
        
        return AuthResult(success=False, reason="Authentication failed")
    
    def authorize_action(self, user: User, action: str, resource: str) -> bool:
        """Check if user is authorized for action on resource."""
        return self.access_control.check_permission(user, action, resource)
```

### Data Protection

```python
class DataProtection:
    def __init__(self, config: SecurityConfig):
        self.encryption_key = config.encryption_key
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data before storage."""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data after retrieval."""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

## 📈 Performance Architecture

### Optimization Strategies

1. **Lazy Loading** - Load data only when needed
2. **Connection Pooling** - Reuse database connections
3. **Batch Processing** - Process multiple items together
4. **Caching** - Cache frequently accessed data
5. **Streaming** - Process large datasets without loading into memory

### Performance Monitoring

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation."""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str):
        """End timing and record duration."""
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            self.metrics[f"{operation}_duration"].append(duration)
            del self.start_times[operation]
    
    def record_metric(self, name: str, value: float):
        """Record a custom metric."""
        self.metrics[name].append(value)
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics."""
        stats = {}
        for metric_name, values in self.metrics.items():
            stats[metric_name] = {
                'count': len(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'min': min(values),
                'max': max(values)
            }
        return stats
```

## 🔧 Configuration Architecture

### Hierarchical Configuration

```python
class ConfigManager:
    def __init__(self):
        self.config_sources = [
            EnvironmentConfigSource(),
            FileConfigSource(),
            DefaultConfigSource()
        ]
    
    def load_config(self) -> Config:
        """Load configuration from multiple sources with precedence."""
        config_data = {}
        
        # Load from sources in reverse precedence order
        for source in reversed(self.config_sources):
            source_config = source.load()
            config_data = self._deep_merge(config_data, source_config)
        
        return Config.from_dict(config_data)
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge configuration dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
```

## 🔗 Integration Architecture

### MCP Server Integration

```python
class MCPServer:
    def __init__(self, loader: LoaderManager):
        self.loader = loader
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Tool]:
        """Register available MCP tools."""
        return {
            'semantic_search': SemanticSearchTool(self.loader),
            'hierarchy_search': HierarchySearchTool(self.loader),
            'attachment_search': AttachmentSearchTool(self.loader)
        }
    
    async def handle_tool_call(self, tool_name: str, arguments: dict) -> ToolResult:
        """Handle incoming tool calls from MCP clients."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        return await tool.execute(arguments)
```

## 🧪 Testing Architecture

### Test Structure

```python
class TestArchitecture:
    """Test architecture follows the same modular design."""
    
    def __init__(self):
        self.unit_tests = UnitTestSuite()
        self.integration_tests = IntegrationTestSuite()
        self.performance_tests = PerformanceTestSuite()
        self.end_to_end_tests = E2ETestSuite()
    
    def run_all_tests(self) -> TestResults:
        """Run comprehensive test suite."""
        results = TestResults()
        
        results.unit = self.unit_tests.run()
        results.integration = self.integration_tests.run()
        results.performance = self.performance_tests.run()
        results.e2e = self.end_to_end_tests.run()
        
        return results
```

## 📊 Monitoring and Observability

### Metrics Collection

```python
class MetricsCollector:
    def __init__(self, config: MonitoringConfig):
        self.prometheus_client = PrometheusClient(config.prometheus)
        self.custom_metrics = {}
    
    def increment_counter(self, name: str, labels: dict = None):
        """Increment a counter metric."""
        self.prometheus_client.increment(name, labels)
    
    def record_histogram(self, name: str, value: float, labels: dict = None):
        """Record a histogram value."""
        self.prometheus_client.histogram(name, value, labels)
    
    def set_gauge(self, name: str, value: float, labels: dict = None):
        """Set a gauge value."""
        self.prometheus_client.gauge(name, value, labels)
```

## 🔗 Related Documentation

- **[API Reference](./api-reference.md)** - Detailed API documentation
- **[Extending Guide](./extending.md)** - How to extend the architecture
- **[Testing Guide](./testing.md)** - Testing strategies and frameworks
- **[Deployment Guide](./deployment.md)** - Production deployment architecture
- **[Performance Tuning](../users/configuration/advanced-settings.md)** - Performance optimization

---

**Understanding the architecture?** Continue with the [API Reference](./api-reference.md) for detailed technical specifications, or check the [Extending Guide](./extending.md) to learn how to build on this architecture.
