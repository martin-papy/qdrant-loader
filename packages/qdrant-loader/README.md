# QDrant Loader

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A powerful data ingestion engine that collects and vectorizes technical content from multiple sources for storage in QDrant vector database. Part of the [QDrant Loader monorepo](../../) ecosystem.

## 🚀 What It Does

QDrant Loader is the data ingestion engine that:

- **Collects content** from Git repositories, Confluence, JIRA, documentation sites, and local files
- **Converts files** automatically from 20+ formats including PDF, Office docs, and images
- **Processes intelligently** with smart chunking, metadata extraction, and change detection
- **Stores efficiently** in QDrant vector database with optimized embeddings
- **Updates incrementally** to keep your knowledge base current

## 🔄 Supported Data Sources

| Source | Description | Key Features |
|--------|-------------|--------------|
| **Git** | Code repositories and documentation | Branch selection, file filtering, commit metadata |
| **Confluence** | Cloud & Data Center/Server | Space filtering, hierarchy preservation, attachment processing |
| **JIRA** | Cloud & Data Center/Server | Project filtering, issue tracking, attachment support |
| **Public Docs** | External documentation sites | CSS selector extraction, version detection |
| **Local Files** | Local directories and files | Glob patterns, recursive scanning, file type filtering |

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

### Key Features

- **Automatic detection**: Files are converted when `enable_file_conversion: true`
- **Attachment processing**: Downloads and converts attachments from all sources
- **Fallback handling**: Graceful handling when conversion fails
- **Metadata preservation**: Original file information maintained
- **Performance optimized**: Configurable size limits and timeouts

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install qdrant-loader
```

### From Source (Development)

```bash
# Clone the monorepo
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install in development mode
pip install -e packages/qdrant-loader[dev]
```

### With MCP Server

For complete AI integration:

```bash
# Install both packages
pip install qdrant-loader qdrant-loader-mcp-server
```

## ⚡ Quick Start

### 1. Workspace Setup (Recommended)

```bash
# Create workspace directory
mkdir my-qdrant-workspace && cd my-qdrant-workspace

# Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template
```

### 2. Environment Configuration

Edit `.env` file:

```bash
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_docs
QDRANT_API_KEY=your_api_key  # Required for QDrant Cloud

# Embedding Configuration
OPENAI_API_KEY=your_openai_key

# State Management
STATE_DB_PATH=./state.db
```

### 3. Data Source Configuration

Edit `config.yaml`:

```yaml
# Global configuration
global_config:
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  
  embedding:
    endpoint: "https://api.openai.com/v1"
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 100
    vector_size: 1536
  
  file_conversion:
    max_file_size: 52428800  # 50MB
    conversion_timeout: 300
    markitdown:
      enable_llm_descriptions: false

# Multi-project configuration
projects:
  my-project:
    project_id: "my-project"
    display_name: "My Documentation Project"
    description: "Project description"
    
    sources:
      git:
        my-repo:
          base_url: "https://github.com/your-org/your-repo.git"
          branch: "main"
          include_paths:
            - "**/*.md"
            - "**/*.py"
          exclude_paths:
            - "**/node_modules/**"
          token: "${REPO_TOKEN}"
          enable_file_conversion: true

      localfile:
        local-docs:
          base_url: "file://./docs"
          include_paths:
            - "**/*.md"
            - "**/*.pdf"
          enable_file_conversion: true
```

### 4. Load Your Data

```bash
# Initialize QDrant collection
qdrant-loader --workspace . init

# Load data from configured sources
qdrant-loader --workspace . ingest

# Check project status
qdrant-loader project --workspace . status
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `QDRANT_URL` | QDrant instance URL | `http://localhost:6333` | Yes |
| `QDRANT_API_KEY` | QDrant API key | None | Cloud only |
| `QDRANT_COLLECTION_NAME` | Collection name | `documents` | Yes |
| `OPENAI_API_KEY` | OpenAI API key | None | Yes |
| `STATE_DB_PATH` | State database path | `./state.db` | Yes |

### Source-Specific Variables

#### Git Repositories

```bash
REPO_TOKEN=your_github_token
```

#### Confluence (Cloud)

```bash
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=SPACE
CONFLUENCE_TOKEN=your_token
CONFLUENCE_EMAIL=your_email
```

#### Confluence (Data Center/Server)

```bash
CONFLUENCE_URL=https://your-confluence-server.com
CONFLUENCE_SPACE_KEY=SPACE
CONFLUENCE_PAT=your_personal_access_token
```

#### JIRA (Cloud)

```bash
JIRA_URL=https://your-domain.atlassian.net
JIRA_PROJECT_KEY=PROJ
JIRA_TOKEN=your_token
JIRA_EMAIL=your_email
```

#### JIRA (Data Center/Server)

```bash
JIRA_URL=https://your-jira-server.com
JIRA_PROJECT_KEY=PROJ
JIRA_PAT=your_personal_access_token
```

## 🎯 Usage Examples

### Basic Commands

```bash
# Show current configuration
qdrant-loader --workspace . config

# Initialize collection (one-time setup)
qdrant-loader --workspace . init

# Ingest data from all configured sources
qdrant-loader --workspace . ingest

# Check project status
qdrant-loader project --workspace . status

# List all projects
qdrant-loader project --workspace . list

# Show help
qdrant-loader --help
```

### Advanced Usage

```bash
# Specify configuration files individually
qdrant-loader --config config.yaml --env .env ingest

# Debug logging
qdrant-loader --workspace . --log-level DEBUG ingest

# Force full re-ingestion
qdrant-loader --workspace . init --force
qdrant-loader --workspace . ingest

# Process specific project
qdrant-loader --workspace . ingest --project my-project

# Process specific source type
qdrant-loader --workspace . ingest --source-type git

# Enable performance profiling
qdrant-loader --workspace . ingest --profile
```

### Project Management

```bash
# Validate project configurations
qdrant-loader project --workspace . validate

# Validate specific project
qdrant-loader project --workspace . validate --project-id my-project

# Show project status in JSON format
qdrant-loader project --workspace . status --format json

# Show specific project status
qdrant-loader project --workspace . status --project-id my-project
```

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

## 🧪 Testing

```bash
# Run all tests
pytest packages/qdrant-loader/tests/

# Run with coverage
pytest --cov=qdrant_loader packages/qdrant-loader/tests/

# Run specific test categories
pytest -m "unit" packages/qdrant-loader/tests/
pytest -m "integration" packages/qdrant-loader/tests/
```

## 🤝 Contributing

This package is part of the QDrant Loader monorepo. See the [main contributing guide](../../CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install in development mode
pip install -e packages/qdrant-loader[dev]

# Run tests
pytest packages/qdrant-loader/tests/
```

## 📚 Documentation

- **[Complete Documentation](../../docs/)** - Comprehensive guides and references
- **[Getting Started](../../docs/getting-started/)** - Quick start and core concepts
- **[User Guides](../../docs/users/)** - Detailed usage instructions
- **[Developer Docs](../../docs/developers/)** - Architecture and API reference

## 🆘 Support

- **[Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community Q&A
- **[Documentation](../../docs/)** - Comprehensive guides

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](../../LICENSE) file for details.

---

**Ready to load your data?** Check out the [Quick Start Guide](../../docs/getting-started/quick-start.md) or explore the [complete documentation](../../docs/).
