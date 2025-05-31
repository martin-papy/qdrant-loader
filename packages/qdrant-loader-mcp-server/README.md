# QDrant Loader MCP Server

A Model Context Protocol (MCP) server that provides advanced Retrieval-Augmented Generation (RAG) capabilities to AI development tools like Cursor, Windsurf, and other LLM applications. Part of the QDrant Loader monorepo ecosystem.

## 🚀 Features

### Core Capabilities

- **MCP Protocol Implementation**: Full compliance with MCP 2024-11-05 specification
- **Advanced Semantic Search**: Multi-layered search across multiple data sources with intelligent context understanding
- **Hierarchy-Aware Search**: Deep understanding of Confluence page relationships and document structure
- **Attachment-Aware Search**: Comprehensive file attachment support with parent document relationships
- **Real-time Processing**: Streaming responses for large result sets
- **Multi-source Integration**: Search across Git, Confluence, Jira, documentation, and local file sources
- **Local File Support**: Index and search local files with configurable filtering and file type support
- **Natural Language Queries**: Intelligent query processing and expansion

### Advanced Search Features

- **Three Specialized Search Tools**:
  - `search`: Standard semantic search with hierarchy and attachment context
  - `hierarchy_search`: Confluence-specific search with hierarchy filtering and organization
  - `attachment_search`: File-focused search with attachment filtering and parent document context

- **Hierarchy Understanding**:
  - Parent/child page relationships in Confluence
  - Breadcrumb navigation paths and depth levels
  - Hierarchical organization of search results
  - Visual indicators for document structure (📍 paths, 🏗️ hierarchy, ⬆️ parents, ⬇️ children)

- **File Attachment Intelligence**:
  - Parent document relationships for all file attachments
  - File metadata (size, type, author, upload date)
  - Attachment filtering by type, size, author, and parent document
  - Rich attachment context display (📎 files, 📋 details, 📄 parent docs)

- **Hybrid Search**: Combines semantic and keyword search for optimal results
- **Source Filtering**: Filter results by source type, project, or metadata
- **Result Ranking**: Intelligent ranking based on relevance, recency, and relationships
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

**Cursor AI Benefits with Enhanced Search:**

- **Hierarchy-Aware Context**: Cursor's AI can understand document structure and navigate Confluence hierarchies intelligently
- **File Attachment Discovery**: Find supporting materials, templates, and examples related to your code
- **Contextual Documentation**: Get relevant documentation with parent/child relationships for better understanding
- **Smart File Management**: Locate configuration files, specifications, and resources by type, size, or author

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

# Hierarchy search - find root pages with children
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"documentation","hierarchy_filter":{"root_only":true,"has_children":true},"organize_by_hierarchy":true,"limit":5}}}' | mcp-qdrant-loader

# Attachment search - find PDF files larger than 1MB
echo '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"requirements","attachment_filter":{"attachments_only":true,"file_type":"pdf","file_size_min":1048576},"limit":5}}}' | mcp-qdrant-loader

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

## 🎯 Advanced Search Examples

### Hierarchy-Aware Search

The MCP server provides sophisticated hierarchy understanding for Confluence documents, enabling navigation and discovery based on document structure.

#### Find Documentation Structure

```bash
# Find all root documentation pages
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"documentation","hierarchy_filter":{"root_only":true},"organize_by_hierarchy":true}}}' | mcp-qdrant-loader

# Find pages at specific depth levels
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"API","hierarchy_filter":{"depth":2},"limit":10}}}' | mcp-qdrant-loader

# Find child pages of a specific parent
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"implementation","hierarchy_filter":{"parent_title":"Developer Guide"},"limit":10}}}' | mcp-qdrant-loader
```

#### Navigate Document Hierarchies

```bash
# Find pages that have children (section headers)
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"guide","hierarchy_filter":{"has_children":true},"organize_by_hierarchy":true}}}' | mcp-qdrant-loader

# Find leaf pages (no children) for detailed content
echo '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"tutorial","hierarchy_filter":{"has_children":false},"limit":15}}}' | mcp-qdrant-loader
```

### Attachment-Aware Search

The MCP server understands file attachments and their relationships to parent documents, enabling comprehensive file discovery and management.

#### Find Specific File Types

```bash
# Find all PDF documents
echo '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"specification","attachment_filter":{"attachments_only":true,"file_type":"pdf"},"limit":10}}}' | mcp-qdrant-loader

# Find Excel spreadsheets with data
echo '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"data analysis","attachment_filter":{"attachments_only":true,"file_type":"xlsx"},"limit":5}}}' | mcp-qdrant-loader

# Find image files (screenshots, diagrams)
echo '{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"architecture","attachment_filter":{"attachments_only":true,"file_type":"png"},"limit":8}}}' | mcp-qdrant-loader
```

#### File Size and Author Filtering

```bash
# Find large files (>5MB) for cleanup
echo '{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"file_size_min":5242880},"limit":20}}}' | mcp-qdrant-loader

# Find files by specific author
echo '{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"project","attachment_filter":{"attachments_only":true,"author":"john.doe@company.com"},"limit":10}}}' | mcp-qdrant-loader

# Find small files for quick reference
echo '{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"template","attachment_filter":{"attachments_only":true,"file_size_max":1048576},"limit":15}}}' | mcp-qdrant-loader
```

#### Parent Document Context

```bash
# Find attachments related to specific documentation
echo '{"jsonrpc":"2.0","id":12,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"requirements","attachment_filter":{"parent_document_title":"Project Planning"},"include_parent_context":true,"limit":10}}}' | mcp-qdrant-loader

# Find all files attached to API documentation
echo '{"jsonrpc":"2.0","id":13,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"parent_document_title":"API Reference"},"limit":20}}}' | mcp-qdrant-loader
```

### Combined Search Strategies

#### Content Discovery Workflow

```bash
# 1. Find main documentation sections
echo '{"jsonrpc":"2.0","id":14,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"getting started","hierarchy_filter":{"depth":1,"has_children":true},"organize_by_hierarchy":true}}}' | mcp-qdrant-loader

# 2. Find supporting materials (attachments)
echo '{"jsonrpc":"2.0","id":15,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"getting started","attachment_filter":{"attachments_only":true},"include_parent_context":true}}}' | mcp-qdrant-loader

# 3. Standard search for comprehensive results
echo '{"jsonrpc":"2.0","id":16,"method":"tools/call","params":{"name":"search","arguments":{"query":"getting started guide","source_types":["confluence"],"limit":10}}}' | mcp-qdrant-loader
```

#### File Management and Audit

```bash
# Find all large PDF files for storage optimization
echo '{"jsonrpc":"2.0","id":17,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"file_type":"pdf","file_size_min":10485760},"limit":50}}}' | mcp-qdrant-loader

# Find orphaned or poorly organized content
echo '{"jsonrpc":"2.0","id":18,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"","hierarchy_filter":{"depth":0,"has_children":false},"limit":20}}}' | mcp-qdrant-loader

# Find recent uploads by specific users
echo '{"jsonrpc":"2.0","id":19,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"author":"new.employee@company.com"},"limit":25}}}' | mcp-qdrant-loader
```

### Use Cases

#### For Developers

- **Code Documentation**: Find API references and their supporting files
- **Architecture Diagrams**: Locate system architecture images and specifications
- **Configuration Examples**: Find template files and configuration documentation

#### For Project Managers

- **Project Documentation**: Navigate project hierarchies and find all related materials
- **Requirements Tracking**: Locate requirement documents and their attachments
- **Status Reports**: Find project status files and supporting documentation

#### For Content Managers

- **Content Audit**: Identify large files, orphaned pages, and content gaps
- **Documentation Structure**: Understand and optimize documentation hierarchies
- **File Management**: Track file uploads, authors, and parent document relationships

#### For End Users

- **Quick Navigation**: Find specific sections within large documentation sets
- **Resource Discovery**: Locate supporting materials like templates and examples
- **Contextual Search**: Understand document relationships and navigation paths

## 🛠️ API Reference

### MCP Tools

#### search

Perform semantic search across data sources with hierarchy and attachment context.

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
      },
      "breadcrumb_text": "Developer Guide > API Documentation",
      "depth": 2,
      "children_count": 3,
      "hierarchy_context": "Path: Developer Guide > API Documentation | Depth: 2 | Children: 3"
    }
  ],
  "total": 1,
  "query_time": 0.123
}
```

#### hierarchy_search

Search Confluence documents with hierarchy-aware filtering and organization.

**Parameters:**

- `query` (string): Natural language search query
- `hierarchy_filter` (object, optional): Hierarchy-based filtering options
  - `depth` (integer): Filter by specific hierarchy depth (0 = root pages)
  - `parent_title` (string): Filter by parent page title
  - `root_only` (boolean): Show only root pages (no parent)
  - `has_children` (boolean): Filter by whether pages have children
- `organize_by_hierarchy` (boolean, optional): Group results by hierarchy structure (default: false)
- `limit` (integer, optional): Maximum number of results (default: 10)

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "API documentation",
      "hierarchy_filter": {
        "depth": 1,
        "has_children": true
      },
      "organize_by_hierarchy": true,
      "limit": 10
    }
  }
}
```

#### attachment_search

Search for file attachments and their parent documents across multiple sources.

**Parameters:**

- `query` (string): Natural language search query
- `attachment_filter` (object, optional): Attachment-based filtering options
  - `attachments_only` (boolean): Show only file attachments
  - `parent_document_title` (string): Filter by parent document title
  - `file_type` (string): Filter by file type (e.g., 'pdf', 'xlsx', 'png')
  - `file_size_min` (integer): Minimum file size in bytes
  - `file_size_max` (integer): Maximum file size in bytes
  - `author` (string): Filter by attachment author
- `include_parent_context` (boolean, optional): Include parent document information (default: true)
- `limit` (integer, optional): Maximum number of results (default: 10)

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "project requirements",
      "attachment_filter": {
        "attachments_only": true,
        "file_type": "pdf",
        "file_size_min": 1048576
      },
      "limit": 5
    }
  }
}
```

**Response:**

```json
{
  "results": [
    {
      "id": "att_456",
      "title": "Attachment: requirements.pdf",
      "content": "# Project Requirements\n\nDetailed specifications...",
      "source_type": "confluence",
      "score": 0.92,
      "is_attachment": true,
      "parent_document_id": "doc_123",
      "parent_document_title": "Project Planning",
      "attachment_id": "att_456",
      "original_filename": "requirements.pdf",
      "file_size": 2048000,
      "mime_type": "application/pdf",
      "attachment_author": "project.manager@company.com",
      "attachment_context": "File: requirements.pdf | Size: 2.0 MB | Type: application/pdf | Author: project.manager@company.com"
    }
  ]
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

# Test specific search functionality
pytest packages/qdrant-loader-mcp-server/tests/ -k "test_search"
pytest packages/qdrant-loader-mcp-server/tests/ -k "test_hierarchy"
pytest packages/qdrant-loader-mcp-server/tests/ -k "test_attachment"
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

## 📚 Documentation

### Advanced Search Guides (v0.3.2)

- [**Advanced Search Examples**](../../docs/mcp-server/SearchExamples.md) - Comprehensive examples of hierarchy and attachment search capabilities
- [**Hierarchy Search Guide**](../../docs/mcp-server/SearchHierarchyExemple.md) - Confluence hierarchy navigation, filtering, and organization
- [**Attachment Search Guide**](../../docs/mcp-server/AttachementSearchExemple.md) - File attachment discovery, filtering, and parent document relationships

### Related Documentation

- [QDrant Loader Documentation](../qdrant-loader/README.md) - Data ingestion and processing
- [File Conversion Guide](../../docs/FileConversionGuide.md) - File conversion support for diverse formats
- [Migration Guide](../../docs/MigrationGuide.md) - Upgrading to v0.3.2
- [Features Overview](../../docs/Features.md) - Complete feature documentation
- [Contributing Guide](../../docs/CONTRIBUTING.md) - Development guidelines

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
6. **Test All Tools**: Test each search tool individually:

   ```bash
   # Test standard search
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | /path/to/venv/bin/mcp-qdrant-loader
   
   # Test hierarchy search (requires Confluence data)
   echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"documentation","limit":1}}}' | /path/to/venv/bin/mcp-qdrant-loader
   
   # Test attachment search (requires attachment data)
   echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"file","limit":1}}}' | /path/to/venv/bin/mcp-qdrant-loader
   ```

7. **Check Data Sources**: Verify your collection contains the expected data types:
   - For hierarchy search: Confluence pages with parent/child relationships
   - For attachment search: Documents with file attachments and metadata

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
