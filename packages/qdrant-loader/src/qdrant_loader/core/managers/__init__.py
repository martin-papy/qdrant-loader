"""Manager classes for QDrant Loader core functionality.

This package contains manager classes that handle different aspects of the system:
- GraphitiManager: Manages Graphiti knowledge graph operations
- IDMappingManager: Handles cross-database ID mapping between QDrant and Neo4j
- Neo4jManager: Manages Neo4j database operations and connections
- ProjectManager: Handles project configuration and context management
- QdrantManager: Manages QDrant vector database operations
- TemporalManager: Manages temporal knowledge and conflict resolution
"""

# Core manager classes
from .graphiti_manager import GraphitiManager
from .id_mapping_manager import (
    IDMapping,
    IDMappingManager,
    MappingStatus,
    MappingType,
)
from .neo4j_manager import Neo4jManager
from .project_manager import (
    ProjectContext,
    ProjectManager,
)
from .qdrant_manager import (
    QdrantConnectionError,
    QdrantManager,
)
from .temporal_manager import (
    ConflictInfo,
    ConflictResolutionStrategy,
    TemporalManager,
    TemporalQuery,
)

# Export all manager classes and related types
__all__ = [
    # Core managers
    "GraphitiManager",
    "IDMappingManager",
    "Neo4jManager",
    "ProjectManager",
    "QdrantManager",
    "TemporalManager",
    # ID Mapping related
    "IDMapping",
    "MappingStatus",
    "MappingType",
    # Project management related
    "ProjectContext",
    # QDrant related
    "QdrantConnectionError",
    # Temporal management related
    "ConflictInfo",
    "ConflictResolutionStrategy",
    "TemporalQuery",
]
