# Changelog

All notable changes to the qdrant-loader package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Moved to monorepo structure under `packages/qdrant-loader/`
- Updated license from GPL-3.0 to Apache-2.0
- Improved project structure and organization
- **BREAKING**: Implemented unified versioning across all packages in the monorepo
- Enhanced release process with comprehensive safety checks and dry-run capabilities

## [0.2.0b2] - 2024-01-XX

### Added

- Multiple data source connectors (Git, Confluence, Jira, Public Docs)
- Intelligent document processing and chunking
- Vector embeddings with OpenAI
- Incremental updates and change detection
- Performance monitoring and optimization
- State management for incremental ingestion
- Configurable through environment variables and YAML configuration
- Command-line interface for easy operation
- Comprehensive logging and debugging capabilities

### Features

- **Git Connector**: Ingest code and documentation from Git repositories
- **Confluence Connector**: Extract technical documentation from Confluence spaces
- **JIRA Connector**: Collect technical specifications and documentation from JIRA issues
- **Public Documentation Connector**: Ingest public technical documentation from websites
- **Local File Connector**: Ingest files from local directories (docs, code, markdown, etc.)
- **Custom Sources**: Extensible architecture for adding new data sources

### Technical Requirements

- Python 3.12 or higher
- QDrant server (local or cloud instance)
- OpenAI API key (if using OpenAI, but you can use a local embedding if you like)
- Sufficient disk space for the vector database
- Internet connection for API access
- Access to local files for localfile connector
