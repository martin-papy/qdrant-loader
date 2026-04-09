# QDrant Loader

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A powerful data ingestion engine that collects and vectorizes technical content from multiple sources for storage in QDrant vector database. Part of the [QDrant Loader monorepo](../../) ecosystem.

## <img src="/assets/icons/library/target-icon.svg" width="32" alt="Rocket Icon"> What It Does

QDrant Loader is the data ingestion engine that:

- **Collects content** from Git repositories, Confluence, JIRA, documentation sites, and local files
- **Converts files** automatically from 20+ formats including PDF, Office docs, and images
- **Processes intelligently** with smart chunking, metadata extraction, and change detection
- **Stores efficiently** in QDrant vector database with optimized embeddings
- **Updates incrementally** to keep your knowledge base current

## <img src="/assets/icons/library/arrow-reload-icon.svg" width="32" alt="Support icon"> Supported Data Sources

| Source | Description | Key Features |
|--------|-------------|--------------|
| **Git** | Code repositories and documentation | Branch selection, file filtering, commit metadata |
| **Confluence** | Cloud & Data Center/Server | Space filtering, hierarchy preservation, attachment processing |
| **JIRA** | Cloud & Data Center/Server | Project filtering, issue tracking, attachment support |
| **Public Docs** | External documentation sites | CSS selector extraction, version detection |
| **Local Files** | Local directories and files | Glob patterns, recursive scanning, file type filtering |

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
- **Metadata preservation**: Original file information maintained
- **Performance optimized**: Configurable size limits and timeouts

## <img src="/assets/icons/library/package-icon.svg" width="32" alt="Insallation icon"> Installation

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
pip install -e packages/qdrant-loader
```

### With MCP Server

For complete AI integration:

```bash
# Install both packages
pip install qdrant-loader qdrant-loader-mcp-server
```

## <img src="/assets/icons/library/rocket-icon.svg" width="32" alt="Rocket Icon"> Quick Start

### 1. Workspace Setup (Recommended)

```bash
# Create workspace directory
mkdir my-qdrant-workspace && cd my-qdrant-workspace

# Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template
```

### 2. Environment Configuration
#### 🧠 LLM Provider Support

This system is designed to support **both local and cloud-based Large Language Model (LLM) providers**.

Currently supported providers:

- **Ollama** — local models (**default and preferred**)
- **OpenAI** — cloud-based models

The system uses a **unified configuration approach**, allowing you to switch providers without changing application code.

---

#### 🖥️ Ollama (Local Models – Recommended)

Ollama is the **default and recommended provider**, especially for local development and privacy-sensitive environments.

#### Prerequisites

To use **local models with Ollama**, ensure the following:

1. **Ollama is installed and running on your machine**

   - Ollama must be accessible at the configured endpoint  
     (default: `http://localhost:11434`).

   - Installation guide:  
     https://ollama.com/download

2. **Required models must be pulled locally before running the system**

   - For embedding generation, the following model is required:

   ```bash
   ollama pull argus-ai/pplx-embed-v1-0.6b:fp32
   ```

#### 🖥️ OpenAI (Cloud Models)
The system also supports OpenAI as a cloud-based LLM provider.
#### Requirements: 
**To use OpenAI, you must:**
- Set the provider: `LLM_PROVIDER=openai`
- Configure the OpenAI endpoint: `LLM_BASE_URL=https://api.openai.com/v1`
- Provide a valid API key: `OPENAI_API_KEY=your_openai_key`


Edit `.env` file:

```bash
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_docs
QDRANT_API_KEY=your_api_key  # Required for QDrant Cloud


# =========================
# LLM Configuration (Unified, Ollama-first)
# =========================

LLM_PROVIDER=ollama #openai
# Possible values:
#   - ollama (default, local)
#   - openai (cloud)

LLM_BASE_URL=http://localhost:11434/v1
# Ollama: Local OpenAI-compatible endpoint
# OpenAI equivalent: https://api.openai.com/v1

LLM_API_KEY=ollama
# Ollama: Always use "ollama" (no authentication required)
# OpenAI: Use your real API key (e.g. sk-xxxx)


LLM_EMBEDDING_MODEL=argus-ai/pplx-embed-v1-0.6b:fp32
# Ollama: Local embedding model
# OpenAI equivalent:
#   - text-embedding-3-small (1536 dims)


LLM_CHAT_MODEL=llama3.1:8b
# Ollama: Local chat / instruction model
# OpenAI equivalent:
#   - gpt-4o
#   - gpt-4o-mini

VECTOR_SIZE=1024
# OpenAI: 1536


# Legacy (still supported)
OPENAI_API_KEY=your_openai_key
# Only used when LLM_PROVIDER=openai

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
  
  llm:
    provider: "${LLM_PROVIDER}"
    base_url: "${LLM_BASE_URL}"
    api_key: "${LLM_API_KEY}" # {OPENAI_API_KEY} if LLM_ PROVIDER=openai
    models:
      embeddings: "${LLM_EMBEDDING_MODEL}"
      chat: "${LLM_CHAT_MODEL}"
    request:
      batch_size: 100
    embeddings:
      vector_size: ${VECTOR_SIZE}
  
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
qdrant-loader init --workspace .

# Load data from configured sources
qdrant-loader ingest --workspace .

# Check project status
qdrant-loader project --workspace . status
```

## <img src="/assets/icons/library/wrench-icon.svg" width="32" alt="Congiguration icon"> Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `QDRANT_URL` | QDrant instance URL | `http://localhost:6333` | Yes |
| `QDRANT_API_KEY` | QDrant API key | None | Cloud only |
| `QDRANT_COLLECTION_NAME` | Collection name | `documents` | Yes |
| `LLM_API_KEY` | LLM API key (unified) | None | Yes |
| `OPENAI_API_KEY` | OpenAI API key (legacy) | None | Legacy |
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

## <img src="/assets/icons/library/target-icon.svg" width="32" alt="Example icon"> Usage Examples

### Basic Commands

```bash
# Show current configuration
qdrant-loader config --workspace .

# Initialize collection (one-time setup)
qdrant-loader init --workspace .

# Ingest data from all configured sources
qdrant-loader ingest --workspace .

# Check project status
qdrant-loader project status --workspace .

# List all projects
qdrant-loader project list --workspace .

# Show help
qdrant-loader --help
```

### Advanced Usage

```bash
# Specify configuration files individually
qdrant-loader --config config.yaml --env .env ingest

# Debug logging
qdrant-loader ingest --workspace . --log-level DEBUG

# Force full re-ingestion
qdrant-loader init --workspace . --force
qdrant-loader ingest --workspace .

# Process specific project
qdrant-loader ingest --workspace . --project my-project

# Process specific source type
qdrant-loader ingest --workspace . --source-type git

# Enable performance profiling
qdrant-loader ingest --workspace . --profile
```

### Project Management

```bash
# Validate project configurations
qdrant-loader project validate --workspace .

# Validate specific project
qdrant-loader project validate --workspace . --project-id my-project

# Show project status in JSON format
qdrant-loader project status --workspace . --format json

# Show specific project status
qdrant-loader project status --workspace . --project-id my-project
```

## <img src="/assets/icons/library/architect-icon.svg" width="32" alt="Architecture Icon"> Architecture

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

## <img src="/assets/icons/library/test-tube-icon.svg" width="32" alt="Testing Icon"> Testing

```bash
# Run all tests
pytest packages/qdrant-loader/tests/

# Run with coverage
pytest --cov=qdrant_loader packages/qdrant-loader/tests/

# Run specific test categories
pytest -m "unit" packages/qdrant-loader/tests/
pytest -m "integration" packages/qdrant-loader/tests/
```

## <img src="/assets/icons/library/hand-sake-icon.svg" width="32" alt="Contributing icon"> Contributing

This package is part of the QDrant Loader monorepo. See the [main contributing guide](../../CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install in development mode
pip install -e "packages/qdrant-loader[dev]"

# Run tests
pytest packages/qdrant-loader/tests/
```

## <img src="/assets/icons/library/book-icon.svg" width="32" alt="Documentation icon"> Documentation

- **[Complete Documentation](../../docs/)** - Comprehensive guides and references
- **[Getting Started](../../docs/getting-started/)** - Quick start and core concepts
- **[User Guides](../../docs/users/)** - Detailed usage instructions
- **[Developer Docs](../../docs/developers/)** - Architecture and API reference

## <img src="/assets/icons/library/sos-icon.svg" width="32" alt="Support Icon"> Support

- **[Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community Q&A
- **[Documentation](../../docs/)** - Comprehensive guides

## <img src="/assets/icons/library/file-icon.svg" width="32" alt="License icon"> License

This project is licensed under the GNU GPLv3 - see the [LICENSE](../../LICENSE) file for details.

---

**Ready to load your data?** Check out the [Quick Start Guide](../../docs/getting-started/quick-start.md) or explore the [complete documentation](../../docs/).
