# Metadata Extraction Architecture

## Problem Solved

**Issue**: Having two `GitMetadataExtractor` classes in different locations was confusing and violated clean architecture principles.

**Solution**: Renamed and clarified the roles of each component to create a clear, maintainable architecture.

## Final Architecture

### 1. Main Git Metadata Extractor
**Location**: `src/qdrant_loader/connectors/git/metadata_extractor.py`
**Class**: `GitMetadataExtractor`
**Role**: Primary interface for Git metadata extraction

**Responsibilities**:
- Legacy metadata extraction (file info, repo info, Git history, structure analysis)
- Backward compatibility with all existing code
- Optional integration with enhanced metadata framework
- Single point of entry for Git metadata extraction

**Usage**: This is what existing code should continue to use. No changes required.

### 2. Relationship-Focused Extractor
**Location**: `src/qdrant_loader/connectors/metadata/git_relationship_extractor.py`
**Class**: `GitRelationshipExtractor`
**Role**: Specialized extractor for knowledge graph relationships

**Responsibilities**:
- Author relationship extraction
- File hierarchy mapping
- Cross-reference detection
- Git-specific structural metadata for knowledge graphs
- Implements the `BaseMetadataExtractor` interface

**Usage**: Used internally by `GitMetadataExtractor` when enhanced metadata is enabled. Not directly used by application code.

## Integration Pattern

```python
# GitMetadataExtractor (main class)
class GitMetadataExtractor:
    def __init__(self, config, enable_enhanced_metadata=True):
        # Legacy functionality always available
        self.config = config
        
        # Enhanced metadata is optional
        if enable_enhanced_metadata:
            # Lazy import to avoid circular dependencies
            from ...metadata.git_relationship_extractor import GitRelationshipExtractor
            self._enhanced_extractor = GitRelationshipExtractor(config)
    
    def extract_all_metadata(self, file_path, content):
        # Always extract legacy metadata
        metadata = self._extract_legacy_metadata(file_path, content)
        
        # Optionally add enhanced metadata
        if self._enhanced_extractor:
            enhanced = self._enhanced_extractor.extract_metadata(content, context)
            metadata["enhanced_metadata"] = enhanced
        
        return metadata
```

## Benefits of This Architecture

### 1. **Clear Separation of Concerns**
- `GitMetadataExtractor`: Comprehensive metadata extraction with backward compatibility
- `GitRelationshipExtractor`: Specialized relationship extraction for knowledge graphs

### 2. **No Breaking Changes**
- All existing code continues to work unchanged
- Enhanced features are opt-in via constructor parameter
- Legacy metadata extraction always available

### 3. **Circular Dependency Resolution**
- Lazy imports prevent circular dependency issues
- Clean module boundaries
- Proper dependency hierarchy

### 4. **Extensible Framework**
- `BaseMetadataExtractor` provides interface for other data sources
- Standardized metadata schemas via Pydantic models
- Configurable extraction parameters

### 5. **User-Friendly**
- Single import for users: `GitMetadataExtractor`
- Enhanced features automatically available when enabled
- Clear documentation and naming

## Framework Components

### Core Framework
- **`metadata/base.py`**: Abstract base classes and configuration
- **`metadata/schemas.py`**: Pydantic models for standardized metadata
- **`metadata/README.md`**: Framework documentation

### Specialized Extractors
- **`metadata/git_relationship_extractor.py`**: Git relationship extraction
- Future: `metadata/confluence_relationship_extractor.py`
- Future: `metadata/jira_relationship_extractor.py`

## Migration Guide

**For existing code**: No changes required. Everything continues to work as before.

**For new features**: 
- Use `GitMetadataExtractor` as the main interface
- Enhanced metadata is automatically available under `metadata["enhanced_metadata"]`
- Configure extraction via `MetadataExtractionConfig` if needed

## Testing

All imports work correctly without circular dependencies:
```bash
# Framework components
python -c "from qdrant_loader.connectors.metadata import GitRelationshipExtractor"

# Main extractor
python -c "from qdrant_loader.connectors.git.metadata_extractor import GitMetadataExtractor"

# Git connector (full integration)
python -c "from qdrant_loader.connectors.git import GitConnector"
```

## Future Extensibility

This architecture supports:
- Additional data source extractors (Confluence, JIRA, etc.)
- Custom metadata schemas
- Configurable extraction strategies
- Knowledge graph relationship mapping
- Cross-source relationship detection

The framework is designed to grow with the project's needs while maintaining backward compatibility and clean architecture principles. 