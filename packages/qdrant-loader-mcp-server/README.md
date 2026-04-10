# QDrant Loader MCP Server

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader-mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader-mcp-server)](https://pypi.org/project/qdrant-loader-mcp-server/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Model Context Protocol (MCP) server that brings advanced RAG search to AI development tools. Part of the [QDrant Loader monorepo](../../) ecosystem.

## <img src="/assets/icons/library/target-icon.svg" width="32" alt="What It Does"> What It Does

- **Intelligent search** via semantic, hierarchy-aware, and attachment-focused tools
- **Seamless integration** with Cursor, Windsurf, Claude Desktop, and any MCP-compatible tool
- **Context understanding** — document hierarchies, file relationships, and rich metadata
- **Streaming responses** for fast, real-time search results

## <img src="/assets/icons/library/plug-icon.svg" width="32" alt="Supported AI Tools"> Supported AI Tools

| Tool                | Status          | Integration Features                                                         |
| ------------------- | --------------- | ---------------------------------------------------------------------------- |
| **Cursor**          | ✅ Full Support | Context-aware code assistance, documentation lookup, intelligent suggestions |
| **Windsurf**        | ✅ Compatible   | MCP protocol integration, semantic search capabilities                       |
| **Claude Desktop**  | ✅ Compatible   | Direct MCP integration, conversational search interface                      |
| **Other MCP Tools** | ✅ Compatible   | Any tool supporting MCP 2024-11-05 specification                             |

For per-tool JSON configuration, see **[MCP setup and integration](../../docs/users/detailed-guides/mcp-server/setup-and-integration.md)**.

## <img src="/assets/icons/library/search-icon.svg" width="32" alt="Search Tools"> Search Tools

### Core search tools

| Tool                | Purpose                                                      |
| ------------------- | ------------------------------------------------------------ |
| `search`            | General semantic search across all content                   |
| `hierarchy_search`  | Confluence-aware search with parent/child page relationships |
| `attachment_search` | File-focused search with parent document context             |

### Cross-document intelligence

`analyze_relationships`, `find_similar_documents`, `detect_document_conflicts`, `find_complementary_content`, `cluster_documents`, `expand_document`, `expand_cluster`, `expand_chunk_context`

For full parameter references and usage examples, see **[MCP search capabilities](../../docs/users/detailed-guides/mcp-server/search-capabilities.md)**.

## <img src="/assets/icons/library/package-icon.svg" width="32" alt="Installation"> Installation

```bash
pip install qdrant-loader-mcp-server
```

For the full ingestion + MCP pipeline:

```bash
pip install qdrant-loader qdrant-loader-mcp-server
```

## <img src="/assets/icons/library/rocket-icon.svg" width="32" alt="Quick Start"> Quick Start

### 1. Set environment variables

```bash
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your_api_key"        # Required for QDrant Cloud
export LLM_API_KEY="your_openai_key"
export MCP_DISABLE_CONSOLE_LOGGING="true"   # Required for Cursor
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
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | mcp-qdrant-loader
```

## <img src="/assets/icons/library/wrench-icon.svg" width="32" alt="Configuration"> Configuration

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
# HTTP transport — eliminates GIL contention for CPU-bound work
mcp-qdrant-loader --transport http --port 8080 --workers 4
```

Each worker has its own event loop and Qdrant connection pool. Total concurrent Qdrant load = `workers × SEARCH_MAX_CONCURRENT`.

| Workers | `SEARCH_MAX_CONCURRENT` | Max concurrent Qdrant queries |
| ------- | ----------------------- | ----------------------------- |
| 1       | 4 (default)             | 4                             |
| 4       | 4 (default)             | 16                            |
| 4       | 2                       | 8                             |

If you see `408 Request Timeout` from Qdrant, lower `SEARCH_MAX_CONCURRENT`:

```bash
export SEARCH_MAX_CONCURRENT=2
mcp-qdrant-loader --transport http --workers 4
```

## <img src="/assets/icons/library/target-icon.svg" width="32" alt="Usage Examples"> Usage Examples

Ask your AI assistant in natural language:

- _"Find documentation about authentication in our API"_
- _"Show me examples of error handling patterns in our codebase"_
- _"Find all PDF attachments related to database schema"_
- _"Show me the hierarchy of pages under the Architecture section"_

## <img src="/assets/icons/library/architect-icon.svg" width="32" alt="Architecture"> Architecture

### MCP Protocol Implementation

- **Full MCP 2024-11-05 compliance** with proper JSON-RPC communication
- **Tool registration** for `search`, `hierarchy_search`, and `attachment_search`
- **Streaming responses** for large result sets
- **Error handling** with proper MCP error codes

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

## <img src="../../../assets/icons/library/book-icon.svg" width="32" alt="Book icon"> Canonical Documentation

- **[Monorepo overview](../../)** - Repository layout, package responsibilities, and navigation entry points.
- **[MCP server guide](../../docs/users/detailed-guides/mcp-server/)** - End-to-end overview of MCP usage with QDrant Loader.
- **[MCP setup and integration](../../docs/users/detailed-guides/mcp-server/setup-and-integration.md)** - Tool-specific setup steps and integration configuration.
- **[MCP search capabilities](../../docs/users/detailed-guides/mcp-server/search-capabilities.md)** - Available search tools, parameters, and usage patterns.
- **[Environment variables reference](../../docs/users/configuration/environment-variables.md)** - Required and optional runtime variables for server behavior.

## <img src="/assets/icons/library/hand-sake-icon.svg" width="32" alt="Contributing icon"> Contributing

See **[CONTRIBUTING](../../CONTRIBUTING.md)** - Contribution guidelines, development standards, and pull request process.
