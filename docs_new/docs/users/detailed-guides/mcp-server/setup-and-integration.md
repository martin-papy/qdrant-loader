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
qdrant-loader list

# 4. Test search functionality
qdrant-loader search "test query"

# 5. Install MCP server if not already installed
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

# Test MCP server startup
mcp-qdrant-loader --test

# Expected output:
# ✅ QDrant connection: OK
# ✅ OpenAI API: OK
# ✅ MCP tools: 3 available
# ✅ Configuration: Valid
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
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_MAX_RESULTS=10
MCP_SERVER_TIMEOUT=30
```

## 🎨 Cursor IDE

Cursor is an AI-powered code editor with excellent MCP support. It's the most popular choice for AI-assisted development.

### Installation

1. **Download Cursor IDE**
   - Visit [cursor.sh](https://cursor.sh/)
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

3. **Verify MCP Tools**
   - You should see "QDrant Loader" listed as available tools
   - The status should show "Connected"

4. **Test Search**

   ```
   Type: "Can you search for information about deployment?"
   ```

   Expected response: The AI should use the MCP server to search your knowledge base and provide relevant results.

### Advanced Cursor Configuration

#### Project-Specific Setup

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

#### Performance Optimization

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
        "MCP_SERVER_CACHE_ENABLED": "true",
        "MCP_SERVER_CACHE_TTL": "300"
      }
    }
  }
}
```

## 🌊 Windsurf

Windsurf is an AI development environment with MCP support for enhanced development workflows.

### Installation

1. **Download Windsurf**
   - Visit the Windsurf website
   - Download for your platform
   - Install and launch Windsurf

### Configuration

1. **Open Windsurf Settings**

   ```
   Windsurf → Preferences → Settings
   Or: File → Preferences → Settings
   ```

2. **Navigate to MCP Configuration**

   ```
   Search: "MCP" or "Model Context Protocol"
   Or: Extensions → MCP Servers
   ```

3. **Add QDrant Loader Configuration**

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

### Alternative Configuration File

If Windsurf uses a configuration file:

1. **Locate Configuration File**

   ```bash
   # Common locations
   ~/.windsurf/config.json
   ~/.config/windsurf/mcp-servers.json
   ```

2. **Add MCP Server Configuration**

   ```json
   {
     "mcp": {
       "servers": {
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
   }
   ```

### Testing Windsurf Integration

1. **Restart Windsurf** after configuration

2. **Access AI Features**
   - Open the AI chat or assistant panel
   - Look for MCP tools or knowledge base access

3. **Test Knowledge Search**

   ```
   Ask: "Search our documentation for deployment procedures"
   ```

## 🤖 Claude Desktop

Claude Desktop is Anthropic's desktop application with MCP support for enhanced AI assistance.

### Installation

1. **Download Claude Desktop**
   - Visit [claude.ai](https://claude.ai/)
   - Download the desktop application
   - Install and sign in with your Anthropic account

### Configuration

Claude Desktop uses a configuration file for MCP servers:

1. **Locate Configuration File**

   ```bash
   # macOS
   ~/Library/Application Support/Claude/claude_desktop_config.json
   
   # Windows
   %APPDATA%\Claude\claude_desktop_config.json
   
   # Linux
   ~/.config/Claude/claude_desktop_config.json
   ```

2. **Create or Edit Configuration**

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

3. **Advanced Configuration**

   ```json
   {
     "mcpServers": {
       "qdrant-loader": {
         "command": "mcp-qdrant-loader",
         "args": [
           "--max-results", "10",
           "--log-level", "INFO"
         ],
         "env": {
           "QDRANT_URL": "http://localhost:6333",
           "OPENAI_API_KEY": "your-openai-api-key",
           "QDRANT_COLLECTION_NAME": "documents",
           "MCP_SERVER_TIMEOUT": "30"
         }
       }
     }
   }
   ```

### Testing Claude Desktop Integration

1. **Restart Claude Desktop** after configuration changes

2. **Check MCP Status**
   - Look for MCP server indicators in the interface
   - Check for "QDrant Loader" in available tools

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
# Test MCP server directly
mcp-qdrant-loader --test

# Run MCP server in stdio mode (most common)
mcp-qdrant-loader

# Run with specific configuration
mcp-qdrant-loader --config custom-config.yaml

# List available tools
mcp-qdrant-loader --list-tools
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
qdrant-loader config show
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
qdrant-loader list

# Check collection exists
qdrant-loader status

# Test search directly
qdrant-loader search "test query"

# Re-ingest if needed
qdrant-loader ingest --source local --path docs/
```

#### 5. Slow Performance

**Problem**: MCP searches are slow

**Solutions**:

```json
{
  "args": ["--max-results", "3", "--timeout", "5"],
  "env": {
    "MCP_SERVER_CACHE_ENABLED": "true",
    "MCP_SERVER_CACHE_TTL": "300"
  }
}
```

### Debug Mode

Enable debug logging for troubleshooting:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": ["--log-level", "DEBUG"],
      "env": {
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

# View AI tool logs (varies by tool)
# Cursor: ~/Library/Logs/Cursor/main.log
# Claude: ~/Library/Logs/Claude/main.log
```

## ⚙️ Advanced Configuration

### Multiple Knowledge Bases

Configure different MCP servers for different knowledge bases:

```json
{
  "mcpServers": {
    "project-docs": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "project_docs"],
      "env": {
        "QDRANT_COLLECTION_NAME": "project_docs"
      }
    },
    "company-wiki": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "company_wiki"],
      "env": {
        "QDRANT_COLLECTION_NAME": "company_wiki"
      }
    },
    "api-docs": {
      "command": "mcp-qdrant-loader",
      "args": ["--collection", "api_documentation"],
      "env": {
        "QDRANT_COLLECTION_NAME": "api_documentation"
      }
    }
  }
}
```

### Performance Tuning

#### For Large Knowledge Bases

```json
{
  "args": [
    "--max-results", "5",
    "--timeout", "15",
    "--similarity-threshold", "0.8"
  ],
  "env": {
    "MCP_SERVER_CACHE_ENABLED": "true",
    "MCP_SERVER_CACHE_TTL": "600",
    "MCP_SERVER_MAX_CONNECTIONS": "3"
  }
}
```

#### For Real-time Usage

```json
{
  "args": [
    "--max-results", "3",
    "--timeout", "5",
    "--quick-mode"
  ],
  "env": {
    "MCP_SERVER_CACHE_ENABLED": "true",
    "MCP_SERVER_CACHE_TTL": "300"
  }
}
```

### Security Configuration

#### Secure Environment Variables

```bash
# Use environment file
export $(cat .env | xargs)

# Or use secure credential storage
# macOS Keychain, Windows Credential Manager, etc.
```

#### Network Security

```json
{
  "env": {
    "QDRANT_URL": "https://your-secure-qdrant-instance.com",
    "QDRANT_API_KEY": "your-secure-api-key",
    "MCP_SERVER_TLS_ENABLED": "true"
  }
}
```

## 📊 Monitoring and Analytics

### Usage Tracking

Enable analytics to monitor MCP server usage:

```json
{
  "env": {
    "MCP_SERVER_ANALYTICS": "true",
    "MCP_SERVER_ANALYTICS_FILE": "~/.qdrant-loader/logs/mcp-analytics.log"
  }
}
```

### Performance Monitoring

```bash
# Monitor search performance
tail -f ~/.qdrant-loader/logs/mcp-server.log | grep "performance"

# View usage statistics
grep "search_query" ~/.qdrant-loader/logs/mcp-analytics.log | \
  cut -d'"' -f4 | sort | uniq -c | sort -nr | head -10
```

### Health Checks

```bash
# Check MCP server health
mcp-qdrant-loader --health

# Test all connections
mcp-qdrant-loader --test-all

# Monitor continuously
watch -n 30 'mcp-qdrant-loader --health'
```

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Cursor Integration](./cursor-integration.md)** - Detailed Cursor setup
- **[Search Capabilities](./search-capabilities.md)** - Available search features
- **[Basic Configuration](../../getting-started/basic-configuration.md)** - QDrant Loader setup

## 📋 Setup Checklist

### Pre-Setup

- [ ] **QDrant Loader** installed and configured
- [ ] **QDrant database** running and accessible
- [ ] **Documents ingested** into QDrant collection
- [ ] **OpenAI API key** configured
- [ ] **AI tool** installed and updated

### MCP Server Setup

- [ ] **MCP server package** installed
- [ ] **Environment variables** configured
- [ ] **MCP server** starts without errors
- [ ] **Test mode** passes all checks

### AI Tool Integration

- [ ] **MCP configuration** added to AI tool
- [ ] **AI tool restarted** after configuration
- [ ] **MCP tools** visible in AI tool interface
- [ ] **Search functionality** tested and working

### Optimization

- [ ] **Performance settings** tuned for use case
- [ ] **Caching enabled** if needed
- [ ] **Logging configured** appropriately
- [ ] **Monitoring enabled** if desired

---

**Your AI tools are now supercharged with your knowledge base!** 🚀

With the MCP server properly configured, your AI development tools can now access and search your entire knowledge base, making development faster, more informed, and more efficient. The AI can help you understand code, implement features, debug issues, and maintain documentation - all grounded in your actual project knowledge.
