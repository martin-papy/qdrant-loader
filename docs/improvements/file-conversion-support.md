# File Conversion Support Implementation Plan

## Overview

This document outlines the implementation plan for adding support for PDF, Excel, PowerPoint, Word, and other file formats to the qdrant-loader ingestion process. The approach involves creating a preprocessing layer that converts files to Markdown format using Microsoft's MarkItDown tool, then leveraging the existing markdown chunking strategy for processing.

## Architecture Overview

### Current State

- qdrant-loader supports multiple source types: git, confluence, jira, publicdocs, localfile
- Each source type has dedicated connectors
- Documents are processed through chunking strategies (markdown, html, etc.)
- State management tracks document ingestion and changes

### Target State

- Add file conversion preprocessing layer before chunking
- Support parent-child relationships for documents with attachments
- Extend state management to track attachment metadata
- Configure file conversion per connector with global settings

## Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 File Conversion Service

**Location**: `packages/qdrant-loader/src/qdrant_loader/core/file_conversion/`

**Components**:

- `file_converter.py` - Main conversion service using MarkItDown
- `file_detector.py` - MIME type and extension-based file type detection
- `conversion_config.py` - Configuration models for file conversion
- `exceptions.py` - Custom exceptions for conversion failures

**Key Features**:

- MIME type detection with file extension fallback
- Integration with MarkItDown for file-to-markdown conversion
- Graceful error handling with fallback to minimal document creation
- Support for all MarkItDown-supported formats
- File size validation and limits

#### 1.2 Document Model Extensions

**Location**: `packages/qdrant-loader/src/qdrant_loader/core/document.py`

**Changes**:

- Add `parent_document_id` field to support attachment relationships
- Add `attachment_metadata` field for file-specific information
- Add `is_attachment` boolean field
- Add `original_file_type` field to track source format
- Add `conversion_method` field to track how file was processed

#### 1.3 State Management Extensions

**Location**: `packages/qdrant-loader/src/qdrant_loader/core/state/`

**Changes to `state_manager.py`**:

- Add attachment-specific metadata tracking (file_size, last_modified_date, file_hash)
- Extend `DocumentStateRecord` model to include attachment fields
- Add methods for querying parent-child document relationships
- Add attachment change detection capabilities

**New Model Fields**:

```python
# Add to DocumentStateRecord
file_size: Optional[int] = None
file_last_modified: Optional[datetime] = None
file_hash: Optional[str] = None
parent_document_id: Optional[str] = None
is_attachment: bool = False
original_file_type: Optional[str] = None
```

### Phase 2: Configuration System

#### 2.1 Global Configuration

**Location**: Configuration files (`config.yaml`, `config.template.yaml`, `tests/config.test.yaml`)

**New Global Section**:

```yaml
global:
  # ... existing configuration ...
  
  # File conversion configuration
  file_conversion:
    # Maximum file size for conversion (in bytes)
    max_file_size: 52428800  # 50MB
    
    # Timeout for conversion operations (in seconds)
    conversion_timeout: 300  # 5 minutes
    
    # MarkItDown specific settings
    markitdown:
      # Enable LLM integration for image descriptions
      enable_llm_descriptions: false
      # LLM model for image descriptions (when enabled)
      llm_model: "gpt-4o"
      # LLM endpoint (when enabled)
      llm_endpoint: "https://api.openai.com/v1"
```

#### 2.2 Per-Connector Configuration

**Changes to each source type**:

```yaml
sources:
  git:
    example_repo:
      # ... existing configuration ...
      # Enable file conversion for this connector
      enable_file_conversion: true
      
  confluence:
    example_space:
      # ... existing configuration ...
      # Enable file conversion for this connector
      enable_file_conversion: true
      # Download and process attachments
      download_attachments: true
      
  jira:
    example_project:
      # ... existing configuration ...
      # Enable file conversion for this connector
      enable_file_conversion: true
      # Download and process attachments
      download_attachments: true
      
  publicdocs:
    example_docs:
      # ... existing configuration ...
      # Enable file conversion for this connector
      enable_file_conversion: true
      # Download and process attachments
      download_attachments: true
      
  localfile:
    example_files:
      # ... existing configuration ...
      # Enable file conversion for this connector
      enable_file_conversion: true
```

### Phase 3: Connector Extensions

#### 3.1 File Download Capability

**Locations**:

- `packages/qdrant-loader/src/qdrant_loader/connectors/confluence/`
- `packages/qdrant-loader/src/qdrant_loader/connectors/jira/`
- `packages/qdrant-loader/src/qdrant_loader/connectors/publicdocs/`

**New Components**:

- `attachment_downloader.py` - Generic attachment download service
- Integration with existing connector APIs to detect and download attachments
- Temporary file management for downloaded attachments

**Key Features**:

- Download attachments to temporary storage
- Extract attachment metadata (size, modification date, etc.)
- Create parent-child document relationships
- Clean up temporary files after processing

#### 3.2 Git Connector Extensions

**Location**: `packages/qdrant-loader/src/qdrant_loader/connectors/git/`

**Changes**:

- Detect supported file types in repositories
- Apply file conversion when `enable_file_conversion: true`
- Maintain existing file type filtering logic
- Skip conversion for files already handled by specific strategies (e.g., HTML, Markdown)

#### 3.3 Local File Connector Extensions

**Location**: `packages/qdrant-loader/src/qdrant_loader/connectors/localfile/`

**Changes**:

- Detect supported file types in local directories
- Apply file conversion when `enable_file_conversion: true`
- Maintain existing file type filtering logic

### Phase 4: Integration Layer

#### 4.1 Preprocessing Pipeline

**Location**: `packages/qdrant-loader/src/qdrant_loader/core/pipeline/`

**New Component**: `file_conversion_processor.py`

**Integration Points**:

- Hook into existing ingestion pipeline before chunking
- Determine if file needs conversion based on:
  - Connector configuration (`enable_file_conversion`)
  - File type detection
  - Existing strategy availability
- Convert files to markdown using MarkItDown
- Pass converted content to markdown chunking strategy

#### 4.2 Chunking Strategy Selection

**Location**: `packages/qdrant-loader/src/qdrant_loader/core/chunking/`

**Logic Updates**:

```python
def select_chunking_strategy(document: Document, config: Settings):
    # Existing logic for HTML, Markdown, etc.
    if document.content_type == "text/html":
        return HTMLChunkingStrategy(config)
    elif document.content_type == "text/markdown":
        return MarkdownChunkingStrategy(config)
    
    # New logic for converted files
    elif document.metadata.get("conversion_method") == "markitdown":
        # Use markdown strategy for converted files
        return MarkdownChunkingStrategy(config)
    
    # Fallback to base strategy
    return BaseChunkingStrategy(config)
```

### Phase 5: Error Handling and Fallbacks

#### 5.1 Conversion Failure Handling

**Strategies**:

1. **Log Warning**: Record conversion failure in logs
2. **Minimal Document Creation**: Create document with filename and basic metadata
3. **State Tracking**: Mark conversion failures in state management
4. **Continue Processing**: Don't fail entire ingestion for single file failures

#### 5.2 Fallback Document Structure

```python
# When conversion fails, create minimal document
fallback_document = Document(
    content=f"# {filename}\n\nFile type: {file_type}\nSize: {file_size} bytes\nConversion failed: {error_message}",
    metadata={
        "original_filename": filename,
        "file_type": file_type,
        "file_size": file_size,
        "conversion_failed": True,
        "conversion_error": error_message,
        "is_attachment": is_attachment,
        "parent_document_id": parent_document_id
    },
    # ... other fields
)
```

### Phase 6: Dependencies and Installation

#### 6.1 MarkItDown Integration

**Location**: `packages/qdrant-loader/pyproject.toml`

**Changes**:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "markitdown>=0.1.2",
]

# Optional dependencies for MarkItDown features
[project.optional-dependencies]
markitdown-full = [
    "markitdown[all]>=0.1.2",
]
```

#### 6.2 Supported File Types

**Auto-detection from MarkItDown capabilities**:

- PDF files
- Microsoft Office documents (Word, Excel, PowerPoint)
- Images (with OCR and metadata extraction)
- Audio files (with transcription)
- EPUB files
- ZIP archives
- And other formats supported by MarkItDown

**Exclusions**:

- HTML files (use existing HTML strategy)
- Markdown files (use existing Markdown strategy)
- Plain text files (use existing base strategy)

### Phase 7: Testing Strategy

#### 7.1 Unit Tests

**Locations**: `packages/qdrant-loader/tests/`

**Test Coverage**:

- File type detection (MIME type and extension)
- MarkItDown integration and conversion
- Error handling and fallbacks
- Configuration parsing and validation
- State management extensions
- Parent-child document relationships

#### 7.2 Integration Tests

**Test Scenarios**:

- End-to-end file conversion and ingestion
- Attachment download and processing
- Connector-specific file conversion
- Large file handling and timeouts
- Conversion failure scenarios

#### 7.3 Test Data

**Required Test Files**:

- Sample PDF, DOCX, XLSX, PPTX files
- Corrupted files for error testing
- Large files for size limit testing
- Files with various encodings and formats

### Phase 8: Documentation and Migration

#### 8.1 Configuration Documentation

**Updates to**:

- `README.md` - Add file conversion capabilities overview
- Configuration examples and best practices
- Troubleshooting guide for conversion issues

#### 8.2 Migration Guide

**For Existing Users**:

- File conversion is disabled by default
- How to enable file conversion per connector
- Performance considerations for large file processing
- Storage requirements for temporary files

## Implementation Timeline

### Week 1-2: Core Infrastructure

- Implement file conversion service
- Extend document model
- Update state management

### Week 3: Configuration System

- Add global and per-connector configuration
- Update all configuration files
- Implement configuration validation

### Week 4-5: Connector Extensions

- Add download capabilities to Confluence/JIRA/PublicDocs
- Extend Git and LocalFile connectors
- Implement attachment handling

### Week 6: Integration and Testing

- Integrate preprocessing pipeline
- Implement chunking strategy selection
- Add comprehensive test coverage

### Week 7: Documentation and Polish

- Update documentation
- Performance optimization
- Error handling refinement

## Risk Mitigation

### Performance Risks

- **Large File Processing**: Implement file size limits and timeouts
- **Memory Usage**: Use streaming for large file conversions
- **Conversion Speed**: Parallel processing where possible

### Reliability Risks

- **Conversion Failures**: Comprehensive error handling and fallbacks
- **Dependency Issues**: Pin MarkItDown version and test thoroughly
- **Storage Issues**: Proper temporary file cleanup

### Compatibility Risks

- **Existing Workflows**: File conversion disabled by default
- **Configuration Changes**: Backward compatible configuration
- **API Changes**: Maintain existing connector interfaces

## Success Metrics

### Functional Metrics

- Support for all MarkItDown file formats
- Successful parent-child document relationships
- Proper attachment change detection
- Zero breaking changes to existing functionality

### Performance Metrics

- File conversion time < 30 seconds for typical documents
- Memory usage increase < 20% during conversion
- No significant impact on non-converted document processing

### Quality Metrics

- Test coverage > 90% for new components
- Zero critical bugs in file conversion pipeline
- Comprehensive error handling and logging

## Future Enhancements

### Phase 2 Features (Future)

- **Caching Layer**: Persistent file conversion cache
- **Advanced OCR**: Enhanced image and PDF text extraction
- **Custom Converters**: Plugin system for custom file types
- **Batch Processing**: Optimized bulk file conversion
- **Cloud Storage**: Direct integration with cloud file storage

### Monitoring and Analytics

- Conversion success/failure rates
- Processing time metrics
- File type distribution analytics
- Storage usage tracking
