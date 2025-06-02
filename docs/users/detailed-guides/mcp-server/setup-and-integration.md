# Setup and Integration Guide

This comprehensive guide covers setting up the QDrant Loader MCP Server with all supported AI development tools. Follow the instructions for your specific AI tool to enable knowledge-powered development.

## 🎯 Overview

The QDrant Loader MCP Server integrates with popular AI development tools through the Model Context Protocol (MCP), providing seamless access to your knowledge base during development.

### Supported AI Tools

- **[Cursor IDE](#cursor-ide)** - AI-powered code editor with MCP support
- **[Windsurf](#windsurf)** - AI development environment
- **[Claude Desktop](#claude-desktop)** - Anthropic's desktop AI assistant
- **[Other MCP-Compatible Tools](#other-tools)** - Generic MCP setup

### What You'll Achieve

After completing this guide, you'll have:

- ✅ **MCP Server running** and accessible to your AI tool
- ✅ **AI tool configured** to use your knowledge base
- ✅ **Search capabilities** working in your development environment
- ✅ **Optimized performance** for your specific use case

## 🚀 Prerequisites

Before starting, ensure you have:

### Required Components

- **QDrant Loader** installed and configured
- **QDrant database** running (local or cloud)
- **Documents ingested** into your QDrant collection
- **OpenAI API key** for embeddings
- **AI development tool** installed

### Verification Steps

```bash
# 1. Verify QDrant Loader installation
qdrant-loader --version

# 2. Check QDrant database connection
curl http://localhost:6333/health

# 3. Verify documents are ingested
qdrant-loader --workspace . project status

# 4. Install MCP server if not already installed
pip install qdrant-loader-mcp-server
```

## 🔧 MCP Server Installation

### Install the MCP Server Package

```bash
# Option 1: Install standalone MCP server
pip install qdrant-loader-mcp-server

# Option 2: Install with QDrant Loader (includes MCP server)
pip install qdrant-loader[mcp]

# Option 3: Install from source
git clone https://github.com/your-org/qdrant-loader.git
cd qdrant-loader
pip install -e ".[mcp]"
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

# Optional: MCP Server customization
MCP_DISABLE_CONSOLE_LOGGING=true  # Recommended for Cursor
```

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

   ```
   Cursor → Preferences → Settings
   Or press: Cmd/Ctrl + ,
   ```

2. **Navigate to MCP Configuration**

   ```
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
       "QDRANT_COLLECTION_NAME": "documents"
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
           "QDRANT_API_KEY": "your-qdrant-cloud-api-key"
         }
       }
     }
   }
   ```

### Testing Cursor Integration

1. **Restart Cursor** after configuration changes

2. **Open Chat Interface**

   ```
   Press: Cmd/Ctrl + L
   Or: Click the chat icon in the sidebar
   ```

3. **Test Knowledge Access**

   ```
   Ask: "Can you search my knowledge base for information about API authentication?"
   ```

## 🌊 Windsurf

Windsurf is an AI development environment with MCP support.

### Installation

1. **Download Windsurf**
   - Visit the Windsurf website
   - Download for your platform
   - Install and launch Windsurf

### Configuration

1. **Open Settings**

   ```
   Windsurf → Preferences → Settings
   ```

2. **Navigate to MCP Configuration**

   ```
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

   ```
   Ask: "Can you search for information about deployment procedures?"
   ```

## 🤖 Claude Desktop

Claude Desktop is Anthropic's desktop AI assistant with MCP support.

### Installation

1. **Download Claude Desktop**
   - Visit [claude.ai](https://claude.ai/)
   - Download the desktop application
   - Install and launch Claude Desktop

### Configuration

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
           "OPENAI_API_KEY": "your_openai_key"
         }
       }
     }
   }
   ```

### Testing Claude Desktop Integration

1. **Restart Claude Desktop** after configuration

2. **Start a New Conversation**

3. **Test Knowledge Access**

   ```
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
        "QDRANT_COLLECTION_NAME": "documents"
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

# Run with specific configuration
mcp-qdrant-loader --config custom-config.yaml

# Run with debug logging
mcp-qdrant-loader --log-level DEBUG
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

# Use full path in configuration
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

# Check configuration
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
qdrant-loader --workspace . project status

# Check collection exists
curl http://localhost:6333/collections/documents

# Re-ingest if needed
qdrant-loader --workspace . ingest
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
export MCP_LOG_LEVEL=DEBUG
export MCP_LOG_FILE="/tmp/mcp-debug.log"
mcp-qdrant-loader

# Monitor logs
tail -f /tmp/mcp-debug.log
```

#### Test MCP Server Manually

```bash
# Test JSON-RPC communication
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | mcp-qdrant-loader

# Test search functionality
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | mcp-qdrant-loader
```

## 🚀 Performance Optimization

### For Large Knowledge Bases

1. **Optimize Search Parameters**
   - Use smaller `limit` values
   - Filter by `source_types` or `project_ids`
   - Use specific search tools for targeted queries

2. **Environment Configuration**

   ```bash
   # Disable console logging for better performance
   export MCP_DISABLE_CONSOLE_LOGGING=true
   
   # Use log file for debugging
   export MCP_LOG_FILE="/path/to/mcp.log"
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

## 📊 Monitoring and Maintenance

### Health Checks

```bash
# Check QDrant health
curl http://localhost:6333/health

# Check collection status
curl http://localhost:6333/collections/documents

# Verify MCP server
mcp-qdrant-loader --version
```

### Log Management

```bash
# Configure logging
export MCP_LOG_LEVEL=INFO
export MCP_LOG_FILE="/var/log/mcp-qdrant-loader.log"

# Rotate logs (add to crontab)
0 0 * * * /usr/sbin/logrotate /etc/logrotate.d/mcp-qdrant-loader
```

### Regular Maintenance

1. **Update Dependencies**

   ```bash
   pip install --upgrade qdrant-loader-mcp-server
   ```

2. **Monitor Performance**
   - Track search response times
   - Monitor memory usage
   - Check error rates

3. **Backup Configuration**
   - Save MCP server configurations
   - Document environment variables
   - Keep track of AI tool settings

## 📚 Related Documentation

- **[MCP Server Overview](./README.md)** - Main MCP server guide
- **[Search Capabilities](./search-capabilities.md)** - Complete search features
- **[Cursor Integration](./cursor-integration.md)** - Detailed Cursor setup
- **[Configuration Reference](../../configuration/)** - QDrant Loader configuration
- **[Troubleshooting](../../troubleshooting/)** - General troubleshooting

---

**Ready to integrate AI tools with your knowledge base!** 🚀

Choose your AI tool from the sections above and follow the specific setup instructions. The MCP server will provide powerful search capabilities that make your AI tools much more useful by grounding them in your actual documentation and codebase.
