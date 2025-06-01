# QDrant Loader MCP Server

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader-mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader-mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Model Context Protocol (MCP) server that provides advanced Retrieval-Augmented Generation (RAG) capabilities to AI development tools. Part of the [QDrant Loader monorepo](../../) ecosystem.

## 🚀 What It Does

The MCP Server bridges your QDrant knowledge base with AI development tools:

- **Provides intelligent search** through semantic, hierarchy-aware, and attachment-focused tools
- **Integrates seamlessly** with Cursor, Windsurf, Claude Desktop, and other MCP-compatible tools
- **Understands context** including document hierarchies, file relationships, and metadata
- **Streams responses** for fast, real-time search results
- **Preserves relationships** between documents, attachments, and parent content

## 🔌 Supported AI Tools

| Tool | Status | Integration Features |
|------|--------|---------------------|
| **Cursor** | ✅ Full Support | Context-aware code assistance, documentation lookup, intelligent suggestions |
| **Windsurf** | ✅ Compatible | MCP protocol integration, semantic search capabilities |
| **Claude Desktop** | ✅ Compatible | Direct MCP integration, conversational search interface |
| **Other MCP Tools** | ✅ Compatible | Any tool supporting MCP 2024-11-05 specification |

## 🔍 Advanced Search Capabilities

### Three Specialized Search Tools

#### 1. `search` - Universal Semantic Search

- **Purpose**: General-purpose semantic search across all content
- **Best for**: Finding relevant information by meaning, not just keywords
- **Features**: Multi-source search, relevance ranking, context preservation

#### 2. `hierarchy_search` - Confluence-Aware Search

- **Purpose**: Confluence-specific search with deep hierarchy understanding
- **Best for**: Navigating complex documentation structures, finding related pages
- **Features**: Parent/child relationships, breadcrumb paths, hierarchy filtering

#### 3. `attachment_search` - File-Focused Search

- **Purpose**: Finding files and attachments with parent document context
- **Best for**: Locating specific files, templates, specifications, or supporting materials
- **Features**: File type filtering, size filtering, parent document relationships

### Search Intelligence Features

- **Hierarchy Understanding**: Recognizes parent/child page relationships in Confluence
- **Attachment Awareness**: Connects files to their parent documents and context
- **Metadata Enrichment**: Includes authors, dates, file sizes, and source information
- **Visual Indicators**: Rich formatting with icons and context clues
- **Relationship Mapping**: Shows connections between related content

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install qdrant-loader-mcp-server
```

### From Source (Development)

```bash
# Clone the monorepo
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install in development mode
pip install -e packages/qdrant-loader-mcp-server[dev]
```

### Complete RAG Pipeline

For full functionality with data ingestion:

```bash
# Install both packages
pip install qdrant-loader qdrant-loader-mcp-server
```

## ⚡ Quick Start

### 1. Environment Setup

```bash
# Required environment variables
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your_api_key"  # Required for QDrant Cloud
export OPENAI_API_KEY="your_openai_key"

# Optional configuration
export QDRANT_COLLECTION_NAME="documents"  # Default collection name
export MCP_LOG_LEVEL="INFO"                # Logging level
export MCP_LOG_FILE="/path/to/mcp.log"     # Log file path
export MCP_DISABLE_CONSOLE_LOGGING="true"  # Recommended for Cursor
```

### 2. Start the Server

```bash
# Start MCP server
mcp-qdrant-loader

# With debug logging
mcp-qdrant-loader --log-level DEBUG

# Show help
mcp-qdrant-loader --help
```

### 3. Test the Connection

```bash
# Test with a simple search
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | mcp-qdrant-loader
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `QDRANT_URL` | QDrant instance URL | `http://localhost:6333` | Yes |
| `QDRANT_API_KEY` | QDrant API key | None | Cloud only |
| `QDRANT_COLLECTION_NAME` | Collection name | `documents` | No |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | None | Yes |
| `MCP_LOG_LEVEL` | Logging level | `INFO` | No |
| `MCP_LOG_FILE` | Log file path | None | No |
| `MCP_DISABLE_CONSOLE_LOGGING` | Disable console output | `false` | **Yes for Cursor** |

### Important Configuration Notes

- **For Cursor Integration**: Always set `MCP_DISABLE_CONSOLE_LOGGING=true` to prevent interference with JSON-RPC communication
- **For Debugging**: Use `MCP_LOG_FILE` to write logs when console logging is disabled
- **API Keys**: OpenAI API keys should start with `sk-proj-` for project keys or `sk-` for user keys

## 🎯 AI Tool Integration

### Cursor IDE Integration

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "/path/to/venv/bin/mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "your_qdrant_api_key",
        "OPENAI_API_KEY": "sk-proj-your_openai_api_key",
        "QDRANT_COLLECTION_NAME": "your_collection",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_LOG_FILE": "/path/to/logs/mcp.log",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
    }
  }
}
```

### Windsurf Integration

Similar configuration in Windsurf's MCP settings:

```json
{
  "mcp": {
    "servers": {
      "qdrant-loader": {
        "command": "/path/to/venv/bin/mcp-qdrant-loader",
        "env": {
          "QDRANT_URL": "http://localhost:6333",
          "OPENAI_API_KEY": "your_openai_key",
          "MCP_DISABLE_CONSOLE_LOGGING": "true"
        }
      }
    }
  }
}
```

### Claude Desktop Integration

Add to Claude Desktop's configuration:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "/path/to/venv/bin/mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your_openai_key"
      }
    }
  }
}
```

## 🎯 Usage Examples

### In Cursor IDE

Ask your AI assistant:

- *"Find documentation about authentication in our API"*
- *"Show me examples of error handling patterns in our codebase"*
- *"What are the deployment requirements for this service?"*
- *"Find all PDF attachments related to database schema"*
- *"Show me the hierarchy of pages under the Architecture section"*

### Advanced Search Queries

#### Semantic Search

```
Find information about rate limiting implementation
```

#### Hierarchy Search

```
Show me all child pages under the API Documentation section
```

#### Attachment Search

```
Find all Excel files uploaded by john.doe in the last month
```

## 🏗️ Architecture

### MCP Protocol Implementation

- **Full MCP 2024-11-05 compliance** with proper JSON-RPC communication
- **Tool registration** for search, hierarchy_search, and attachment_search
- **Streaming responses** for large result sets
- **Error handling** with proper MCP error codes
- **Resource management** for efficient memory usage

### Search Engine Components

- **Embedding Service**: Generates query embeddings using OpenAI
- **Vector Search**: Performs semantic similarity search in QDrant
- **Metadata Processor**: Enriches results with hierarchy and attachment information
- **Result Formatter**: Creates rich, contextual response formatting
- **Caching Layer**: Optimizes performance for repeated queries

### Data Flow

```text
AI Tool → MCP Server → QDrant Search → Result Processing → Formatted Response
    ↓         ↓            ↓              ↓                ↓
Cursor    JSON-RPC    Vector Query   Metadata         Rich Context
Windsurf  Protocol    Embedding      Enrichment       Visual Indicators
Claude    Tool Call   Similarity     Hierarchy        Relationship Info
Other     Streaming   Ranking        Attachments      Source Attribution
```

## 🔍 Search Tool Details

### Universal Search (`search`)

**Parameters:**

- `query` (required): Natural language search query
- `limit` (optional): Maximum number of results (default: 5)
- `source_types` (optional): Filter by source types (git, confluence, jira, etc.)

**Example:**

```json
{
  "name": "search",
  "arguments": {
    "query": "authentication implementation",
    "limit": 10,
    "source_types": ["git", "confluence"]
  }
}
```

### Hierarchy Search (`hierarchy_search`)

**Parameters:**

- `query` (required): Search query
- `limit` (optional): Maximum results (default: 10)
- `organize_by_hierarchy` (optional): Group results by hierarchy (default: false)
- `hierarchy_filter` (optional): Filter options:
  - `root_only`: Show only root pages
  - `depth`: Filter by hierarchy depth
  - `parent_title`: Filter by parent page title
  - `has_children`: Filter by whether pages have children

**Example:**

```json
{
  "name": "hierarchy_search",
  "arguments": {
    "query": "API documentation",
    "organize_by_hierarchy": true,
    "hierarchy_filter": {
      "depth": 2,
      "has_children": true
    }
  }
}
```

### Attachment Search (`attachment_search`)

**Parameters:**

- `query` (required): Search query
- `limit` (optional): Maximum results (default: 10)
- `include_parent_context` (optional): Include parent document info (default: true)
- `attachment_filter` (optional): Filter options:
  - `attachments_only`: Show only attachments
  - `file_type`: Filter by file extension
  - `file_size_min`/`file_size_max`: Size range filtering
  - `author`: Filter by attachment author
  - `parent_document_title`: Filter by parent document

**Example:**

```json
{
  "name": "attachment_search",
  "arguments": {
    "query": "database schema",
    "attachment_filter": {
      "file_type": "pdf",
      "file_size_min": 1024
    }
  }
}
```

## 🧪 Testing

```bash
# Run all tests
pytest packages/qdrant-loader-mcp-server/tests/

# Run with coverage
pytest --cov=qdrant_loader_mcp_server packages/qdrant-loader-mcp-server/tests/

# Test MCP protocol compliance
pytest -m "mcp" packages/qdrant-loader-mcp-server/tests/
```

## 🤝 Contributing

This package is part of the QDrant Loader monorepo. See the [main contributing guide](../../CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install in development mode
pip install -e packages/qdrant-loader-mcp-server[dev]

# Run tests
pytest packages/qdrant-loader-mcp-server/tests/
```

## 📚 Documentation

- **[Complete Documentation](../../docs/)** - Comprehensive guides and references
- **[Getting Started](../../docs/getting-started/)** - Quick start and core concepts
- **[MCP Server Guide](../../docs/users/detailed-guides/mcp-server/)** - Detailed MCP server documentation
- **[Developer Docs](../../docs/developers/)** - Architecture and API reference

## 🆘 Support

- **[Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community Q&A
- **[Documentation](../../docs/)** - Comprehensive guides

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](../../LICENSE) file for details.

---

**Ready to supercharge your AI development?** Check out the [MCP Server Guide](../../docs/users/detailed-guides/mcp-server/) or explore the [complete documentation](../../docs/).
