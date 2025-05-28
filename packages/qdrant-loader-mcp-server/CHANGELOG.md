# Changelog

All notable changes to the qdrant-loader-mcp-server package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0b1] - 2024-12-XX

### Added

- **Local File Support**: Added support for searching local files through the new localfile connector
- Enhanced source type filtering to include localfile alongside git, confluence, jira, and documentation
- Improved query processing with localfile-specific keyword detection
- Updated MCP tool definition to include localfile in source_types enum

### Changed

- Moved to monorepo structure under `packages/qdrant-loader-mcp-server/`
- Updated license from GPL-3.0 to Apache-2.0
- Improved project structure and organization
- Added dependency on qdrant-loader package for shared functionality
- **BREAKING**: Implemented unified versioning with qdrant-loader package
- Enhanced release process with comprehensive safety checks and dry-run capabilities

## [0.1.0] - 2024-01-XX

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
