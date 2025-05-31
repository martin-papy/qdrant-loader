# QDrant Loader

A comprehensive toolkit for loading data into Qdrant vector database with MCP server support.

## 📦 Packages

This repository contains two main packages:

### 🔄 [qdrant-loader](./packages/qdrant-loader/)

A tool for collecting and vectorizing technical content from multiple sources and storing it in a QDrant vector database.

**Features:**

- Multiple data source connectors (Git, Confluence Cloud & Data Center, JIRA Cloud & Data Center, Public Docs, Local Files)
- **File conversion support** - Process PDF, Office docs, images, and more with automatic conversion to markdown
  - **Powered by [Microsoft MarkItDown](https://github.com/microsoft/markitdown)** - Leverages Microsoft's robust file conversion library
  - **AI-powered image descriptions** - LLM integration for intelligent image content extraction
- Intelligent document processing and chunking
- Vector embeddings with OpenAI
- Incremental updates and change detection
- Performance monitoring and optimization

### 🔌 [qdrant-loader-mcp-server](./packages/qdrant-loader-mcp-server/)

A Model Context Protocol (MCP) server that provides RAG capabilities to Cursor and other LLM applications using Qdrant.

**Features:**

- MCP protocol implementation for LLM integration
- **Hierarchy-Aware Search** - Enhanced Confluence search with page hierarchy understanding
- **Attachment-Aware Search** - Comprehensive file attachment support and parent document relationships
- **Advanced Search Tools** - Three specialized search tools for different use cases
- **Three Specialized Search Tools**: `search`, `hierarchy_search`, and `attachment_search` for different use cases
- **Enhanced Search Results**: Rich visual indicators for navigation context and file metadata
- **Advanced Filtering**: Support for filtering by hierarchy depth, parent pages, file types, sizes, and authors
- Semantic search capabilities
- Real-time query processing
- Integration with Cursor IDE

## 🚀 Quick Start

### Installation

Install both packages in development mode:

```bash
# Clone the repository
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]
```

### Configuration

#### Option 1: Workspace Mode (Recommended)

The `--workspace` flag simplifies configuration by automatically discovering config files in a directory:

```bash
# Create a workspace directory
mkdir my-qdrant-workspace
cd my-qdrant-workspace

# Copy configuration templates
cp packages/qdrant-loader/conf/config.template.yaml config.yaml
cp packages/qdrant-loader/conf/.env.template .env

# Edit configuration files
# .env: Add your API keys and configuration
# config.yaml: Configure your data sources

# Use workspace mode - automatically finds config.yaml and .env
qdrant-loader --workspace . init
qdrant-loader --workspace . ingest
```

#### Option 2: Individual Files

```bash
# Specify configuration files individually
cp packages/qdrant-loader/conf/config.template.yaml config.yaml
cp packages/qdrant-loader/conf/.env.template .env

# Edit configuration files
qdrant-loader --config config.yaml --env .env init
qdrant-loader --config config.yaml --env .env ingest
```

### Usage

#### QDrant Loader

```bash
# Initialize QDrant collection
qdrant-loader init

# Load data from configured sources
qdrant-loader ingest

# Check status
qdrant-loader status

# Show current configuration
qdrant-loader config
```

#### MCP Server

```bash
# Start the MCP server
mcp-qdrant-loader

# Show help and available options
mcp-qdrant-loader --help

# Show version information
mcp-qdrant-loader --version
```

## 🏗️ Development

### Project Structure

```text
qdrant-loader/
├── packages/
│   ├── qdrant-loader/           # Core loader functionality
│   │   ├── src/qdrant_loader/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── qdrant-loader-mcp-server/ # MCP server functionality
│       ├── src/qdrant_loader_mcp_server/
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
├── docs/                        # Shared documentation
├── .github/workflows/           # CI/CD pipelines
├── pyproject.toml              # Workspace configuration
└── README.md                   # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests for specific package
pytest packages/qdrant-loader/tests/
pytest packages/qdrant-loader-mcp-server/tests/

# Run with coverage
pytest --cov=packages --cov-report=html
```

### Code Quality

```bash
# Format code
black packages/
isort packages/

# Lint code
ruff check packages/

# Type checking
mypy packages/
```

## 📚 Documentation

### Core Documentation

- [QDrant Loader Documentation](./packages/qdrant-loader/README.md)
- [MCP Server Documentation](./packages/qdrant-loader-mcp-server/README.md)
- [**🆕 File Conversion Guide**](./docs/FileConversionGuide.md)
- [**🆕 Migration Guide (v0.3.2)**](./docs/MigrationGuide.md)

### MCP Server Advanced Features (v0.3.2)

- [**🆕 Advanced Search Examples**](./docs/mcp-server/SearchExamples.md) - Comprehensive examples of hierarchy and attachment search capabilities
- [**🆕 Hierarchy Search Guide**](./docs/mcp-server/SearchHierarchyExemple.md) - Confluence hierarchy navigation, filtering, and organization
- [**🆕 Attachment Search Guide**](./docs/mcp-server/AttachementSearchExemple.md) - File attachment discovery, filtering, and parent document relationships

### General Documentation

- [Release Management Guide](./docs/RELEASE.md)
- [Features Overview](./docs/Features.md)
- [Confluence Data Center Support](./docs/ConfluenceDataCenterSupport.md)
- [JIRA Data Center Support](./docs/JiraDataCenterSupport.md)
- [Client Usage Guide](./docs/ClientUsage.md)
- [Contributing Guide](./docs/CONTRIBUTING.md)

## 🔧 Configuration

Both packages share common configuration patterns but have their own specific settings:

- **QDrant Loader**: Configured via `config.yaml` and environment variables
- **MCP Server**: Configured via environment variables and command-line arguments

See individual package documentation for detailed configuration options.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./docs/CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes in the appropriate package
4. Add tests for your changes
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- [Issues](https://github.com/martin-papy/qdrant-loader/issues)
- [Discussions](https://github.com/martin-papy/qdrant-loader/discussions)
- [Documentation](./docs/)

## 🏷️ Releases

Both packages use **unified versioning** - they always have the same version number:

- **qdrant-loader**: [![PyPI](https://img.shields.io/pypi/v/qdrant-loader)](https://pypi.org/project/qdrant-loader/)
- **qdrant-loader-mcp-server**: [![PyPI](https://img.shields.io/pypi/v/qdrant-loader-mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)

**📊 Test Coverage**: [View detailed coverage reports](https://martin-papy.github.io/qdrant-loader/)

### Release Management

Use the `release.py` script to manage releases:

```bash
# Check release readiness (dry run)
python release.py --dry-run

# Sync package versions if needed
python release.py --sync-versions

# Create a new release
python release.py
```

The script performs comprehensive safety checks and ensures both packages are released with the same version number.
