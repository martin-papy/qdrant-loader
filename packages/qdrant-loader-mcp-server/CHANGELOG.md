# Changelog

All notable changes to the qdrant-loader-mcp-server package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2025-01-30

### Added

- **Hierarchy-Aware Search**: Enhanced Confluence search with page hierarchy understanding
  - Added hierarchy information to search results (parent/child relationships, breadcrumb paths, depth levels)
  - New `hierarchy_search` tool with advanced filtering capabilities
  - Support for filtering by hierarchy depth, parent pages, root pages, and pages with children
  - Hierarchical organization of search results with tree-like structure display
  - Rich visual indicators for navigation context (📍 paths, 🏗️ hierarchy info, ⬆️ parents, ⬇️ children)

- **Attachment-Aware Search**: Comprehensive file attachment support and parent document relationships
  - Added attachment information to all search results (file metadata, parent document context)
  - New `attachment_search` tool for specialized file discovery and filtering
  - Support for filtering by file type, size, author, and parent document
  - Rich attachment context display (📎 file indicators, 📋 file details, 📄 parent documents)
  - Parent document relationship leveraging for meaningful file search

- **Enhanced Search Result Model**: Extended SearchResult with comprehensive metadata
  - Hierarchy fields: `parent_id`, `parent_title`, `breadcrumb_text`, `depth`, `children_count`, `hierarchy_context`
  - Attachment fields: `is_attachment`, `parent_document_id`, `parent_document_title`, `attachment_id`, `original_filename`, `file_size`, `mime_type`, `attachment_author`, `attachment_context`
  - Convenience methods for hierarchy and attachment operations

- **Advanced Search Tools**: Three specialized search tools for different use cases
  - `search`: Standard semantic search with hierarchy and attachment context
  - `hierarchy_search`: Confluence-specific search with hierarchy filtering and organization
  - `attachment_search`: File-focused search with attachment filtering and parent document context

### Enhanced

- **Search Result Display**: Rich formatting with contextual information
  - Visual hierarchy indicators and breadcrumb navigation
  - File attachment details with size, type, and author information
  - Parent document relationships for both hierarchy and attachments
  - Human-readable file sizes and comprehensive metadata display

- **Hybrid Search Engine**: Enhanced metadata extraction and processing
  - Unified `_extract_metadata_info()` method for hierarchy and attachment data
  - Intelligent context generation for both document structure and file relationships
  - Improved result scoring and relevance ranking

### Use Cases Enabled

- **Content Discovery**: Find documents by hierarchy level, parent relationships, or attached files
- **File Management**: Locate attachments by type, size, author, or parent document
- **Documentation Navigation**: Understand document structure and supporting materials
- **Content Audit**: Analyze file distribution, identify large files, and assess documentation completeness

### Technical Improvements

- Enhanced SearchResult and HybridSearchResult models with comprehensive metadata
- Improved MCP handler with specialized formatting for different search types
- Advanced filtering capabilities for both hierarchy and attachment characteristics
- Backward compatibility maintained with existing search functionality

## [0.3.0b2] - 2025-05-28

### Added

- **Local File Support**: Added support for searching local files through the new localfile connector
- Enhanced source type filtering to include localfile alongside git, confluence, jira, and documentation
- Improved query processing with localfile-specific keyword detection
- Updated MCP tool definition to include localfile in source_types enum

### Changed

- Moved to monorepo structure under `packages/qdrant-loader-mcp-server/`
- Improved project structure and organization
- Added dependency on qdrant-loader package for shared functionality
- **BREAKING**: Implemented unified versioning with qdrant-loader package
- Enhanced release process with comprehensive safety checks and dry-run capabilities

## [0.1.0] - [Unreleased]

### Added

- Model Context Protocol (MCP) server implementation
- RAG capabilities for Cursor and other LLM applications
- Semantic search capabilities using Qdrant vector database
- Real-time query processing
- Integration with Cursor IDE
- RESTful API endpoints
- FastAPI-based web server
- JSON-RPC protocol support
- Structured logging with structlog
- Configuration via environment variables
- Health check endpoints
- Metrics collection support

### Features

- **MCP Protocol**: Full implementation of Model Context Protocol for LLM integration
- **Semantic Search**: Advanced semantic search using vector embeddings
- **Real-time Processing**: Fast query processing and response generation
- **Cursor Integration**: Seamless integration with Cursor IDE
- **API Endpoints**: RESTful API for external integrations
- **Monitoring**: Built-in health checks and metrics

### Technical Requirements

- Python 3.12 or higher
- QDrant server (local or cloud instance)
- OpenAI API key for embeddings
- FastAPI and Uvicorn for web server
- Access to qdrant-loader data sources
