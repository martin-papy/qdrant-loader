# QDrant Loader MCP Server

A Model Context Protocol (MCP) server that provides Retrieval-Augmented Generation (RAG) capabilities to AI development tools like Cursor, Windsurf, and other LLM applications. Part of the QDrant Loader monorepo ecosystem.

## 🚀 Features

### Core Capabilities

- **MCP Protocol Implementation**: Full compliance with MCP 2024-11-05 specification
- **Semantic Search**: Advanced vector search across multiple data sources
- **Real-time Processing**: Streaming responses for large result sets
- **Multi-source Integration**: Search across Git, Confluence, Jira, documentation, and local file sources
- **Local File Support**: Index and search local files with configurable filtering and file type support
- **Natural Language Queries**: Intelligent query processing and expansion

### Advanced Features

- **Hybrid Search**: Combines semantic and keyword search for optimal results
- **Source Filtering**: Filter results by source type, project, or metadata
- **Result Ranking**: Intelligent ranking based on relevance and recency
- **Caching**: Optimized caching for frequently accessed content
- **Error Recovery**: Robust error handling and graceful degradation

## 🔌 Integration Support

| Tool | Status | Features |
|------|--------|----------|
| **Cursor** | ✅ Full Support | Context-aware code assistance, documentation lookup |
| **Windsurf** | ✅ Compatible | MCP protocol integration |
| **Claude Desktop** | ✅ Compatible | Direct MCP integration |

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

### With QDrant Loader

For a complete RAG pipeline:

```bash
# Install both packages
pip install qdrant-loader qdrant-loader-mcp-server

# Or from source
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]
```

## ⚡ Quick Start

### 1. Environment Setup

```bash
# Required environment variables
export QDRANT_URL="http://localhost:6333"  # or your QDrant Cloud URL
export QDRANT_API_KEY="your_api_key"       # Required for cloud, optional for local
export OPENAI_API_KEY="your_openai_key"    # For embeddings

# Optional configuration
export QDRANT_COLLECTION_NAME="my_collection"  # Default: "documents"

# Optional MCP logging configuration
export MCP_LOG_LEVEL="INFO"                    # Default: INFO
export MCP_LOG_FILE="/path/to/logs/mcp.log"    # Recommended: log to file
export MCP_DISABLE_CONSOLE_LOGGING="true"      # Recommended: true for Cursor
```

### 2. Start the Server

```bash
# Start MCP server
mcp-qdrant-loader

# Show help and available options
mcp-qdrant-loader --help

# Show version information
mcp-qdrant-loader --version

# With debug logging
mcp-qdrant-loader --log-level DEBUG
```

### 3. Test the Server

```bash
# Test the MCP server with a manual JSON-RPC call
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | mcp-qdrant-loader

# The server communicates via stdio (JSON-RPC), not HTTP
# For integration testing, use it with Cursor or other MCP clients
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `QDRANT_URL` | QDrant instance URL | `http://localhost:6333` | Yes |
| `QDRANT_API_KEY` | QDrant API key | None | Cloud only |
| `QDRANT_COLLECTION_NAME` | Collection name | `documents` | No |
| `OPENAI_API_KEY` | OpenAI API key | None | Yes |
| `MCP_LOG_LEVEL` | MCP-specific log level | `INFO` | No |
| `MCP_LOG_FILE` | Path to MCP log file | None | No |
| `MCP_DISABLE_CONSOLE_LOGGING` | Disable console logging | `false` | **Yes for Cursor** |

### Configuration via Environment Variables

The MCP server is configured entirely through environment variables. Configuration files are not currently supported.

**Important Notes:**

- The `--config` CLI option exists but is not yet implemented. All configuration must be done via environment variables as shown in the table above.
- **For Cursor Integration**: Set `MCP_DISABLE_CONSOLE_LOGGING=true` to prevent console output from interfering with JSON-RPC communication over stdio.
- **For Debugging**: Use `MCP_LOG_FILE` to write logs to a file when console logging is disabled.

## 🎯 Usage Examples

### Cursor Integration

Add to your Cursor MCP configuration (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "mcp-qdrant-loader": {
      "command": "/path/to/your/venv/bin/mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "https://your-cluster.gcp.cloud.qdrant.io",
        "QDRANT_API_KEY": "your_qdrant_api_key",
        "OPENAI_API_KEY": "sk-proj-your_openai_api_key",
        "QDRANT_COLLECTION_NAME": "your_collection_name",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_LOG_FILE": "/path/to/logs/mcp.log",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
    }
  }
}
```

**Important Configuration Notes:**

- **`command`**: Use the full path to your virtual environment's `mcp-qdrant-loader` executable
- **`QDRANT_URL`**: Your QDrant instance URL (local or cloud)
- **`QDRANT_API_KEY`**: Required for QDrant Cloud, optional for local instances
- **`OPENAI_API_KEY`**: Valid OpenAI API key for embeddings (starts with `sk-proj-` for project keys)
- **`QDRANT_COLLECTION_NAME`**: Name of your QDrant collection containing the data
- **`MCP_LOG_LEVEL`**: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **`MCP_LOG_FILE`**: Path where MCP server logs will be written (helpful for debugging)
- **`MCP_DISABLE_CONSOLE_LOGGING`**: Set to "true" to disable console output and only log to file

**Example with Local QDrant:**

```json
{
  "mcpServers": {
    "mcp-qdrant-loader": {
      "command": "/Users/yourname/project/venv/bin/mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "sk-proj-your_openai_api_key",
        "QDRANT_COLLECTION_NAME": "documents",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_LOG_FILE": "/Users/yourname/project/logs/mcp.log",
        "MCP_DISABLE_CONSOLE_LOGGING":"true"
      }
    }
  }
}
```

### Manual MCP Testing

```bash
# Basic search via JSON-RPC
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"How to implement authentication?","limit":5}}}' | mcp-qdrant-loader

# Filtered search
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search","arguments":{"query":"database migration","source_types":["git","confluence"],"limit":10}}}' | mcp-qdrant-loader

# Search local files
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search","arguments":{"query":"configuration files","source_types":["localfile"],"limit":5}}}' | mcp-qdrant-loader

# Note: The server communicates via JSON-RPC over stdio, not HTTP
# For normal usage, integrate with Cursor or other MCP-compatible tools
```

### MCP Protocol Usage

The server communicates via JSON-RPC over stdio. Here's how to integrate it programmatically:

```python
import asyncio
import json
import subprocess

async def search_via_mcp(query: str, limit: int = 5):
    """Search using the MCP server via subprocess."""
    # Prepare the JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search",
            "arguments": {
                "query": query,
                "limit": limit
            }
        }
    }
    
    # Call the MCP server
    process = subprocess.Popen(
        ["mcp-qdrant-loader"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(json.dumps(request))
    
    if process.returncode == 0:
        response = json.loads(stdout)
        return response.get("result", [])
    else:
        raise Exception(f"MCP server error: {stderr}")

# Example usage
async def main():
    results = await search_via_mcp("authentication implementation", limit=3)
    for result in results:
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Source: {result.get('source', 'N/A')}")
        print(f"Content: {result.get('content', '')[:200]}...")
        print("---")

# Run the search
asyncio.run(main())
```

## 🛠️ API Reference

### MCP Tools

#### search

Perform semantic search across data sources.

**Parameters:**

- `query` (string): Natural language search query
- `source_types` (array, optional): Filter by source types (`git`, `confluence`, `jira`, `documentation`, `localfile`)
- `limit` (integer, optional): Maximum number of results (default: 10, max: 100)
- `filters` (object, optional): Additional metadata filters

**Response:**

```json
{
  "results": [
    {
      "id": "doc_123",
      "title": "Authentication Guide",
      "content": "Complete guide to implementing authentication...",
      "source": "backend-docs",
      "source_type": "confluence",
      "url": "https://docs.company.com/auth",
      "score": 0.95,
      "metadata": {
        "author": "john.doe",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-20T14:45:00Z"
      }
    }
  ],
  "total": 1,
  "query_time": 0.123
}
```

### JSON-RPC Methods

The server supports these JSON-RPC methods over stdio:

#### tools/list

List available tools.

#### tools/call

Call a specific tool (currently only "search" is available).

#### initialize

Initialize the MCP session.

**Note**: The server does not provide HTTP/REST endpoints. All communication is via JSON-RPC over stdio.

## 🔍 Advanced Features

### Hybrid Search

The server automatically combines semantic vector search with keyword matching for optimal results. This feature is always enabled and does not require configuration.

### Query Expansion

Automatically expands queries with related terms:

```python
# Original query: "auth"
# Expanded query: "authentication authorization login security"
```

### Result Caching

The server includes built-in caching for improved performance. Caching is automatically enabled and optimized for typical usage patterns.

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
pip install -e packages/qdrant-loader-mcp-server[dev]

# Run tests
pytest packages/qdrant-loader-mcp-server/tests/
```

### Testing

```bash
# Run all tests
pytest packages/qdrant-loader-mcp-server/tests/

# Run with coverage
pytest --cov=qdrant_loader_mcp_server packages/qdrant-loader-mcp-server/tests/

# Run specific test categories
pytest packages/qdrant-loader-mcp-server/tests/unit/
pytest packages/qdrant-loader-mcp-server/tests/integration/
```

### Development Server

```bash
# Start development server with auto-reload
mcp-qdrant-loader --dev --reload

# Run with debug logging
mcp-qdrant-loader --log-level DEBUG
```

## 🔗 Integration Examples

### Complete RAG Workflow

```bash
# 1. Load data with qdrant-loader
qdrant-loader init
qdrant-loader ingest --source-type git --source my-repo
qdrant-loader ingest --source-type confluence --source tech-docs
qdrant-loader ingest --source-type localfile --source /path/to/local/files

# 2. Start MCP server
mcp-qdrant-loader

# 3. Use in Cursor for AI-powered development
# The server provides context to Cursor's AI assistant
```

### Custom Integration

```python
import json
import subprocess

class MCPRAGClient:
    def __init__(self, mcp_command="mcp-qdrant-loader"):
        self.mcp_command = mcp_command
    
    def search(self, query, **kwargs):
        """Search using the MCP server."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": query, **kwargs}
            }
        }
        
        process = subprocess.Popen(
            [self.mcp_command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(json.dumps(request))
        
        if process.returncode == 0:
            response = json.loads(stdout)
            return response.get("result", [])
        else:
            raise Exception(f"MCP server error: {stderr}")
    
    def get_context(self, query, max_tokens=4000):
        """Get context from search results."""
        results = self.search(query, limit=10)
        context = ""
        for result in results:
            content = f"{result.get('title', '')}\n{result.get('content', '')}\n\n"
            if len(context) + len(content) < max_tokens:
                context += content
            else:
                break
        return context

# Usage
client = MCPRAGClient()
context = client.get_context("How to implement caching?")
print(context)
```

## 📋 Requirements

- **Python**: 3.12 or higher
- **QDrant**: Local instance or QDrant Cloud with data loaded
- **Memory**: Minimum 2GB RAM for basic operation
- **Network**: Internet access for embedding API calls
- **Storage**: Minimal local storage for caching

## 🤝 Contributing

We welcome contributions! See the [Contributing Guide](../../docs/CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make changes in `packages/qdrant-loader-mcp-server/`
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](../../LICENSE) file for details.

## 🔧 Troubleshooting

### Common Issues

#### MCP Tool Not Working in Cursor

If the MCP search tool returns errors or no results:

1. **Disable Console Logging**: Console output can interfere with JSON-RPC communication. Always set `MCP_DISABLE_CONSOLE_LOGGING=true` for Cursor.
2. **Check API Keys**: Ensure your OpenAI API key is valid and has sufficient credits
3. **Enable File Logging**: Add logging configuration to your `.cursor/mcp.json`:

   ```json
   "env": {
     "MCP_LOG_LEVEL": "DEBUG",
     "MCP_LOG_FILE": "/path/to/logs/mcp.log",
     "MCP_DISABLE_CONSOLE_LOGGING": "true"
   }
   ```

4. **Check Logs**: Monitor the log file for errors:

   ```bash
   tail -f /path/to/logs/mcp.log
   ```

5. **Verify Collection**: Ensure your QDrant collection exists and contains data
6. **Test Manually**: Test the server directly:

   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | /path/to/venv/bin/mcp-qdrant-loader
   ```

#### Authentication Errors

- **OpenAI 401 Error**: Invalid or expired OpenAI API key
- **QDrant Connection Error**: Check QDrant URL and API key
- **Collection Not Found**: Verify collection name matches your data

#### Performance Issues

- **Slow Responses**: Increase QDrant timeout or reduce search limit
- **Memory Usage**: Monitor memory usage with large collections
- **Network Latency**: Use QDrant Cloud regions close to your location

### Debug Mode

Enable debug logging for detailed troubleshooting:

```json
{
  "mcpServers": {
    "mcp-qdrant-loader": {
      "command": "/path/to/venv/bin/mcp-qdrant-loader",
      "args": ["--log-level", "DEBUG"],
      "env": {
        "MCP_LOG_LEVEL": "DEBUG",
        "MCP_LOG_FILE": "/tmp/mcp-debug.log"
      }
    }
  }
}
```

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
- **Discussions**: [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)
- **Documentation**: [Project Documentation](../../docs/)

## 🔄 Related Projects

- [qdrant-loader](../qdrant-loader/): Data ingestion and processing
- [QDrant](https://qdrant.tech/): Vector database engine
- [Model Context Protocol](https://modelcontextprotocol.io/): AI integration standard
- [Cursor](https://cursor.sh/): AI-powered code editor
