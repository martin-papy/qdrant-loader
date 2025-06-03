# Release Notes

## Version 0.4.5 - June 3, 2025

### 🚀 Performance Improvements

#### CLI Startup Optimization

**Speed Improvements**

- **CLI startup performance**: Reduced startup time by 60-67% for basic commands ([#24](https://github.com/martin-papy/qdrant-loader/issues/24))
  - `--help`: ~6.8s → 2.33s (**66% improvement**)
  - `--version`: ~6.3s → 2.57s (**59% improvement**)
- **Lazy loading implementation**: Heavy modules now load only when needed (96-97% import time reduction)
- **Fixed version detection**: Replaced custom parsing with `importlib.metadata.version()` - works in all environments
- **Resolved circular imports**: Eliminated `config` → `connectors` → `config` dependency cycle

#### Excel File Processing

**Warning Management**

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
