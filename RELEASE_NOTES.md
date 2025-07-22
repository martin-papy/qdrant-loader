# Release Notes

## Version 0.4.15 - July 22, 2025

### 🐛 Critical Bug Fixes

#### Chunking Strategy Consistency

- **Fixed chunking strategy inconsistency**: Resolved major discrepancy where `DefaultChunkingStrategy` and `MarkdownChunkingStrategy` interpreted `chunk_size` parameter differently
  - **Problem**: Default strategy used token-based chunking (600 tokens ≈ 2,400-3,000 chars) vs markdown strategy's character-based chunking (600 chars)
  - **Impact**: This caused 4-5x difference in chunk counts between strategies for the same configuration
  - **Solution**: Modified `DefaultChunkingStrategy` to always use character-based chunking for consistency
  - **Tokenizer role**: Tokenizer now only used for smart boundary detection (avoiding mid-word splits) while respecting character-based size limits
- **Enhanced boundary detection**: Improved word/token boundary detection while maintaining character-based sizing
- **Updated documentation**: Clarified that all chunking strategies now consistently use character-based `chunk_size` interpretation
- **Comprehensive testing**: Added integration tests to verify consistency between strategies and prevent regression

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

#### Technical Improvements

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

### 🐛 Bug Fixes

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

### 🐛 Bug Fixes

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

### 🐛 Bug Fixes

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

**Fixed Critical File Conversion Issues**

- **Fixed file conversion initialization**: Resolved issue where file conversion was not working due to missing `set_file_conversion_config` calls in the pipeline ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Enhanced strategy selection**: Converted files (Excel, Word, PDF, etc.) now correctly use `MarkdownChunkingStrategy` instead of `DefaultChunkingStrategy` ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Improved NLP processing**: Converted files now have full NLP processing enabled instead of being skipped with `content_type_inappropriate` ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))

**Enhanced File Processing Pipeline**

- Added proper file conversion configuration initialization in source processors ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Implemented automatic strategy selection based on conversion status ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Fixed metadata propagation for converted files ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))

#### Chunking Strategy Improvements

**Resolved Infinite Loop Issues**

- **Fixed MarkdownChunkingStrategy infinite loops**: Resolved critical issue where documents with very long words would create infinite loops, hitting the 1000 chunk limit ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Added safety limits**: Implemented `MAX_CHUNKS_PER_SECTION = 100` and `MAX_CHUNKS_PER_DOCUMENT = 500` limits ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- **Enhanced error handling**: Added proper handling for words longer than `max_size` by truncating them with warnings ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

**Improved Chunking Logic**

- Added safety checks to prevent infinite loops in `_split_large_section` method ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Enhanced logging for debugging chunking issues ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Added warnings when chunking limits are reached ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

#### Workspace Management

**Better Log Organization**

- **Fixed workspace logs location**: Logs are now stored in `workspace_path/logs/qdrant-loader.log` instead of cluttering the workspace root ([589ae4b](https://github.com/martin-papy/qdrant-loader/commit/589ae4b))
- **Enhanced workspace structure**: Added automatic creation of logs directory ([589ae4b](https://github.com/martin-papy/qdrant-loader/commit/589ae4b))
- **Updated documentation**: Reflected new log structure in workspace mode documentation ([589ae4b](https://github.com/martin-papy/qdrant-loader/commit/589ae4b))

#### Resource Management & Stability

**Fixed Pipeline Hanging Issues**

- **Resolved ResourceManager cleanup**: Fixed issue where normal cleanup was setting shutdown events, causing workers to exit prematurely ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))
- **Enhanced signal handling**: Distinguished between normal cleanup and signal-based shutdown ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))
- **Improved graceful shutdown**: Workers now properly complete processing before shutdown ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))

**Performance Optimizations**

- Increased `MAX_CHUNKS_TO_PROCESS` from 100 to 1000 chunks to accommodate larger documents ([1bfe550](https://github.com/martin-papy/qdrant-loader/commit/1bfe550))
- Better handling of large documents (up to ~1000KB text limit per document) ([1bfe550](https://github.com/martin-papy/qdrant-loader/commit/1bfe550))
- Improved change detection for incremental updates ([5408db9](https://github.com/martin-papy/qdrant-loader/commit/5408db9))

### 🔧 Technical Improvements

#### Code Quality & Testing

**Enhanced Test Coverage**

- Added comprehensive tests for converted file NLP processing ([7de3526](https://github.com/martin-papy/qdrant-loader/commit/7de3526))
- Added tests for chunking strategy selection ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Enhanced error handling test coverage ([4844abf](https://github.com/martin-papy/qdrant-loader/commit/4844abf))
- All existing functionality preserved with 100% test pass rate

**Architecture Improvements**

- Enhanced base connector class with proper file conversion support ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Improved factory pattern for pipeline component creation ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Better separation of concerns in source processing ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

#### Configuration & Setup

**Improved File Conversion Support**

- Enhanced connector initialization with file conversion configuration ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Better error handling for conversion failures ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))
- Improved fallback mechanisms for unsupported file types ([9d16b8d](https://github.com/martin-papy/qdrant-loader/commit/9d16b8d))

### 🐛 Bug Fixes

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
