# QDrant Loader MCP Server

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader-mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader-mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Model Context Protocol (MCP) server that brings advanced RAG search to AI development tools. Part of the [QDrant Loader monorepo](../../) ecosystem.

## 🎯 What It Does

- **Provides intelligent search** through semantic, hierarchy-aware, and attachment-focused tools
- **Integrates seamlessly** with Cursor, Windsurf, Claude Desktop, and other MCP-compatible tools
- **Understands context** including document hierarchies, file relationships, and metadata
- **Streams responses** for fast, real-time search results
- **Preserves relationships** between documents, attachments, and parent content

## 🔌 Supported AI Tools

| Tool                | Status          | Integration Features                                                         |
| ------------------- | --------------- | ---------------------------------------------------------------------------- |
| **Cursor**          | ✅ Full Support | Context-aware code assistance, documentation lookup, intelligent suggestions |
| **Windsurf**        | ✅ Compatible   | MCP protocol integration, semantic search capabilities                       |
| **Claude Desktop**  | ✅ Compatible   | Direct MCP integration, conversational search interface                      |
| **Other MCP Tools** | ✅ Compatible   | Any tool supporting MCP 2024-11-05 specification                             |

For per-tool JSON configuration, see **[MCP setup and integration](../../docs/users/detailed-guides/mcp-server/setup-and-integration.md)**.

## 🔍 Search Tools

### Core search tools

| Tool                | Purpose                                                      | Best for                                                              |
| ------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------- |
| `search`            | General semantic search across all content                   | Finding relevant information by meaning, not just keywords            |
| `hierarchy_search`  | Confluence-aware search with parent/child page relationships | Navigating complex documentation structures and finding related pages |
| `attachment_search` | File-focused search with parent document context             | Locating files, templates, specifications, and supporting materials   |

### Search Intelligence Features

- **Hierarchy Understanding**: Recognizes parent/child page relationships in Confluence
- **Attachment Awareness**: Connects files to their parent documents and context
- **Metadata Enrichment**: Includes authors, dates, file sizes, and source information
- **Visual Indicators**: Rich formatting with icons and context clues
- **Relationship Mapping**: Shows connections between related content

### Additional MCP Tools

Beyond the three core search tools, the server also provides cross-document and expansion tools:

`analyze_relationships`, `find_similar_documents`, `detect_document_conflicts`, `find_complementary_content`, `cluster_documents`, `expand_document`, `expand_cluster`, `expand_chunk_context`

For full parameter references and usage examples, see **[MCP search capabilities](../../docs/users/detailed-guides/mcp-server/search-capabilities.md)**.

## 📦 Installation

```bash
pip install qdrant-loader-mcp-server
```

For the full ingestion + MCP pipeline:

```bash
pip install qdrant-loader qdrant-loader-mcp-server
```

## 🚀 Quick Start

### 1. Set environment variables

```bash
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your_api_key"        # Required for QDrant Cloud
export LLM_API_KEY="your_openai_key"

# Optional configuration
export QDRANT_COLLECTION_NAME="documents"  # Default collection name
export MCP_LOG_LEVEL="INFO"                # Logging level
export MCP_LOG_FILE="/path/to/mcp.log"     # Log file path
export MCP_DISABLE_CONSOLE_LOGGING="true"  # Recommended for Cursor
```

### 2. Start the server

```bash
mcp-qdrant-loader

# With debug logging
mcp-qdrant-loader --log-level DEBUG

# Help
mcp-qdrant-loader --help
```

### 3. Test the connection

```bash
# Test with a simple search
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | mcp-qdrant-loader
```

## 🔧 Configuration

### Environment variables

| Variable                      | Description                              | Default                 | Required           |
| ----------------------------- | ---------------------------------------- | ----------------------- | ------------------ |
| `QDRANT_URL`                  | QDrant instance URL                      | `http://localhost:6333` | Yes                |
| `QDRANT_API_KEY`              | QDrant API key                           | None                    | Cloud only         |
| `QDRANT_COLLECTION_NAME`      | Collection name                          | `documents`             | No                 |
| `LLM_API_KEY`                 | LLM API key for embeddings               | None                    | Yes                |
| `MCP_LOG_LEVEL`               | Logging level                            | `INFO`                  | No                 |
| `MCP_LOG_FILE`                | Log file path                            | None                    | No                 |
| `MCP_DISABLE_CONSOLE_LOGGING` | Disable console output                   | `false`                 | **Yes for Cursor** |
| `SEARCH_MAX_CONCURRENT`       | Max concurrent Qdrant queries per worker | `4`                     | No                 |

> **For Cursor**: Always set `MCP_DISABLE_CONSOLE_LOGGING=true` to prevent JSON-RPC interference. Use `MCP_LOG_FILE` to capture logs instead.

### HTTP transport and workers

For production deployments with multiple worker processes:

```bash
# Start with HTTP transport (single worker, good for local development)
mcp-qdrant-loader --transport http --port 8080

# Start with multiple workers for production
mcp-qdrant-loader --transport http --port 8080 --workers 4
```

Each worker is a separate OS process with its own event loop, Qdrant connection pool, and search engine. This eliminates GIL contention for CPU-bound work (SpaCy, BM25, reranking).

### Tuning Concurrency

`SEARCH_MAX_CONCURRENT` limits the number of simultaneous Qdrant queries **per worker**. With multiple workers, the total concurrent load on Qdrant is `workers × SEARCH_MAX_CONCURRENT`.

| Workers | `SEARCH_MAX_CONCURRENT` | Max concurrent Qdrant queries |
| ------- | ----------------------- | ----------------------------- |
| 1       | 4 (default)             | 4                             |
| 4       | 4 (default)             | 16                            |
| 4       | 2                       | 8                             |

If you see `408 Request Timeout` from Qdrant, lower `SEARCH_MAX_CONCURRENT` to match your Qdrant instance's capacity:

```bash
export SEARCH_MAX_CONCURRENT=2
mcp-qdrant-loader --transport http --workers 4
```

## 🎯 Usage Examples

Ask your AI assistant in natural language:

- _"Find documentation about authentication in our API"_
- _"Show me examples of error handling patterns in our codebase"_
- _"What are the deployment requirements for this service?"_
- _"Find all PDF attachments related to database schema"_
- _"Show me the hierarchy of pages under the Architecture section"_

### Advanced Search Queries

#### Semantic Search

```text
Find information about rate limiting implementation
```

#### Hierarchy Search

```text
Show me all child pages under the API Documentation section
```

#### Attachment Search

```text
Find all Excel files uploaded by john.doe in the last month
```

## 🏗️ Architecture

### MCP Protocol Implementation

- **Full MCP 2024-11-05 compliance** with proper JSON-RPC communication
- **Tool registration** for `search`, `hierarchy_search`, and `attachment_search`
- **Streaming responses** for large result sets
- **Error handling** with proper MCP error codes
- **Resource management** for efficient memory usage

### Search Engine Components

- **Embedding Service** — Generates query embeddings using the configured LLM provider
- **Vector Search** — Performs semantic similarity search in QDrant
- **Metadata Processor** — Enriches results with hierarchy and attachment information
- **Result Formatter** — Creates rich, contextual response formatting
- **Caching Layer** — Optimizes performance for repeated queries

### Data Flow

```text
AI Tool → MCP Server → QDrant Search → Result Processing → Formatted Response
    ↓         ↓            ↓              ↓                ↓
Cursor    JSON-RPC    Vector Query   Metadata         Rich Context
Windsurf  Protocol    Embedding      Enrichment       Visual Indicators
Claude    Tool Call   Similarity     Hierarchy        Relationship Info
Other     Streaming   Ranking        Attachments      Source Attribution
```

For system-level architecture, see **[Architecture guide](../../docs/developers/architecture/)**.

## 📚 Documentation

- **[Getting Started](../../docs/getting-started/)** - Quick start and core concepts
- **[Monorepo overview](../../)** - Repository layout, package responsibilities, and navigation entry points.
- **[Quick start](../../docs/getting-started/quick-start.md)** - Fast setup path from install to first successful ingestion.
- **[User Guides](../../docs/users/)** - Detailed usage instructions
- **[Developer Docs](../../docs/developers/)** - Architecture and API reference
- **[MCP server guide](../../docs/users/detailed-guides/mcp-server/)** - End-to-end overview of MCP usage with QDrant Loader.
- **[Basic Configuration](../../docs/getting-started/basic-configuration.md)** - Getting started with configuration

## 🆘 Support

- **[Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community Q&A

## 🤝 Contributing

See **[CONTRIBUTING](../../CONTRIBUTING.md)** - Contribution guidelines, development standards, and pull request process.

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](../../LICENSE) file for details.

---

**Ready to get started?** Check out our [Quick Start Guide](../../docs/getting-started/quick-start.md) or browse the [complete documentation](../../docs).
