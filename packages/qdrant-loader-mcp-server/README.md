# QDrant Loader MCP Server

A Model Context Protocol (MCP) server that provides Retrieval-Augmented Generation (RAG) capabilities to AI development tools like Cursor, Windsurf, and other LLM applications. Part of the QDrant Loader monorepo ecosystem.

## 🚀 Features

### Core Capabilities

- **MCP Protocol Implementation**: Full compliance with MCP 2024-11-05 specification
- **Semantic Search**: Advanced vector search across multiple data sources
- **Real-time Processing**: Streaming responses for large result sets
- **Multi-source Integration**: Search across Git, Confluence, Jira, and documentation sources
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
| **Custom Tools** | ✅ RESTful API | HTTP endpoints for custom integrations |

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
export SERVER_HOST="localhost"                 # Default: "localhost"
export SERVER_PORT="8000"                     # Default: 8000
export LOG_LEVEL="INFO"                       # Default: INFO
```

### 2. Start the Server

```bash
# Start MCP server
mcp-qdrant-loader

# With custom configuration
mcp-qdrant-loader --config custom-config.yaml --port 8080

# With debug logging
mcp-qdrant-loader --log-level DEBUG
```

### 3. Test the Server

```bash
# Test basic connectivity
curl http://localhost:8000/health

# Test search functionality
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication methods", "limit": 5}'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `QDRANT_URL` | QDrant instance URL | `http://localhost:6333` | Yes |
| `QDRANT_API_KEY` | QDrant API key | None | Cloud only |
| `QDRANT_COLLECTION_NAME` | Collection name | `documents` | No |
| `OPENAI_API_KEY` | OpenAI API key | None | Yes |
| `SERVER_HOST` | Server bind address | `localhost` | No |
| `SERVER_PORT` | Server port | `8000` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### Configuration File

Create a `config.yaml` file for advanced configuration:

```yaml
# Server configuration
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4

# QDrant configuration
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "documents"
  timeout: 30

# Search configuration
search:
  default_limit: 10
  max_limit: 100
  similarity_threshold: 0.7
  enable_hybrid_search: true

# Embedding configuration
embedding:
  model: "text-embedding-3-small"
  batch_size: 100
  cache_embeddings: true

# Logging configuration
logging:
  level: "INFO"
  format: "json"
  file: "mcp-server.log"
```

## 🎯 Usage Examples

### Cursor Integration

Add to your Cursor MCP configuration:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "your_api_key",
        "OPENAI_API_KEY": "your_openai_key"
      }
    }
  }
}
```

### Search Queries

```bash
# Basic search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to implement authentication?",
    "limit": 5
  }'

# Filtered search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "database migration",
    "source_types": ["git", "confluence"],
    "limit": 10
  }'

# Advanced search with metadata
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "API documentation",
    "filters": {
      "project": "backend-api",
      "author": "john.doe"
    },
    "limit": 20
  }'
```

### MCP Protocol Usage

```python
import asyncio
from mcp_client import MCPClient

async def search_documents():
    client = MCPClient("http://localhost:8000")
    
    # Initialize connection
    await client.initialize()
    
    # Search for documents
    results = await client.call_tool("search", {
        "query": "authentication implementation",
        "source_types": ["git", "confluence"],
        "limit": 5
    })
    
    for result in results:
        print(f"Title: {result['title']}")
        print(f"Source: {result['source']}")
        print(f"Content: {result['content'][:200]}...")
        print("---")

# Run the search
asyncio.run(search_documents())
```

## 🛠️ API Reference

### MCP Tools

#### search

Perform semantic search across data sources.

**Parameters:**

- `query` (string): Natural language search query
- `source_types` (array, optional): Filter by source types (`git`, `confluence`, `jira`, `documentation`)
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

### REST API Endpoints

#### GET /health

Health check endpoint.

#### POST /search

Direct search endpoint (same as MCP search tool).

#### GET /stats

Server and collection statistics.

#### GET /sources

List available data sources.

## 🔍 Advanced Features

### Hybrid Search

Combines semantic vector search with keyword matching:

```python
# Enable hybrid search in configuration
search:
  enable_hybrid_search: true
  semantic_weight: 0.7
  keyword_weight: 0.3
```

### Query Expansion

Automatically expands queries with related terms:

```python
# Original query: "auth"
# Expanded query: "authentication authorization login security"
```

### Result Caching

Intelligent caching for improved performance:

```python
# Cache configuration
cache:
  enabled: true
  ttl: 3600  # 1 hour
  max_size: 1000  # Maximum cached queries
```

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

# Run with custom configuration
mcp-qdrant-loader --config dev-config.yaml --log-level DEBUG
```

## 🔗 Integration Examples

### Complete RAG Workflow

```bash
# 1. Load data with qdrant-loader
qdrant-loader init
qdrant-loader ingest --source-type git --source my-repo
qdrant-loader ingest --source-type confluence --source tech-docs

# 2. Start MCP server
mcp-qdrant-loader

# 3. Use in Cursor for AI-powered development
# The server provides context to Cursor's AI assistant
```

### Custom Integration

```python
import requests

class CustomRAGClient:
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
    
    def search(self, query, **kwargs):
        response = requests.post(
            f"{self.server_url}/search",
            json={"query": query, **kwargs}
        )
        return response.json()
    
    def get_context(self, query, max_tokens=4000):
        results = self.search(query, limit=10)
        context = ""
        for result in results["results"]:
            if len(context) + len(result["content"]) < max_tokens:
                context += f"{result['title']}\n{result['content']}\n\n"
        return context

# Usage
client = CustomRAGClient()
context = client.get_context("How to implement caching?")
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

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
- **Discussions**: [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)
- **Documentation**: [Project Documentation](../../docs/)

## 🔄 Related Projects

- [qdrant-loader](../qdrant-loader/): Data ingestion and processing
- [QDrant](https://qdrant.tech/): Vector database engine
- [Model Context Protocol](https://modelcontextprotocol.io/): AI integration standard
- [Cursor](https://cursor.sh/): AI-powered code editor
