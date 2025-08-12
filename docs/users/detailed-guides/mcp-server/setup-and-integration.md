# Setup and Integration Guide

This comprehensive guide covers setting up the QDrant Loader MCP Server with all supported AI development tools. Follow the instructions for your specific AI tool to enable **advanced knowledge-powered development** with semantic search, hierarchy navigation, attachment analysis, and cross-document intelligence.

## 🎯 Overview

The QDrant Loader MCP Server integrates with popular AI development tools through the Model Context Protocol (MCP), providing seamless access to your knowledge base during development with **advanced search capabilities**.

### Supported AI Tools

- **Cursor IDE** - AI-powered code editor with MCP support (detailed setup)
- **Windsurf** - AI development environment
- **Claude Desktop** - Anthropic's desktop AI assistant
- **Other MCP-Compatible Tools** - Generic MCP setup

### 🚀 Advanced Search Capabilities

The MCP server provides **8 powerful search tools**:

#### Core Search Tools

- **🔍 Universal Search** - Semantic search across all content types
- **🏗️ Hierarchy Search** - Structure-aware navigation with document relationships
- **📎 Attachment Search** - Specialized file and document analysis

#### Cross-Document Intelligence

- **🤝 Document Relationships** - Comprehensive relationship analysis
- **👥 Similar Documents** - Multi-metric similarity detection
- **⚠️ Conflict Detection** - Identify contradictions and inconsistencies
- **🧩 Complementary Content** - Discover related and supporting materials
- **📊 Document Clustering** - Group documents by content and relationships

### What You'll Achieve

After completing this guide, you'll have:

- ✅ **MCP Server running** and accessible to your AI tool
- ✅ **AI tool configured** to use your knowledge base with advanced search
- ✅ **All 8 search capabilities** working in your development environment
- ✅ **Cross-document intelligence** for analyzing document relationships
- ✅ **Optimized performance** for your specific use case

## 🚀 Prerequisites

Before starting, ensure you have:

### Required Components

- **QDrant Loader** installed and configured
- **QDrant database** running (local or cloud)
- **Documents ingested** into your QDrant collection with semantic metadata
- **OpenAI API key** for embeddings
- **AI development tool** installed

### Verification Steps

```bash
# 1. Verify QDrant Loader installation
qdrant-loader --version

# 2. Check QDrant database connection
curl http://localhost:6333/health

# 3. Verify documents are ingested
qdrant-loader status

# 4. Install MCP server if not already installed
pip install qdrant-loader-mcp-server
```

## 🔧 MCP Server Installation

### Install the MCP Server Package

```bash
# Option 1: Install standalone MCP server
pip install qdrant-loader-mcp-server

# Option 2: Install with QDrant Loader and MCP server as separate packages
pip install qdrant-loader qdrant-loader-mcp-server

# Option 3: Install from source
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader
pip install -e packages/qdrant-loader
pip install -e packages/qdrant-loader-mcp-server
```

### Verify Installation

```bash
# Check MCP server is available
mcp-qdrant-loader --version

# Check help for available options
mcp-qdrant-loader --help
```

### Environment Setup

Create a `.env` file with your configuration:

```bash
# .env file
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
OPENAI_API_KEY=sk-your-openai-api-key

# Optional: QDrant Cloud
QDRANT_API_KEY=your-qdrant-cloud-api-key

# IMPORTANT: Recommended for all AI tools (especially Cursor)
MCP_DISABLE_CONSOLE_LOGGING=true
```

> **💡 Pro Tip**: `MCP_DISABLE_CONSOLE_LOGGING=true` significantly improves performance and prevents console spam in AI tools.

## 🎨 Cursor IDE

Cursor is an AI-powered code editor with excellent MCP support. It's the most popular choice for AI-assisted development.

### Installation

1. **Download Cursor IDE**
   - Visit [cursor.com](https://www.cursor.com/)
   - Download for your platform (macOS, Windows, Linux)
   - Install and launch Cursor

2. **Verify MCP Support**
   - Open Cursor Settings (`Cmd/Ctrl + ,`)
   - Search for "MCP" to confirm MCP support is available

### Configuration

#### Method 1: Settings UI (Recommended)

1. **Open Settings**

   ```text
   Cursor → Preferences → Settings
   Or press: Cmd/Ctrl + ,
   ```

2. **Navigate to MCP Configuration**

   ```text
   Search: "MCP"
   Or: Extensions → MCP Servers
   ```

3. **Add QDrant Loader Server**

   ```json
   {
     "name": "qdrant-loader",
     "command": "mcp-qdrant-loader",
     "args": [],
     "env": {
       "QDRANT_URL": "http://localhost:6333",
       "OPENAI_API_KEY": "your-openai-api-key",
       "QDRANT_COLLECTION_NAME": "documents",
       "MCP_DISABLE_CONSOLE_LOGGING": "true"
     }
   }
   ```

#### Method 2: Configuration File

1. **Locate Configuration Directory**

   ```bash
   # macOS
   ~/.cursor/User/globalStorage/cursor.mcp/
   
   # Windows
   %APPDATA%\Cursor\User\globalStorage\cursor.mcp\
   
   # Linux
   ~/.config/Cursor/User/globalStorage/cursor.mcp/
   ```

2. **Create MCP Configuration**

   Create or edit `mcp-servers.json`:

   ```json
   {
     "mcpServers": {
       "qdrant-loader": {
         "command": "mcp-qdrant-loader",
         "args": [],
         "env": {
           "QDRANT_URL": "http://localhost:6333",
           "OPENAI_API_KEY": "your-openai-api-key",
           "QDRANT_COLLECTION_NAME": "documents",
           "MCP_DISABLE_CONSOLE_LOGGING": "true"
         }
       }
     }
   }
   ```

### Testing Cursor Integration

1. **Restart Cursor** after configuration changes

2. **Open Chat Interface**

   ```text
   Press: Cmd/Ctrl + L
   Or: Click the chat icon in the sidebar
   ```

3. **Test Advanced Search Capabilities**

   **Basic Semantic Search:**

   ```text
   You: "Can you search my knowledge base for information about API authentication?"
   ```

   **Hierarchy Navigation:**

   ```text
   You: "Show me the structure of our API documentation and navigate to authentication sections"
   ```

   **Cross-Document Intelligence:**

   ```text
   You: "Are there any conflicts or inconsistencies in our authentication documentation across different services?"
   ```

   **Document Clustering:**

   ```text
   You: "Group our microservices documentation by related topics and show me the clusters"
   ```

### Advanced Cursor Workflow Examples

#### Code Understanding Workflow

```text
You: "How does our authentication middleware connect to the user management system?"

AI Response (using semantic + hierarchy search):
I'll trace the connections between authentication and user management.

Found Related Components:
1. [middleware/auth.js] → JWT validation and user ID extraction
2. [services/user-service.js] → User lookup and management operations
3. [models/user.js] → User data model and database operations
4. [controllers/user-controller.js] → User management API endpoints

Document Relationships:
- Middleware passes user context to all downstream services
- User service has dependency on authentication state
- Error handling flows back through authentication middleware

This shows the complete flow from authentication to user management.
```

#### Conflict Detection Workflow

```text
You: "Are there any conflicts in our API documentation?"

AI Response (using cross-document analysis):
I've analyzed your documentation for conflicts and inconsistencies.

🚨 Conflicts Detected:

**Conflict 1: API Rate Limiting**
- [api/rate-limits.md] → 1000 requests/hour limit
- [config/production.yml] → 500 requests/hour limit
- Impact: Production config doesn't match documentation

**Conflict 2: Authentication Token Expiration**
- [auth/jwt-guide.md] → 24 hour token expiration
- [mobile/config.md] → 1 hour token expiration
- Impact: Mobile apps may fail with longer tokens

💡 Resolution Suggestions:
1. Update production config to match documented 1000/hour rate limit
2. Clarify token expiration policy for different client types
3. Add mobile-specific authentication documentation
```

## 🌊 Windsurf

Windsurf is an AI development environment with MCP support.

### Windsurf Installation

1. **Download Windsurf**
   - Visit the Windsurf website
   - Download for your platform
   - Install and launch Windsurf

### Windsurf Configuration

1. **Open Settings**

   ```text
   Windsurf → Preferences → Settings
   ```

2. **Navigate to MCP Configuration**

   ```text
   Search: "MCP" or "Model Context Protocol"
   ```

3. **Add QDrant Loader Server**

   ```json
   {
     "mcp": {
       "servers": {
         "qdrant-loader": {
           "command": "mcp-qdrant-loader",
           "env": {
             "QDRANT_URL": "http://localhost:6333",
             "OPENAI_API_KEY": "your_openai_key",
             "QDRANT_COLLECTION_NAME": "documents",
             "MCP_DISABLE_CONSOLE_LOGGING": "true"
           }
         }
       }
     }
   }
   ```

### Testing Windsurf Integration

1. **Restart Windsurf** after configuration
2. **Open AI Chat**
3. **Test Knowledge Access**

   ```text
   Ask: "Can you search for information about deployment procedures?"
   ```

## 🤖 Claude Desktop

Claude Desktop is Anthropic's desktop AI assistant with MCP support.

### Claude Desktop Installation

1. **Download Claude Desktop**
   - Visit [claude.ai](https://claude.ai/)
   - Download the desktop application
   - Install and launch Claude Desktop

### Claude Desktop Configuration

1. **Locate Configuration File**

   ```bash
   # macOS
   ~/Library/Application Support/Claude/claude_desktop_config.json
   
   # Windows
   %APPDATA%\Claude\claude_desktop_config.json
   
   # Linux
   ~/.config/Claude/claude_desktop_config.json
   ```

2. **Edit Configuration File**

   ```json
   {
     "mcpServers": {
       "qdrant-loader": {
         "command": "mcp-qdrant-loader",
         "args": [],
         "env": {
           "QDRANT_URL": "http://localhost:6333",
           "OPENAI_API_KEY": "your_openai_key",
           "QDRANT_COLLECTION_NAME": "documents",
           "MCP_DISABLE_CONSOLE_LOGGING": "true"
         }
       }
     }
   }
   ```

### Testing Claude Desktop Integration

1. **Restart Claude Desktop** after configuration
2. **Start a New Conversation**
3. **Test Knowledge Access**

   ```text
   Ask: "Can you search my knowledge base for information about API authentication?"
   ```

## 🔧 Other MCP-Compatible Tools

For other AI tools that support MCP, use this generic configuration approach:

### Generic MCP Configuration

Most MCP-compatible tools use similar configuration patterns:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "documents",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
    }
  }
}
```

### Command Line Testing

Test MCP server compatibility:

```bash
# Run MCP server in stdio mode (most common)
mcp-qdrant-loader

# Run with debug logging (helpful for troubleshooting)
mcp-qdrant-loader --log-level DEBUG
```

## 🔍 Advanced Search Capabilities Reference

### Search Tools Reference

#### 1. Universal Search (`search`)

**Purpose**: General-purpose semantic search across all documents

```text
Example: "Find information about authentication implementation"
```

#### 2. Hierarchy Search (`hierarchy_search`)

**Purpose**: Navigate document structures and understand organizational relationships

```text
Example: "Show me the structure of our API documentation"
```

#### 3. Attachment Search (`attachment_search`)

**Purpose**: Find and analyze files, diagrams, and documents

```text
Example: "Find architecture diagrams related to our microservices"
```

### Cross-Document Intelligence Tools

#### 4. Document Relationships (`analyze_document_relationships`)

**Purpose**: Comprehensive analysis of document connections and dependencies

```text
Example: "Analyze relationships between our authentication and user management docs"
```

#### 5. Similar Documents (`find_similar_documents`)

**Purpose**: Find documents similar using multiple similarity metrics

- Entity overlap, topic overlap, semantic similarity
- Metadata similarity, hierarchical distance, content features

```text
Example: "Find documents similar to our payment processing guide"
```

#### 6. Conflict Detection (`detect_document_conflicts`)

**Purpose**: Identify contradictions and inconsistencies between documents

```text
Example: "Are there any conflicts in our API rate limiting documentation?"
```

#### 7. Complementary Content (`find_complementary_content`)

**Purpose**: Discover content that complements or supports a target document

```text
Example: "What content complements our deployment guide?"
```

#### 8. Document Clustering (`cluster_documents`)

**Purpose**: Group documents by content similarity and relationships

- **Strategies**: mixed_features, entity_based, topic_based, project_based

```text
Example: "Cluster our microservices documentation by related topics"
```

## ⚙️ Configuration Reference

### Supported Environment Variables

```bash
# Required Configuration
QDRANT_URL=http://localhost:6333  # QDrant instance URL
OPENAI_API_KEY=sk-your-openai-api-key  # OpenAI API key for embeddings

# Optional Configuration
QDRANT_COLLECTION_NAME=documents  # Collection name (default: "documents")
QDRANT_API_KEY=your-qdrant-cloud-key  # For QDrant Cloud instances
MCP_DISABLE_CONSOLE_LOGGING=true  # Disable console logs (recommended)
```

### Multiple Knowledge Bases

For different projects with different knowledge bases:

```json
{
  "mcpServers": {
    "project-docs": {
      "command": "mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "project_docs"
      }
    },
    "team-knowledge": {
      "command": "mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "team_knowledge"
      }
    }
  }
}
```

## 🔧 Troubleshooting

### Common Issues

#### 1. MCP Server Not Found

**Error**: `Command 'mcp-qdrant-loader' not found`

**Solutions**:

```bash
# Check installation
which mcp-qdrant-loader

# Install if missing
pip install qdrant-loader-mcp-server

# Use full path in configuration if needed
{
  "command": "/path/to/venv/bin/mcp-qdrant-loader"
}
```

#### 2. Connection Refused

**Error**: `Connection refused to QDrant server`

**Solutions**:

```bash
# Check QDrant is running
curl http://localhost:6333/health

# Start QDrant if needed
docker run -p 6333:6333 qdrant/qdrant

# Check QDrant Loader status
qdrant-loader status
```

#### 3. Authentication Errors

**Error**: `OpenAI API key not found or invalid`

**Solutions**:

```bash
# Check environment variable
echo $OPENAI_API_KEY

# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# Set in configuration
{
  "env": {
    "OPENAI_API_KEY": "sk-your-actual-api-key"
  }
}
```

#### 4. No Search Results

**Error**: MCP searches return empty results

**Solutions**:

```bash
# Verify documents are ingested
qdrant-loader status

# Check collection exists
curl http://localhost:6333/collections/documents

# Re-ingest if needed
qdrant-loader ingest --path /your/documents
```

#### 5. AI Tool Connection Issues

**Error**: AI tool can't connect to MCP server

**Solutions**:

1. **Check MCP server is running**
2. **Verify configuration syntax** (valid JSON)
3. **Restart AI tool** after configuration changes
4. **Check logs** for error messages
5. **Use full path** to mcp-qdrant-loader executable

### Advanced Troubleshooting

#### Debug MCP Communication

```bash
# Enable debug logging
mcp-qdrant-loader --log-level DEBUG

# Check logs in your AI tool's console or log files
```

#### Test MCP Server Manually

```bash
# Test basic connectivity (will wait for JSON-RPC input)
mcp-qdrant-loader
```

> **Note**: Manual JSON-RPC testing is complex. Use AI tool integration for practical testing.

## 🚀 Performance Optimization

### For Large Knowledge Bases

1. **Optimize Search Parameters**
   - Use smaller `limit` values for faster responses
   - Filter by `source_types` or `project_ids` for targeted searches
   - Use specific search tools for targeted queries

2. **Environment Configuration**

   ```bash
   # Essential for performance
   export MCP_DISABLE_CONSOLE_LOGGING=true
   ```

### For Real-time Usage

1. **Keep MCP Server Running**
   - Don't restart for each query
   - Use persistent connections

2. **Optimize QDrant Configuration**
   - Use appropriate vector dimensions
   - Configure proper indexing

3. **Monitor Resource Usage**
   - Watch memory consumption
   - Monitor QDrant performance

## 📊 Best Practices

### Effective Prompting

#### 1. Be Specific and Contextual

**Good Examples**:

```text
✅ "How do I implement JWT refresh tokens in our Express.js API following our existing patterns?"
✅ "Show me code examples for handling file uploads in our Node.js application"
✅ "What's our complete code review process from PR creation to merge?"
```

**Avoid Vague Queries**:

```text
❌ "authentication"
❌ "deployment"
❌ "API"
```

#### 2. Use Natural Language

```text
✅ "Users are getting 500 errors on the login endpoint - help me debug this systematically"
✅ "Our API response times are slow - guide me through performance investigation"
✅ "What are the security considerations for our file upload feature?"
```

#### 3. Leverage Advanced Search Features

```text
✅ "Are there any inconsistencies in our API documentation across different services?" (conflict detection)
✅ "Show me documents similar to our payment processing guide" (similarity search)
✅ "Group our microservices documentation by related topics" (clustering)
```

### Configuration Management for Teams

#### Team-Specific Settings

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": [],
      "env": {
        "QDRANT_URL": "http://team-qdrant.internal:6333",
        "OPENAI_API_KEY": "team-openai-key",
        "QDRANT_COLLECTION_NAME": "team_knowledge",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
    }
  }
}
```

## 📊 Available Search Tools Summary

The MCP server provides these search capabilities:

### Search Tools Overview

1. **search** - Universal semantic search across all documents
2. **hierarchy_search** - Structure-aware search with hierarchy navigation
3. **attachment_search** - File and attachment search with content analysis

### Intelligence Tools Overview

1. **analyze_document_relationships** - Comprehensive relationship analysis
2. **find_similar_documents** - Document similarity detection using multiple metrics
3. **detect_document_conflicts** - Conflict and inconsistency identification
4. **find_complementary_content** - Complementary content discovery
5. **cluster_documents** - Document clustering based on content and relationships

## 📋 Integration Checklist

### Pre-Setup

- [ ] **AI Tool** installed and updated to latest version
- [ ] **QDrant Loader** installed and configured
- [ ] **Documents ingested** with semantic metadata
- [ ] **OpenAI API key** available and tested
- [ ] **MCP server package** installed

### Setup Configuration

- [ ] **MCP configuration** added to AI tool settings
- [ ] **Environment variables** properly set (including `MCP_DISABLE_CONSOLE_LOGGING=true`)
- [ ] **AI tool restarted** after configuration changes
- [ ] **MCP tools** visible in chat interface

### Testing

- [ ] **Basic search** working in AI tool chat
- [ ] **Hierarchy search** navigating document structures
- [ ] **Attachment search** finding files and documents
- [ ] **Cross-document analysis** detecting relationships and conflicts
- [ ] **Performance** acceptable for daily development use

### Team Optimization

- [ ] **Team configurations** documented and shared
- [ ] **Best practices** established for effective prompting
- [ ] **Security considerations** addressed for API keys
- [ ] **Onboarding documentation** updated with integration guide

---

**Your AI development tool is now enhanced with intelligent search capabilities!** 🚀

With the MCP server properly configured, your AI tool can access and search your knowledge base using **8 powerful search tools**, providing contextual answers, navigating document relationships, detecting conflicts, and analyzing content to support your development workflow. The system provides semantic understanding and cross-document intelligence that goes far beyond simple keyword matching, making your development process more informed and efficient! ✨

## 📚 Related Documentation

- **[Search Capabilities](./search-capabilities.md)** - Complete search features reference
- **[Attachment Search](./attachment-search.md)** - File and attachment search guide
- **[Hierarchy Search](./hierarchy-search.md)** - Document structure navigation
- **[Configuration Reference](../../configuration/)** - QDrant Loader configuration
- **[Troubleshooting](../../troubleshooting/)** - General troubleshooting guide
