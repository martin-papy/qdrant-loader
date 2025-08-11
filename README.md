# QDrant Loader

[![PyPI - qdrant-loader](https://img.shields.io/pypi/v/qdrant-loader?label=qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![PyPI - mcp-server](https://img.shields.io/pypi/v/qdrant-loader-mcp-server?label=mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/martin-papy/qdrant-loader?labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
[![Test Coverage](https://img.shields.io/badge/coverage-view%20reports-blue)](https://qdrant-loader.net/coverage/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

📋 **[Release Notes v0.6.0](./RELEASE_NOTES.md)** - Latest improvements and bug fixes (August 05, 2025)

A comprehensive toolkit for loading data into Qdrant vector database with advanced MCP server support for AI-powered development workflows.

## 🎯 What is QDrant Loader?

QDrant Loader is a data ingestion and retrieval system that collects content from multiple sources, processes and vectorizes it, then provides intelligent search capabilities through a Model Context Protocol (MCP) server for AI development tools.

**Perfect for:**

- 🤖 **AI-powered development** with Cursor, Windsurf, and other MCP-compatible tools
- 📚 **Knowledge base creation** from technical documentation
- 🔍 **Intelligent code assistance** with contextual information
- 🏢 **Enterprise content integration** from multiple data sources

## 📦 Packages

This monorepo contains two complementary packages:

### 🔄 [QDrant Loader](./packages/qdrant-loader/)

_Data ingestion and processing engine_

Collects and vectorizes content from multiple sources into QDrant vector database.

**Key Features:**

- **Multi-source connectors**: Git, Confluence (Cloud & Data Center), JIRA (Cloud & Data Center), Public Docs, Local Files
- **File conversion**: PDF, Office docs (Word, Excel, PowerPoint), images, audio, EPUB, ZIP, and more using MarkItDown
- **Smart chunking**: Intelligent document processing with metadata extraction and hierarchical context
- **Incremental updates**: Change detection and efficient synchronization
- **Multi-project support**: Organize sources into projects with shared collections
- **Flexible embeddings**: OpenAI, local models, and custom endpoints

### 🔌 [QDrant Loader MCP Server](./docs/packages/mcp-server/)

_AI development integration layer_

Model Context Protocol server providing search capabilities to AI development tools.

**Key Features:**

- **MCP protocol compliance**: Integration with Cursor, Windsurf, and Claude Desktop
- **Advanced search tools**: Semantic search, hierarchy-aware search, and attachment discovery
- **Cross-document intelligence**: Document similarity, clustering, and relationship analysis
- **Confluence support**: Understanding of page hierarchies and attachment relationships
- **Real-time processing**: Efficient search with result streaming

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
   qdrant-loader --workspace . init
   ```

3. **Configure your environment** (edit `.env`)

   ```bash
   QDRANT_URL=http://localhost:6333
   QDRANT_COLLECTION_NAME=my_docs
   OPENAI_API_KEY=your_openai_key
   ```

4. **Configure data sources** (edit `config.yaml`)

   ```yaml
   global_config:
     qdrant:
       url: "http://localhost:6333"
       collection_name: "my_docs"
     embedding:
       model: "text-embedding-3-small"
       api_key: "${OPENAI_API_KEY}"

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
   mcp-qdrant-loader
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
pip install -e "packages/qdrant-loader[dev]"
pip install -e "packages/qdrant-loader-mcp-server[dev]"

```

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](LICENSE) file for details.

---

**Ready to get started?** Check out our [Quick Start Guide](./docs/getting-started/quick-start.md) or browse the [complete documentation](./docs/).
