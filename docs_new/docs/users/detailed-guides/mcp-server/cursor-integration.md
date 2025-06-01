# Cursor IDE Integration Guide

This guide provides complete instructions for integrating QDrant Loader with Cursor IDE, enabling AI-powered development with access to your knowledge base.

## 🎯 Overview

Cursor IDE is an AI-powered code editor that supports the Model Context Protocol (MCP). By integrating QDrant Loader, you can:

- **Ask questions about your codebase** and get contextual answers
- **Search documentation** without leaving your IDE
- **Get AI suggestions** based on your specific project knowledge
- **Access team knowledge** during development

## 🚀 Quick Setup

### Prerequisites

- **Cursor IDE** installed ([download here](https://cursor.sh/))
- **QDrant Loader** installed and configured
- **Documents ingested** into your QDrant database
- **MCP server** package installed

### 1. Install MCP Server

```bash
# Install the MCP server package
pip install qdrant-loader-mcp-server

# Or if using the full QDrant Loader package
pip install qdrant-loader[mcp]

# Verify installation
mcp-qdrant-loader --version
```

### 2. Configure Cursor IDE

#### Option A: Using Cursor Settings UI

1. **Open Cursor Settings**
   - Press `Cmd/Ctrl + ,` or go to **File** → **Preferences** → **Settings**

2. **Navigate to MCP Configuration**
   - Search for "MCP" in the settings search bar
   - Or go to **Extensions** → **MCP Servers**

3. **Add QDrant Loader Server**
   - Click **"Add MCP Server"**
   - Fill in the configuration:

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

#### Option B: Manual Configuration File

1. **Locate Cursor Configuration Directory**

```bash
# macOS
~/.cursor/User/globalStorage/cursor.mcp/

# Windows
%APPDATA%\Cursor\User\globalStorage\cursor.mcp\

# Linux
~/.config/Cursor/User/globalStorage/cursor.mcp/
```

2. **Create or Edit MCP Configuration**

Create/edit `mcp-servers.json`:

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
        "QDRANT_API_KEY": "your-qdrant-cloud-api-key"
      }
    }
  }
}
```

### 3. Restart Cursor

After configuration, restart Cursor IDE to load the MCP server.

### 4. Verify Integration

1. **Open Cursor Chat**
   - Press `Cmd/Ctrl + L` or click the chat icon
   - You should see "QDrant Loader" listed as an available tool

2. **Test the Connection**
   - Type: "Can you search for information about deployment?"
   - The AI should use the MCP server to search your knowledge base

## ⚙️ Advanced Configuration

### Environment Variables Setup

Create a `.env` file in your project root:

```bash
# .env file for project-specific configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_project_docs
OPENAI_API_KEY=sk-your-openai-api-key

# Optional: QDrant Cloud
QDRANT_API_KEY=your-qdrant-cloud-api-key

# Optional: MCP Server customization
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_MAX_RESULTS=10
MCP_SERVER_TIMEOUT=30
```

### Project-Specific Configuration

For different projects with different knowledge bases:

```json
{
  "mcpServers": {
    "project-docs": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "project_docs"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "project_docs"
      }
    },
    "team-knowledge": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "team_knowledge"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "team_knowledge"
      }
    }
  }
}
```

### Performance Optimization

For better performance in Cursor:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": [
        "--max-results", "5",
        "--timeout", "10",
        "--log-level", "WARNING"
      ],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "documents",
        "MCP_SERVER_CACHE_ENABLED": "true",
        "MCP_SERVER_CACHE_TTL": "300"
      }
    }
  }
}
```

## 🎯 Usage Examples

### Development Workflow

#### 1. Code Understanding

**Scenario**: Understanding existing code

```text
You: "How does the authentication system work in this codebase?"

AI Response (using MCP search):
Based on your codebase documentation, here's how authentication works:

1. **JWT Token System** (from auth/README.md):
   - Uses JWT tokens for stateless authentication
   - Tokens expire after 24 hours
   - Refresh tokens valid for 30 days

2. **Implementation** (from auth/jwt.py):
   - `generate_token()` creates new JWT tokens
   - `verify_token()` validates incoming tokens
   - `refresh_token()` handles token renewal

3. **Middleware** (from middleware/auth.py):
   - Automatically validates tokens on protected routes
   - Adds user context to request object

Would you like me to show you specific code examples?
```

#### 2. Feature Implementation

**Scenario**: Implementing a new feature

```text
You: "I need to add rate limiting to our API. How should I implement this?"

AI Response (using MCP search):
Found several relevant approaches in your documentation:

1. **Rate Limiting Strategy** (from architecture/rate-limiting.md):
   - Use Redis for distributed rate limiting
   - Implement sliding window algorithm
   - Different limits for different user tiers

2. **Existing Implementation** (from middleware/rate_limit.py):
   - `RateLimiter` class already exists
   - Supports per-user and per-IP limiting
   - Configurable time windows and limits

3. **Configuration** (from config/rate_limits.yaml):
   - Current limits: 1000 req/hour for authenticated users
   - 100 req/hour for anonymous users
   - Premium users: 5000 req/hour

Here's how to add it to your new endpoint...
```

#### 3. Debugging and Troubleshooting

**Scenario**: Debugging an issue

```text
You: "Users are reporting slow response times. What could be causing this?"

AI Response (using MCP search):
Found several potential causes in your troubleshooting docs:

1. **Database Performance** (from troubleshooting/database.md):
   - Check for missing indexes on frequently queried columns
   - Monitor connection pool usage
   - Look for long-running queries

2. **Caching Issues** (from troubleshooting/cache.md):
   - Redis cache might be full or slow
   - Check cache hit rates in monitoring dashboard
   - Verify cache invalidation is working correctly

3. **Recent Changes** (from changelog.md):
   - Version 2.1.0 added new database queries
   - Some users reported performance regression
   - Hotfix 2.1.1 available with optimizations

Let me search for specific performance monitoring commands...
```

### Documentation Workflow

#### 1. Finding Related Documentation

```text
You: "I'm updating the API documentation. What existing docs should I review?"

AI Response (using MCP search):
Found existing API documentation that you should review:

1. **Core API Docs** (from api/):
   - api/authentication.md - Auth endpoints
   - api/users.md - User management endpoints
   - api/data.md - Data manipulation endpoints

2. **Examples** (from examples/api/):
   - Complete request/response examples
   - Error handling patterns
   - Rate limiting examples

3. **OpenAPI Spec** (from openapi.yaml):
   - Current API specification
   - Last updated 2 weeks ago
   - Includes all current endpoints

4. **Change History** (from api/CHANGELOG.md):
   - Recent API changes and deprecations
   - Breaking changes in v2.0
   - Migration guide for v1 to v2

This gives you a complete picture of the current API documentation state.
```

#### 2. Consistency Checking

```text
You: "Are there any inconsistencies in how we document error responses?"

AI Response (using MCP search):
Found some inconsistencies in error response documentation:

1. **Inconsistent Error Formats**:
   - api/users.md uses `{"error": "message"}` format
   - api/data.md uses `{"message": "error", "code": 400}` format
   - api/auth.md uses `{"errors": ["message1", "message2"]}` format

2. **Missing Error Codes**:
   - Some endpoints don't document all possible error codes
   - 429 (rate limit) responses not documented consistently

3. **Recommended Standard** (from style-guide.md):
   - Use consistent `{"error": {"message": "...", "code": "..."}}` format
   - Always document 400, 401, 403, 404, 429, 500 responses

Would you like me to find all endpoints that need error documentation updates?
```

### Team Collaboration

#### 1. Onboarding New Team Members

```text
You: "A new developer is joining. What documentation should they read first?"

AI Response (using MCP search):
Here's the recommended onboarding path for new developers:

1. **Getting Started** (from onboarding/):
   - onboarding/README.md - Overview and setup
   - onboarding/development-environment.md - Local setup
   - onboarding/first-contribution.md - Making your first PR

2. **Architecture** (from architecture/):
   - architecture/overview.md - System architecture
   - architecture/data-flow.md - How data moves through the system
   - architecture/security.md - Security considerations

3. **Development Practices** (from development/):
   - development/coding-standards.md - Code style and conventions
   - development/testing.md - Testing practices
   - development/deployment.md - How we deploy

4. **Team Processes** (from team/):
   - team/workflow.md - Our development workflow
   - team/code-review.md - Code review process
   - team/communication.md - How we communicate

This should get them productive within their first week.
```

## 🔧 Troubleshooting

### Common Issues

#### 1. MCP Server Not Found

**Error**: `Command 'mcp-qdrant-loader' not found`

**Solutions**:

```bash
# Check if MCP server is installed
which mcp-qdrant-loader

# Install if missing
pip install qdrant-loader-mcp-server

# Check PATH
echo $PATH

# Use full path in configuration
{
  "command": "/path/to/venv/bin/mcp-qdrant-loader",
  ...
}
```

#### 2. Connection Refused

**Error**: `Connection refused to QDrant server`

**Solutions**:

```bash
# Check if QDrant is running
curl http://localhost:6333/health

# Start QDrant if needed
docker run -p 6333:6333 qdrant/qdrant

# Check configuration
qdrant-loader config show
```

#### 3. No Search Results

**Error**: MCP searches return empty results

**Solutions**:

```bash
# Verify documents are ingested
qdrant-loader list

# Check collection exists
qdrant-loader status

# Test search directly
qdrant-loader search "test query"

# Re-ingest if needed
qdrant-loader ingest --source local --path docs/
```

#### 4. Slow Response Times

**Problem**: MCP searches are slow in Cursor

**Solutions**:

1. **Reduce result limit**:

```json
{
  "args": ["--max-results", "3"],
  ...
}
```

2. **Increase timeout**:

```json
{
  "env": {
    "MCP_SERVER_TIMEOUT": "5",
    ...
  }
}
```

3. **Enable caching**:

```json
{
  "env": {
    "MCP_SERVER_CACHE_ENABLED": "true",
    "MCP_SERVER_CACHE_TTL": "300",
    ...
  }
}
```

#### 5. Authentication Errors

**Error**: `OpenAI API key not found or invalid`

**Solutions**:

```bash
# Check environment variable
echo $OPENAI_API_KEY

# Set in configuration
{
  "env": {
    "OPENAI_API_KEY": "sk-your-actual-api-key",
    ...
  }
}

# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

### Debug Mode

Enable debug logging to troubleshoot issues:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": ["--log-level", "DEBUG"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "MCP_SERVER_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Check logs:

```bash
# View MCP server logs
tail -f ~/.qdrant-loader/logs/mcp-server.log

# View Cursor logs (macOS)
tail -f ~/Library/Logs/Cursor/main.log

# View Cursor logs (Windows)
tail -f %APPDATA%\Cursor\logs\main.log
```

## 🎨 Customization

### Custom Search Prompts

You can customize how the AI uses search results by creating custom prompts:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": [
        "--search-prompt", "Search our codebase and documentation for: {query}",
        "--result-format", "detailed"
      ],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key"
      }
    }
  }
}
```

### Multiple Knowledge Bases

Configure multiple MCP servers for different knowledge bases:

```json
{
  "mcpServers": {
    "project-docs": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "project_docs"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "project_docs"
      }
    },
    "company-wiki": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "company_wiki"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "company_wiki"
      }
    },
    "api-docs": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "api_documentation"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "api_documentation"
      }
    }
  }
}
```

## 📊 Monitoring Usage

### Track MCP Usage

Enable analytics to see how the MCP server is being used:

```json
{
  "env": {
    "MCP_SERVER_ANALYTICS": "true",
    "MCP_SERVER_ANALYTICS_FILE": "~/.qdrant-loader/logs/mcp-analytics.log",
    ...
  }
}
```

### View Usage Statistics

```bash
# View search queries
grep "search_query" ~/.qdrant-loader/logs/mcp-analytics.log

# View response times
grep "response_time" ~/.qdrant-loader/logs/mcp-analytics.log

# View most common queries
grep "search_query" ~/.qdrant-loader/logs/mcp-analytics.log | \
  cut -d'"' -f4 | sort | uniq -c | sort -nr | head -10
```

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Search Capabilities](./search-capabilities.md)** - Available search features
- **[Setup and Integration](./setup-and-integration.md)** - General setup guide
- **[Basic Configuration](../../getting-started/basic-configuration.md)** - QDrant Loader configuration

## 📋 Cursor Integration Checklist

- [ ] **Cursor IDE** installed and updated
- [ ] **QDrant Loader** installed with MCP server
- [ ] **Documents ingested** into QDrant database
- [ ] **MCP server configuration** added to Cursor
- [ ] **Environment variables** properly set
- [ ] **Connection tested** successfully
- [ ] **Search functionality** working in Cursor chat
- [ ] **Performance optimized** for your use case

---

**Ready to supercharge your development with AI-powered knowledge search!** 🚀

With QDrant Loader integrated into Cursor, you now have instant access to your entire knowledge base while coding. The AI can help you understand code, implement features, debug issues, and maintain documentation - all grounded in your actual project knowledge.
