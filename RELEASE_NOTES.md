# Release Notes

## Version 0.7.0 - Sept 03, 2025

### LLM Provider-Agnostic Configuration & Migration

- BETA: Added Azure OpenAI support (no more 404s from misconfigured endpoints) and robust Ollama endpoint handling
- Introduced unified `global.llm.*` configuration controlling provider, `base_url`, models, tokenizer, request policy, rate limits, and `embeddings.vector_size`.
- Legacy fields (`global.embedding.*` and `file_conversion.markitdown.*`) remain supported with deprecation warnings; migration is recommended.
- Vector size is now read from config; hardcoded `1536` defaults replaced with config-driven values and a deprecated fallback warning when unspecified.
- Structured logging added for LLM requests (provider, operation, model, latency; secrets redacted) and normalized exception mapping across providers.
- Documentation updated with the new schema and env vars:
  - Azure logs label provider as `azure_openai`; OpenAI as `openai`; Ollama logs include latency for chat.
  - Clear error when Azure `base_url` includes `/openai/deployments/...`; requires `api_version`.
  - Ollama auto-detects `/v1` vs native. Native tries batch `/api/embed` first, falls back to `/api/embeddings`.
- Documentation updated with the new schema and env vars:
  - Configuration reference: `docs/users/configuration/config-file-reference.md`
  - Environment variables: `docs/users/configuration/environment-variables.md`

### Massive Codebase Refactor

- Centralized LLM layer in `qdrant-loader-core` with provider adapters (OpenAI / OpenAI-compatible via `base_url`, Ollama native or `/v1`).
- Removed direct OpenAI imports from application code; apps now use a provider factory from the core package.
- MCP server now prefers config file loading with CLI/env/file precedence and redacted `--print-config`; legacy env-only mode warns.
- Replaced hardcoded vector-size usage across components with configuration-driven values.
- Updated tests and documentation to align with provider-agnostic architecture.

## Version 0.6.1 - August 13, 2025

### Document Conflict Detection : Performance Improvements

#### MCP Server - Document Conflict Detection Optimization

- **Resolved performance bottlenecks**: Fixed timeout and error issues in `detect_document_conflicts` tool, achieving P95 latency target of 8-10 seconds
- **Tiered analysis implementation**: Added intelligent document pair prioritization (primary, secondary, tertiary tiers) to analyze most promising conflicts first
- **LLM optimization**: Implemented strict budgeting for expensive LLM calls with configurable limits (default 2 pairs) and per-process caching
- **Parallel processing**: Added concurrent Qdrant vector retrieval with semaphore-based concurrency control (default 5 concurrent operations)
- **Configurable performance parameters**: Added 8 new configuration options for fine-tuning conflict detection performance:
  - `conflict_overall_timeout_s`: Overall operation timeout (default 9.0s)
  - `conflict_max_pairs_total`: Maximum document pairs to analyze (default 24)
  - `conflict_max_llm_pairs`: Maximum LLM-analyzed pairs (default 2)
  - `conflict_text_window_chars`: Text truncation for LLM input (default 2000 chars)
  - `conflict_embeddings_timeout_s`: Vector retrieval timeout (default 2.0s)
  - `conflict_embeddings_max_concurrency`: Parallel retrieval limit (default 5)
- **Runtime transparency**: Added detailed performance statistics in tool responses showing pairs analyzed, LLM usage, and execution time
- **Graceful degradation**: Implemented partial results with time budget exhaustion handling instead of hard failures
- **Enhanced tool schema**: Added optional per-call parameter overrides for `use_llm`, `max_llm_pairs`, `overall_timeout_s`, `max_pairs_total`, and `text_window_chars`

#### Bug Fixes

- **Fixed AttributeError in conflict formatter**: Resolved `'dict' object has no attribute 'document_id'` error by adding proper handling for both SearchResult objects and dictionary formats
- **Enhanced error handling**: Improved graceful handling of malformed document data in conflict detection pipeline

## Version 0.6.0 - August 12, 2025

### **MAJOR MILESTONE RELEASE**

#### 🚀 Upgraded MCP Server Architecture

- **Streamable HTTP Transport Support**: Added FastAPI-based HTTP transport alongside existing stdio transport, enabling web-based MCP clients and multiple concurrent connections
- **MCP Protocol 2025-06-18 Compliance**: Upgraded from MCP Protocol version 2024-11-05 to the latest 2025-06-18 specification with full backward compatibility
- **Server-Sent Events (SSE) Streaming**: Implemented real-time streaming capabilities for enhanced client communication
- **Dual Transport Architecture**: Support for both stdio (subprocess-based clients) and HTTP (web clients) transports simultaneously

#### 🔧 Enhanced Integration & Connectivity

- **Production-Ready HTTP Server**: FastAPI implementation with proper security, session management, and CORS support
- **Advanced Security Features**: Origin validation, localhost binding, and DNS rebinding protection
- **CLI Transport Selection**: Added `--transport` option to choose between stdio and HTTP modes
- **Health Check Endpoints**: Built-in monitoring and health check capabilities for production deployment

#### 📊 Structured Output & Protocol Features  

- **Structured Tool Output**: Enhanced tool responses with JSON-structured content while maintaining backward compatibility
- **Tool Behavioral Annotations**: Added annotations for all 8 tools indicating read-only and compute-intensive operations
- **Protocol Version Validation**: Header-based protocol version validation with graceful degradation
- **Session Management**: Comprehensive session handling for stateful HTTP connections

#### 🔄 Backward Compatibility & Migration

- **Zero Breaking Changes**: Existing stdio clients continue to work unchanged
- **Seamless Migration Path**: Easy transition between transport modes without configuration changes  
- **Legacy Support**: Full support for existing MCP 2024-11-05 clients
- **Configuration Compatibility**: All existing configurations work with new transport layer

#### 🏗️ Architecture Improvements

- **Modular Transport Layer**: Clean separation between protocol handling and transport mechanisms
- **Enhanced Error Handling**: Improved error messages and graceful failure handling
- **Performance Optimizations**: Efficient connection handling and resource management
- **Comprehensive Testing**: Full test coverage for HTTP transport, session management, and protocol compliance

## Version 0.5.1 - July 28, 2025

### 🏗️ Major Architecture Improvements

#### Chunking Strategy Modernization

- **Modular architecture implementation**: Complete refactor of all chunking strategies (Default, HTML, Code, JSON) into modular components for enhanced maintainability and extensibility
- **Component-based design**: Introduced dedicated classes for document parsing, section splitting, metadata extraction, and chunk processing across all strategies
- **Improved HTML chunking**: Enhanced robust handling for empty content and malformed HTML with graceful degradation
- **Code and JSON strategy overhaul**: Complete modular redesign with better handling of large documents and fallback mechanisms
- **Enhanced chunk processing**: Added additional metadata fields (source_type, url, content_type, title) and improved semantic analysis handling
- **Updated configuration templates**: Enhanced [config.template.yaml](https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml) and [configuration documentation](docs/users/configuration/config-file-reference.md) with new strategy-specific chunking options

## Version 0.5.0 - July 25, 2025

### 🚀 Major Features

#### Advanced Search Intelligence

- **Cross-document intelligence**: Document similarity analysis, clustering, and relationship detection
- **Intent-aware adaptive search**: AI-powered query understanding and strategy selection
- **Knowledge graph integration**: Entity relationships and multi-hop reasoning capabilities
- **Topic-driven search chaining**: Automatic topic discovery and related content suggestions
- **Dynamic faceted search**: Real-time facet generation and filtering interface

#### Enhanced Semantic Analysis

- **spaCy integration**: Advanced NLP processing with configurable language models
- **Improved topic extraction**: Enhanced LDA modeling with optimized parameters
- **Entity recognition**: Structured entity and topic conversion in search results
- **Semantic analysis configuration**: Comprehensive topic modeling settings

#### CLI & User Experience

- **Force ingestion option**: Added `--force` flag to bypass change detection for complete reprocessing
- **Enhanced chunking**: Improved timeout handling and performance thresholds
- **Better logging**: Structured logging for semantic analysis and search components

## Version 0.4.15 - July 22, 2025

### 🚀 Major Improvements

#### Chunking Strategy Overhaul

- **Fixed critical chunking inconsistency**: All strategies now use character-based `chunk_size` (was mixed token/character interpretation causing 4-5x chunk count differences)
- **Markdown strategy modularization**: Complete refactor into focused components (DocumentParser, SectionSplitter, MetadataExtractor, ChunkProcessor) for better maintainability
- **Enhanced hierarchical metadata**: Added intelligent section analysis with HeaderAnalysis and SectionMetadata for richer document context
- **Smart split level detection**: Automatic optimization of header split levels based on document structure and type
- **Improved boundary detection**: Tokenizer now used for word/token boundaries while respecting character-based limits
- **Comprehensive testing**: Added integration tests ensuring strategy consistency and preventing regression

## Version 0.4.14 - July 13, 2025

### 🐛 Critical Bug Fixes

#### Excel File Chunking Fixes

- **Fixed regex error in table detection**: Resolved `bad character range |-\s at position 2` error that was preventing Excel files from being chunked properly
  - **Root cause**: Invalid regex pattern `r"^[|-\s:]+$"` in `_split_excel_sheet_content` method
  - **Solution**: Escaped dash character to create valid pattern: `r"^[|\-\s:]+$"`
  - **Impact**: Excel files no longer fall back to default chunking strategy
- **Fixed large table chunking logic**: Resolved issue where large Excel tables were treated as single massive chunks
  - **Problem**: 128K character files created only 2-5 chunks instead of ~200 chunks at 600-character limit
  - **Root cause**: Large logical units (tables) were not split when exceeding max_size
  - **Solution**: Added intelligent splitting logic that preserves table structure while respecting chunk size limits
  - **Result**: Large Excel files now properly chunk into appropriate sizes (e.g., 74K chars → 127 chunks @ ~588 chars each)
- **Eliminated token limit warnings**: Fixed the `Content exceeds maximum token limit, truncating` warnings that occurred with large Excel chunks
  - **Before**: Chunks up to 128K characters (47K+ tokens) being truncated
  - **After**: All chunks properly sized to stay within token limits
- **Enhanced table structure preservation**: Table boundaries are now intelligently detected and preserved during chunking

#### Technical Improvements

- **Better logical unit management**: Enhanced `_split_excel_sheet_content` to handle large units by splitting at line boundaries
- **Preserved table formatting**: Chunking algorithm maintains table structure integrity while enforcing size limits
- **Improved error handling**: Better error messages and fallback behavior for edge cases
- **Performance optimization**: More efficient chunking for large Excel files without infinite loops

#### Testing & Validation

- **All existing tests pass**: 50 markdown strategy tests continue to pass, ensuring backward compatibility
- **Verified chunking accuracy**: Large test files now produce expected chunk counts with proper size distribution
- **Regex pattern validation**: Confirmed table detection works correctly for all markdown table formats

## Version 0.4.13 - July 11, 2025

### ✨ New Features

#### Excel File Chunking Improvements

- **Enhanced Excel-to-markdown chunking**: Improved MarkdownChunkingStrategy to properly handle Excel files converted to markdown by MarkItDown
- **Sheet-aware sectioning**: Excel files now split on H2 headers (sheet names) instead of treating the entire file as one "Preamble" section
- **Table-aware chunking**: Added specialized `_split_excel_sheet_content` method that preserves table structure when splitting large sheets
- **Intelligent content detection**: Automatically detects converted Excel files based on `original_file_type` metadata and applies appropriate chunking rules
- **Backward compatibility**: Regular markdown files continue to use H1-only sectioning, maintaining existing behavior
- **Comprehensive testing**: Added 3 new test cases covering Excel chunking scenarios and ensuring regular markdown files are unaffected

#### Excel Chunking — Technical Improvements

- **Context-aware splitting**: Different header level thresholds based on file type (H1 for markdown, H1+H2 for Excel)
- **Enhanced metadata tracking**: Added `is_excel_sheet` metadata to identify Excel-derived chunks
- **Table boundary preservation**: Smart table detection prevents breaking tables in the middle when chunking
- **Document reference management**: Added proper cleanup of document references to prevent memory leaks

## Version 0.4.12 - July 10, 2025

### 🐛 Bug Fixes

#### Chunking Strategy Improvements

- **Fixed missing chunk overlap in MarkdownChunkingStrategy**: Implemented proper overlap functionality that was completely missing from markdown file chunking
- **Added intelligent overlap calculation**: Overlap now respects the configured `chunk_overlap` parameter and uses paragraph/sentence boundaries for natural breaks
- **Enhanced overlap configuration support**: When `chunk_overlap=0`, chunks have no overlap; when configured, up to 25% of chunk content can overlap for better context continuity
- **Added comprehensive overlap testing**: New test suite verifies overlap works correctly across different configurations and content types

## Version 0.4.11 - July 10, 2025

### 🐛 File Processing & Configuration Bug Fixes

#### File Processing & Chunking

- **Fixed file size detection limits**: Increased default file size limits to handle larger documents (docx, xlsx files up to 5MB)
- **Resolved MarkdownChunkingStrategy issues**: Fixed chunking strategy to respect `chunk_size` configuration instead of only splitting on H1 headers
- **Fixed unique chunk ID generation**: Resolved issue where chunks from same document had identical IDs, causing overwrites in Qdrant storage
- **Enhanced chunk count management**: Replaced hard-coded chunk limits with configurable `max_chunks_per_document` setting

#### Configuration Management

- **Improved chunking configuration**: Added `max_chunks_per_document` parameter for better control over document processing
- **Cleaned up redundant settings**: Removed conflicting `max_document_size` parameter to maintain clean separation between file size and chunk count limits
- **Enhanced error messages**: Added actionable configuration advice when chunk limits are reached

#### Processing Pipeline

- **Fixed content truncation**: Eliminated "maximum chunks per section limit" warnings by making limits dynamic based on user configuration
- **Improved chunk estimation**: Added better user guidance for optimal chunk count configuration
- **Enhanced section handling**: Made section limits dynamic (50% of max_chunks_per_document)

## Version 0.4.10 - June 18, 2025

### 🐛 Windows & File Processing Bug Fixes

#### Windows Compatibility & Logging

- **Fixed duplicate debug logging**: Resolved `[DEBUG] [DEBUG]` duplicate level tags in both console and file output
- **Enhanced logging verbosity control**: Added filtering for noisy third-party library debug messages (chardet, pdfminer, httpx)
- **Improved Windows path formatting**: Fixed mixed path separators in log output for consistent cross-platform display
- **Complete path normalization**: Fixed remaining instances of backslashes in Windows file paths in FileDetector and file processor logging
- **Fixed .txt file processing**: Resolved issue where `.txt` files were excluded from ingestion when `file_types: []` was empty

#### File Processing

- **LocalFile connector**: `.txt` files now properly processed by default text strategy when no specific file types configured
- **Git connector**: Consistent file type processing logic across all connectors
- **Path normalization**: All file paths in logs now use forward slashes for consistency

## Version 0.4.9 - June 18, 2025

### Bug fix

- **Issue when deleting a deleted document** : missing content_type="md" field to the `_create_deleted_document method`

## Version 0.4.8 - June 17, 2025

### 🪟 Windows Compatibility Fixes

- **LocalFile Connector**: Fixed Windows file URL parsing (`file:///C:/Users/...` now works correctly)
- **Git Connector**: Fixed document URL generation with Windows paths (backslashes → forward slashes)
- **File Conversion**: Cross-platform timeout handling (threading on Windows, signals on Unix)
- **MarkItDown Integration**: Fixed Windows signal compatibility (`signal.SIGALRM` errors resolved)
- **Console Output**: Enhanced emoji handling for clean Windows display
- **Logging**: Suppressed verbose SQLite logs and fixed duplicate log level display (`[DEBUG] [DEBUG]` → `[DEBUG]`)
- **Testing**: Added 38 Windows compatibility test cases

## Version 0.4.7 - June 9, 2025

### 🧹 Test Suite Improvements

### 🐛 CLI & User Experience Bug Fixes

#### CLI and User Experience

- **Version check improvements**: Fixed upgrade instructions to include `qdrant-loader-mcp-server` package in version check output
- **Branch display logic**: Fixed branch display logic to default to 'main' when branch is unknown in coverage reports
- **Error handling**: Improved error handling in CLI for invalid input scenarios

### 📚 Documentation

- **Configuration template**: Enhanced configuration template with detailed comments for better user guidance
- **PublicDocs connector**: Improved logging in PublicDocsConnector for better debugging

### 🔧 Release Process Enhancement

- **Release notes validation**: Updated release script to automatically check that `RELEASE_NOTES.md` has been updated for new versions before allowing releases
- **Improved release safety**: Enhanced pre-release checks to ensure documentation consistency

## Version 0.4.6 - June 3, 2025

### 🔔 User Experience Enhancements

#### Version Notifications

- **Automatic update notifications**: CLI now checks for new package versions and notifies users when updates are available
- **Non-intrusive background checks**: Version checking runs in background without affecting CLI performance

## Version 0.4.5 - June 3, 2025

### 🚀 Performance Improvements

#### CLI Startup Optimization

- **CLI startup performance**: Reduced startup time by 60-67% for basic commands ([#24](https://github.com/martin-papy/qdrant-loader/issues/24))
  - `--help`: ~6.8s → 2.33s (**66% improvement**)
  - `--version`: ~6.3s → 2.57s (**59% improvement**)
- **Lazy loading implementation**: Heavy modules now load only when needed (96-97% import time reduction)
- **Fixed version detection**: Replaced custom parsing with `importlib.metadata.version()` - works in all environments
- **Resolved circular imports**: Eliminated `config` → `connectors` → `config` dependency cycle

### 🎨 User Experience Enhancements

#### Excel File Processing

- **Warning capture system**: Intercepts openpyxl warnings during Excel conversion
- **Structured logging**: Routes warnings through qdrant-loader logging system for visual consistency
- **Smart detection**: Captures "Data Validation" and "Conditional Formatting" warnings with context
- **Summary reporting**: Provides comprehensive summary of unsupported Excel features

## Version 0.4.4 - June 3, 2025

### 🎉 Major Improvements

#### File Conversion & Processing Overhaul

##### Fixed Critical File Conversion Issues

- **Fixed file conversion initialization**: Resolved issue where file conversion was not working due to missing `set_file_conversion_config` calls in the pipeline ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Enhanced strategy selection**: Converted files (Excel, Word, PDF, etc.) now correctly use `MarkdownChunkingStrategy` instead of `DefaultChunkingStrategy` ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Improved NLP processing**: Converted files now have full NLP processing enabled instead of being skipped with `content_type_inappropriate` ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))

##### Enhanced File Processing Pipeline

- Added proper file conversion configuration initialization in source processors ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Implemented automatic strategy selection based on conversion status ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Fixed metadata propagation for converted files ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))

#### Chunking Strategy — Infinite Loop & Safety Fixes

##### Resolved Infinite Loop Issues

- **Fixed MarkdownChunkingStrategy infinite loops**: Resolved critical issue where documents with very long words would create infinite loops, hitting the 1000 chunk limit ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Added safety limits**: Implemented `MAX_CHUNKS_PER_SECTION = 100` and `MAX_CHUNKS_PER_DOCUMENT = 500` limits ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Enhanced error handling**: Added proper handling for words longer than `max_size` by truncating them with warnings ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

##### Improved Chunking Logic

- Added safety checks to prevent infinite loops in `_split_large_section` method ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Enhanced logging for debugging chunking issues ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Added warnings when chunking limits are reached ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

#### Workspace Management

##### Better Log Organization

- **Fixed workspace logs location**: Logs are now stored in `workspace_path/logs/qdrant-loader.log` instead of cluttering the workspace root ([589ae4b](https://github.com/martin-papy/qdrant-loader/commit/589ae4b))
- **Enhanced workspace structure**: Added automatic creation of logs directory ([589ae4b](https://github.com/martin-papy/qdrant-loader/commit/589ae4b))
- **Updated documentation**: Reflected new log structure in workspace mode documentation ([589ae4b](https://github.com/martin-papy/qdrant-loader/commit/589ae4b))

#### Resource Management & Stability

##### Fixed Pipeline Hanging Issues

- **Resolved ResourceManager cleanup**: Fixed issue where normal cleanup was setting shutdown events, causing workers to exit prematurely ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))
- **Enhanced signal handling**: Distinguished between normal cleanup and signal-based shutdown ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))
- **Improved graceful shutdown**: Workers now properly complete processing before shutdown ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))

##### Performance Optimizations

- Increased `MAX_CHUNKS_TO_PROCESS` from 100 to 1000 chunks to accommodate larger documents ([1bfe550](https://github.com/martin-papy/qdrant-loader/commit/1bfe550))
- Better handling of large documents (up to ~1000KB text limit per document) ([1bfe550](https://github.com/martin-papy/qdrant-loader/commit/1bfe550))
- Improved change detection for incremental updates ([5408db9](https://github.com/martin-papy/qdrant-loader/commit/5408db9))

### 🔧 Technical Improvements

#### Code Quality & Testing

##### Enhanced Test Coverage

- Added comprehensive tests for converted file NLP processing ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))
- Added tests for chunking strategy selection ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Enhanced error handling test coverage ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))
- All existing functionality preserved with 100% test pass rate

##### Architecture Improvements

- Enhanced base connector class with proper file conversion support ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Improved factory pattern for pipeline component creation ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Better separation of concerns in source processing ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

#### Configuration & Setup

##### Improved File Conversion Support

- Enhanced connector initialization with file conversion configuration ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Better error handling for conversion failures ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Improved fallback mechanisms for unsupported file types ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

### 🐛 Critical Pipeline & Processing Bug Fixes

#### Critical Fixes

- **File conversion not working**: Fixed missing initialization causing 0 documents to be processed ([5408db9](https://github.com/martin-papy/qdrant-loader/commit/5408db9))
- **Infinite chunking loops**: Resolved MarkdownChunkingStrategy creating thousands of chunks for simple documents ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Pipeline hanging**: Fixed ResourceManager causing workers to exit prematurely ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))
- **NLP processing skipped**: Fixed converted files being inappropriately skipped for NLP processing ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))

#### Minor Fixes

- Fixed workspace log file location ([589ae4b](https://github.com/martin-papy/qdrant-loader/commit/589ae4b))
- Improved error messages and logging ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Enhanced metadata handling for converted files ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))
- Better handling of edge cases in chunking strategies ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

### 🔄 Migration Notes

**For Existing Users:**

- Logs will now be created in `workspace/logs/` directory instead of workspace root
- Converted files will now be processed with enhanced NLP capabilities
- Large documents will be chunked more efficiently with higher limits
- No breaking changes to existing configurations

**Performance Impact:**

- Improved processing speed for converted files
- Better memory usage with enhanced chunking limits
- More stable pipeline execution with proper resource management
