# QDrant Loader

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A powerful data ingestion engine that collects and vectorizes technical content from multiple sources for storage in QDrant vector database. Part of the [QDrant Loader monorepo](../../) ecosystem.

For full setup and configuration, start with the documentation links below.

## <img src="/assets/icons/library/target-icon.svg" width="32" alt="What It Does"> What It Does

- Collects content from Git repositories, Confluence, JIRA, public documentation sites, and local files
- Converts supported file types (via MarkItDown) when enabled per source
- Chunks, embeds, and stores content in QDrant for semantic retrieval
- Supports incremental ingestion workflows through the CLI

For detailed source setup and conversion behavior, see:

- **[Data source guides](../../docs/users/detailed-guides/data-sources)** - Source-specific setup for Git, Confluence, Jira, local files, and public docs.
- **[File conversion guide](../../docs/users/detailed-guides/file-conversion)** - Supported formats, conversion behavior, and practical tuning options.

## <img src="/assets/icons/library/file-icon.svg" width="32" alt="File icon"> File Conversion Support

Automatically converts diverse file formats using Microsoft's MarkItDown:

### Supported Formats

- **Documents**: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
- **Images**: PNG, JPEG, GIF, BMP, TIFF (with optional OCR)
- **Archives**: ZIP files with automatic extraction
- **Data**: JSON, CSV, XML, YAML
- **Audio**: MP3, WAV (transcription support)
- **E-books**: EPUB format
- **And more**: 20+ file types supported

### Key Features

- **Automatic detection**: Files are converted when `enable_file_conversion: true`
- **Attachment processing**: Downloads and converts attachments from all sources
- **Fallback handling**: Graceful handling when conversion fails
- **Metadata preservation**: Original file information is maintained
- **Performance optimized**: Configurable limits for size, timeouts, and throughput

## <img src="/assets/icons/library/architect-icon.svg" width="32" alt="Data Flow"> Data Flow

```text
Data Sources → File Conversion → Text Processing → Chunking → Embedding → QDrant Storage
	↓              ↓               ↓            ↓          ↓           ↓
Git Repos      PDF/Office      Preprocessing   Smart     OpenAI      Vector DB
Confluence     Images/Audio    Metadata        Chunks    Local       Collections
JIRA           Archives        Extraction      Overlap   Custom      Incremental
Public Docs    Documents       Filtering       Context   Providers   Updates
Local Files    20+ Formats     Cleaning        Tokens    Endpoints   State Tracking
```

## <img src="/assets/icons/library/search-icon.svg" width="32" alt="Search Icon"> Advanced Features

### Incremental Updates

- **Change detection** for all source types
- **Efficient synchronization** with minimal reprocessing
- **State persistence** across runs
- **Conflict resolution** for concurrent updates

### Performance Optimization

- **Batch processing** for efficient embedding generation
- **Rate limiting** to respect API limits
- **Parallel processing** for multiple sources
- **Memory management** for large datasets

### Error Handling

- **Robust retry mechanisms** for transient failures
- **Graceful degradation** when sources are unavailable
- **Detailed logging** for troubleshooting
- **Recovery strategies** for partial failures

Implementation details for tuning and troubleshooting are covered in:

- **[Configuration reference](../../docs/users/configuration)** - Full settings model, defaults, and production-ready examples.
- **[Common workflows](../../docs/users/workflows/common-workflows.md)** - Proven end-to-end paths for ingestion, maintenance, and operations.
- **[Troubleshooting guide](../../docs/users/troubleshooting)** - Common failure patterns and step-by-step fixes.

## <img src="/assets/icons/library/package-icon.svg"  width="32" alt="Installation"> Installation

```bash
pip install qdrant-loader
```

## <img src="/assets/icons/library/test-tube-icon.svg" width="32" alt="CLI"> CLI

```bash
qdrant-loader --help
```

## <img src="/assets/icons/library/rocket-icon.svg" width="32" alt="Quick Start"> Quick Start

```bash
# Initialize collection and metadata structures
qdrant-loader init --workspace .

# Ingest from configured projects/sources
qdrant-loader ingest --workspace .

# Check workspace status
qdrant-loader project --workspace . status
```

For full workspace bootstrapping (.env, config.yaml, and source templates), see **[Quick start](../../docs/getting-started/quick-start.md)**.

## <img src="../../../assets/icons/library/book-icon.svg" width="32" alt="Book icon"> Canonical Documentation

- **[Monorepo overview](../../)** - Project structure, packages, and top-level navigation across the repository.
- **[Quick start](../../docs/getting-started/quick-start.md)** - Fast setup path from install to first successful ingestion.
- **[Installation details](../../docs/getting-started/installation.md)** - Platform-specific install methods and dependency requirements.
- **[Configuration reference](../../docs/users/configuration)** - Configuration model, options, and practical examples.
- **[Data source guides](../../docs/users/detailed-guides/data-sources)** - Source-specific setup for Git, Confluence, Jira, local files, and more.

## <img src="/assets/icons/library/hand-sake-icon.svg" width="32" alt="Contributing icon"> Contributing

See **[CONTRIBUTING](../../CONTRIBUTING.md)** - Contribution guidelines, development standards, and pull request process.
