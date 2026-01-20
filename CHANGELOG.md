# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.5] - 2026-01-20

### Fixed

#### Qdrant-loader-mcp-server

- Mixed document types (dict/object) causing "Untitled" and empty `content_preview` in results [#92]
- Incorrect usage of NestedCondition for `project_ids` filter replaced with dot notation [#97]
- Search results not respecting user-specified `limit` parameter (now defaults to 5) [#98]

### Added

#### Qdrant-loader-mcp-server

- Optional `similarity_threshold` parameter (default 0.7) to `find_similar_documents` for filtering by minimum similarity score [#91]
- Separate `fetch_limit` from user `limit` with configurable defaults for better control [#98]

### Changed

#### Qdrant-loader-mcp-server

- Updated `reason` field from `explanation` to `recommendation_reason` in complementary content results [#100]
- Enhanced validation for text field types to prevent display issues [#92]

## [0.7.4] - 2025-12-11

### Fixed

#### Qdrant-loader

- Windows asyncio event loop crashes with signal handling and stdio support [#76]
- --log-level CLI option not working after logging initialization [#63]
- Missing prometheus-client dependency causing import errors [#75]
- Deprecated langchain.text_splitter import warnings [#76]

#### Qdrant-loader-mcp-server

- Missing Spacy dependency causing Cursor MCP crash on startup [#82]
- MCP Search API compatibility issues with qdrant-client 1.16 [#78]

### Added

#### Qdrant-loader

- Test suite cross-platform support [#76]

## [0.7.3] - 2025-09-11

### Fixed

#### Qdrant-loader

- Logging duplication where CLI commands printed each log message 2-4 times [#56]

### Changed

#### Qdrant-loader-core

- Unified logging architecture with centralized configuration across all packages [#56]
- Idempotent setup with new `reconfigure()` method [#56]

## [0.7.2] - 2025-09-05

### Changed

- Internal inter-package dependencies now pinned to unified release version [#54]
- Enhanced dry-run output to preview internal dependency pin changes [#54]
- Enforced explicit release order: bump → update classifiers → pin deps → commit → tag → release [#54]
- Updated commit messages to reflect classifier and internal dependency updates [#54]

## [0.7.1] - 2025-09-04

### Added

#### Qdrant-loader-core

- Azure OpenAI support with robust endpoint handling (BETA) [#52]
- Ollama endpoint handling [#52]
- Unified `global.llm.*` configuration for provider-agnostic setup [#52]
- Structured logging for LLM requests (provider, operation, model, latency) [#52]
- Secret redaction in logs [#52]
- Normalized exception mapping across providers [#52]

### Changed

#### Qdrant-loader-core

- Vector size now read from config instead of hardcoded `1536` defaults [#52]
- Centralized LLM layer with provider adapters [#52]
- Direct OpenAI imports removed from application code [#52]
- Tests and documentation updated for provider-agnostic architecture [#52]

#### Qdrant-loader-mcp-server

- MCP server prefers config file loading with CLI/env/file precedence [#53]

### Deprecated

#### Qdrant-loader-core

- Legacy fields `global.embedding.*` and `file_conversion.markitdown.*` (deprecation warnings shown) [#52]

### Security

#### Qdrant-loader-mcp-server

- Redacted `--print-config` for MCP server [#53]

## [0.6.1] - 2025-08-13

### Fixed

#### Qdrant-loader-mcp-server

- Timeout and error issues in `detect_document_conflicts` tool (achieved P95 latency 8-10s) [#45]
- AttributeError in conflict formatter: `'dict' object has no attribute 'document_id'` [#45]

### Added

#### Qdrant-loader-mcp-server

- Tiered analysis with intelligent document pair prioritization [#45]
- Parallel processing with concurrent Qdrant vector retrieval [#45]
- 8 configuration options for conflict detection performance tuning [#45]
- Detailed performance statistics in tool responses [#45]
- Optional per-call parameter overrides for conflict detection [#45]

### Changed

#### Qdrant-loader-mcp-server

- Strict budgeting for expensive LLM calls (default 2 pairs) [#45]
- Graceful degradation with partial results instead of hard failures [#45]
- Tool schema enhanced with performance parameters [#45]
- Error handling for malformed document data [#45]

## [0.6.0] - 2025-08-12

### Added

#### Qdrant-loader-mcp-server

- FastAPI-based HTTP transport alongside stdio transport [#43]
- Server-Sent Events (SSE) streaming capabilities [#43]
- `--transport` CLI option to choose between stdio and HTTP modes [#43]
- Health check endpoints for production deployment [#43]
- Structured tool output with JSON content [#43]
- Tool behavioral annotations for all 8 tools [#43]
- Protocol version validation with graceful degradation [#43]
- Comprehensive session management for HTTP connections [#43]

### Changed

#### Qdrant-loader-mcp-server

- MCP Protocol upgraded from 2024-11-05 to 2025-06-18 [#43]
- Modular transport layer with clean separation [#43]
- Error handling with improved messages [#43]
- Connection handling performance optimizations [#43]

## [0.5.1] - 2025-07-28

### Changed

#### Qdrant-loader-core

- All chunking strategies refactored into modular components [#39]
- Dedicated classes for document parsing, section splitting, metadata extraction [#39]
- HTML chunking with robust handling for empty content and malformed HTML [#39]
- Code and JSON strategy complete modular redesign [#39]
- Chunk processing with additional metadata fields [#39]
- Configuration templates with new strategy-specific options [#39]

## [0.5.0] - 2025-07-25

### Added

#### Qdrant-loader-mcp-server

- Cross-document intelligence: similarity analysis, clustering, relationship detection [#35]
- Intent-aware adaptive search with AI-powered query understanding [#35]
- Knowledge graph integration with entity relationships [#35]
- Topic-driven search chaining with automatic discovery [#35]
- Dynamic faceted search with real-time generation [#35]
- spaCy integration for advanced NLP processing [#35]

#### Qdrant-loader

- `--force` flag to bypass change detection for complete reprocessing [#35]

### Changed

#### Qdrant-loader-core

- Topic extraction with enhanced LDA modeling [#35]
- Entity recognition with structured conversion [#35]
- Chunking with improved timeout handling [#35]
- Structured logging for semantic analysis [#35]

## [0.4.15] - 2025-07-22

### Fixed

#### Qdrant-loader-core

- Critical chunking inconsistency (all strategies now use character-based `chunk_size`) [#33]

### Changed

#### Qdrant-loader-core

- Markdown strategy refactored into focused components [#33]
- Hierarchical metadata with intelligent section analysis [#33]
- Split level detection based on document structure [#33]
- Boundary detection using tokenizer for word/token boundaries [#33]

### Added

#### Qdrant-loader-core

- Comprehensive integration tests for strategy consistency [#33]

## [0.4.14] - 2025-07-13

### Fixed

#### Qdrant-loader-core

- Regex error in Excel table detection: `bad character range |-\s` [#33]
- Large Excel tables treated as single massive chunks [#33]
- Token limit warnings for large Excel chunks [#33]

### Changed

#### Qdrant-loader-core

- Logical unit management with intelligent splitting at line boundaries [#33]
- Efficient chunking for large Excel files [#33]
- Error handling with better error messages [#33]
- Table structure preservation during chunking [#33]

## [0.4.13] - 2025-07-11

### Added

#### Qdrant-loader-core

- Sheet-aware sectioning for Excel files (split on H2 headers) [#33]
- Table-aware chunking with specialized `_split_excel_sheet_content` method [#33]
- Intelligent content detection based on `original_file_type` metadata [#33]
- 3 test cases for Excel chunking scenarios [#33]

### Changed

#### Qdrant-loader-core

- Excel-to-markdown chunking in MarkdownChunkingStrategy [#33]
- Context-aware splitting with different header level thresholds [#33]
- Metadata tracking with `is_excel_sheet` field [#33]
- Table boundary preservation in chunking [#33]

## [0.4.12] - 2025-07-10

### Fixed

#### Qdrant-loader-core

- Missing chunk overlap in MarkdownChunkingStrategy [#33]

### Added

#### Qdrant-loader-core

- Intelligent overlap calculation using paragraph/sentence boundaries [#33]
- Comprehensive overlap testing [#33]

### Changed

#### Qdrant-loader-core

- Overlap configuration support (0 for no overlap, up to 25% for context) [1f53556]

## [0.4.11] - 2025-07-10

### Fixed

#### Qdrant-loader-core

- File size detection limits for larger documents [6160435]
- MarkdownChunkingStrategy not respecting `chunk_size` configuration [6160435]
- Unique chunk ID generation (chunks had identical IDs causing overwrites) [6160435]

### Added

#### Qdrant-loader-core

- `max_chunks_per_document` configuration parameter [6160435]

### Changed

#### Qdrant-loader-core

- Chunk count management with configurable limits [6160435]
- Error messages with actionable configuration advice [6160435]
- Section limits now dynamic (50% of max_chunks_per_document) [6160435]

### Removed

#### Qdrant-loader-core

- Conflicting `max_document_size` parameter [6160435]

## [0.4.10] - 2025-06-18

### Fixed

#### Qdrant-loader

- Duplicate debug logging with `[DEBUG] [DEBUG]` tags [c72a872]
- Mixed path separators in Windows log output [c72a872]
- .txt file processing when `file_types: []` was empty [c72a872]

#### Qdrant-loader-core

- Windows file URL parsing for LocalFile connector [c72a872]
- Git connector document URL generation with Windows paths [c72a872]

### Changed

#### Qdrant-loader

- Logging verbosity control for third-party libraries [c72a872]
- Emoji handling for Windows console [c72a872]
- SQLite logs now suppressed [c72a872]

#### Qdrant-loader-core

- Path normalization across all connectors [c72a872]
- Timeout handling (threading on Windows, signals on Unix) [c72a872]

### Added

#### Qdrant-loader

- 38 Windows compatibility test cases [c72a872]

## [0.4.9] - 2025-06-18

### Fixed

#### Qdrant-loader-core

- Missing `content_type="md"` field in `_create_deleted_document` method [430cb2a]

## [0.4.8] - 2025-06-17

### Fixed

#### Qdrant-loader-core

- Windows file URL parsing in LocalFile Connector [b60e6e0]
- Git Connector document URL generation with Windows paths [b60e6e0]
- File conversion timeout handling for cross-platform [b60e6e0]
- MarkItDown Windows signal compatibility [b60e6e0]

#### Qdrant-loader

- Console emoji handling for Windows [b60e6e0]
- Duplicate log level display [b60e6e0]

### Added

#### Qdrant-loader

- 38 Windows compatibility test cases [b60e6e0]

## [0.4.7] - 2025-06-09

### Fixed

#### Qdrant-loader

- Upgrade instructions to include `qdrant-loader-mcp-server` package [fecc0dc]

#### Qdrant-loader-core

- Branch display logic to default to 'main' when unknown [fecc0dc]

### Changed

#### Qdrant-loader

- Configuration template with detailed comments [fecc0dc]
- Release script with automatic RELEASE_NOTES.md validation [fecc0dc]

#### Qdrant-loader-core

- Logging in PublicDocsConnector [fecc0dc]

## [0.4.6] - 2025-06-03

### Added

#### Qdrant-loader

- Automatic update notifications when new versions available [3604f92]
- Non-intrusive background version checking [3604f92]

## [0.4.5] - 2025-06-03

### Fixed

#### Qdrant-loader

- Version detection using `importlib.metadata.version()` [#25]

#### Qdrant-loader-core

- Circular imports in config → connectors → config cycle [#25]

### Changed

#### Qdrant-loader

- CLI startup time reduced by 60-67% for basic commands [#24]
  - `--help`: ~6.8s → 2.33s (66% improvement)
  - `--version`: ~6.3s → 2.57s (59% improvement)
- Lazy loading for heavy modules (96-97% import time reduction) [#25]

### Added

#### Qdrant-loader-core

- Warning capture system for Excel file processing [#25]
- Structured logging for openpyxl warnings [#25]
- Smart detection for "Data Validation" and "Conditional Formatting" warnings [#25]
- Summary reporting for unsupported Excel features [#25]

## [0.4.4] - 2025-06-03

### Fixed

#### Qdrant-loader-core

- File conversion initialization with missing `set_file_conversion_config` calls [#21]
- Converted files using wrong chunking strategy [#21]
- NLP processing skipped for converted files [#21]
- MarkdownChunkingStrategy infinite loops with very long words [#21]

#### Qdrant-loader

- ResourceManager cleanup causing workers to exit prematurely [#21]

### Added

#### Qdrant-loader-core

- Safety limits: `MAX_CHUNKS_PER_SECTION = 100` and `MAX_CHUNKS_PER_DOCUMENT = 500` [#21]
- Handling for words longer than `max_size` [#21]
- Comprehensive tests for converted file NLP processing [#21]

### Changed

#### Qdrant-loader-core

- Strategy selection based on conversion status [#21]
- Metadata propagation for converted files [#21]
- `MAX_CHUNKS_TO_PROCESS` increased from 100 to 1000 chunks [#21]
- Large document handling (up to ~1000KB text limit) [#21]

#### Qdrant-loader

- Change detection for incremental updates [#21]
- Signal handling for graceful shutdown [#21]

[0.7.5]: https://github.com/martin-papy/qdrant-loader/compare/v0.7.4...v0.7.5
[0.7.4]: https://github.com/martin-papy/qdrant-loader/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/martin-papy/qdrant-loader/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/martin-papy/qdrant-loader/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/martin-papy/qdrant-loader/compare/v0.6.1...v0.7.1
[0.6.1]: https://github.com/martin-papy/qdrant-loader/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/martin-papy/qdrant-loader/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/martin-papy/qdrant-loader/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.15...v0.5.0
[0.4.15]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.14...v0.4.15
[0.4.14]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.13...v0.4.14
[0.4.13]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.12...v0.4.13
[0.4.12]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.11...v0.4.12
[0.4.11]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.10...v0.4.11
[0.4.10]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.9...v0.4.10
[0.4.9]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.8...v0.4.9
[0.4.8]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.7...v0.4.8
[0.4.7]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.6...v0.4.7
[0.4.6]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.5...v0.4.6
[0.4.5]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/martin-papy/qdrant-loader/compare/v0.4.3...v0.4.4
