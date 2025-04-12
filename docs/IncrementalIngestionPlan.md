# Incremental Ingestion Implementation Plan

## Product Requirements Document (PRD)

### Overview

The incremental ingestion feature aims to optimize the document ingestion process by only processing documents that have changed since the last ingestion. This will improve performance, reduce resource usage, and ensure our Qdrant database stays in sync with source systems.

### Goals

1. **Performance Optimization**
   - Reduce processing time by only handling changed documents
   - Minimize resource usage (CPU, memory, network)
   - Improve overall ingestion efficiency

2. **Data Consistency**
   - Ensure Qdrant database reflects the latest state of source systems
   - Properly handle document deletions
   - Maintain accurate document versions

3. **Reliability**
   - Implement robust error handling
   - Ensure data integrity during incremental updates
   - Provide clear visibility into ingestion status

### Requirements

#### Functional Requirements

1. **Change Detection**
   - Track document changes across all source types (Git, Confluence, Jira, Public Docs)
   - Detect document deletions
   - Support source-specific change detection methods

2. **State Management**
   - Maintain local state of ingested documents
   - Track last successful ingestion per source
   - Store document metadata for change comparison

3. **Incremental Processing**
   - Process only changed documents
   - Update Qdrant database efficiently
   - Handle document deletions properly

4. **Monitoring and Reporting**
   - Provide detailed ingestion logs
   - Show statistics about processed changes
   - Support dry-run mode for change preview

#### Non-Functional Requirements

1. **Performance**
   - Minimize processing time for unchanged documents
   - Optimize database operations
   - Support future batch and parallel processing

2. **Reliability**
   - Handle network failures gracefully
   - Implement proper error recovery
   - Maintain data consistency

3. **Maintainability**
   - Clear code organization
   - Comprehensive documentation
   - Extensive test coverage

4. **Usability**
   - Simple configuration
   - Clear logging and reporting
   - Intuitive CLI interface

### Success Metrics

1. **Performance Metrics**
   - Reduction in processing time for unchanged documents
   - Decrease in resource usage
   - Improvement in overall ingestion speed

2. **Reliability Metrics**
   - Successful completion rate of incremental updates
   - Data consistency between sources and Qdrant
   - Error recovery success rate

3. **User Experience Metrics**
   - Configuration simplicity
   - Log clarity and usefulness
   - CLI usability

### Technical Constraints

1. **State Management**
   - Use SQLite for local state storage
   - Support both user-specific and package-specific paths
   - Implement proper database migrations

2. **Change Detection**
   - Support source-specific change detection methods
   - Handle timezone differences
   - Manage concurrent updates

3. **Qdrant Integration**
   - Maintain document ID consistency
   - Support efficient updates and deletions
   - Handle batch operations

### Risks and Mitigations

1. **Data Inconsistency**
   - Risk: Mismatch between source and Qdrant state
   - Mitigation: Implement robust state tracking and validation

2. **Performance Issues**
   - Risk: Slow change detection or processing
   - Mitigation: Optimize algorithms and support future parallel processing

3. **Error Handling**
   - Risk: Failed updates or partial updates
   - Mitigation: Implement comprehensive error handling and recovery

4. **Resource Usage**
   - Risk: High memory or CPU usage
   - Mitigation: Implement resource monitoring and limits

### Future Considerations

1. **Scalability**
   - Support for larger document sets
   - Distributed processing capabilities
   - Enhanced parallel processing

2. **Additional Features**
   - Custom change detection rules
   - Advanced filtering options
   - Enhanced monitoring and reporting

3. **Integration**
   - Support for additional source types
   - Enhanced API capabilities
   - Webhook support for real-time updates

### File Structure

```text
src/qdrant_loader/
├── core/
│   ├── state/
│   │   ├── __init__.py
│   │   ├── state_manager.py          # StateManager class for SQLite operations
│   │   ├── models.py                 # SQLAlchemy models for state database
│   │   ├── migrations/               # Alembic migrations
│   │   └── exceptions.py             # State management exceptions
│   │
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── batch_processor.py        # Batch processing implementation
│   │   ├── parallel_processor.py     # Parallel processing implementation
│   │   ├── monitor.py                # Performance monitoring
│   │   └── resource_manager.py       # Resource management
│   │
│   └── ingestion_pipeline.py         # Updated pipeline with incremental support
│
├── connectors/
│   ├── git/
│   │   ├── __init__.py
│   │   ├── connector.py              # Existing Git connector
│   │   └── change_detector.py        # Git-specific change detection
│   │
│   ├── confluence/
│   │   ├── __init__.py
│   │   ├── connector.py              # Existing Confluence connector
│   │   └── change_detector.py        # Confluence-specific change detection
│   │
│   ├── jira/
│   │   ├── __init__.py
│   │   ├── connector.py              # Existing Jira connector
│   │   └── change_detector.py        # Jira-specific change detection
│   │
│   ├── public_docs/
│   │   ├── __init__.py
│   │   ├── connector.py              # Existing Public Docs connector
│   │   └── change_detector.py        # Public Docs-specific change detection
│   │
│   └── base.py                       # Base classes for connectors and change detectors
│
├── config/
│   ├── __init__.py
│   ├── settings.py                   # Updated settings with state management
│   └── schemas.py                    # Pydantic schemas for new configs
│
└── cli/
    ├── __init__.py
    └── commands.py                   # Updated CLI with incremental commands

tests/
├── unit/
│   ├── core/
│   │   ├── state/
│   │   │   ├── test_state_manager.py
│   │   │   └── test_models.py
│   │   │
│   │   ├── performance/
│   │   │   ├── test_batch_processor.py
│   │   │   ├── test_parallel_processor.py
│   │   │   ├── test_monitor.py
│   │   │   └── test_resource_manager.py
│   │   │
│   │   └── test_ingestion_pipeline.py
│   │
│   ├── connectors/
│   │   ├── git/
│   │   │   ├── test_connector.py
│   │   │   └── test_change_detector.py
│   │   │
│   │   ├── confluence/
│   │   │   ├── test_connector.py
│   │   │   └── test_change_detector.py
│   │   │
│   │   ├── jira/
│   │   │   ├── test_connector.py
│   │   │   └── test_change_detector.py
│   │   │
│   │   └── public_docs/
│   │       ├── test_connector.py
│   │       └── test_change_detector.py
│   │
│   └── cli/
│       └── test_commands.py
│
└── integration/
    ├── test_state_management.py
    ├── test_change_detection.py
    └── test_incremental_ingestion.py

docs/
├── state_management.md               # State management documentation
├── change_detection.md               # Change detection documentation
└── incremental_ingestion.md          # Incremental ingestion guide
```

#### Key Components and Their Locations

1. **State Management**
   - `src/qdrant_loader/core/state/`: Contains all state management related code
   - Uses SQLAlchemy for database operations
   - Includes migrations for schema changes

2. **Change Detection**
   - Integrated into each connector directory
   - Each connector has its own change detector
   - Common interface defined in `connectors/base.py`

3. **Performance Components**
   - `src/qdrant_loader/core/performance/`: Performance optimization code
   - Separate modules for batch and parallel processing
   - Resource monitoring and management

4. **Configuration**
   - Updated settings in `config/` directory
   - New schemas for state management and performance settings

5. **CLI**
   - Updated commands in `cli/` directory
   - New commands for incremental ingestion

6. **Testing**
   - Unit tests for each component
   - Integration tests for end-to-end functionality
   - Performance tests for optimization features

7. **Documentation**
   - Separate documentation files for each major component
   - Usage examples and configuration guides

This revised structure:
- Maintains our existing connector-based organization
- Keeps change detection logic close to the connectors it works with
- Follows our established patterns for code organization
- Ensures proper separation of concerns while maintaining cohesion

## Phase 1: State Management Infrastructure

### 1.1 Database Setup

- [ ] Create SQLite state management system
  - [ ] Design database schema

    ```sql
    -- Ingestion history tracking
    CREATE TABLE ingestion_history (
        id INTEGER PRIMARY KEY,
        source_type TEXT NOT NULL,
        source_name TEXT NOT NULL,
        last_successful_ingestion TIMESTAMP NOT NULL,
        status TEXT NOT NULL,
        document_count INTEGER,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Document state tracking
    CREATE TABLE document_states (
        id TEXT PRIMARY KEY,
        source_type TEXT NOT NULL,
        source_name TEXT NOT NULL,
        document_id TEXT NOT NULL,
        last_updated TIMESTAMP NOT NULL,
        last_ingested TIMESTAMP NOT NULL,
        is_deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source_type, source_name, document_id)
    );

    -- Create indexes for performance
    CREATE INDEX idx_document_states_source ON document_states(source_type, source_name);
    CREATE INDEX idx_document_states_last_updated ON document_states(last_updated);
    CREATE INDEX idx_ingestion_history_source ON ingestion_history(source_type, source_name);
    ```

  - [ ] Implement database initialization
    - [ ] Handle user-specific paths
      - [ ] Use `appdirs` package for cross-platform path handling
      - [ ] Default path: `~/.qdrant-loader/state.db` (Unix) or `%APPDATA%/qdrant-loader/state.db` (Windows)
    - [ ] Handle pip-installed package paths
      - [ ] Use `pkg_resources` for package data
      - [ ] Create default state.db in user directory if not exists
    - [ ] Add database migration support
      - [ ] Use Alembic for migrations
      - [ ] Create initial migration
      - [ ] Add migration tests
  - [ ] Add database tests
    - [ ] Test database creation
      - [ ] Test path resolution
      - [ ] Test file permissions
      - [ ] Test concurrent access
    - [ ] Test schema initialization
      - [ ] Test table creation
      - [ ] Test index creation
      - [ ] Test constraint enforcement
    - [ ] Test path handling
      - [ ] Test user-specific paths
      - [ ] Test package paths
      - [ ] Test path creation
    - [ ] Test migration support
      - [ ] Test migration application
      - [ ] Test rollback
      - [ ] Test concurrent migrations

### 1.2 State Management Service

- [ ] Create StateManager class
  - [ ] Implement CRUD operations for ingestion history

    ```python
    class StateManager:
        def __init__(self, db_path: str):
            self.db_path = db_path
            self.connection = None
            
        async def get_last_ingestion(self, source_type: str, source_name: str) -> Optional[datetime]:
            """Get last successful ingestion time for a source."""
            
        async def update_ingestion(self, source_type: str, source_name: str, 
                                 status: str, count: int, error: Optional[str] = None):
            """Update ingestion history."""
            
        async def get_document_state(self, source_type: str, source_name: str, 
                                   document_id: str) -> Optional[DocumentState]:
            """Get document state."""
            
        async def update_document_state(self, document_state: DocumentState):
            """Update document state."""
            
        async def mark_document_deleted(self, source_type: str, source_name: str, 
                                      document_id: str):
            """Mark document as deleted."""
    ```

  - [ ] Implement CRUD operations for document states
  - [ ] Add transaction support
    - [ ] Use SQLite transaction context managers
    - [ ] Implement rollback on errors
  - [ ] Add error handling
    - [ ] Handle database connection errors
    - [ ] Handle constraint violations
    - [ ] Handle concurrent access
  - [ ] Add logging
    - [ ] Log database operations
    - [ ] Log errors
    - [ ] Log performance metrics
  - [ ] Add StateManager tests
    - [ ] Test CRUD operations
      - [ ] Test create operations
      - [ ] Test read operations
      - [ ] Test update operations
      - [ ] Test delete operations
    - [ ] Test transaction handling
      - [ ] Test successful transactions
      - [ ] Test rollback on error
      - [ ] Test concurrent transactions
    - [ ] Test error scenarios
      - [ ] Test connection errors
      - [ ] Test constraint violations
      - [ ] Test concurrent access errors
    - [ ] Test logging
      - [ ] Test operation logging
      - [ ] Test error logging
      - [ ] Test performance logging

### 1.3 Configuration Integration

- [ ] Add state management configuration
  - [ ] Add database path configuration

    ```yaml
    state_management:
      database:
        path: ~/.qdrant-loader/state.db  # Default path
        create_if_missing: true
        permissions: 0o600  # Secure permissions
    ```

  - [ ] Add migration configuration

    ```yaml
    state_management:
      migrations:
        enabled: true
        auto_migrate: true
        backup_before_migrate: true
    ```

  - [ ] Add configuration validation
    - [ ] Validate path format
    - [ ] Validate permissions
    - [ ] Validate migration settings
  - [ ] Add configuration tests
    - [ ] Test path configuration
      - [ ] Test path resolution
      - [ ] Test path creation
      - [ ] Test permissions
    - [ ] Test migration configuration
      - [ ] Test migration enabling
      - [ ] Test auto-migration
      - [ ] Test backup
    - [ ] Test validation
      - [ ] Test valid configurations
      - [ ] Test invalid configurations
      - [ ] Test default values

## Phase 2: Change Detection Implementation

### 2.1 Git Change Detection

- [ ] Implement Git change detection
  - [ ] Track file-level changes

    ```python
    class GitChangeDetector:
        def __init__(self, repo_path: str):
            self.repo = git.Repo(repo_path)
            
        async def get_changes_since(self, since: datetime) -> List[GitChange]:
            """Get all changes since given timestamp."""
            
        async def get_deleted_files(self, since: datetime) -> List[str]:
            """Get all deleted files since given timestamp."""
    ```

  - [ ] Implement last commit timestamp tracking
    - [ ] Use git log with --since
    - [ ] Parse commit timestamps
    - [ ] Handle timezone conversions
  - [ ] Handle file deletions
    - [ ] Track deleted files in git log
    - [ ] Update document states
    - [ ] Remove from Qdrant
  - [ ] Add Git change detection tests
    - [ ] Test file change detection
      - [ ] Test modified files
      - [ ] Test new files
      - [ ] Test renamed files
    - [ ] Test timestamp tracking
      - [ ] Test commit timestamps
      - [ ] Test timezone handling
    - [ ] Test deletion handling
      - [ ] Test deleted files
      - [ ] Test state updates
      - [ ] Test Qdrant removal

### 2.2 Confluence Change Detection

- [ ] Implement Confluence change detection
  - [ ] Track page updates

    ```python
    class ConfluenceChangeDetector:
        def __init__(self, client: ConfluenceClient):
            self.client = client
            
        async def get_updated_pages(self, since: datetime) -> List[ConfluencePage]:
            """Get all updated pages since given timestamp."""
            
        async def get_deleted_pages(self, since: datetime) -> List[str]:
            """Get all deleted pages since given timestamp."""
    ```

  - [ ] Track page deletions
    - [ ] Use Confluence API for deleted pages
    - [ ] Update document states
    - [ ] Remove from Qdrant
  - [ ] Track page moves/renames
    - [ ] Detect page moves
    - [ ] Update document URLs
    - [ ] Update document states
  - [ ] Add Confluence change detection tests
    - [ ] Test page update detection
      - [ ] Test content updates
      - [ ] Test metadata updates
    - [ ] Test deletion detection
      - [ ] Test page deletion
      - [ ] Test state updates
    - [ ] Test move/rename detection
      - [ ] Test page moves
      - [ ] Test page renames
      - [ ] Test URL updates

### 2.3 Jira Change Detection

- [ ] Implement Jira change detection
  - [ ] Track all field changes

    ```python
    class JiraChangeDetector:
        def __init__(self, client: JiraClient):
            self.client = client
            
        async def get_updated_issues(self, since: datetime) -> List[JiraIssue]:
            """Get all updated issues since given timestamp."""
            
        async def get_deleted_issues(self, since: datetime) -> List[str]:
            """Get all deleted issues since given timestamp."""
    ```

  - [ ] Track issue updates
    - [ ] Use Jira changelog
    - [ ] Track all field changes
    - [ ] Update document states
  - [ ] Track issue deletions
    - [ ] Detect deleted issues
    - [ ] Update document states
    - [ ] Remove from Qdrant
  - [ ] Add Jira change detection tests
    - [ ] Test field change detection
      - [ ] Test all field types
      - [ ] Test multiple changes
    - [ ] Test update detection
      - [ ] Test issue updates
      - [ ] Test state updates
    - [ ] Test deletion detection
      - [ ] Test issue deletion
      - [ ] Test state updates

### 2.4 Public Docs Change Detection

- [ ] Implement public docs change detection
  - [ ] Track file modification times

    ```python
    class PublicDocsChangeDetector:
        def __init__(self, base_url: str):
            self.base_url = base_url
            
        async def get_updated_docs(self, since: datetime) -> List[PublicDoc]:
            """Get all updated docs since given timestamp."""
            
        async def get_deleted_docs(self, since: datetime) -> List[str]:
            """Get all deleted docs since given timestamp."""
    ```

  - [ ] Track URL changes
    - [ ] Monitor URL changes
    - [ ] Update document states
    - [ ] Update Qdrant documents
  - [ ] Add public docs change detection tests
    - [ ] Test modification time tracking
      - [ ] Test file updates
      - [ ] Test timezone handling
    - [ ] Test URL change detection
      - [ ] Test URL changes
      - [ ] Test state updates

## Phase 3: Incremental Processing Pipeline

### 3.1 Pipeline Modifications

- [ ] Modify IngestionPipeline class
  - [ ] Add state management integration

    ```python
    class IngestionPipeline:
        def __init__(self, settings: Settings):
            self.state_manager = StateManager(settings.state_management.database.path)
            
        async def process_documents_incremental(self, 
                                              config: SourcesConfig,
                                              source_type: Optional[str] = None,
                                              source_name: Optional[str] = None,
                                              dry_run: bool = False):
            """Process documents incrementally."""
    ```

  - [ ] Implement incremental processing logic
    - [ ] Get last ingestion time
    - [ ] Get changed documents
    - [ ] Update document states
    - [ ] Update Qdrant
  - [ ] Add dry-run mode support
    - [ ] Show changes without applying
    - [ ] Log proposed changes
    - [ ] Show statistics
  - [ ] Add pipeline tests
    - [ ] Test state management integration
      - [ ] Test state updates
      - [ ] Test error handling
    - [ ] Test incremental processing
      - [ ] Test change detection
      - [ ] Test state updates
      - [ ] Test Qdrant updates
    - [ ] Test dry-run mode
      - [ ] Test change reporting
      - [ ] Test statistics
      - [ ] Test no actual changes

### 3.2 Source Processing Updates

- [ ] Update source processors
  - [ ] Git processor updates
    - [ ] Add change detection
    - [ ] Add state management
    - [ ] Add deletion handling
  - [ ] Confluence processor updates
    - [ ] Add change detection
    - [ ] Add state management
    - [ ] Add deletion handling
  - [ ] Jira processor updates
    - [ ] Add change detection
    - [ ] Add state management
    - [ ] Add deletion handling
  - [ ] Public docs processor updates
    - [ ] Add change detection
    - [ ] Add state management
    - [ ] Add deletion handling
  - [ ] Add processor tests
    - [ ] Test each source processor
      - [ ] Test change detection
      - [ ] Test state updates
      - [ ] Test deletion handling
    - [ ] Test error handling
      - [ ] Test connection errors
      - [ ] Test processing errors
    - [ ] Test state updates
      - [ ] Test state tracking
      - [ ] Test state persistence

### 3.3 Qdrant Integration

- [ ] Update QdrantManager
  - [ ] Add document deletion support

    ```python
    class QdrantManager:
        async def delete_documents(self, document_ids: List[str]):
            """Delete documents from Qdrant."""
            
        async def update_documents(self, documents: List[Document]):
            """Update documents in Qdrant."""
    ```

  - [ ] Add batch update support
    - [ ] Implement batch operations
    - [ ] Add batch size configuration
    - [ ] Add error handling
  - [ ] Add QdrantManager tests
    - [ ] Test deletion functionality
      - [ ] Test single deletion
      - [ ] Test batch deletion
      - [ ] Test error handling
    - [ ] Test batch updates
      - [ ] Test batch size
      - [ ] Test error handling
      - [ ] Test performance
    - [ ] Test error handling
      - [ ] Test connection errors
      - [ ] Test update errors
      - [ ] Test deletion errors

## Phase 4: CLI and Configuration

### 4.1 CLI Updates

- [ ] Add incremental ingestion commands
  - [ ] Add --incremental flag

    ```python
    @click.command()
    @click.option('--incremental', is_flag=True, help='Enable incremental ingestion')
    @click.option('--dry-run', is_flag=True, help='Show changes without applying')
    @click.option('--since', type=click.DateTime(), help='Process changes since given time')
    def ingest(incremental, dry_run, since):
        """Ingest documents from configured sources."""
    ```

  - [ ] Add --dry-run flag
  - [ ] Add --since flag for specific time
  - [ ] Add CLI tests
    - [ ] Test flag handling
      - [ ] Test flag combinations
      - [ ] Test flag validation
    - [ ] Test command execution
      - [ ] Test successful execution
      - [ ] Test error handling
    - [ ] Test error handling
      - [ ] Test invalid flags
      - [ ] Test invalid arguments
      - [ ] Test execution errors

### 4.2 Configuration Updates

- [ ] Update configuration system
  - [ ] Add incremental ingestion settings

    ```yaml
    ingestion:
      incremental:
        enabled: true
        default_since: 24h  # Default time to look back
        batch_size: 100
    ```

  - [ ] Add state management settings
  - [ ] Add configuration tests
    - [ ] Test settings validation
      - [ ] Test valid settings
      - [ ] Test invalid settings
    - [ ] Test default values
      - [ ] Test default settings
      - [ ] Test override settings
    - [ ] Test error handling
      - [ ] Test validation errors
      - [ ] Test parsing errors

## Phase 5: Testing and Documentation

### 5.1 Testing

- [ ] Add comprehensive tests
  - [ ] Add end-to-end tests
    - [ ] Test full ingestion flow
    - [ ] Test incremental flow
    - [ ] Test error scenarios
  - [ ] Add integration tests
    - [ ] Test source integration
    - [ ] Test state management
    - [ ] Test Qdrant integration
  - [ ] Add performance tests
    - [ ] Test ingestion speed
    - [ ] Test memory usage
    - [ ] Test database performance
  - [ ] Add error handling tests
    - [ ] Test connection errors
    - [ ] Test processing errors
    - [ ] Test state errors

### 5.2 Documentation

- [ ] Add incremental ingestion documentation
  - [ ] Document configuration options
    - [ ] Document all settings
    - [ ] Document default values
    - [ ] Document examples
  - [ ] Add usage examples
    - [ ] Add basic examples
    - [ ] Add advanced examples
    - [ ] Add troubleshooting examples
  - [ ] Create troubleshooting guide
    - [ ] Document common issues
    - [ ] Document solutions
    - [ ] Document workarounds
  - [ ] Add API documentation
    - [ ] Document public API
    - [ ] Document internal API
    - [ ] Document extension points
  - [ ] Add documentation tests
    - [ ] Test configuration examples
      - [ ] Test example validity
      - [ ] Test example execution
    - [ ] Test usage examples
      - [ ] Test example validity
      - [ ] Test example execution
    - [ ] Test troubleshooting guide
      - [ ] Test issue descriptions
      - [ ] Test solution validity

## Phase 6: Performance Optimization (Future)

### 6.1 Batch Processing

- [ ] Implement batch processing
  - [ ] Add batch configuration

    ```yaml
    ingestion:
      batch:
        size: 100
        timeout: 30s
        retry_attempts: 3
        retry_delay: 5s
    ```

  - [ ] Implement batch operations

    ```python
    class BatchProcessor:
        def __init__(self, settings: Settings):
            self.batch_size = settings.ingestion.batch.size
            self.timeout = settings.ingestion.batch.timeout
            self.retry_attempts = settings.ingestion.batch.retry_attempts
            self.retry_delay = settings.ingestion.batch.retry_delay
            
        async def process_batch(self, documents: List[Document]) -> BatchResult:
            """Process a batch of documents with retry logic."""
            
        async def process_stream(self, document_stream: AsyncIterator[Document]) -> StreamResult:
            """Process a stream of documents in batches."""
    ```

  - [ ] Add batch processing tests
    - [ ] Test batch size limits
    - [ ] Test timeout handling
    - [ ] Test retry logic
    - [ ] Test error recovery

### 6.2 Parallel Processing

- [ ] Implement parallel processing
  - [ ] Add parallel configuration

    ```yaml
    ingestion:
      parallel:
        max_workers: 4
        queue_size: 1000
        timeout: 60s
    ```

  - [ ] Implement parallel operations

    ```python
    class ParallelProcessor:
        def __init__(self, settings: Settings):
            self.max_workers = settings.ingestion.parallel.max_workers
            self.queue_size = settings.ingestion.parallel.queue_size
            self.timeout = settings.ingestion.parallel.timeout
            
        async def process_sources(self, sources: List[Source]) -> List[SourceResult]:
            """Process multiple sources in parallel."""
            
        async def process_documents(self, documents: List[Document]) -> List[DocumentResult]:
            """Process documents in parallel batches."""
    ```

  - [ ] Add parallel processing tests
    - [ ] Test worker limits
    - [ ] Test queue management
    - [ ] Test timeout handling
    - [ ] Test error propagation

### 6.3 Performance Monitoring

- [ ] Add performance monitoring
  - [ ] Add metrics collection

    ```python
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = defaultdict(list)
            
        def record_metric(self, name: str, value: float):
            """Record a performance metric."""
            
        def get_statistics(self) -> Dict[str, Statistics]:
            """Get performance statistics."""
    ```

  - [ ] Add monitoring configuration

    ```yaml
    monitoring:
      metrics:
        enabled: true
        interval: 60s
        retention: 24h
    ```

  - [ ] Add monitoring tests
    - [ ] Test metric collection
    - [ ] Test statistics calculation
    - [ ] Test retention policy

### 6.4 Resource Management

- [ ] Implement resource management
  - [ ] Add resource limits

    ```yaml
    resources:
      memory:
        max_percentage: 80
        check_interval: 30s
      cpu:
        max_percentage: 80
        check_interval: 30s
    ```

  - [ ] Implement resource monitoring

    ```python
    class ResourceMonitor:
        def __init__(self, settings: Settings):
            self.memory_limit = settings.resources.memory.max_percentage
            self.cpu_limit = settings.resources.cpu.max_percentage
            
        async def check_resources(self) -> ResourceStatus:
            """Check current resource usage."""
            
        async def enforce_limits(self):
            """Enforce resource limits."""
    ```

  - [ ] Add resource tests
    - [ ] Test memory monitoring
    - [ ] Test CPU monitoring
    - [ ] Test limit enforcement
