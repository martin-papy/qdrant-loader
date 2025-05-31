# Multi-Project Support Specification

**Issue**: #20  
**Version**: 1.0  
**Date**: May 31, 2025  
**Status**: Draft

## 📋 Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Architecture](#architecture)
4. [Configuration Schema](#configuration-schema)
5. [Database Schema](#database-schema)
6. [API Changes](#api-changes)
7. [Implementation Strategy](#implementation-strategy)
8. [Migration Strategy](#migration-strategy)
9. [Testing Strategy](#testing-strategy)
10. [Performance Considerations](#performance-considerations)

## 🎯 Overview

### Problem Statement

Currently, QDrant Loader operates with a single project scope where all sources are ingested into one collection without project-level organization. Users managing multiple projects, clients, or product lines need to:

- Run separate instances for each project
- Maintain multiple configuration files
- Use different QDrant collections or servers
- Cannot search across projects when needed

### Solution Summary

Implement multi-project support that allows:

- **Single Configuration**: One `config.yaml` file defining multiple projects
- **Unified Infrastructure**: One QDrant server and one MCP server instance
- **Project Isolation**: Clear separation between project data
- **Cross-Project Search**: Ability to search within specific projects or across all projects
- **Backward Compatibility**: Existing configurations continue to work unchanged

### Key Benefits

1. **Resource Efficiency**: Single infrastructure for multiple projects
2. **Operational Simplicity**: One configuration file and server to manage
3. **Flexible Search**: Project-specific or cross-project search capabilities
4. **Organizational Clarity**: Clear project boundaries and metadata
5. **Scalability**: Easy addition of new projects without infrastructure changes

## 📋 Requirements

### Functional Requirements

#### FR-1: Project Configuration

- **FR-1.1**: Support multiple projects in a single configuration file
- **FR-1.2**: Each project must have a unique identifier and display name
- **FR-1.3**: Projects can have independent source configurations
- **FR-1.4**: Projects can override global settings with project-specific values
- **FR-1.5**: Support for project descriptions and metadata

#### FR-2: Data Ingestion

- **FR-2.1**: All documents must be tagged with their project identifier
- **FR-2.2**: Support project-specific ingestion commands
- **FR-2.3**: Maintain separate state tracking per project
- **FR-2.4**: Support incremental updates per project
- **FR-2.5**: Handle project-specific error reporting and logging

#### FR-3: Search and Retrieval

- **FR-3.1**: Search within specific projects
- **FR-3.2**: Search across multiple selected projects
- **FR-3.3**: Search across all projects
- **FR-3.4**: Include project context in search results
- **FR-3.5**: Support project-based filtering in MCP server

#### FR-4: CLI Interface

- **FR-4.1**: List all configured projects
- **FR-4.2**: Show status for specific projects
- **FR-4.3**: Ingest data for specific projects
- **FR-4.4**: Support project-specific operations
- **FR-4.5**: Display project-aware statistics and metrics

#### FR-5: MCP Server Integration

- **FR-5.1**: Add project filtering to existing search tools
- **FR-5.2**: Implement project management tools
- **FR-5.3**: Include project context in search results
- **FR-5.4**: Support project discovery and listing

### Non-Functional Requirements

#### NFR-1: Performance

- **NFR-1.1**: No significant performance degradation for single-project use cases
- **NFR-1.2**: Efficient project filtering in search operations
- **NFR-1.3**: Minimal memory overhead for project metadata
- **NFR-1.4**: Fast project switching and filtering

#### NFR-2: Compatibility

- **NFR-2.1**: 100% backward compatibility with existing configurations
- **NFR-2.2**: Existing single-project setups work without changes
- **NFR-2.3**: Gradual migration path for existing users
- **NFR-2.4**: No breaking changes to existing APIs

#### NFR-3: Scalability

- **NFR-3.1**: Support for 100+ projects in a single configuration
- **NFR-3.2**: Efficient handling of large numbers of documents across projects
- **NFR-3.3**: Reasonable memory usage with many projects
- **NFR-3.4**: Fast project-based operations

#### NFR-4: Maintainability

- **NFR-4.1**: Clear separation of project-specific and global logic
- **NFR-4.2**: Consistent project handling across all components
- **NFR-4.3**: Comprehensive logging and debugging support
- **NFR-4.4**: Well-documented project configuration options

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                      │
├─────────────────────────────────────────────────────────────┤
│  config.yaml                                               │
│  ├── global: (shared settings)                             │
│  ├── projects:                                             │
│  │   ├── project-alpha: (sources, settings)               │
│  │   ├── project-beta: (sources, settings)                │
│  │   └── project-gamma: (sources, settings)               │
│  └── sources: (legacy, maps to default project)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Ingestion Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│  Project Manager                                           │
│  ├── Project Discovery & Validation                        │
│  ├── Project-Specific State Management                     │
│  └── Project Metadata Injection                           │
│                                                            │
│  Enhanced Connectors                                       │
│  ├── Git Connector + Project Context                       │
│  ├── Confluence Connector + Project Context                │
│  ├── JIRA Connector + Project Context                      │
│  ├── LocalFile Connector + Project Context                 │
│  └── PublicDocs Connector + Project Context                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
├─────────────────────────────────────────────────────────────┤
│  QDrant Collection                                         │
│  ├── Documents with project_id metadata                    │
│  ├── Project-aware vector search                           │
│  └── Efficient project filtering                           │
│                                                            │
│  State Database                                            │
│  ├── Projects table (metadata)                             │
│  ├── Documents table + project_id                          │
│  ├── Document_chunks table + project_id                    │
│  └── Project-specific state tracking                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Search & Retrieval                       │
├─────────────────────────────────────────────────────────────┤
│  Enhanced MCP Server                                       │
│  ├── Project-aware search tools                            │
│  ├── Project management tools                              │
│  ├── Cross-project search capabilities                     │
│  └── Project context in results                            │
│                                                            │
│  CLI Interface                                             │
│  ├── Project listing and status                            │
│  ├── Project-specific operations                           │
│  └── Cross-project commands                                │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

#### Project Manager

- **Responsibility**: Central coordination of project-related operations
- **Functions**:
  - Project discovery from configuration
  - Project validation and metadata management
  - Project-specific state coordination
  - Project context injection into documents

#### Enhanced Connectors

- **Responsibility**: Source-specific data ingestion with project awareness
- **Functions**:
  - Accept project context from Project Manager
  - Tag all documents with project metadata
  - Maintain project-specific state
  - Handle project-specific error reporting

#### Storage Layer

- **Responsibility**: Persistent storage with project organization
- **Functions**:
  - Store documents with project metadata
  - Provide efficient project-based filtering
  - Maintain project-specific state information
  - Support cross-project operations

#### Search & Retrieval

- **Responsibility**: Project-aware search and management interfaces
- **Functions**:
  - Filter search results by project
  - Provide project context in results
  - Support project management operations
  - Enable cross-project search capabilities

## 📝 Configuration Schema

### New Configuration Structure

```yaml
# Global configuration (shared across all projects)
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null
  embedding:
    model: "text-embedding-3-small"
    batch_size: 100
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  state_management:
    database_path: "${STATE_DB_PATH}"
    table_prefix: "qdrant_loader_"
  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 300

# Project-specific configurations
projects:
  # Project Alpha - Customer Portal
  project-alpha:
    # Project metadata
    display_name: "Project Alpha - Customer Portal"
    description: "Customer-facing portal documentation and code"
    
    # Optional: Custom collection name (defaults to global + project suffix)
    collection_name: "project_alpha_docs"
    
    # Optional: Project-specific overrides
    chunking:
      chunk_size: 1000  # Override global setting
    
    # Project-specific sources
    sources:
      git:
        frontend-repo:
          base_url: "https://github.com/company/alpha-frontend.git"
          branch: "main"
          include_paths: ["docs/**", "src/**"]
          enable_file_conversion: true
      
      confluence:
        alpha-space:
          base_url: "https://company.atlassian.net/wiki"
          deployment_type: "cloud"
          space_key: "ALPHA"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
  
  # Project Beta - Internal Tools
  project-beta:
    display_name: "Project Beta - Internal Tools"
    description: "Internal tooling and infrastructure documentation"
    
    sources:
      git:
        tools-repo:
          base_url: "https://github.com/company/beta-tools.git"
          branch: "develop"
          include_paths: ["**"]
          enable_file_conversion: true
      
      jira:
        beta-project:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "BETA"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
      
      localfile:
        internal-docs:
          base_url: "file:///path/to/internal/docs"
          include_paths: ["**/*.md", "**/*.pdf"]
          enable_file_conversion: true

# Legacy support: sources at root level map to default project
sources:
  # Existing configuration for backward compatibility
  # These will be automatically assigned to a "default" project
  git:
    legacy-repo:
      base_url: "https://github.com/company/legacy.git"
      branch: "main"
```

### Configuration Validation Rules

#### Project Validation

1. **Unique Project IDs**: All project IDs must be unique
2. **Valid Identifiers**: Project IDs must be valid Python identifiers (alphanumeric + underscores)
3. **Required Fields**: `display_name` is required for each project
4. **Collection Names**: If specified, collection names must be unique across projects

#### Source Validation

1. **Unique Source Names**: Source names must be unique within a project
2. **Valid Source Types**: All source types must be supported
3. **Required Configuration**: Each source must have valid configuration for its type

#### Global vs Project Settings

1. **Override Rules**: Project settings override global settings
2. **Merge Strategy**: Complex objects (like chunking) are merged, not replaced
3. **Validation**: Overridden settings must pass the same validation as global settings

### Default Project Behavior

#### Legacy Configuration Support

- Existing `sources` at root level automatically create a "default" project
- Default project gets ID: `"default"`
- Default project display name: `"Default Project"`
- No breaking changes for existing configurations

#### Collection Naming Strategy

- **With explicit collection_name**: Use the specified name
- **Without explicit collection_name**: Use pattern `{global_collection_name}_{project_id}`
- **Default project**: Use global collection name unchanged (backward compatibility)

## 🗄️ Database Schema

### New Tables

#### Projects Table

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,                    -- Project identifier
    display_name TEXT NOT NULL,             -- Human-readable project name
    description TEXT,                       -- Project description
    collection_name TEXT,                   -- QDrant collection name
    config_hash TEXT,                       -- Hash of project configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(collection_name)
);
```

#### Project Sources Table

```sql
CREATE TABLE project_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,               -- Reference to projects.id
    source_type TEXT NOT NULL,              -- git, confluence, jira, etc.
    source_name TEXT NOT NULL,              -- Source identifier within project
    config_hash TEXT,                       -- Hash of source configuration
    last_sync_time TIMESTAMP,               -- Last successful sync
    status TEXT DEFAULT 'pending',          -- pending, syncing, completed, error
    error_message TEXT,                     -- Last error message if any
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, source_type, source_name)
);
```

### Modified Tables

#### Documents Table

```sql
-- Add project_id column
ALTER TABLE documents ADD COLUMN project_id TEXT;

-- Add index for efficient project filtering
CREATE INDEX idx_documents_project_id ON documents(project_id);

-- Add foreign key constraint (for new installations)
-- ALTER TABLE documents ADD FOREIGN KEY (project_id) REFERENCES projects(id);
```

#### Document Chunks Table

```sql
-- Add project_id column
ALTER TABLE document_chunks ADD COLUMN project_id TEXT;

-- Add index for efficient project filtering
CREATE INDEX idx_document_chunks_project_id ON document_chunks(project_id);

-- Add foreign key constraint (for new installations)
-- ALTER TABLE document_chunks ADD FOREIGN KEY (project_id) REFERENCES projects(id);
```

#### Ingestion State Table

```sql
-- Add project_id column to existing state tracking
ALTER TABLE ingestion_state ADD COLUMN project_id TEXT;

-- Add index for project-specific state queries
CREATE INDEX idx_ingestion_state_project_id ON ingestion_state(project_id);

-- Update unique constraints to include project_id
-- This will require data migration for existing installations
```

### Migration Strategy

#### Phase 1: Schema Updates

1. Add new tables (`projects`, `project_sources`)
2. Add `project_id` columns to existing tables
3. Create indexes for efficient project filtering
4. Update constraints and foreign keys

#### Phase 2: Data Migration

1. Create default project for existing data
2. Assign all existing documents to default project
3. Migrate existing state data to project-aware format
4. Validate data integrity after migration

#### Phase 3: Cleanup

1. Make `project_id` NOT NULL after migration
2. Add foreign key constraints
3. Remove any temporary migration artifacts

## 🔌 API Changes

### CLI Interface Changes

#### New Commands

```bash
# Project management
qdrant-loader projects list                           # List all projects
qdrant-loader projects status                         # Status of all projects
qdrant-loader projects status --project PROJECT_ID   # Status of specific project
qdrant-loader projects info --project PROJECT_ID     # Detailed project information

# Project-specific operations
qdrant-loader ingest --project PROJECT_ID            # Ingest specific project
qdrant-loader ingest --project PROJECT_ID --source-type git  # Ingest specific source in project
qdrant-loader init --project PROJECT_ID              # Initialize specific project

# Cross-project operations
qdrant-loader ingest --all-projects                  # Ingest all projects
qdrant-loader status --all-projects                  # Status of all projects
```

#### Modified Commands

```bash
# Existing commands with project awareness
qdrant-loader ingest                                  # Ingest all projects (new default)
qdrant-loader ingest --source-type git               # Ingest git sources across all projects
qdrant-loader status                                  # Show status for all projects
qdrant-loader config                                  # Show configuration including projects
```

### MCP Server API Changes

#### Enhanced Search Tools

##### Standard Search with Project Filtering

```json
{
  "name": "search",
  "arguments": {
    "query": "authentication implementation",
    "project_ids": ["project-alpha", "project-beta"],  // New: Optional project filtering
    "source_types": ["git", "confluence"],
    "limit": 10
  }
}
```

##### Hierarchy Search with Project Context

```json
{
  "name": "hierarchy_search",
  "arguments": {
    "query": "API documentation",
    "project_ids": ["project-alpha"],                  // New: Project filtering
    "hierarchy_filter": {
      "root_only": true,
      "has_children": true
    },
    "organize_by_hierarchy": true,
    "limit": 10
  }
}
```

##### Attachment Search with Project Scope

```json
{
  "name": "attachment_search",
  "arguments": {
    "query": "requirements",
    "project_ids": ["project-alpha"],                  // New: Project filtering
    "attachment_filter": {
      "attachments_only": true,
      "file_type": "pdf"
    },
    "include_parent_context": true,
    "limit": 10
  }
}
```

#### New Project Management Tools

##### List Projects

```json
{
  "name": "list_projects",
  "arguments": {}
}
```

**Response:**

```json
{
  "projects": [
    {
      "id": "project-alpha",
      "display_name": "Project Alpha - Customer Portal",
      "description": "Customer-facing portal documentation and code",
      "collection_name": "project_alpha_docs",
      "source_count": 3,
      "document_count": 1250,
      "last_updated": "2025-05-31T10:30:00Z"
    },
    {
      "id": "project-beta",
      "display_name": "Project Beta - Internal Tools",
      "description": "Internal tooling and infrastructure documentation",
      "collection_name": "documents_project_beta",
      "source_count": 2,
      "document_count": 890,
      "last_updated": "2025-05-30T15:45:00Z"
    }
  ]
}
```

##### Get Project Information

```json
{
  "name": "get_project_info",
  "arguments": {
    "project_id": "project-alpha"
  }
}
```

**Response:**

```json
{
  "project": {
    "id": "project-alpha",
    "display_name": "Project Alpha - Customer Portal",
    "description": "Customer-facing portal documentation and code",
    "collection_name": "project_alpha_docs",
    "sources": [
      {
        "type": "git",
        "name": "frontend-repo",
        "status": "completed",
        "document_count": 450,
        "last_sync": "2025-05-31T10:30:00Z"
      },
      {
        "type": "confluence",
        "name": "alpha-space",
        "status": "completed",
        "document_count": 800,
        "last_sync": "2025-05-31T09:15:00Z"
      }
    ],
    "statistics": {
      "total_documents": 1250,
      "total_chunks": 5600,
      "storage_size": "45.2 MB",
      "last_updated": "2025-05-31T10:30:00Z"
    }
  }
}
```

#### Enhanced Search Results

All search results now include project context:

```json
{
  "results": [
    {
      "id": "doc_123",
      "score": 0.85,
      "text": "Authentication implementation details...",
      "source_type": "git",
      "source_title": "auth.py",
      "project_id": "project-alpha",                    // New: Project context
      "project_name": "Project Alpha - Customer Portal", // New: Project display name
      "project_context": "Project: Project Alpha - Customer Portal", // New: Formatted context
      // ... existing fields
    }
  ]
}
```

## 🚀 Implementation Strategy

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 Configuration System Enhancement

- **Files**: `src/qdrant_loader/config/`
- **Tasks**:
  - Extend configuration schema to support projects
  - Implement project validation and parsing
  - Add backward compatibility for legacy configurations
  - Create project configuration models

#### 1.2 Database Schema Updates

- **Files**: `src/qdrant_loader/core/state/`
- **Tasks**:
  - Create migration scripts for new tables
  - Add project_id columns to existing tables
  - Implement project-aware state management
  - Create project metadata management

#### 1.3 Project Manager Component

- **Files**: `src/qdrant_loader/core/project_manager.py`
- **Tasks**:
  - Implement project discovery and validation
  - Create project metadata injection system
  - Handle project-specific state coordination
  - Implement project lifecycle management

### Phase 2: Ingestion Pipeline Enhancement (Week 3-4)

#### 2.1 Connector Updates

- **Files**: `src/qdrant_loader/connectors/*/`
- **Tasks**:
  - Update all connectors to accept project context
  - Implement project metadata injection in documents
  - Update state management to be project-aware
  - Add project-specific error handling and logging

#### 2.2 Document Processing Pipeline

- **Files**: `src/qdrant_loader/core/ingestion_pipeline.py`
- **Tasks**:
  - Integrate Project Manager into pipeline
  - Ensure all documents get project metadata
  - Update chunking to preserve project context
  - Implement project-specific processing options

#### 2.3 CLI Interface Updates

- **Files**: `src/qdrant_loader/cli/`
- **Tasks**:
  - Add project management commands
  - Update existing commands for project awareness
  - Implement project-specific operations
  - Add project status and information commands

### Phase 3: Search and Retrieval Enhancement (Week 5-6)

#### 3.1 MCP Server Updates

- **Files**: `packages/qdrant-loader-mcp-server/src/`
- **Tasks**:
  - Add project filtering to existing search tools
  - Implement new project management tools
  - Update search engine for project-aware queries
  - Enhance result formatting with project context

#### 3.2 Search Engine Enhancement

- **Files**: `packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/`
- **Tasks**:
  - Implement efficient project filtering in QDrant queries
  - Add project context to search results
  - Support cross-project search capabilities
  - Optimize performance for project-based operations

### Phase 4: Testing and Documentation (Week 7-8)

#### 4.1 Comprehensive Testing

- **Files**: `tests/`, `packages/qdrant-loader-mcp-server/tests/`
- **Tasks**:
  - Unit tests for all project-related functionality
  - Integration tests for multi-project scenarios
  - Migration testing for existing installations
  - Performance testing with multiple projects

#### 4.2 Documentation Updates

- **Files**: `docs/`, `README.md`, package READMEs
- **Tasks**:
  - Update all documentation with multi-project examples
  - Create migration guide for existing users
  - Document new CLI commands and MCP tools
  - Create best practices guide for multi-project setups

## 🔄 Migration Strategy

### Automatic Migration for Existing Users

#### Detection of Legacy Configuration

```python
def detect_legacy_configuration(config: dict) -> bool:
    """Detect if configuration uses legacy single-project format."""
    return "sources" in config and "projects" not in config
```

#### Automatic Migration Process

1. **Detect Legacy Format**: Check if configuration has `sources` at root level
2. **Create Default Project**: Generate a default project configuration
3. **Migrate Sources**: Move root-level sources to default project
4. **Preserve Settings**: Maintain all existing settings and behavior
5. **Update Database**: Assign existing documents to default project

#### Migration Example

```yaml
# Before (legacy)
global:
  qdrant:
    collection_name: "documents"
sources:
  git:
    my-repo:
      base_url: "https://github.com/user/repo.git"

# After (automatic migration)
global:
  qdrant:
    collection_name: "documents"
projects:
  default:
    display_name: "Default Project"
    description: "Migrated from legacy configuration"
    sources:
      git:
        my-repo:
          base_url: "https://github.com/user/repo.git"
```

### Manual Migration for Advanced Users

#### Gradual Migration Path

1. **Phase 1**: Continue using legacy format (fully supported)
2. **Phase 2**: Add new projects while keeping legacy sources
3. **Phase 3**: Migrate legacy sources to explicit default project
4. **Phase 4**: Reorganize into logical project structure

#### Migration Tools

```bash
# Validate current configuration
qdrant-loader config --validate

# Preview migration changes
qdrant-loader migrate --dry-run

# Perform automatic migration
qdrant-loader migrate --auto

# Manual migration assistance
qdrant-loader migrate --interactive
```

## 🧪 Testing Strategy

### Unit Testing

#### Configuration Testing

- **Test Cases**:
  - Valid multi-project configurations
  - Invalid project configurations (duplicate IDs, invalid names)
  - Legacy configuration backward compatibility
  - Project-specific setting overrides
  - Configuration validation and error handling

#### Project Manager Testing

- **Test Cases**:
  - Project discovery and validation
  - Project metadata injection
  - Project-specific state management
  - Error handling for invalid projects

#### Connector Testing

- **Test Cases**:
  - Project context acceptance and propagation
  - Document metadata injection
  - Project-specific state tracking
  - Error handling and logging

### Integration Testing

#### Multi-Project Ingestion

- **Test Scenarios**:
  - Ingest multiple projects simultaneously
  - Project-specific source configurations
  - Cross-project state isolation
  - Error isolation between projects

#### Search and Retrieval

- **Test Scenarios**:
  - Project-filtered search operations
  - Cross-project search capabilities
  - Project context in search results
  - MCP server project management tools

#### Migration Testing

- **Test Scenarios**:
  - Legacy configuration migration
  - Data migration for existing installations
  - Rollback capabilities
  - Migration validation and verification

### Performance Testing

#### Scalability Testing

- **Test Scenarios**:
  - Performance with 10, 50, 100+ projects
  - Memory usage with large numbers of projects
  - Search performance with project filtering
  - Ingestion performance across multiple projects

#### Regression Testing

- **Test Scenarios**:
  - Single-project performance (no degradation)
  - Legacy configuration performance
  - Existing API compatibility
  - Memory and CPU usage patterns

## ⚡ Performance Considerations

### QDrant Query Optimization

#### Efficient Project Filtering

```python
# Optimized project filtering using QDrant filters
filter_conditions = models.Filter(
    must=[
        models.FieldCondition(
            key="project_id",
            match=models.MatchValue(value=project_id)
        )
    ]
)

search_result = qdrant_client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    query_filter=filter_conditions,
    limit=limit
)
```

#### Index Strategy

- **Project ID Index**: Ensure efficient filtering by project_id
- **Composite Indexes**: Consider indexes on (project_id, source_type) for common queries
- **Collection Strategy**: Single collection with filtering vs. multiple collections

### Memory Management

#### Project Metadata Caching

- Cache project configurations in memory
- Lazy loading of project-specific settings
- Efficient project context propagation
- Minimal memory overhead per project

#### State Management Optimization

- Project-specific state caching
- Efficient database queries with project filtering
- Connection pooling for multi-project operations
- Batch operations where possible

### Search Performance

#### Query Optimization

- Pre-filter by project before semantic search
- Efficient project context injection
- Optimized result formatting
- Caching of project metadata

#### Cross-Project Search

- Parallel search across multiple projects
- Efficient result merging and ranking
- Configurable project weights
- Performance monitoring and optimization

### Scalability Targets

#### Performance Goals

- **Projects**: Support 100+ projects without significant performance degradation
- **Documents**: Handle 1M+ documents across all projects efficiently
- **Search Latency**: Maintain <200ms average search response time
- **Memory Usage**: <10MB additional memory per project
- **Ingestion Speed**: No significant reduction in ingestion throughput

#### Monitoring and Metrics

- Project-specific performance metrics
- Cross-project operation monitoring
- Resource usage tracking per project
- Performance regression detection

---

This specification provides a comprehensive foundation for implementing multi-project support in QDrant Loader. The design prioritizes backward compatibility, performance, and user experience while enabling powerful new multi-project capabilities.
