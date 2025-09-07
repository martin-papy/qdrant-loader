# Getting Started with QDrant Loader

Welcome to QDrant Loader! This section will help you understand, install, and start using QDrant Loader effectively, whether you're a content creator, researcher, developer, or system administrator.

## 🎯 Choose Your Path

### 🚀 I want to get started quickly

**[Quick Start Guide](./quick-start.md)** - Get up and running in 5 minutes with a basic setup.

### 🤔 I want to understand what this is

**[What is QDrant Loader?](./what-is-qdrant-loader.md)** - Learn about the project, its use cases, and how it can help you.

### 📚 I want to understand the concepts

**Core Concepts** - Covered inline on this page and throughout Getting Started.

### 💻 I need detailed installation instructions

**[Installation Guide](./installation.md)** - Complete installation instructions for all platforms and scenarios.

### ⚙️ I want to configure it properly

**[Basic Configuration](./basic-configuration.md)** - Essential configuration to get started with your data sources.

## 🎯 What You'll Learn

By the end of this section, you'll be able to:

- ✅ **Understand** what QDrant Loader is and how it can help your workflow
- ✅ **Install** QDrant Loader on your system
- ✅ **Configure** basic data sources (Git, local files, or documentation)
- ✅ **Load** your first content into QDrant
- ✅ **Search** your content using the MCP server
- ✅ **Integrate** with AI development tools like Cursor

## 🧠 Core Concepts

Understanding these key concepts will help you use QDrant Loader effectively:

### 🔄 Data Ingestion Pipeline

**QDrant Loader** processes content through a multi-stage pipeline:

1. **Collection** - Gathers content from configured data sources
2. **Conversion** - Transforms files (PDFs, Office docs, images) to text
3. **Chunking** - Splits content into optimal segments for search
4. **Embedding** - Creates vector representations using LLM providers (OpenAI, Azure OpenAI, Ollama, OpenAI-compatible)
5. **Storage** - Saves vectors and metadata to QDrant database

### 🏗️ Multi-Project Architecture

- **Projects** - Logical groupings of related data sources
- **Global Configuration** - Shared settings (LLM, chunking, QDrant)
- **Unified Collection** - All projects stored in same QDrant collection for cross-project search
- **Workspace Mode** - Recommended approach for organized project management

### 🔌 MCP Integration

**Model Context Protocol (MCP)** connects QDrant Loader to AI tools:

- **MCP Server** - Provides search tools to AI applications
- **Transport Modes** - Stdio (default) and HTTP for different use cases
- **Search Types** - Semantic, hierarchy-aware, and attachment-focused search
- **Real-time** - Streaming responses for fast AI interactions

### 📊 Data Sources

**Supported Sources** with intelligent processing:

- **Git** - Repositories, branches, commit history, file filtering
- **Confluence** - Pages, spaces, attachments, hierarchy preservation
- **JIRA** - Issues, projects, comments, attachment processing
- **Local Files** - Directories, glob patterns, recursive scanning
- **Public Docs** - External documentation sites with CSS extraction

### 🔍 Search Intelligence

**Advanced Search Capabilities**:

- **Semantic Search** - Understands meaning beyond keywords
- **Hierarchy Search** - Respects document relationships and structure
- **Attachment Search** - Finds files and their parent documents
- **Cross-Document** - Discovers relationships between different sources

## 🛤️ Recommended Learning Path

### For Everyone (20 minutes)

1. **[What is QDrant Loader?](./what-is-qdrant-loader.md)** *(3 min)* - Project overview
1. **Core Concepts** *(7 min)* - Key concepts summarized above
1. **[Quick Start](./quick-start.md)** *(10 min)* - Hands-on setup

### For Users (Additional 10 minutes)

1. **[Installation Guide](./installation.md)** *(5 min)* - Detailed installation
1. **[Basic Configuration](./basic-configuration.md)** *(5 min)* - Configuration essentials

### Next Steps

After completing the getting started section:

- **Users**: Explore [User Documentation](../users/) for detailed guides and advanced configuration
- **Developers**: Check out [Developer Documentation](../developers/) for architecture and contribution guides

## 🆘 Need Help?

- **Quick questions**: Check our [Troubleshooting Guide](../users/troubleshooting/)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
- **Discussions**: Join the conversation on [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)

---
**Ready to start?** Begin with [What is QDrant Loader?](./what-is-qdrant-loader.md) or jump straight to the [Quick Start Guide](./quick-start.md).
