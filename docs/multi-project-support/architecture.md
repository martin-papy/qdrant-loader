# Multi-Project Support Architecture

**Issue**: #20  
**Version**: 1.0  
**Date**: May 31, 2025  
**Status**: Draft

## 📋 Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Database Design](#database-design)
6. [API Design](#api-design)
7. [Configuration Architecture](#configuration-architecture)
8. [Performance Considerations](#performance-considerations)
9. [Security Considerations](#security-considerations)
10. [Extension Points](#extension-points)

## 🎯 Overview

### Architectural Goals

1. **Backward Compatibility**: Existing single-project configurations must work unchanged
2. **Performance**: Multi-project support should not significantly impact performance
3. **Scalability**: Support for 100+ projects with efficient resource usage
4. **Maintainability**: Clear separation of concerns and modular design
5. **Extensibility**: Easy addition of new project-related features

### Design Principles

1. **Single Responsibility**: Each component has a clear, focused purpose
2. **Dependency Injection**: Components receive dependencies rather than creating them
3. **Interface Segregation**: Small, focused interfaces for better testability
4. **Open/Closed**: Open for extension, closed for modification
5. **Composition over Inheritance**: Favor composition for flexibility

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interface Layer                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  CLI Interface                    │  MCP Server                             │
│  ├── Project Commands             │  ├── Enhanced Search Tools              │
│  ├── Legacy Commands              │  ├── Project Management Tools           │
│  └── Status & Info Commands       │  └── Cross-Project Search               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Application Layer                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Project Manager                  │  Ingestion Pipeline                     │
│  ├── Project Discovery            │  ├── Document Processing                │
│  ├── Project Validation           │  ├── Metadata Injection                 │
│  ├── Context Management           │  └── State Coordination                 │
│  └── Lifecycle Management         │                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Connector Layer                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Base Connector                   │  Specific Connectors                    │
│  ├── Project Context Interface    │  ├── Git Connector                      │
│  ├── Metadata Injection           │  ├── Confluence Connector               │
│  ├── State Management             │  ├── JIRA Connector                     │
│  └── Error Handling               │  ├── LocalFile Connector                │
│                                   │  └── PublicDocs Connector               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Layer                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Configuration System             │  Storage Layer                          │
│  ├── Multi-Project Parser         │  ├── QDrant Vector Store                │
│  ├── Legacy Support               │  ├── State Database                     │
│  ├── Validation Engine            │  ├── Project Metadata                   │
│  └── Migration Tools              │  └── Document Storage                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
Configuration → Project Manager → Connectors → Storage
      ↓              ↓              ↓           ↓
   Validation → Context Injection → Documents → QDrant
      ↓              ↓              ↓           ↓
   Migration  → State Management → Metadata → Database
```

## 🔧 Component Design

### Project Manager

#### Responsibilities

- Discover and validate projects from configuration
- Manage project lifecycle and metadata
- Inject project context into processing pipeline
- Coordinate project-specific operations

#### Interface Design

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class ProjectContext:
    """Project context information passed through the pipeline."""
    project_id: str
    display_name: str
    description: Optional[str]
    collection_name: str
    config_overrides: Dict[str, Any]
    
class ProjectManager(ABC):
    """Abstract base class for project management."""
    
    @abstractmethod
    def discover_projects(self, config: Dict[str, Any]) -> List[ProjectContext]:
        """Discover all projects from configuration."""
        pass
    
    @abstractmethod
    def validate_project(self, project_context: ProjectContext) -> bool:
        """Validate a project configuration."""
        pass
    
    @abstractmethod
    def get_project_context(self, project_id: str) -> Optional[ProjectContext]:
        """Get project context by ID."""
        pass
    
    @abstractmethod
    def inject_project_metadata(self, document: Document, project_context: ProjectContext) -> Document:
        """Inject project metadata into a document."""
        pass
```

#### Implementation Details

```python
class DefaultProjectManager(ProjectManager):
    """Default implementation of project management."""
    
    def __init__(self, config_manager: ConfigManager, state_manager: StateManager):
        self.config_manager = config_manager
        self.state_manager = state_manager
        self._project_cache: Dict[str, ProjectContext] = {}
    
    def discover_projects(self, config: Dict[str, Any]) -> List[ProjectContext]:
        """Discover projects from configuration with legacy support."""
        projects = []
        
        # Handle new multi-project format
        if "projects" in config:
            for project_id, project_config in config["projects"].items():
                projects.append(self._create_project_context(project_id, project_config))
        
        # Handle legacy format
        if "sources" in config and "projects" not in config:
            default_project = self._create_default_project(config["sources"])
            projects.append(default_project)
        
        # Cache projects for quick access
        self._project_cache = {p.project_id: p for p in projects}
        return projects
    
    def _create_project_context(self, project_id: str, project_config: Dict[str, Any]) -> ProjectContext:
        """Create project context from configuration."""
        return ProjectContext(
            project_id=project_id,
            display_name=project_config.get("display_name", project_id),
            description=project_config.get("description"),
            collection_name=self._determine_collection_name(project_id, project_config),
            config_overrides=project_config.get("overrides", {})
        )
    
    def _determine_collection_name(self, project_id: str, project_config: Dict[str, Any]) -> str:
        """Determine collection name for project."""
        if "collection_name" in project_config:
            return project_config["collection_name"]
        
        global_collection = self.config_manager.get_global_config().get("qdrant", {}).get("collection_name", "documents")
        
        if project_id == "default":
            return global_collection  # Backward compatibility
        else:
            return f"{global_collection}_{project_id}"
```

### Enhanced Connectors

#### Base Connector Interface

```python
from abc import ABC, abstractmethod
from typing import Iterator, Optional

class ProjectAwareConnector(ABC):
    """Base class for project-aware connectors."""
    
    def __init__(self, project_context: ProjectContext, config: Dict[str, Any]):
        self.project_context = project_context
        self.config = config
        self.state_manager = self._create_state_manager()
    
    @abstractmethod
    def fetch_documents(self) -> Iterator[Document]:
        """Fetch documents with project context."""
        pass
    
    def inject_project_metadata(self, document: Document) -> Document:
        """Inject project metadata into document."""
        document.metadata.update({
            "project_id": self.project_context.project_id,
            "project_name": self.project_context.display_name,
            "collection_name": self.project_context.collection_name
        })
        return document
    
    def _create_state_manager(self) -> ProjectStateManager:
        """Create project-specific state manager."""
        return ProjectStateManager(
            project_id=self.project_context.project_id,
            source_type=self.get_source_type(),
            source_name=self.get_source_name()
        )
```

#### Git Connector Enhancement

```python
class GitConnector(ProjectAwareConnector):
    """Git connector with project awareness."""
    
    def __init__(self, project_context: ProjectContext, source_name: str, config: Dict[str, Any]):
        super().__init__(project_context, config)
        self.source_name = source_name
        self.repo_url = config["base_url"]
        self.branch = config.get("branch", "main")
    
    def fetch_documents(self) -> Iterator[Document]:
        """Fetch Git documents with project context."""
        # Check if we need to update based on project-specific state
        last_commit = self.state_manager.get_last_processed_commit()
        
        for file_path, content in self._fetch_changed_files(last_commit):
            document = Document(
                content=content,
                metadata={
                    "source_type": "git",
                    "source_name": self.source_name,
                    "file_path": file_path,
                    "repository": self.repo_url,
                    "branch": self.branch
                }
            )
            
            # Inject project metadata
            document = self.inject_project_metadata(document)
            yield document
    
    def get_source_type(self) -> str:
        return "git"
    
    def get_source_name(self) -> str:
        return self.source_name
```

### Configuration System

#### Multi-Project Configuration Parser

```python
class MultiProjectConfigParser:
    """Parser for multi-project configurations with legacy support."""
    
    def __init__(self, validator: ConfigValidator):
        self.validator = validator
    
    def parse(self, config_data: Dict[str, Any]) -> ParsedConfig:
        """Parse configuration with multi-project support."""
        # Validate configuration structure
        self.validator.validate_structure(config_data)
        
        # Parse global configuration
        global_config = self._parse_global_config(config_data.get("global", {}))
        
        # Parse projects
        projects = self._parse_projects(config_data, global_config)
        
        return ParsedConfig(
            global_config=global_config,
            projects=projects,
            is_legacy=self._is_legacy_config(config_data)
        )
    
    def _parse_projects(self, config_data: Dict[str, Any], global_config: GlobalConfig) -> List[ProjectConfig]:
        """Parse project configurations."""
        projects = []
        
        # Handle new multi-project format
        if "projects" in config_data:
            for project_id, project_data in config_data["projects"].items():
                project_config = self._parse_project_config(project_id, project_data, global_config)
                projects.append(project_config)
        
        # Handle legacy format
        if "sources" in config_data and "projects" not in config_data:
            default_project = self._create_default_project(config_data["sources"], global_config)
            projects.append(default_project)
        
        return projects
    
    def _parse_project_config(self, project_id: str, project_data: Dict[str, Any], global_config: GlobalConfig) -> ProjectConfig:
        """Parse individual project configuration."""
        # Merge project-specific overrides with global config
        merged_config = self._merge_configs(global_config, project_data)
        
        return ProjectConfig(
            project_id=project_id,
            display_name=project_data.get("display_name", project_id),
            description=project_data.get("description"),
            collection_name=self._determine_collection_name(project_id, project_data, global_config),
            sources=self._parse_sources(project_data.get("sources", {})),
            config_overrides=merged_config
        )
```

### State Management

#### Project-Aware State Manager

```python
class ProjectStateManager:
    """Manages state for project-specific operations."""
    
    def __init__(self, project_id: str, source_type: str, source_name: str):
        self.project_id = project_id
        self.source_type = source_type
        self.source_name = source_name
        self.db_manager = DatabaseManager()
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get last sync time for this project source."""
        return self.db_manager.execute_query(
            "SELECT last_sync_time FROM project_sources WHERE project_id = ? AND source_type = ? AND source_name = ?",
            (self.project_id, self.source_type, self.source_name)
        ).fetchone()
    
    def update_sync_status(self, status: str, error_message: Optional[str] = None):
        """Update sync status for this project source."""
        self.db_manager.execute_query(
            """UPDATE project_sources 
               SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE project_id = ? AND source_type = ? AND source_name = ?""",
            (status, error_message, self.project_id, self.source_type, self.source_name)
        )
    
    def get_processed_documents(self) -> List[str]:
        """Get list of processed document IDs for this project."""
        return self.db_manager.execute_query(
            "SELECT document_id FROM documents WHERE project_id = ?",
            (self.project_id,)
        ).fetchall()
```

## 🔄 Data Flow

### Ingestion Data Flow

```
1. Configuration Loading
   ├── Parse config.yaml
   ├── Detect legacy vs multi-project format
   ├── Validate project configurations
   └── Create project contexts

2. Project Discovery
   ├── Project Manager discovers all projects
   ├── Validate each project configuration
   ├── Create project-specific state managers
   └── Initialize project metadata

3. Connector Initialization
   ├── Create connectors for each project source
   ├── Inject project context into connectors
   ├── Initialize project-specific state tracking
   └── Set up error handling per project

4. Document Processing
   ├── Fetch documents from each source
   ├── Inject project metadata into documents
   ├── Process documents with project-specific settings
   └── Store documents with project context

5. Storage Operations
   ├── Store documents in QDrant with project metadata
   ├── Update project-specific state in database
   ├── Track processing statistics per project
   └── Handle errors with project context
```

### Search Data Flow

```
1. Search Request
   ├── Parse search parameters
   ├── Extract project filtering criteria
   ├── Validate project access permissions
   └── Prepare search context

2. Query Construction
   ├── Build base semantic search query
   ├── Add project filtering conditions
   ├── Apply source type filters if specified
   └── Set result limits and pagination

3. QDrant Query Execution
   ├── Execute vector search with filters
   ├── Apply project-based filtering
   ├── Retrieve matching documents
   └── Score and rank results

4. Result Processing
   ├── Inject project context into results
   ├── Format results with project information
   ├── Apply additional filtering if needed
   └── Prepare response with metadata

5. Response Delivery
   ├── Include project context in each result
   ├── Provide project statistics if requested
   ├── Format response according to API specification
   └── Return results to client
```

## 🗄️ Database Design

### Entity Relationship Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Projects     │    │ Project_Sources │    │   Documents     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (PK)         │◄──┤ project_id (FK) │    │ id (PK)         │
│ display_name    │    │ source_type     │    │ project_id (FK) │◄─┐
│ description     │    │ source_name     │    │ content         │  │
│ collection_name │    │ config_hash     │    │ metadata        │  │
│ config_hash     │    │ last_sync_time  │    │ created_at      │  │
│ created_at      │    │ status          │    │ updated_at      │  │
│ updated_at      │    │ error_message   │    └─────────────────┘  │
└─────────────────┘    │ created_at      │                        │
                       │ updated_at      │                        │
                       └─────────────────┘                        │
                                                                  │
┌─────────────────┐                                              │
│ Document_Chunks │                                              │
├─────────────────┤                                              │
│ id (PK)         │                                              │
│ document_id (FK)│──────────────────────────────────────────────┘
│ project_id (FK) │
│ chunk_index     │
│ content         │
│ embedding       │
│ metadata        │
│ created_at      │
└─────────────────┘
```

### Database Schema Details

#### Projects Table

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,                    -- Project identifier (e.g., 'project-alpha')
    display_name TEXT NOT NULL,             -- Human-readable name
    description TEXT,                       -- Project description
    collection_name TEXT,                   -- QDrant collection name
    config_hash TEXT,                       -- Hash of project configuration for change detection
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(collection_name)                 -- Ensure unique collection names
);

-- Indexes for efficient queries
CREATE INDEX idx_projects_collection_name ON projects(collection_name);
```

#### Project Sources Table

```sql
CREATE TABLE project_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,               -- Reference to projects.id
    source_type TEXT NOT NULL,              -- 'git', 'confluence', 'jira', etc.
    source_name TEXT NOT NULL,              -- Source identifier within project
    config_hash TEXT,                       -- Hash of source configuration
    last_sync_time TIMESTAMP,               -- Last successful synchronization
    status TEXT DEFAULT 'pending',          -- 'pending', 'syncing', 'completed', 'error'
    error_message TEXT,                     -- Last error message if any
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, source_type, source_name)  -- Unique source per project
);

-- Indexes for efficient queries
CREATE INDEX idx_project_sources_project_id ON project_sources(project_id);
CREATE INDEX idx_project_sources_status ON project_sources(status);
```

#### Enhanced Documents Table

```sql
-- Add project_id column to existing documents table
ALTER TABLE documents ADD COLUMN project_id TEXT;

-- Add foreign key constraint (for new installations)
-- For existing installations, this will be added during migration
-- ALTER TABLE documents ADD FOREIGN KEY (project_id) REFERENCES projects(id);

-- Add index for efficient project filtering
CREATE INDEX idx_documents_project_id ON documents(project_id);

-- Composite index for common queries
CREATE INDEX idx_documents_project_source ON documents(project_id, source_type);
```

#### Enhanced Document Chunks Table

```sql
-- Add project_id column to existing document_chunks table
ALTER TABLE document_chunks ADD COLUMN project_id TEXT;

-- Add index for efficient project filtering
CREATE INDEX idx_document_chunks_project_id ON document_chunks(project_id);

-- Composite index for common queries
CREATE INDEX idx_document_chunks_project_document ON document_chunks(project_id, document_id);
```

### Migration Strategy

#### Schema Migration Scripts

```python
class DatabaseMigration:
    """Handles database schema migrations for multi-project support."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
    
    def migrate_to_multi_project(self):
        """Migrate existing database to multi-project schema."""
        try:
            # Step 1: Create new tables
            self._create_projects_table()
            self._create_project_sources_table()
            
            # Step 2: Add project_id columns to existing tables
            self._add_project_id_columns()
            
            # Step 3: Create default project for existing data
            self._create_default_project()
            
            # Step 4: Migrate existing data
            self._migrate_existing_documents()
            self._migrate_existing_state()
            
            # Step 5: Create indexes
            self._create_indexes()
            
            # Step 6: Validate migration
            self._validate_migration()
            
        except Exception as e:
            self.connection.rollback()
            raise MigrationError(f"Migration failed: {e}")
        else:
            self.connection.commit()
    
    def _create_default_project(self):
        """Create default project for existing data."""
        self.connection.execute("""
            INSERT INTO projects (id, display_name, description, collection_name)
            VALUES ('default', 'Default Project', 'Migrated from legacy configuration', 'documents')
        """)
    
    def _migrate_existing_documents(self):
        """Assign existing documents to default project."""
        self.connection.execute("""
            UPDATE documents SET project_id = 'default' WHERE project_id IS NULL
        """)
        
        self.connection.execute("""
            UPDATE document_chunks SET project_id = 'default' WHERE project_id IS NULL
        """)
```

## 🔌 API Design

### MCP Server API Extensions

#### Enhanced Search Tools

```python
class ProjectAwareSearchTool:
    """Enhanced search tool with project filtering."""
    
    def search(self, query: str, project_ids: Optional[List[str]] = None, 
               source_types: Optional[List[str]] = None, limit: int = 10) -> SearchResults:
        """
        Search with optional project filtering.
        
        Args:
            query: Search query string
            project_ids: Optional list of project IDs to filter by
            source_types: Optional list of source types to filter by
            limit: Maximum number of results to return
            
        Returns:
            SearchResults with project context included
        """
        # Build QDrant filter conditions
        filter_conditions = []
        
        if project_ids:
            filter_conditions.append(
                models.FieldCondition(
                    key="project_id",
                    match=models.MatchAny(any=project_ids)
                )
            )
        
        if source_types:
            filter_conditions.append(
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchAny(any=source_types)
                )
            )
        
        # Execute search with filters
        results = self.search_engine.search(
            query=query,
            filters=filter_conditions,
            limit=limit
        )
        
        # Enhance results with project context
        enhanced_results = []
        for result in results:
            enhanced_result = self._enhance_with_project_context(result)
            enhanced_results.append(enhanced_result)
        
        return SearchResults(results=enhanced_results)
    
    def _enhance_with_project_context(self, result: SearchResult) -> SearchResult:
        """Add project context to search result."""
        project_id = result.metadata.get("project_id")
        if project_id:
            project_context = self.project_manager.get_project_context(project_id)
            if project_context:
                result.metadata.update({
                    "project_name": project_context.display_name,
                    "project_context": f"Project: {project_context.display_name}"
                })
        return result
```

#### Project Management Tools

```python
class ProjectManagementTool:
    """Tool for managing projects through MCP server."""
    
    def list_projects(self) -> ProjectListResponse:
        """List all configured projects with statistics."""
        projects = []
        
        for project_context in self.project_manager.get_all_projects():
            project_info = ProjectInfo(
                id=project_context.project_id,
                display_name=project_context.display_name,
                description=project_context.description,
                collection_name=project_context.collection_name,
                source_count=self._get_source_count(project_context.project_id),
                document_count=self._get_document_count(project_context.project_id),
                last_updated=self._get_last_updated(project_context.project_id)
            )
            projects.append(project_info)
        
        return ProjectListResponse(projects=projects)
    
    def get_project_info(self, project_id: str) -> ProjectDetailResponse:
        """Get detailed information about a specific project."""
        project_context = self.project_manager.get_project_context(project_id)
        if not project_context:
            raise ProjectNotFoundError(f"Project '{project_id}' not found")
        
        # Get project sources and their status
        sources = self._get_project_sources(project_id)
        
        # Get project statistics
        statistics = self._get_project_statistics(project_id)
        
        return ProjectDetailResponse(
            project=ProjectDetail(
                id=project_context.project_id,
                display_name=project_context.display_name,
                description=project_context.description,
                collection_name=project_context.collection_name,
                sources=sources,
                statistics=statistics
            )
        )
```

### CLI API Extensions

```python
class ProjectCLI:
    """CLI commands for project management."""
    
    @click.group()
    def projects():
        """Project management commands."""
        pass
    
    @projects.command()
    def list():
        """List all configured projects."""
        project_manager = get_project_manager()
        projects = project_manager.get_all_projects()
        
        table = Table(title="Configured Projects")
        table.add_column("Project ID", style="cyan")
        table.add_column("Display Name", style="green")
        table.add_column("Sources", justify="right")
        table.add_column("Documents", justify="right")
        table.add_column("Status", style="yellow")
        
        for project in projects:
            status = get_project_status(project.project_id)
            table.add_row(
                project.project_id,
                project.display_name,
                str(get_source_count(project.project_id)),
                str(get_document_count(project.project_id)),
                status
            )
        
        console.print(table)
    
    @projects.command()
    @click.option("--project", required=True, help="Project ID")
    def status(project: str):
        """Show detailed status for a specific project."""
        project_manager = get_project_manager()
        project_context = project_manager.get_project_context(project)
        
        if not project_context:
            console.print(f"[red]Project '{project}' not found[/red]")
            return
        
        # Display project information and source status
        display_project_status(project_context)
```

## ⚡ Performance Considerations

### QDrant Query Optimization

#### Efficient Project Filtering

```python
class OptimizedProjectSearch:
    """Optimized search implementation for project filtering."""
    
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant_client = qdrant_client
        self.project_cache = {}  # Cache project metadata
    
    def search_with_project_filter(self, query_vector: List[float], 
                                 project_ids: List[str], 
                                 collection_name: str,
                                 limit: int = 10) -> List[ScoredPoint]:
        """Optimized search with project filtering."""
        
        # Use QDrant's native filtering for best performance
        filter_condition = models.Filter(
            must=[
                models.FieldCondition(
                    key="project_id",
                    match=models.MatchAny(any=project_ids)
                )
            ]
        )
        
        # Execute search with pre-filtering
        search_result = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=filter_condition,
            limit=limit,
            with_payload=True,
            with_vectors=False  # Don't return vectors to save bandwidth
        )
        
        return search_result
    
    def get_project_statistics(self, project_id: str, collection_name: str) -> ProjectStats:
        """Get cached project statistics."""
        cache_key = f"{project_id}:{collection_name}"
        
        if cache_key not in self.project_cache:
            # Count documents for this project
            count_result = self.qdrant_client.count(
                collection_name=collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="project_id",
                            match=models.MatchValue(value=project_id)
                        )
                    ]
                )
            )
            
            self.project_cache[cache_key] = ProjectStats(
                document_count=count_result.count,
                last_updated=datetime.now()
            )
        
        return self.project_cache[cache_key]
```

### Memory Management

#### Project Context Caching

```python
class ProjectContextCache:
    """Efficient caching of project contexts."""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}
    
    def get_project_context(self, project_id: str) -> Optional[ProjectContext]:
        """Get project context with LRU caching."""
        if project_id in self.cache:
            self.access_times[project_id] = time.time()
            return self.cache[project_id]
        
        # Load from configuration if not cached
        project_context = self._load_project_context(project_id)
        if project_context:
            self._add_to_cache(project_id, project_context)
        
        return project_context
    
    def _add_to_cache(self, project_id: str, project_context: ProjectContext):
        """Add project context to cache with LRU eviction."""
        if len(self.cache) >= self.max_size:
            # Evict least recently used item
            lru_project = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.cache[lru_project]
            del self.access_times[lru_project]
        
        self.cache[project_id] = project_context
        self.access_times[project_id] = time.time()
```

### Database Query Optimization

```python
class OptimizedProjectQueries:
    """Optimized database queries for project operations."""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self._prepare_statements()
    
    def _prepare_statements(self):
        """Prepare commonly used SQL statements."""
        self.get_project_documents = self.db.prepare("""
            SELECT id, content, metadata 
            FROM documents 
            WHERE project_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """)
        
        self.get_project_stats = self.db.prepare("""
            SELECT 
                COUNT(*) as document_count,
                MAX(updated_at) as last_updated,
                SUM(LENGTH(content)) as total_size
            FROM documents 
            WHERE project_id = ?
        """)
    
    def get_project_document_count(self, project_id: str) -> int:
        """Get document count for project with prepared statement."""
        result = self.get_project_stats.execute(project_id).fetchone()
        return result[0] if result else 0
```

## 🔒 Security Considerations

### Project Isolation

```python
class ProjectSecurityManager:
    """Manages security and isolation between projects."""
    
    def __init__(self):
        self.project_permissions = {}
    
    def validate_project_access(self, user_context: UserContext, project_id: str) -> bool:
        """Validate user access to specific project."""
        # Implementation depends on authentication system
        # For now, all projects are accessible to all users
        return True
    
    def filter_projects_by_access(self, user_context: UserContext, 
                                projects: List[ProjectContext]) -> List[ProjectContext]:
        """Filter projects based on user access permissions."""
        accessible_projects = []
        
        for project in projects:
            if self.validate_project_access(user_context, project.project_id):
                accessible_projects.append(project)
        
        return accessible_projects
    
    def sanitize_project_data(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize project data before returning to client."""
        # Remove sensitive configuration data
        sanitized = project_data.copy()
        
        # Remove sensitive keys
        sensitive_keys = ["api_keys", "tokens", "passwords", "secrets"]
        for key in sensitive_keys:
            sanitized.pop(key, None)
        
        return sanitized
```

### Configuration Security

```python
class SecureConfigManager:
    """Secure handling of project configurations."""
    
    def __init__(self):
        self.encryption_key = self._get_encryption_key()
    
    def store_sensitive_config(self, project_id: str, config_data: Dict[str, Any]):
        """Store sensitive configuration data securely."""
        # Encrypt sensitive data before storage
        encrypted_data = self._encrypt_config(config_data)
        
        # Store in secure location
        self._store_encrypted_config(project_id, encrypted_data)
    
    def load_sensitive_config(self, project_id: str) -> Dict[str, Any]:
        """Load and decrypt sensitive configuration data."""
        encrypted_data = self._load_encrypted_config(project_id)
        return self._decrypt_config(encrypted_data)
    
    def _encrypt_config(self, config_data: Dict[str, Any]) -> bytes:
        """Encrypt configuration data."""
        # Implementation using cryptography library
        pass
    
    def _decrypt_config(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt configuration data."""
        # Implementation using cryptography library
        pass
```

## 🔧 Extension Points

### Custom Project Types

```python
class ProjectTypeRegistry:
    """Registry for custom project types and behaviors."""
    
    def __init__(self):
        self.project_types = {}
        self.project_handlers = {}
    
    def register_project_type(self, type_name: str, handler_class: Type[ProjectHandler]):
        """Register a custom project type handler."""
        self.project_types[type_name] = handler_class
    
    def create_project_handler(self, project_type: str, project_context: ProjectContext) -> ProjectHandler:
        """Create handler for specific project type."""
        handler_class = self.project_types.get(project_type, DefaultProjectHandler)
        return handler_class(project_context)

class ProjectHandler(ABC):
    """Abstract base class for project-specific handlers."""
    
    def __init__(self, project_context: ProjectContext):
        self.project_context = project_context
    
    @abstractmethod
    def process_document(self, document: Document) -> Document:
        """Process document with project-specific logic."""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate project-specific configuration."""
        pass
```

### Custom Metadata Processors

```python
class MetadataProcessorRegistry:
    """Registry for custom metadata processors."""
    
    def __init__(self):
        self.processors = []
    
    def register_processor(self, processor: MetadataProcessor):
        """Register a custom metadata processor."""
        self.processors.append(processor)
    
    def process_metadata(self, document: Document, project_context: ProjectContext) -> Document:
        """Apply all registered metadata processors."""
        for processor in self.processors:
            document = processor.process(document, project_context)
        return document

class MetadataProcessor(ABC):
    """Abstract base class for metadata processors."""
    
    @abstractmethod
    def process(self, document: Document, project_context: ProjectContext) -> Document:
        """Process document metadata."""
        pass

# Example custom processor
class TimestampMetadataProcessor(MetadataProcessor):
    """Adds timestamp metadata to documents."""
    
    def process(self, document: Document, project_context: ProjectContext) -> Document:
        document.metadata["processed_at"] = datetime.now().isoformat()
        document.metadata["processor_version"] = "1.0.0"
        return document
```

### Plugin System

```python
class ProjectPluginManager:
    """Manages plugins for project-specific functionality."""
    
    def __init__(self):
        self.plugins = {}
        self.hooks = defaultdict(list)
    
    def register_plugin(self, plugin: ProjectPlugin):
        """Register a project plugin."""
        self.plugins[plugin.name] = plugin
        
        # Register plugin hooks
        for hook_name, callback in plugin.get_hooks().items():
            self.hooks[hook_name].append(callback)
    
    def execute_hook(self, hook_name: str, *args, **kwargs):
        """Execute all callbacks for a specific hook."""
        results = []
        for callback in self.hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Plugin hook '{hook_name}' failed: {e}")
        return results

class ProjectPlugin(ABC):
    """Abstract base class for project plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass
    
    @abstractmethod
    def get_hooks(self) -> Dict[str, Callable]:
        """Return dictionary of hook names to callback functions."""
        pass
```

---

This architecture document provides a comprehensive technical foundation for implementing multi-project support in QDrant Loader. The design emphasizes modularity, performance, and extensibility while maintaining backward compatibility with existing installations.
