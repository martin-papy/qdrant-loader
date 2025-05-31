# QDrant Loader

A powerful tool for collecting and vectorizing technical content from multiple sources and storing it in a QDrant vector database. Part of the QDrant Loader monorepo ecosystem that enables AI-powered development workflows through tools like Cursor, Windsurf, and GitHub Copilot.

## 🚀 Features

### Core Capabilities

- **Multi-source ingestion**: Collect content from Git, Confluence Cloud & Data Center, JIRA Cloud & Data Center, public documentation, and local files
- **🆕 File conversion support**: Automatically convert PDF, Office documents, images, and 20+ file types to markdown for processing
- **Intelligent processing**: Smart chunking, preprocessing, and metadata extraction
- **Flexible embeddings**: Support for OpenAI, local models (BAAI/bge-small-en-v1.5), and custom endpoints
- **Vector storage**: Optimized storage in QDrant vector database
- **State management**: Incremental updates with SQLite-based state tracking
- **Performance monitoring**: Comprehensive logging and debugging capabilities

### 🆕 File Conversion Support (v0.3.2)

QDrant Loader now supports automatic conversion of diverse file formats using Microsoft's MarkItDown:

#### Supported File Types

- **Documents**: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
- **Images**: PNG, JPEG, GIF, BMP, TIFF (with optional OCR)
- **Archives**: ZIP files with automatic extraction
- **Data**: JSON, CSV, XML, YAML
- **Audio**: MP3, WAV (transcription support)
- **E-books**: EPUB format
- **And more**: 20+ file types supported

#### Key Features

- **Automatic detection**: Files are automatically detected and converted when `enable_file_conversion: true`
- **Attachment processing**: Download and convert attachments from Confluence, JIRA, and documentation sites
- **Fallback handling**: Graceful handling when conversion fails with minimal document creation
- **Metadata preservation**: Original file information preserved through the processing pipeline
- **Performance optimized**: Configurable size limits, timeouts, and lazy loading

See the [File Conversion Guide](../../docs/FileConversionGuide.md) for detailed setup and configuration.

### 🔄 Upgrading to v0.3.2

If you're upgrading from a previous version:

1. **Backup your data**: State database and configuration files
2. **Update package**: `pip install --upgrade qdrant-loader`
3. **Optional**: Enable file conversion in your configuration
4. **Test**: Verify existing functionality and new file conversion features

See the [Migration Guide](../../docs/MigrationGuide.md) for detailed upgrade instructions.

### 🆕 New: Data Center Support

QDrant Loader now supports **both Cloud and Data Center/Server** deployments for Atlassian products:

#### Confluence Data Center Support

- **Secure authentication methods**: API tokens (Cloud) and Personal Access Tokens (Data Center)
- **Deployment-specific optimization**: Proper pagination and API handling for each deployment type
- **Seamless migration**: Easy transition from Cloud to Data Center configurations
- **Auto-detection**: Automatic deployment type detection based on URL patterns

#### JIRA Data Center Support

- **Multi-deployment authentication**: Basic Auth (Cloud) and Bearer tokens (Data Center)
- **User field compatibility**: Handles different user formats between deployments
- **Optimized performance**: Deployment-specific rate limiting and page sizes
- **Cross-deployment features**: All JIRA features work across both deployment types

See our detailed guides:

- [Confluence Data Center Support Guide](../../docs/ConfluenceDataCenterSupport.md)
- [JIRA Data Center Support Guide](../../docs/JiraDataCenterSupport.md)

### Advanced Features

- **Change detection**: Intelligent incremental updates for all source types
- **Configurable chunking**: Token-based chunking with customizable overlap
- **Batch processing**: Efficient batch embedding with rate limiting
- **Error recovery**: Robust error handling and retry mechanisms
- **Extensible architecture**: Plugin-based connector system for custom sources

## 🔌 Supported Connectors

| Connector | Description | Key Features |
|-----------|-------------|--------------|
| **Git** | Code and documentation from repositories | Branch selection, file filtering, commit metadata |
| **Confluence** | Technical documentation from Atlassian Cloud & Data Center | Space filtering, label-based selection, comment processing, secure authentication |
| **JIRA** | Issues and specifications from Cloud & Data Center | Project filtering, attachment processing, incremental sync, cross-deployment compatibility |
| **Public Docs** | External documentation websites | CSS selector-based extraction, version detection |
| **Local Files** | Local directories and files | Glob pattern matching, file type filtering |

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

## ⚡ Quick Start

### 1. Configuration Setup

```bash
# Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/env.template

# Edit configuration files
# .env: Add your API keys and database paths
# config.yaml: Configure your data sources
```

### 2. Environment Variables

Required variables:

```bash
# QDrant Configuration
QDRANT_URL=http://localhost:6333  # or your QDrant Cloud URL
QDRANT_COLLECTION_NAME=my_collection
QDRANT_API_KEY=your_api_key  # Required for cloud, optional for local

# Embedding Configuration
OPENAI_API_KEY=your_openai_key  # If using OpenAI embeddings

# State Management
STATE_DB_PATH=/path/to/state.db
```

Source-specific variables (as needed):

```bash
# Git
REPO_TOKEN=your_github_token
REPO_URL=https://github.com/user/repo.git

# Confluence (Cloud)
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_SPACE_KEY=SPACE
CONFLUENCE_TOKEN=your_token
CONFLUENCE_EMAIL=your_email

# Confluence (Data Center/Server) - Personal Access Token
CONFLUENCE_PAT=your_personal_access_token

# JIRA (Cloud)
JIRA_URL=https://your-domain.atlassian.net
JIRA_PROJECT_KEY=PROJ
JIRA_TOKEN=your_token
JIRA_EMAIL=your_email

# JIRA (Data Center/Server) - Personal Access Token
JIRA_PAT=your_personal_access_token
```

### 3. Basic Usage

```bash
# Initialize QDrant collection
qdrant-loader init

# Run full ingestion
qdrant-loader ingest

# Source-specific ingestion
qdrant-loader ingest --source-type git
qdrant-loader ingest --source-type confluence --source my-space
```

## 🛠️ Advanced Usage

### Command Line Interface

```bash
# Show all available commands
qdrant-loader --help

# Configuration management
qdrant-loader config                    # Show current config
qdrant-loader config --validate         # Validate configuration

# Selective ingestion
qdrant-loader ingest --source-type git --source my-repo
qdrant-loader ingest --source-type localfile --source my-docs

# Debugging and monitoring
qdrant-loader ingest --log-level DEBUG
qdrant-loader status                    # Show ingestion status
```

### Configuration Examples

#### Git Repository

```yaml
sources:
  git:
    my-repo:
      base_url: "https://github.com/user/repo.git"
      branch: "main"
      include_paths: ["docs/**", "src/**", "README.md"]
      exclude_paths: ["node_modules/**", "*.log"]
      file_types: ["*.md", "*.py", "*.js", "*.ts"]
      max_file_size: 1048576  # 1MB
```

#### Confluence Space

```yaml
sources:
  confluence:
    # Confluence Cloud
    tech-docs-cloud:
      base_url: "${CONFLUENCE_URL}"
      deployment_type: "cloud"
      space_key: "TECH"
      content_types: ["page", "blogpost"]
      include_labels: ["public", "documentation"]
      exclude_labels: ["draft", "archived"]
      token: "${CONFLUENCE_TOKEN}"
      email: "${CONFLUENCE_EMAIL}"
    
    # Confluence Data Center with Personal Access Token
    tech-docs-datacenter:
      base_url: "https://confluence.company.com"
      deployment_type: "datacenter"
      space_key: "TECH"
      content_types: ["page", "blogpost"]
      token: "${CONFLUENCE_PAT}"
```

#### JIRA Project

```yaml
sources:
  jira:
    # JIRA Cloud
    support-cloud:
      base_url: "https://mycompany.atlassian.net"
      deployment_type: "cloud"
      project_key: "SUPPORT"
      token: "${JIRA_TOKEN}"
      email: "${JIRA_EMAIL}"
      page_size: 50
      requests_per_minute: 60
    
    # JIRA Data Center with Personal Access Token
    engineering-datacenter:
      base_url: "https://jira.company.com"
      deployment_type: "datacenter"
      project_key: "ENG"
      token: "${JIRA_PAT}"
      page_size: 100
      requests_per_minute: 120
```

#### Local Files

```yaml
sources:
  localfile:
    project-docs:
      base_url: "file:///path/to/docs"
      include_paths: ["**/*.md", "**/*.rst"]
      exclude_paths: ["archive/**", "tmp/**"]
      max_file_size: 2097152  # 2MB
```

## 🔧 Configuration Reference

### Global Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `chunking.chunk_size` | Maximum characters per chunk | 500 |
| `chunking.chunk_overlap` | Character overlap between chunks | 50 |
| `embedding.model` | Embedding model to use | text-embedding-3-small |
| `embedding.batch_size` | Batch size for embeddings | 100 |
| `embedding.endpoint` | Custom embedding endpoint | OpenAI API |

### State Management

| Setting | Description |
|---------|-------------|
| `state_management.database_path` | SQLite database path |
| `state_management.table_prefix` | Database table prefix |
| `state_management.connection_pool.size` | Connection pool size |

## 🔍 Monitoring and Debugging

### Logging Configuration

```bash
# Set log level
qdrant-loader ingest --log-level DEBUG

# Custom log format
export LOG_FORMAT=json  # or 'text'
export LOG_FILE=qdrant-loader.log
```

### Performance Monitoring

```bash
# Monitor ingestion progress
qdrant-loader status

# Check collection statistics
qdrant-loader stats

# Validate data integrity
qdrant-loader validate
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e packages/qdrant-loader[dev]

# Run tests
pytest packages/qdrant-loader/tests/
```

### Testing

```bash
# Run all tests
pytest packages/qdrant-loader/tests/

# Run with coverage
pytest --cov=qdrant_loader packages/qdrant-loader/tests/

# Run specific test categories
pytest packages/qdrant-loader/tests/unit/
pytest packages/qdrant-loader/tests/integration/
```

## 🔗 Integration

### With MCP Server

This package works seamlessly with the [qdrant-loader-mcp-server](../qdrant-loader-mcp-server/) for AI-powered development workflows:

```bash
# Install both packages
pip install qdrant-loader qdrant-loader-mcp-server

# Load data with qdrant-loader
qdrant-loader ingest

# Start MCP server for Cursor integration
mcp-qdrant-loader
```

### With AI Development Tools

- **Cursor**: Use with MCP server for contextual code assistance
- **Windsurf**: Compatible through MCP protocol
- **GitHub Copilot**: Enhanced context through vector search
- **Custom tools**: RESTful API for integration

## 📋 Requirements

- **Python**: 3.12 or higher
- **QDrant**: Local instance or QDrant Cloud
- **Storage**: Sufficient disk space for vector database and state management
- **Network**: Internet access for API calls and remote sources
- **Memory**: Minimum 4GB RAM recommended for large datasets

## 🤝 Contributing

We welcome contributions! See the [Contributing Guide](../../docs/CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make changes in `packages/qdrant-loader/`
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](../../LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
- **Discussions**: [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)
- **Documentation**: [Project Documentation](../../docs/)

## 🔄 Related Projects

- [qdrant-loader-mcp-server](../qdrant-loader-mcp-server/): MCP server for AI integration
- [QDrant](https://qdrant.tech/): Vector database engine
- [Model Context Protocol](https://modelcontextprotocol.io/): AI integration standard
