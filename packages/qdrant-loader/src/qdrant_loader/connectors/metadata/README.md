# Metadata Extraction Framework

This directory contains the metadata extraction framework for enriching knowledge graphs with relationship data.

## Architecture Overview

### Core Framework
- **`base.py`**: Abstract base classes and configuration for metadata extraction
- **`schemas.py`**: Pydantic models for standardized metadata structures

### Extractors
- **`git_relationship_extractor.py`**: Specialized extractor for Git relationship metadata
  - Focuses on author relationships, file hierarchies, cross-references
  - Used internally by the main Git connector's metadata extractor
  - Implements the BaseMetadataExtractor interface

## Integration with Existing Connectors

The framework is designed to integrate with existing connectors without breaking changes:

### Git Connector Integration
- **Main extractor**: `connectors/git/metadata_extractor.py` (GitMetadataExtractor)
  - Provides all legacy metadata extraction functionality
  - Optionally uses GitRelationshipExtractor for enhanced metadata
  - Maintains full backward compatibility
  
- **Relationship extractor**: `metadata/git_relationship_extractor.py` (GitRelationshipExtractor)
  - Specialized for knowledge graph relationship extraction
  - Used internally by GitMetadataExtractor when enhanced metadata is enabled
  - Not directly used by connector code

## Usage

The framework is designed to be used internally by existing connectors. Users should continue to use the main connector classes (e.g., GitMetadataExtractor) which will automatically leverage the enhanced metadata capabilities when enabled.

## Future Extensibility

This framework can be extended for other data sources:
- Confluence relationship extraction
- JIRA issue relationship mapping
- Custom data source metadata extraction

Each new extractor should inherit from `BaseMetadataExtractor` and implement the required methods. 