# Developer Documentation

Welcome to the QDrant Loader developer documentation! This section provides comprehensive guides for understanding the architecture, extending functionality, and contributing to the project.

## 🎯 What You'll Find Here

This documentation is designed for developers who want to:

- **Understand the architecture** - How QDrant Loader works internally
- **Extend functionality** - Add new data source connectors or file converters
- **Contribute to the project** - Submit bug fixes, improvements, and new features
- **Deploy and maintain** - Set up production environments and monitoring

## 📚 Documentation Sections

### 🏗️ Architecture and Design

- **[Architecture Overview](./architecture/)** - System design, components, and data flow
- **[Core Components](./architecture/core-components.md)** - Detailed component documentation
- **[Data Flow](./architecture/data-flow.md)** - How data moves through the system
- **[Connector System](./architecture/connector-system.md)** - Data source connector architecture

### 🔧 CLI and MCP Reference

- **[CLI Documentation](./cli/)** - Command-line interface reference and examples
- **[MCP Server Documentation](./mcp-server/)** - Model Context Protocol server interfaces
- **[Configuration Reference](./configuration/)** - Complete configuration options

### 🚀 Extending QDrant Loader

- **[Extension Guide](./extending/)** - How to add new functionality
- **[Data Source Connectors](./extending/data-source-connectors.md)** - Creating new data source integrations
- **[File Converters](./extending/file-converters.md)** - Adding support for new file formats
- **[MCP Search Tools](./extending/mcp-search-tools.md)** - Extending MCP server search capabilities

### 🧪 Testing and Quality

- **[Testing Guide](./testing/)** - Comprehensive testing documentation
- **[Unit Testing](./testing/unit-testing.md)** - Writing and running unit tests
- **[Integration Testing](./testing/integration-testing.md)** - End-to-end testing strategies
- **[Quality Assurance](./testing/quality-assurance.md)** - Code quality and review processes

### 🚀 Deployment and Operations

- **[Deployment Guide](./deployment/)** - Production deployment strategies
- **[Environment Setup](./deployment/environment-setup.md)** - Setting up production environments
- **[Monitoring and Observability](./deployment/monitoring.md)** - Logging, metrics, and alerting
- **[Performance Tuning](./deployment/performance-tuning.md)** - Production optimization

## 🎯 Quick Navigation by Role

### 🔍 I want to understand how QDrant Loader works

**Recommended path**:

1. **[Architecture Overview](./architecture/)** - Start with the big picture
2. **[Core Components](./architecture/core-components.md)** - Understand key components
3. **[Data Flow](./architecture/data-flow.md)** - See how data moves through the system
4. **[CLI Documentation](./cli/)** - Explore the command-line interface

### 🛠️ I want to add a new data source

**Recommended path**:

1. **[Data Source Connectors](./extending/data-source-connectors.md)** - Learn the connector pattern
2. **[Connector System](./architecture/connector-system.md)** - Understand the connector architecture
3. **[Testing Guide](./testing/)** - Write tests for your connector
4. **[Contributing Guidelines](../../CONTRIBUTING.md)** - Submit your contribution

### 📄 I want to add support for a new file format

**Recommended path**:

1. **[File Converters](./extending/file-converters.md)** - Learn the converter interface
2. **[Core Components](./architecture/core-components.md)** - Understand file processing
3. **[Unit Testing](./testing/unit-testing.md)** - Test your converter
4. **[Configuration Reference](./configuration/)** - Integrate with the config system

### 🤖 I want to extend the MCP server

**Recommended path**:

1. **[MCP Server Documentation](./mcp-server/)** - Understand the MCP interfaces
2. **[MCP Search Tools](./extending/mcp-search-tools.md)** - Learn about search tool development
3. **[Integration Testing](./testing/integration-testing.md)** - Test MCP integrations

### 🚀 I want to deploy QDrant Loader in production

**Recommended path**:

1. **[Deployment Guide](./deployment/)** - Choose your deployment strategy
2. **[Environment Setup](./deployment/environment-setup.md)** - Set up production environment
3. **[Monitoring and Observability](./deployment/monitoring.md)** - Set up monitoring
4. **[Performance Tuning](./deployment/performance-tuning.md)** - Optimize for production

### 🐛 I want to fix a bug or contribute

**Recommended path**:

1. **[Contributing Guidelines](../../CONTRIBUTING.md)** - Understand the contribution process
2. **[Architecture Overview](./architecture/)** - Get familiar with the codebase
3. **[Testing Guide](./testing/)** - Write tests for your changes
4. **[Quality Assurance](./testing/quality-assurance.md)** - Follow quality standards

## 🏗️ System Architecture Overview

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │  QDrant Loader  │    │   AI Tools      │
│                 │    │                 │    │                 │
│ • Git Repos     │───▶│ • CLI Tool      │───▶│ • Cursor IDE    │
│ • Confluence    │    │ • Data Pipeline │    │ • Windsurf      │
│ • JIRA          │    │ • File Convert  │    │ • Claude        │
│ • Local Files   │    │ • Vectorization │    │                 │
│ • Public Docs   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   QDrant DB     │
                       │                 │
                       │ • Vector Store  │
                       │ • Metadata      │
                       │ • Search Index  │
                       └─────────────────┘
                                ▲
                                │
                       ┌─────────────────┐
                       │   MCP Server    │
                       │                 │
                       │ • Search Tools  │
                       │ • Hierarchy Nav │
                       │ • Attachments   │
                       └─────────────────┘
```

### Core Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **Data Source Connectors** | Fetch content from various sources | Git, Confluence, JIRA, Local Files, Web |
| **File Converters** | Convert files to text | 20+ formats via MarkItDown |
| **Content Processors** | Process and chunk content | Text chunking, metadata extraction |
| **Embedding Service** | Generate embeddings | OpenAI integration |
| **QDrant Manager** | Manage vector storage | QDrant integration, collection management |
| **MCP Server** | AI tool integration | Search tools, hierarchy navigation |
| **CLI Interface** | Command-line operations | Ingestion, status, configuration |

### Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Language** | Python 3.12+ |
| **Vector Database** | QDrant |
| **Embeddings** | OpenAI API |
| **File Processing** | MarkItDown, PyPDF2, python-docx |
| **MCP Protocol** | Model Context Protocol |
| **Testing** | pytest, pytest-asyncio |
| **Packaging** | setuptools, pip |
| **CI/CD** | GitHub Actions |

## 🔧 Development Environment Setup

### Prerequisites

```bash
# Python 3.12 or higher
python --version

# Git for version control
git --version
```

### Quick Setup

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

# Run tests
pytest

# Start MCP server
mcp-qdrant-loader
```

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-data-source

# Make changes and test
pytest packages/

# Run linting and formatting
black packages/
isort packages/
ruff check packages/
mypy packages/

# Commit and push
git add .
git commit -m "feat: add new data source connector"
git push origin feature/new-data-source

# Create pull request
# Follow the PR template and guidelines
```

## 📊 Project Statistics

### Codebase Overview

| Metric | Value |
|--------|-------|
| **Languages** | Python (primary), YAML, Markdown |
| **Packages** | 2 (qdrant-loader, qdrant-loader-mcp-server) |
| **Data Sources** | 5 (Git, Confluence, JIRA, Local Files, Public Docs) |
| **File Formats** | 20+ (via MarkItDown integration) |
| **Test Coverage** | 85%+ target |
| **Documentation** | Comprehensive user and developer guides |

### Supported Integrations

| Category | Count | Examples |
|----------|-------|----------|
| **Data Sources** | 5 | GitHub, GitLab, Confluence Cloud/DC, JIRA Cloud/DC |
| **File Formats** | 20+ | PDF, DOCX, PPTX, XLSX, Images, Audio |
| **AI Tools** | 3+ | Cursor, Windsurf, Claude Desktop |
| **Vector Stores** | 1 | QDrant |
| **Embedding Models** | 1 | OpenAI |

## 🎯 Contribution Areas

### High-Priority Areas

1. **New Data Sources** - Slack, Notion, SharePoint, Dropbox
2. **Enhanced File Processing** - Better OCR, audio transcription
3. **Performance Optimization** - Parallel processing, caching
4. **MCP Tool Enhancement** - More search tools, better filtering
5. **Deployment Tools** - Docker images, deployment scripts

### Good First Issues

- **Documentation improvements** - Fix typos, add examples
- **Test coverage** - Add unit tests for existing code
- **Configuration validation** - Better error messages
- **CLI enhancements** - New commands, better output
- **Example configurations** - Real-world use cases

### Advanced Contributions

- **New vector store backends** - Pinecone, Weaviate, Chroma
- **Custom embedding models** - Local model support
- **Advanced search features** - Hybrid search, reranking
- **Monitoring and observability** - Metrics, tracing
- **Performance optimizations** - Async processing, streaming

## 📚 Learning Resources

### Understanding the Codebase

1. **Start with the CLI** - `packages/qdrant-loader/src/qdrant_loader/cli/`
2. **Explore data connectors** - `packages/qdrant-loader/src/qdrant_loader/connectors/`
3. **Study file conversion** - `packages/qdrant-loader/src/qdrant_loader/core/file_conversion/`
4. **Examine the MCP server** - `packages/qdrant-loader-mcp-server/src/`

### External Resources

- **[QDrant Documentation](https://qdrant.tech/documentation/)** - Vector database concepts
- **[OpenAI API](https://platform.openai.com/docs)** - Embedding and API usage
- **[Model Context Protocol](https://modelcontextprotocol.io/)** - MCP specification
- **[MarkItDown](https://github.com/microsoft/markitdown)** - File conversion library

## 🆘 Getting Developer Help

### Community Resources

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Development questions and ideas
- **[Contributing Guide](../../CONTRIBUTING.md)** - Detailed contribution guidelines

### Development Support

- **Architecture questions** - Ask in GitHub Discussions
- **Bug reports** - Use GitHub Issues with detailed reproduction steps
- **Feature proposals** - Start with GitHub Discussions for feedback
- **Code reviews** - Submit PRs following the contribution guidelines

### Documentation Feedback

Found issues with the developer documentation?

- **[Report documentation bugs](https://github.com/martin-papy/qdrant-loader/issues/new?labels=documentation,developer-docs)**
- **[Suggest improvements](https://github.com/martin-papy/qdrant-loader/discussions/new?category=ideas)**
- **[Contribute documentation](../../CONTRIBUTING.md#documentation-contributions)**

---

**Ready to start developing?** Choose your area of interest above and dive into the detailed guides. If you're new to the codebase, start with the [Architecture Overview](./architecture/) to understand how everything fits together.
