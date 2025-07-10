# QDrant Loader

[![PyPI - qdrant-loader](https://img.shields.io/pypi/v/qdrant-loader?label=qdrant-loader)](https://pypi.org/project/qdrant-loader/)
[![PyPI - mcp-server](https://img.shields.io/pypi/v/qdrant-loader-mcp-server?label=mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![Test Coverage](https://img.shields.io/badge/coverage-view%20reports-blue)](https://qdrant-loader.net/coverage/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

📋 **[Release Notes v0.4.12](./RELEASE_NOTES.md)** - Latest improvements and bug fixes (July 10, 2025)

A comprehensive toolkit for loading data into Qdrant vector database with advanced MCP server support for AI-powered development workflows.

## 🎯 What is QDrant Loader?

QDrant Loader is a powerful data ingestion and retrieval system that bridges the gap between your technical content and AI development tools. It collects, processes, and vectorizes content from multiple sources, then provides intelligent search capabilities through a Model Context Protocol (MCP) server.

**Perfect for:**

- 🤖 **AI-powered development** with Cursor, Windsurf, and GitHub Copilot
- 📚 **Knowledge base creation** from scattered documentation
- 🔍 **Intelligent code assistance** with contextual documentation
- 🏢 **Enterprise content integration** from Confluence, JIRA, and Git repositories

## 📦 Packages

This monorepo contains two complementary packages:

### 🔄 [QDrant Loader](./packages/qdrant-loader/)

_Data ingestion and processing engine_

Collects and vectorizes content from multiple sources into QDrant vector database.

**Key Features:**

- **Multi-source connectors**: Git, Confluence (Cloud & Data Center), JIRA (Cloud & Data Center), Public Docs, Local Files
- **Advanced file conversion**: 20+ file types including PDF, Office docs, images with AI-powered processing
- **Intelligent chunking**: Smart document processing with metadata extraction
- **Incremental updates**: Change detection and efficient synchronization
- **Flexible embeddings**: OpenAI, local models, and custom endpoints

### 🔌 [QDrant Loader MCP Server](./packages/qdrant-loader-mcp-server/)

_AI development integration layer_

Model Context Protocol server providing RAG capabilities to AI development tools.

**Key Features:**

- **MCP protocol compliance**: Full integration with Cursor, Windsurf, and Claude Desktop
- **Advanced search tools**: Semantic, hierarchy-aware, and attachment-focused search
- **Confluence intelligence**: Deep understanding of page hierarchies and relationships
- **File attachment support**: Comprehensive attachment discovery with parent document context
- **Real-time processing**: Streaming responses for large result sets

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
   mkdir my-qdrant-workspace && cd my-qdrant-workspace
   ```

2. **Download configuration templates**

   ```bash
   curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
   curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template
   ```

3. **Configure your environment** (edit `.env`)

   ```bash
   QDRANT_URL=http://localhost:6333
   QDRANT_COLLECTION_NAME=my_docs
   OPENAI_API_KEY=your_openai_key
   ```

4. **Configure data sources** (edit `config.yaml`)

   ```yaml
   sources:
     git:
       - url: "https://github.com/your-org/your-repo.git"
         branch: "main"
   ```

5. **Load your data**

   ```bash
   qdrant-loader --workspace . init
   qdrant-loader --workspace . ingest
   ```

6. **Start the MCP server**

   ```bash
   mcp-qdrant-loader
   ```

**🎉 You're ready!** Your content is now searchable through AI development tools.

## 🔧 Integration Examples

### Cursor IDE Integration

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "/path/to/venv/bin/mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION_NAME": "my_docs",
        "OPENAI_API_KEY": "your_key",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
    }
  }
}
```

### Example Queries in Cursor

- _"Find documentation about authentication in our API"_
- _"Show me examples of error handling patterns"_
- _"What are the deployment requirements for this service?"_
- _"Find all attachments related to database schema"_

## 📁 Project Structure

```text
qdrant-loader/
├── packages/
│   ├── qdrant-loader/           # Core data ingestion package
│   └── qdrant-loader-mcp-server/ # MCP server for AI integration
├── docs/                        # Comprehensive documentation
├── website/                     # Documentation website generator
└── README.md                   # This file
```

## 📚 Documentation

### 🚀 Getting Started

- **[What is QDrant Loader?](./docs/getting-started/what-is-qdrant-loader.md)** - Project overview and use cases
- **[Installation Guide](./docs/getting-started/installation.md)** - Complete installation instructions
- **[Quick Start](./docs/getting-started/quick-start.md)** - 5-minute getting started guide
- **[Core Concepts](./docs/getting-started/core-concepts.md)** - Vector databases and embeddings explained

### 👥 For Users

- **[User Documentation](./docs/users/)** - Comprehensive user guides
- **[Data Sources](./docs/users/detailed-guides/data-sources/)** - Git, Confluence, JIRA, and more
- **[File Conversion](./docs/users/detailed-guides/file-conversion/)** - PDF, Office docs, images processing
- **[MCP Server](./docs/users/detailed-guides/mcp-server/)** - AI development integration
- **[Configuration](./docs/users/configuration/)** - Complete configuration reference

### 🛠️ For Developers

- **[Developer Documentation](./docs/developers/)** - Architecture and contribution guides
- **[Architecture](./docs/developers/architecture/)** - System design and components
- **[Testing](./docs/developers/testing/)** - Testing guide and best practices
- **[Deployment](./docs/developers/deployment/)** - Deployment guide and configurations
- **[Extending](./docs/developers/extending/)** - Custom data sources and processors

### 📦 Package Documentation

- **[QDrant Loader Package](./packages/qdrant-loader/)** - Core loader documentation
- **[MCP Server Package](./packages/qdrant-loader-mcp-server/)** - MCP server documentation
- **[Website Generator](./website/)** - Documentation website

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details on:

- Setting up the development environment
- Code style and standards
- Pull request process
- Issue reporting guidelines

### Quick Development Setup

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
```

## 🆘 Support

- **[Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community discussions and Q&A
- **[Documentation](./docs/)** - Comprehensive guides and references

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](LICENSE) file for details.

---

**Ready to supercharge your AI development workflow?** Start with our [Quick Start Guide](./docs/getting-started/quick-start.md) or explore the [complete documentation](./docs/).
