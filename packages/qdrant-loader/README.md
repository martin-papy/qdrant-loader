# QDrant Loader

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A powerful data ingestion engine that collects and vectorizes technical content from multiple sources for storage in QDrant vector database. Part of the [QDrant Loader monorepo](../../) ecosystem.

For full setup and configuration, start with the documentation links below.

## 🚀 What It Does

- **Collects content** from Git repositories, Confluence, JIRA, documentation sites, and local files
- **Converts files** automatically from 20+ formats including PDF, Office docs, and images
- **Processes intelligently** with smart chunking, metadata extraction, and change detection
- **Stores efficiently** in QDrant vector database with optimized embeddings
- **Updates incrementally** to keep your knowledge base current

## 🗄️ Supported Data Sources

| Source          | Description                         | Key Features                                                   |
| --------------- | ----------------------------------- | -------------------------------------------------------------- |
| **Git**         | Code repositories and documentation | Branch selection, file filtering, commit metadata              |
| **Confluence**  | Cloud & Data Center/Server          | Space filtering, hierarchy preservation, attachment processing |
| **JIRA**        | Cloud & Data Center/Server          | Project filtering, issue tracking, attachment support          |
| **Public Docs** | External documentation sites        | CSS selector extraction, version detection                     |
| **Local Files** | Local directories and files         | Glob patterns, recursive scanning, file type filtering         |

## 📄 File Conversion Support

Automatically converts diverse file formats using Microsoft's MarkItDown:

### Supported Formats

- **Documents**: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
- **Images**: PNG, JPEG, GIF, BMP, TIFF (with optional OCR)
- **Archives**: ZIP files with automatic extraction
- **Data**: JSON, CSV, XML, YAML
- **Audio**: MP3, WAV (transcription support)
- **E-books**: EPUB format
- **And more**: 20+ file types supported

For detailed source setup and conversion behavior, see:

- **[Data source guides](../../docs/users/detailed-guides/data-sources)** - Source-specific setup for Git, Confluence, Jira, local files, and public docs.
- **[File conversion guide](../../docs/users/detailed-guides/file-conversion)** - Supported formats, conversion behavior, and practical tuning options.

### Key Features

- **Automatic detection**: Files are converted when `enable_file_conversion: true`
- **Attachment processing**: Downloads and converts attachments from all sources
- **Fallback handling**: Graceful handling when conversion fails
- **Metadata preservation**: Original file information is maintained
- **Performance optimized**: Configurable limits for size, timeouts, and throughput

## 🏗️ Architecture

### Core Components

- **Source Connectors**: Pluggable connectors for different data sources
- **File Processors**: Conversion and processing pipeline for various file types
- **Chunking Engine**: Intelligent text segmentation with configurable overlap
- **Embedding Service**: Flexible embedding generation with multiple providers
- **State Manager**: SQLite-based tracking for incremental updates
- **QDrant Client**: Optimized vector storage and retrieval

### Data Flow

```text
Data Sources → File Conversion → Text Processing → Chunking → Embedding → QDrant Storage
	↓              ↓               ↓            ↓          ↓           ↓
Git Repos      PDF/Office      Preprocessing   Smart     OpenAI      Vector DB
Confluence     Images/Audio    Metadata        Chunks    Local       Collections
JIRA           Archives        Extraction      Overlap   Custom      Incremental
Public Docs    Documents       Filtering       Context   Providers   Updates
Local Files    20+ Formats     Cleaning        Tokens    Endpoints   State Tracking
```

## 🔍 Advanced Features

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

## 📦 Installation

```bash
pip install qdrant-loader
```

For detailed installation instructions, see:

- **[Installation details](../../docs/getting-started/installation.md)** - Platform-specific install methods and dependency requirements.

## ⚙️ Configuration

For detailed configuration setup, see:

- **[Basic Configuration](../../docs/getting-started/basic-configuration.md)** - Getting started with configuration
- **[Configuration reference](../../docs/users/configuration)** - Configuration model, options, and practical examples.
- **[Data source guides](../../docs/users/detailed-guides/data-sources)** - Source-specific setup for Git, Confluence, Jira, local files, and more.
- **[Environment Variables](../../docs/users/configuration/environment-variables.md)** - Environment variable reference and naming conventions.
- **[LLM Provider Guide](../../docs/users/configuration/llm-provider-guide.md)** - Configure provider-specific LLM details

## 🧪 CLI

```bash
qdrant-loader --help
```

## ⚡ Quick Start

```bash
# Initialize collection and metadata structures
qdrant-loader init --workspace .

# Ingest from configured projects/sources
qdrant-loader ingest --workspace .

# Check workspace status
qdrant-loader project --workspace . status
```

For full workspace bootstrapping (.env, config.yaml, and source templates), see **[Quick start](../../docs/getting-started/quick-start.md)**.

## 📚 Documentation

- **[Getting Started](../../docs/getting-started/)** - Quick start and core concepts
- **[Monorepo overview](../../)** - Project structure, packages, and top-level navigation across the repository.
- **[Quick start](../../docs/getting-started/quick-start.md)** - Fast setup path from install to first successful ingestion.
- **[User Guides](../../docs/users/)** - Detailed usage instructions
- **[Developer hub](../../docs/developers)** - Developer guides for architecture, testing, deployment, and contribution workflows.

## 🆘 Support

- **[Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community Q&A

## 🤝 Contributing

See **[CONTRIBUTING](../../CONTRIBUTING.md)** - Contribution guidelines, development standards, and pull request process.

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](../../LICENSE) file for details.

---

**Ready to get started?** Check out our [Quick Start Guide](../../docs/getting-started/README.md) or browse the [complete documentation](../../docs/).
