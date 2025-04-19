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
│   ├── publicdocs/
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
│   │   └── publicdocs/
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

- [x] Create SQLite state management system
  - [x] Design database schema
    - Implemented in `src/qdrant_loader/core/state/models.py`:
      - `IngestionHistory` table for tracking source ingestion history
      - `DocumentState` table for tracking individual document states
      - Added appropriate indexes and constraints
      - Added custom `UTCDateTime` type for timezone-aware datetime handling
  - [x] Implement database initialization
    - [x] Handle user-specific paths
      - Implemented in `StateManager._ensure_db_directory()`
      - Uses `pathlib.Path` for cross-platform path handling
    - [x] Handle pip-installed package paths
      - Implemented in `StateManager.__init__()`
      - Uses provided db_path parameter
  - [x] Add database tests
    - [x] Test database creation
      - Implemented in `tests/unit/core/state/test_models.py`:
        - Test table creation
        - Test index creation
        - Test constraint enforcement
    - [x] Test schema initialization
      - Implemented in `tests/unit/core/state/test_models.py`:
        - Test model creation
        - Test relationships
        - Test constraints
    - [x] Test path handling
      - Implemented in `tests/unit/core/state/test_state_manager.py`:
        - Test database file creation
        - Test temporary database handling

### 1.2 State Management Service

- [x] Create StateManager class
  - [x] Implement CRUD operations for ingestion history
    - Implemented in `src/qdrant_loader/core/state/state_manager.py`:
      - `get_last_ingestion()`
      - `update_ingestion()`
      - Added timezone-aware datetime handling
  - [x] Implement CRUD operations for document states
    - Implemented in `src/qdrant_loader/core/state/state_manager.py`:
      - `get_document_state()`
      - `update_document_state()`
      - `mark_document_deleted()`
      - Added timezone-aware datetime handling
  - [x] Add transaction support
    - Implemented using SQLAlchemy session context managers
    - Added proper session handling in all methods
  - [x] Add error handling
    - Implemented custom exceptions in `src/qdrant_loader/core/state/exceptions.py`:
      - `StateError`
      - `DatabaseError`
      - `MigrationError`
      - `StateNotFoundError`
      - `StateValidationError`
      - `ConcurrentUpdateError`
  - [x] Add logging
    - Implemented using Python's logging module
    - Added logging configuration
  - [x] Add StateManager tests
    - [x] Test CRUD operations
      - Implemented in `tests/unit/core/state/test_state_manager.py`:
        - Test create operations
        - Test read operations
        - Test update operations
        - Test delete operations
    - [x] Test transaction handling
      - Implemented in `tests/unit/core/state/test_state_manager.py`:
        - Test successful transactions
        - Test error handling
        - Test concurrent updates
    - [x] Test error scenarios
      - Implemented in `tests/unit/core/state/test_state_manager.py`:
        - Test not found errors
        - Test validation errors
        - Test concurrent access
    - [x] Test logging
      - Implemented in `tests/unit/core/state/test_state_manager.py`:
        - Test operation logging
        - Test error logging

### 1.3 Configuration Integration

- [x] Add state management configuration
  - [x] Create StateManagementConfig class
    - Implemented in `src/qdrant_loader/config/state.py`:
      - Added database path configuration
      - Added table prefix configuration
      - Added connection pool settings
  - [x] Update GlobalConfig
    - Added state_management field to `src/qdrant_loader/config/global_.py`
  - [x] Update Settings class
    - Added state management environment variables
    - Added validation for state management configuration
  - [x] Add configuration tests
    - Test StateManagementConfig validation
    - Test environment variable handling
    - Test integration with existing config

## Phase 2: Change Detection Implementation

### 2.1 Git Change Detection

- [ ] Implement Git change detection
  - [ ] Track file-level changes
    - [ ] Implement `GitChangeDetector` class
    - [ ] Add file modification tracking
    - [ ] Add file hash comparison
  - [ ] Implement last commit timestamp tracking
    - [ ] Use git log with --since
    - [ ] Parse commit timestamps
    - [ ] Handle timezone conversions using `UTCDateTime`
  - [ ] Handle file deletions
    - [ ] Track deleted files in git log
    - [ ] Update document states using `StateManager`
    - [ ] Remove from Qdrant
  - [ ] Add Git change detection tests
    - [ ] Test file change detection
    - [ ] Test timestamp tracking
    - [ ] Test deletion handling

### 2.2 Confluence Change Detection

- [x] Implement Confluence change detection
  - [x] Track page updates
    - [x] Implement `ConfluenceChangeDetector` class
    - [x] Add page modification tracking
    - [x] Integrate with `StateManager` for state tracking
  - [x] Track page deletions
    - [x] Use Confluence API for deleted pages
    - [x] Update document states using `StateManager`
    - [x] Remove from Qdrant
  - [x] Track page moves/renames
    - [x] Detect page moves
    - [x] Update document URLs
    - [x] Update document states using `StateManager`
  - [x] Add Confluence change detection tests
    - [x] Test page update detection
    - [x] Test deletion detection
    - [x] Test move/rename detection
  - [x] Improve code organization
    - [x] Refactor `ConfluenceChangeDetector` to inherit from `BaseChangeDetector`
    - [x] Update type hints to use modern Python syntax
    - [x] Improve error handling and logging
  - [x] Enhance state management
    - [x] Add proper handling of document states
    - [x] Implement robust URL tracking
    - [x] Add version tracking for documents

### 2.3 Jira Change Detection

- [ ] Implement Jira change detection
  - [ ] Track all field changes
    - [ ] Implement `JiraChangeDetector` class
    - [ ] Add field modification tracking
    - [ ] Integrate with `StateManager` for state tracking
  - [ ] Track issue updates
    - [ ] Use Jira changelog
    - [ ] Track all field changes
    - [ ] Update document states using `StateManager`
  - [ ] Track issue deletions
    - [ ] Detect deleted issues
    - [ ] Update document states using `StateManager`
    - [ ] Remove from Qdrant
  - [ ] Add Jira change detection tests
    - [ ] Test field change detection
    - [ ] Test update detection
    - [ ] Test deletion detection

### 2.4 Public Docs Change Detection

- [x] Implement public docs change detection
  - [x] Track file modification times
    - Implemented `PublicDocsChangeDetector` class
    - Added file modification tracking
    - Integrated with `StateManager` for state tracking
  - [x] Track URL changes
    - Implemented URL change tracking
    - Added state updates using `StateManager`
    - Added Qdrant document updates
  - [x] Add public docs change detection tests
    - [x] Test modification time tracking
    - [x] Test URL change detection
    - [x] Test state updates
  - [x] Improve code organization
    - [x] Create `BaseChangeDetector` abstract class
    - [x] Refactor `PublicDocsChangeDetector` to inherit from base class
    - [x] Update type hints to use modern Python syntax
  - [x] Enhance error handling
    - [x] Add defensive programming for missing fields
    - [x] Improve handling of deleted documents
    - [x] Add proper state management for document deletions
  - [x] Improve test organization
    - [x] Rename test files for better clarity
    - [x] Clean up test imports
    - [x] Ensure proper test isolation

## Phase 3: Incremental Ingestion Implementation

### 3.1 Ingestion Service Updates

- [x] Update ingestion service
  - [x] Add incremental ingestion mode
    - Implemented in `PublicDocsConnector`
    - Added change detection integration
    - Added state management integration
  - [x] Add document update handling
    - Implemented document state updates
    - Added Qdrant vector updates
    - Added state management integration
  - [x] Add document deletion handling
    - Implemented deletion detection
    - Added Qdrant removal
    - Added state management integration
  - [x] Add ingestion service tests
    - [x] Test incremental mode
    - [x] Test update handling
    - [x] Test deletion handling

### 3.2 Performance Optimization

- [ ] Implement batch processing
  - [ ] Add document batching
    - [ ] Implement batch size configuration
    - [ ] Add batch processing logic
    - [ ] Optimize memory usage
  - [ ] Add parallel processing
    - [ ] Implement worker pool
    - [ ] Add task distribution
    - [ ] Handle worker errors
  - [ ] Add performance tests
    - [ ] Test batch processing
    - [ ] Test parallel processing
    - [ ] Test memory usage

### 3.3 Error Handling and Recovery

- [ ] Implement error handling
  - [ ] Add error recovery
    - [ ] Implement retry logic
    - [ ] Add backoff strategy
    - [ ] Handle transient failures
  - [ ] Add transaction rollback
    - [ ] Implement rollback logic
    - [ ] Handle partial failures
    - [ ] Maintain data consistency
  - [ ] Add error handling tests
    - [ ] Test retry logic
    - [ ] Test rollback
    - [ ] Test consistency

## Phase 4: CLI and Configuration Updates

### 4.1 CLI Updates

- [ ] Update CLI commands
  - [ ] Add incremental mode flag
    - [ ] Implement `--incremental` flag
    - [ ] Add mode validation
    - [ ] Update help documentation
  - [ ] Add configuration options
    - [ ] Add batch size option
    - [ ] Add worker count option
    - [ ] Add retry options
  - [ ] Add CLI tests
    - [ ] Test incremental mode
    - [ ] Test configuration
    - [ ] Test validation

### 4.2 Configuration Updates

- [x] Update configuration
  - [x] Add state management config
    - Added database URL config
    - Added table prefix config
    - Added connection pool config
  - [x] Add change detection config
    - Added source-specific settings
    - Added detection intervals
    - Added timeout settings
  - [ ] Add performance config
    - [ ] Add batch size settings
    - [ ] Add worker settings
    - [ ] Add retry settings
  - [x] Add config validation
    - Added validation for required fields
    - Added validation for value ranges
    - Added config tests

### 4.3 Documentation Updates

- [ ] Update documentation
  - [ ] Add incremental mode docs
    - [ ] Document CLI usage
    - [ ] Document configuration
    - [ ] Add examples
  - [ ] Add performance tuning docs
    - [ ] Document batch processing
    - [ ] Document parallel processing
    - [ ] Add benchmarks
  - [ ] Add troubleshooting docs
    - [ ] Document common issues
    - [ ] Add solutions
    - [ ] Add best practices

## Phase 5: Testing and Documentation

### 5.1 Testing

- [x] Add comprehensive tests
  - [x] Add end-to-end tests
    - [x] Test full ingestion flow
    - [x] Test incremental flow
    - [x] Test error scenarios
  - [x] Add integration tests
    - [x] Test source integration
    - [x] Test state management
    - [x] Test Qdrant integration
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
    - [ ] Test usage examples
    - [ ] Test troubleshooting guide

## Phase 6: Performance Optimization (Future)

### 6.1 Batch Processing

- [ ] Implement batch processing
  - [ ] Add batch configuration
  - [ ] Implement batch operations
  - [ ] Add batch processing tests

### 6.2 Parallel Processing

- [ ] Implement parallel processing
  - [ ] Add parallel configuration
  - [ ] Implement parallel operations
  - [ ] Add parallel processing tests

### 6.3 Performance Monitoring

- [ ] Add performance monitoring
  - [ ] Add metrics collection
  - [ ] Add monitoring configuration
  - [ ] Add monitoring tests

### 6.4 Resource Management

- [ ] Implement resource management
  - [ ] Add resource limits
  - [ ] Implement resource monitoring
  - [ ] Add resource tests

## Phase 7: Database Migration Support (Future)

### 7.1 Alembic Setup

- [ ] Set up Alembic for database migrations
  - [ ] Initialize Alembic environment
  - [ ] Configure Alembic for SQLite
  - [ ] Create initial migration
  - [ ] Add migration tests

### 7.2 Migration Management

- [ ] Implement migration management
  - [ ] Add migration commands to CLI
  - [ ] Add migration status tracking
  - [ ] Add rollback support
  - [ ] Add migration tests

### 7.3 Migration Documentation

- [ ] Add migration documentation
  - [ ] Document migration process
  - [ ] Document rollback process
  - [ ] Document best practices
  - [ ] Add migration examples
