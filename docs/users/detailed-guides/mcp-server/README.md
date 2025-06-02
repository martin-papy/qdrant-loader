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
    "source_types": ["git", "confluence", "jira", "documentation", "localfile"],
    "project_ids": ["project1", "project2"]
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
    "limit": 10,
    "organize_by_hierarchy": false,
    "hierarchy_filter": {
      "depth": 3,
      "has_children": true,
      "parent_title": "API Documentation"
    }
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
    "limit": 10,
    "include_parent_context": true,
    "attachment_filter": {
      "file_type": "pdf",
      "file_size_min": 1024,
      "file_size_max": 10485760
    }
  }
}
```

**Example Queries**:

- "Find PDF documents about architecture"
- "Show me Excel files with metrics data"
- "Search for presentation slides about the product roadmap"

## ⚙️ Configuration

### Environment Variables

The MCP server uses environment variables for configuration:

```bash
# Required
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-openai-api-key

# Optional
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=your-qdrant-cloud-api-key
MCP_DISABLE_CONSOLE_LOGGING=true  # Recommended for Cursor
```

### Command Line Options

The MCP server supports these command line options:

```bash
# Start with debug logging
mcp-qdrant-loader --log-level DEBUG

# Start with custom configuration file
mcp-qdrant-loader --config custom-config.yaml

# Show version
mcp-qdrant-loader --version

# Show help
mcp-qdrant-loader --help
```

**Note**: The MCP server communicates via JSON-RPC over stdio and does not support options like `--collection`, `--list-tools`, `--test`, `--status`, or `--stats`.

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
- Source type filtering
- Project-specific search
- Limit and threshold controls

### Hierarchy Navigation

**Detailed Guide**: [Hierarchy Search](./hierarchy-search.md)

**Key Features**:

- Document structure awareness
- Parent-child relationships
- Depth filtering
- Hierarchical organization

### Attachment Handling

**Detailed Guide**: [Attachment Search](./attachment-search.md)

**Key Features**:

- File type filtering
- Parent document context
- File size filtering
- Attachment metadata

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
# Verify documents are ingested using qdrant-loader CLI
qdrant-loader --workspace . project status

# Check collection status
curl http://localhost:6333/collections/documents

# Re-ingest if needed
qdrant-loader --workspace . ingest
```

#### Poor Search Quality

**Problem**: Search results are not relevant

**Solutions**:

1. Use more specific search terms
2. Try different search tools (hierarchy, attachment)
3. Check if documents are properly chunked
4. Verify the correct collection is being used

### Performance Optimization

#### For Large Knowledge Bases

- Use smaller `limit` values in search queries
- Filter by `source_types` or `project_ids` to narrow scope
- Use specific search tools for targeted queries

#### For Real-time Usage

- Keep the MCP server running continuously
- Use environment variables instead of config files for faster startup
- Monitor memory usage for large document collections

## 📊 Monitoring and Analytics

### Server Logs

```bash
# Enable debug logging
mcp-qdrant-loader --log-level DEBUG

# Use log file for Cursor integration
export MCP_LOG_FILE="/path/to/mcp.log"
export MCP_DISABLE_CONSOLE_LOGGING="true"
mcp-qdrant-loader
```

### Usage Monitoring

Monitor MCP server usage through:

- Log file analysis
- QDrant collection metrics
- AI tool usage patterns
- Search query performance

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
