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

- **Cursor IDE** installed ([download here](https://www.cursor.com/))
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

# Optional: MCP Server logging (for debugging)
MCP_DISABLE_CONSOLE_LOGGING=true  # Recommended for Cursor
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

### Performance Optimization

For better performance in Cursor:

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

## 🎯 Usage Examples

### Development Workflow

#### 1. Code Understanding

**Scenario**: Understanding existing code

```text
You: "How does the authentication system work in this codebase?"

AI Response (using MCP search):
Based on your documentation, here's how the authentication system works:

1. [From auth/README.md] JWT tokens are used for stateless authentication
2. [From api/auth.py] The login endpoint validates credentials and returns a token
3. [From middleware/auth.py] The auth middleware validates tokens on protected routes
4. [From config/security.md] Token expiration is set to 24 hours by default

The system uses a standard JWT-based approach with refresh tokens for long-lived sessions.
```

#### 2. Feature Implementation

**Scenario**: Implementing a new feature

```text
You: "How should I implement rate limiting for our API?"

AI Response (using MCP search):
Based on your existing patterns and documentation:

1. [From api/middleware.md] Use the existing RateLimiter middleware
2. [From config/rate-limits.md] Current limits: 100 requests/minute for authenticated users
3. [From examples/rate-limiting.py] Here's how to apply it to new endpoints
4. [From deployment/redis.md] Rate limiting uses Redis for distributed counting

Follow the existing pattern in api/v1/users.py for implementation.
```

#### 3. Bug Investigation

**Scenario**: Debugging an issue

```text
You: "Why might users be getting 'connection timeout' errors?"

AI Response (using MCP search):
Found several potential causes in your documentation:

1. [From troubleshooting/timeouts.md] Database connection pool exhaustion
2. [From monitoring/alerts.md] High CPU usage can cause timeouts
3. [From config/database.md] Default timeout is 30 seconds
4. [From logs/common-errors.md] Check for "pool_timeout" in application logs

Start by checking the database connection pool metrics and recent error logs.
```

### Documentation Workflow

#### 1. Finding Related Documentation

**Scenario**: Writing new documentation

```text
You: "What existing documentation do we have about API versioning?"

AI Response (using MCP search):
Found existing API versioning documentation:

1. [From api/versioning.md] Current versioning strategy (v1, v2)
2. [From changelog.md] Version history and breaking changes
3. [From examples/migration-v1-to-v2.md] Migration guide for clients
4. [From architecture/api-design.md] Versioning principles and guidelines

This gives you the context for maintaining consistency with existing docs.
```

#### 2. Code Examples

**Scenario**: Finding code examples

```text
You: "Show me examples of how we handle file uploads"

AI Response (using MCP search):
Found several file upload examples:

1. [From api/uploads.py] Basic file upload endpoint with validation
2. [From examples/file-processing.py] Processing uploaded files asynchronously
3. [From tests/test_uploads.py] Unit tests for upload functionality
4. [From docs/api/uploads.md] API documentation with curl examples

The pattern uses multipart/form-data with size and type validation.
```

### Team Collaboration

#### 1. Onboarding New Developers

**Scenario**: Helping new team members

```text
You: "What do new developers need to know about our deployment process?"

AI Response (using MCP search):
Here's the essential deployment information for new developers:

1. [From onboarding/deployment.md] Step-by-step deployment guide
2. [From ci-cd/pipeline.md] Automated deployment pipeline overview
3. [From environments/staging.md] How to deploy to staging for testing
4. [From troubleshooting/deployment.md] Common deployment issues and solutions

Start with the onboarding guide and then review the CI/CD pipeline documentation.
```

#### 2. Architecture Decisions

**Scenario**: Understanding design decisions

```text
You: "Why did we choose PostgreSQL over MongoDB for this project?"

AI Response (using MCP search):
Found the architectural decision documentation:

1. [From architecture/database-choice.md] Comparison of PostgreSQL vs MongoDB
2. [From decisions/adr-003-database.md] Architectural Decision Record for database selection
3. [From performance/benchmarks.md] Performance testing results
4. [From team/discussions.md] Team discussion notes from the decision process

The main factors were ACID compliance requirements and existing team expertise.
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

# Use full path in Cursor configuration
{
  "command": "/path/to/venv/bin/mcp-qdrant-loader"
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

# Verify configuration
qdrant-loader --workspace . config
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

# Update Cursor configuration
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
qdrant-loader --workspace . project status

# Check collection exists
curl http://localhost:6333/collections/documents

# Re-ingest if needed
qdrant-loader --workspace . ingest
```

#### 5. Cursor Chat Not Working

**Error**: Chat interface doesn't show MCP tools

**Solutions**:

1. **Restart Cursor** after configuration changes
2. **Check MCP configuration** syntax (valid JSON)
3. **Verify MCP server** is running
4. **Check Cursor logs** for error messages
5. **Update Cursor** to latest version

### Debug Mode

Enable debug logging for troubleshooting:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": ["--log-level", "DEBUG"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key"
      }
    }
  }
}
```

Check logs:

```bash
# View MCP server logs (if log file is configured)
tail -f /tmp/mcp-qdrant-loader.log

# View Cursor logs
# macOS: ~/Library/Logs/Cursor/main.log
# Windows: %APPDATA%\Cursor\logs\main.log
# Linux: ~/.config/Cursor/logs/main.log
```

## 🚀 Best Practices

### Effective Prompting

#### 1. Be Specific

**Good**: "How do I implement JWT authentication in our API?"
**Better**: "Show me the JWT authentication implementation pattern used in our user API endpoints"

#### 2. Reference Context

**Good**: "How does error handling work?"
**Better**: "How does error handling work in our Express.js API, and what's the standard format for error responses?"

#### 3. Ask for Examples

**Good**: "How do I write tests?"
**Better**: "Show me examples of unit tests for API endpoints, following our existing test patterns"

### Configuration Management

#### 1. Use Environment Variables

Store sensitive information in environment variables:

```bash
# .env file
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=sk-your-api-key
QDRANT_COLLECTION_NAME=project_docs
```

#### 2. Project-Specific Setup

Configure different MCP servers for different projects:

```json
{
  "mcpServers": {
    "current-project": {
      "command": "mcp-qdrant-loader",
      "env": {
        "QDRANT_COLLECTION_NAME": "current_project_docs"
      }
    }
  }
}
```

#### 3. Performance Tuning

Optimize for your specific use case:

- **Small teams**: Use default settings
- **Large knowledge bases**: Consider using search filters
- **Real-time usage**: Keep MCP server running continuously

### Security Considerations

#### 1. API Key Management

- Store API keys in environment variables
- Don't commit API keys to version control
- Use different API keys for different environments

#### 2. Network Security

- Use HTTPS for QDrant Cloud connections
- Configure firewall rules for QDrant access
- Monitor API usage and costs

#### 3. Access Control

- Limit MCP server access to authorized users
- Use separate collections for different access levels
- Monitor search queries for sensitive information

## 📊 Monitoring and Analytics

### Usage Tracking

Monitor how the MCP integration is being used:

- **Search query patterns** - What developers are searching for
- **Response quality** - How helpful the AI responses are
- **Performance metrics** - Search response times
- **Error rates** - Connection and search failures

### Performance Optimization

Track these metrics for optimization:

- **Search response time** - Average time for MCP searches
- **Cache hit rate** - If caching is enabled
- **Memory usage** - MCP server resource consumption
- **QDrant performance** - Vector search performance

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Setup and Integration](./setup-and-integration.md)** - General setup for all AI tools
- **[Search Capabilities](./search-capabilities.md)** - Available search features
- **[Basic Configuration](../../getting-started/basic-configuration.md)** - QDrant Loader setup
- **[Troubleshooting](../../troubleshooting/)** - General troubleshooting

## 📋 Cursor Integration Checklist

### Pre-Setup

- [ ] **Cursor IDE** installed and updated
- [ ] **QDrant Loader** installed and configured
- [ ] **Documents ingested** into QDrant collection
- [ ] **OpenAI API key** available
- [ ] **MCP server package** installed

### Configuration

- [ ] **MCP configuration** added to Cursor settings
- [ ] **Environment variables** properly set
- [ ] **Cursor restarted** after configuration
- [ ] **MCP tools** visible in chat interface

### Testing

- [ ] **Basic search** working in Cursor chat
- [ ] **Knowledge base access** confirmed
- [ ] **Search results** relevant and helpful
- [ ] **Performance** acceptable for daily use

### Optimization

- [ ] **Debug logging** configured if needed
- [ ] **Performance settings** tuned for use case
- [ ] **Security considerations** addressed
- [ ] **Team onboarding** documentation updated

---

**Your Cursor IDE is now supercharged with your knowledge base!** 🚀

With the MCP server properly configured, Cursor can now access and search your entire knowledge base, making development faster, more informed, and more efficient. The AI can help you understand code, implement features, debug issues, and maintain documentation - all grounded in your actual project knowledge.
