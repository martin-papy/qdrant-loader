# MCP Server Guide

The QDrant Loader MCP (Model Context Protocol) Server enables seamless integration with AI development tools like Cursor IDE, Windsurf, and Claude Desktop. This guide covers everything you need to know about setting up and using the MCP server.

## 🎯 Overview

The MCP Server acts as a bridge between your AI tools and your QDrant Loader knowledge base, providing intelligent search capabilities directly within your development environment.

### What is MCP?

**Model Context Protocol (MCP)** is an open standard that allows AI applications to securely connect to external data sources and tools. It enables AI assistants to access and search your ingested documents in real-time.

```
AI Tool (Cursor) ←→ MCP Server ←→ QDrant Database
     ↓
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Developer   │    │ MCP Server   │    │ QDrant      │
│ asks: "How  │ ──→│ - Receives   │──→ │ - Searches  │
│ do I deploy │    │   query      │    │   vectors   │
│ this app?"  │    │ - Searches   │    │ - Returns   │
│             │ ←──│   knowledge  │←── │   results   │
│ Gets answer │    │ - Formats    │    │             │
│ with context│    │   response   │    │             │
└─────────────┘    └──────────────┘    └─────────────┘
```

### Key Benefits

- **Contextual AI Responses**: AI tools can access your specific documentation and codebase
- **Real-time Search**: Search across all ingested documents without leaving your IDE
- **Intelligent Filtering**: Advanced search with hierarchy and attachment support
- **Seamless Integration**: Works with popular AI development tools
- **Secure Access**: Controlled access to your knowledge base

## 🚀 Quick Start

### Prerequisites

- QDrant Loader installed and configured
- Documents ingested into QDrant
- AI tool that supports MCP (Cursor, Windsurf, Claude Desktop)

### 1. Start the MCP Server

```bash
# Start the MCP server
mcp-qdrant-loader

# Expected output:
# 🚀 QDrant Loader MCP Server starting...
# 📡 Server running on stdio
# 🔍 Available tools: search, hierarchy_search, attachment_search
# ✅ Ready for connections
```

### 2. Configure Your AI Tool

**For Cursor IDE**:

1. Open Cursor Settings (Cmd/Ctrl + ,)
2. Navigate to **Extensions** → **MCP Servers**
3. Add new server configuration:

```json
{
  "name": "qdrant-loader",
  "command": "mcp-qdrant-loader",
  "args": [],
  "env": {
    "QDRANT_URL": "http://localhost:6333",
    "OPENAI_API_KEY": "your-openai-api-key",
    "QDRANT_COLLECTION_NAME": "documents"
  }
}
```

4. Save and restart Cursor

### 3. Test the Integration

1. Open a new chat in your AI tool
2. Ask a question about your documentation:

```
"Can you search for information about deployment procedures?"
```

3. The AI will use the MCP server to search your knowledge base and provide contextual answers

## 🔧 Available MCP Tools

The QDrant Loader MCP Server provides three powerful search tools:

### 1. Semantic Search Tool

**Purpose**: Basic semantic search across all ingested documents

**Usage**: General queries about any topic in your knowledge base

```json
{
  "name": "search",
  "description": "Search across all ingested documents using semantic similarity",
  "parameters": {
    "query": "search terms or question",
    "limit": 10,
    "threshold": 0.7,
    "source_filter": "optional source filter"
  }
}
```

**Example Queries**:

- "How do I configure authentication?"
- "What are the deployment options?"
- "Find information about API rate limits"

### 2. Hierarchy Search Tool

**Purpose**: Search with document structure and hierarchy awareness

**Usage**: When you need context about document organization and relationships

```json
{
  "name": "hierarchy_search",
  "description": "Search with document hierarchy context",
  "parameters": {
    "query": "search terms",
    "include_hierarchy": true,
    "depth": 3,
    "organize_by_hierarchy": false
  }
}
```

**Example Queries**:

- "Show me the structure of the API documentation"
- "Find all child pages under the deployment section"
- "What's the hierarchy of troubleshooting guides?"

### 3. Attachment Search Tool

**Purpose**: Search file attachments and their parent documents

**Usage**: Finding specific files, diagrams, or documents attached to pages

```json
{
  "name": "attachment_search",
  "description": "Search file attachments and parent documents",
  "parameters": {
    "query": "search terms",
    "file_types": ["pdf", "docx", "xlsx"],
    "include_parent_context": true,
    "attachment_filter": {}
  }
}
```

**Example Queries**:

- "Find PDF documents about architecture"
- "Show me Excel files with metrics data"
- "Search for presentation slides about the product roadmap"

## ⚙️ Configuration

### Environment Variables

The MCP server uses the same configuration as QDrant Loader:

```bash
# Required
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-openai-api-key

# Optional
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=your-qdrant-cloud-api-key
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_MAX_RESULTS=50
```

### Configuration File

You can also configure the MCP server via the QDrant Loader config file:

```yaml
# ~/.qdrant-loader/config.yaml
mcp_server:
  # Server settings
  log_level: "INFO"
  max_connections: 10
  timeout: 30
  
  # Search configuration
  search:
    default_limit: 10
    max_limit: 100
    similarity_threshold: 0.7
    
    # Result formatting
    include_metadata: true
    include_content: true
    max_content_length: 500
  
  # Tool configuration
  tools:
    search:
      enabled: true
      description: "Semantic search across all documents"
    
    hierarchy_search:
      enabled: true
      description: "Search with document hierarchy context"
      max_depth: 5
    
    attachment_search:
      enabled: true
      description: "Search file attachments"
      supported_types:
        - "pdf"
        - "docx"
        - "xlsx"
        - "pptx"
        - "png"
        - "jpg"
```

### Command Line Options

```bash
# Start with custom configuration
mcp-qdrant-loader --config custom-config.yaml

# Start with specific collection
mcp-qdrant-loader --collection my-docs

# Start with debug logging
mcp-qdrant-loader --log-level DEBUG

# List available tools
mcp-qdrant-loader --list-tools

# Test server without starting
mcp-qdrant-loader --test
```

## 🔗 AI Tool Integration Guides

### Cursor IDE Integration

**Detailed Guide**: [Cursor Integration](./cursor-integration.md)

**Quick Setup**:

1. Install QDrant Loader MCP server
2. Configure in Cursor settings
3. Start using AI chat with your knowledge base

### Windsurf Integration

**Setup**:

1. Open Windsurf settings
2. Navigate to MCP configuration
3. Add QDrant Loader server:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Claude Desktop Integration

**Setup**:

1. Open Claude Desktop configuration
2. Edit the MCP settings file
3. Add QDrant Loader configuration:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-api-key"
      }
    }
  }
}
```

## 🔍 Advanced Search Features

### Search Capabilities

**Detailed Guide**: [Search Capabilities](./search-capabilities.md)

**Key Features**:

- Semantic similarity search
- Metadata filtering
- Source-specific search
- Date range filtering
- Content type filtering

### Hierarchy Navigation

**Detailed Guide**: [Hierarchy Search](./hierarchy-search.md)

**Key Features**:

- Document structure awareness
- Parent-child relationships
- Breadcrumb navigation
- Hierarchical filtering

### Attachment Handling

**Detailed Guide**: [Attachment Search](./attachment-search.md)

**Key Features**:

- File type filtering
- Parent document context
- Attachment metadata
- Content extraction from files

## 🎯 Use Cases and Examples

### Development Workflow

**Scenario**: Developer working on a new feature

```
Developer: "How do I implement authentication in our API?"

AI Response (using MCP search):
Based on your documentation, here's how to implement authentication:

1. [From api-auth.md] Use JWT tokens for stateless authentication
2. [From security-guide.md] Implement rate limiting for auth endpoints
3. [From examples/auth.py] Here's a code example...

The search found 5 relevant documents across your codebase and documentation.
```

### Support Team Workflow

**Scenario**: Support agent helping a customer

```
Agent: "Customer is having issues with deployment on AWS"

AI Response (using MCP search):
I found several relevant resources for AWS deployment issues:

1. [From deployment/aws.md] Common AWS deployment troubleshooting
2. [From troubleshooting/aws-errors.md] Specific error codes and solutions
3. [From attachments/aws-architecture.pdf] Architecture diagram showing proper setup

Would you like me to search for more specific error messages?
```

### Content Creation Workflow

**Scenario**: Technical writer updating documentation

```
Writer: "What existing content do we have about API versioning?"

AI Response (using MCP search):
Found existing content about API versioning:

1. [From api/versioning.md] Current versioning strategy (v1, v2)
2. [From changelog.md] Version history and breaking changes
3. [From examples/] Code examples for different API versions
4. [From confluence/API-Strategy] High-level versioning decisions

This gives you a complete picture of existing versioning documentation.
```

## 🔧 Troubleshooting

### Common Issues

#### MCP Server Won't Start

**Problem**: Server fails to start or connect

**Solutions**:

```bash
# Check if QDrant is running
curl http://localhost:6333/health

# Verify configuration
qdrant-loader config show

# Check environment variables
env | grep QDRANT
env | grep OPENAI

# Start with debug logging
mcp-qdrant-loader --log-level DEBUG
```

#### AI Tool Can't Connect

**Problem**: AI tool shows MCP connection errors

**Solutions**:

1. Verify MCP server is running
2. Check AI tool MCP configuration
3. Restart both server and AI tool
4. Check firewall/network settings

#### Search Returns No Results

**Problem**: MCP searches return empty results

**Solutions**:

```bash
# Verify documents are ingested
qdrant-loader list

# Test search directly
qdrant-loader search "test query"

# Check collection status
qdrant-loader status

# Re-ingest if needed
qdrant-loader ingest --source local --path docs/
```

#### Poor Search Quality

**Problem**: Search results are not relevant

**Solutions**:

1. Adjust similarity threshold in configuration
2. Use more specific search terms
3. Try different search tools (hierarchy, attachment)
4. Check if documents are properly chunked

### Performance Optimization

#### For Large Knowledge Bases

```yaml
mcp_server:
  search:
    default_limit: 5      # Fewer results for faster response
    similarity_threshold: 0.8  # Higher threshold for better quality
    max_content_length: 300    # Shorter content for faster processing
```

#### For Real-time Usage

```yaml
mcp_server:
  timeout: 10           # Shorter timeout for responsiveness
  max_connections: 5    # Limit concurrent connections
  
  search:
    default_limit: 3    # Very few results for speed
    include_content: false  # Metadata only for speed
```

## 📊 Monitoring and Analytics

### Server Metrics

```bash
# Check server status
mcp-qdrant-loader --status

# View connection statistics
mcp-qdrant-loader --stats

# Monitor search performance
tail -f ~/.qdrant-loader/logs/mcp-server.log
```

### Usage Analytics

Track how the MCP server is being used:

```yaml
# Enable analytics in config
mcp_server:
  analytics:
    enabled: true
    track_queries: true
    track_performance: true
    log_file: "~/.qdrant-loader/logs/mcp-analytics.log"
```

## 🔗 Related Documentation

### Setup and Integration

- **[Setup and Integration Guide](./setup-and-integration.md)** - Detailed setup for all AI tools
- **[Cursor Integration](./cursor-integration.md)** - Cursor-specific setup and usage

### Search Features

- **[Search Capabilities](./search-capabilities.md)** - Complete search feature reference
- **[Hierarchy Search](./hierarchy-search.md)** - Document hierarchy navigation
- **[Attachment Search](./attachment-search.md)** - File attachment search

### Configuration

- **[Basic Configuration](../../getting-started/basic-configuration.md)** - General QDrant Loader setup
- **[Environment Variables](../../configuration/environment-variables.md)** - Complete variable reference

### Troubleshooting

- **[Common Issues](../../troubleshooting/common-issues.md)** - General troubleshooting
- **[Performance Optimization](../../troubleshooting/performance-optimization.md)** - Performance tuning

## 📋 MCP Server Checklist

- [ ] **QDrant Loader** installed and configured
- [ ] **Documents ingested** into QDrant database
- [ ] **MCP server** starts without errors
- [ ] **AI tool configured** with MCP server details
- [ ] **Search tools** working in AI tool
- [ ] **Environment variables** properly set
- [ ] **Performance** optimized for your use case
- [ ] **Monitoring** enabled if needed

---

**Ready to integrate AI tools with your knowledge base!** 🤖

The MCP server provides powerful search capabilities that make your AI tools much more useful by grounding them in your actual documentation and codebase. Continue with the specific integration guides for your AI tool of choice.
