# QDrant Loader

[![PyPI - qdrant-loader](https://img.shields.io/pypi/v/qdrant-loader?label=qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![PyPI - mcp-server](https://img.shields.io/pypi/v/qdrant-loader-mcp-server?label=mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![PyPI - qdrant-loader-core](https://img.shields.io/pypi/v/qdrant-loader-core?label=qdrant-loader-core)](https://pypi.org/project/qdrant-loader-core/)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/martin-papy/qdrant-loader?labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
[![Test Coverage](https://img.shields.io/badge/coverage-view%20reports-blue)](https://qdrant-loader.net/coverage/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

📋 **[Release Notes v0.7.3](./RELEASE_NOTES.md)** - Latest improvements and bug fixes

A comprehensive toolkit for loading data into Qdrant vector database with advanced MCP server support for AI-powered development workflows.

## 🎯 What is QDrant Loader?

QDrant Loader is a data ingestion and retrieval system that collects content from multiple sources, processes and vectorizes it, then provides intelligent search capabilities through a Model Context Protocol (MCP) server for AI development tools.

**Perfect for:**

- 🤖 **AI-powered development** with Cursor, Windsurf, and other MCP-compatible tools
- 📚 **Knowledge base creation** from technical documentation
- 🔍 **Intelligent code assistance** with contextual information
- 🏢 **Enterprise content integration** from multiple data sources

## 📦 Packages

This monorepo contains three complementary packages:

### 🔄 [QDrant Loader](./packages/qdrant-loader/)

Data ingestion and processing engine

Collects and vectorizes content from multiple sources into QDrant vector database.

**Key Features:**

- **Multi-source connectors**: Git, Confluence (Cloud & Data Center), JIRA (Cloud & Data Center), Public Docs, Local Files
- **File conversion**: PDF, Office docs (Word, Excel, PowerPoint), images, audio, EPUB, ZIP, and more using MarkItDown
- **Smart chunking**: Modular chunking strategies with intelligent document processing and hierarchical context
- **Incremental updates**: Change detection and efficient synchronization
- **Multi-project support**: Organize sources into projects with shared collections
- **Provider-agnostic LLM**: OpenAI, Azure OpenAI, Ollama, and custom endpoints with unified configuration

### ⚙️ [QDrant Loader Core](./packages/qdrant-loader-core/)

Core library and LLM abstraction layer

Provides the foundational components and provider-agnostic LLM interface used by other packages.

**Key Features:**

- **LLM Provider Abstraction**: Unified interface for OpenAI, Azure OpenAI, Ollama, and custom endpoints
- **Configuration Management**: Centralized settings and validation for LLM providers
- **Rate Limiting**: Built-in rate limiting and request management
- **Error Handling**: Robust error handling and retry mechanisms
- **Logging**: Structured logging with configurable levels

### 🔌 [QDrant Loader MCP Server](./packages/qdrant-loader-mcp-server/)

AI development integration layer

Model Context Protocol server providing search capabilities to AI development tools.

**Key Features:**

- **MCP Protocol 2025-06-18**: Latest protocol compliance with dual transport support (stdio + HTTP)
- **Advanced search tools**: Semantic search, hierarchy-aware search, attachment discovery, and conflict detection
- **Cross-document intelligence**: Document similarity, clustering, relationship analysis, and knowledge graphs
- **Streaming capabilities**: Server-Sent Events (SSE) for real-time search results
- **Production-ready**: HTTP transport with security, session management, and health checks

## 🚀 Quick Start

### Installation

```bash
# Install both packages
pip install qdrant-loader qdrant-loader-mcp-server

# Or install individually
pip install qdrant-loader          # Data ingestion only
pip install qdrant-loader-mcp-server  # MCP server only
```

### 5-Minute Setup

1. **Create a workspace**

   ```bash
   mkdir my-workspace && cd my-workspace
   ```

2. **Initialize workspace with templates**

   ```bash
   qdrant-loader init --workspace .
   ```

3. **Configure your environment** (edit `.env`)

   ```bash
   # Qdrant connection
   QDRANT_URL=http://localhost:6333
   QDRANT_COLLECTION_NAME=my_docs

   # LLM provider (new unified configuration)
   OPENAI_API_KEY=your_openai_key
   LLM_PROVIDER=openai
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_EMBEDDING_MODEL=text-embedding-3-small
   LLM_CHAT_MODEL=gpt-4o-mini
   ```

4. **Configure data sources** (edit `config.yaml`)

   ```yaml
   global:
     qdrant:
       url: "http://localhost:6333"
       collection_name: "my_docs"
     llm:
       provider: "openai"
       base_url: "https://api.openai.com/v1"
       api_key: "${OPENAI_API_KEY}"
       models:
         embeddings: "text-embedding-3-small"
         chat: "gpt-4o-mini"
       embeddings:
         vector_size: 1536

   projects:
     my-project:
       project_id: "my-project"
       sources:
         git:
           docs-repo:
             base_url: "https://github.com/your-org/your-repo.git"
             branch: "main"
             file_types: ["*.md", "*.rst"]
   ```

5. **Load your data**

   ```bash
   qdrant-loader ingest --workspace .
   ```

6. **Start the MCP server**

   ```bash
   mcp-qdrant-loader --env /path/tp/your/.env
   ```

## 🔧 Integration with Cursor

Add to your Cursor settings (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "/path/to/venv/bin/mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION_NAME": "my_docs",
        "OPENAI_API_KEY": "your_key"
      }
    }
  }
}
```

**Alternative: Use configuration file** (recommended for complex setups):

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "/path/to/venv/bin/mcp-qdrant-loader",
      "args": ["--config", "/path/to/your/config.yaml", "--env", "/path/to/your/.env"]
    }
  }
}
```

**Example queries in Cursor:**

- _"Find documentation about authentication in our API"_
- _"Show me examples of error handling patterns"_
- _"What are the deployment requirements for this service?"_
- _"Find all attachments related to database schema"_

## 📚 Documentation

### 🚀 Getting Started

- **[Installation Guide](./docs/getting-started/installation.md)** - Complete setup instructions
- **[Quick Start](./docs/getting-started/quick-start.md)** - Step-by-step tutorial
- **Core Concepts** - Covered inline in Getting Started

### 👥 User Guides

- **[Configuration](./docs/users/configuration/)** - Complete configuration reference
- **[Data Sources](./docs/users/detailed-guides/data-sources/)** - Git, Confluence, JIRA setup
- **[File Conversion](./docs/users/detailed-guides/file-conversion/)** - File processing capabilities
- **[MCP Server](./docs/users/detailed-guides/mcp-server/)** - AI tool integration

## ⚠️ Migration Guide (v0.7.1+)

### LLM Configuration Migration Required

- **New unified configuration**: `global.llm.*` replaces legacy `global.embedding.*` and `file_conversion.markitdown.*`
- **Provider-agnostic**: Now supports OpenAI, Azure OpenAI, Ollama, and custom endpoints
- **Legacy support**: Old configuration still works but shows deprecation warnings
- **Action required**: Update your `config.yaml` to use the new syntax (see examples above)

### Migration Resources

- [Configuration File Reference](./docs/users/configuration/config-file-reference.md) - Complete new schema
- [Environment Variables](./docs/users/configuration/environment-variables.md) - Updated variable names

### 🛠️ Developer Resources

- **[Architecture](./docs/developers/architecture/)** - System design overview
- **[Testing](./docs/developers/testing/)** - Testing guide and best practices
- **[Contributing](./CONTRIBUTING.md)** - Development setup and guidelines

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](./CONTRIBUTING.md) for:

- Development environment setup
- Code style and standards
- Pull request process

### Quick Development Setup

```bash
# Clone and setup
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader
python -m venv venv
source venv/bin/activate

# Install packages in development mode
pip install -e ".[dev]"
pip install -e "packages/qdrant-loader-core[dev,openai,ollama]"
pip install -e "packages/qdrant-loader[dev]"
pip install -e "packages/qdrant-loader-mcp-server[dev]"
```

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](LICENSE) file for details.

---

**Ready to get started?** Check out our [Quick Start Guide](./docs/getting-started/quick-start.md) or browse the [complete documentation](./docs/).
