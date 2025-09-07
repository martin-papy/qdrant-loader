# Quick Start Guide

Get up and running with QDrant Loader in 5 minutes! This guide walks you through your first document ingestion and AI tool integration.

## 🎯 What You'll Accomplish

By the end of this guide, you'll have:

- ✅ **QDrant Loader configured** and ready to use
- ✅ **First documents ingested** into your vector database
- ✅ **MCP server running** for AI tool integration
- ✅ **AI tool connected** (Cursor IDE example)
- ✅ **Search working** across your ingested content

**Time Required**: 5-10 minutes

## 🔧 Prerequisites

Before starting, ensure you have:

- [ ] **QDrant Loader installed** - See [Installation Guide](./installation.md)
- [ ] **QDrant database running** (Docker, Cloud, or local)
- [ ] **LLM API key** ready (OpenAI, Azure OpenAI, Ollama, or OpenAI-compatible)
- [ ] **Basic terminal/command line** familiarity

## 🚀 Step 1: Initial Configuration

### Set Up Workspace Directory

Create a workspace directory for your QDrant Loader project:

```bash
# Create workspace directory
mkdir my-qdrant-workspace
cd my-qdrant-workspace

# Create .env file with your credentials
cat > .env << EOF
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=quickstart
# LLM Configuration (new unified approach)
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-openai-api-key-here
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini
# Legacy (still supported)
OPENAI_API_KEY=your-openai-api-key-here
EOF
```

### Initialize Configuration

```bash
# Initialize workspace with default configuration
qdrant-loader init --workspace .

# Expected output:
# ✅ Collection initialized successfully: quickstart
```

### Test Connection

```bash
# Check project status
qdrant-loader config --workspace .
# Expected output shows project configuration and connection status
```

## 📄 Step 2: Your First Document Ingestion

### Option A: Ingest Local Files

```bash
# Create a sample document
cat > sample-doc.md << EOF
# Welcome to QDrant Loader

QDrant Loader is a powerful tool for ingesting documents into vector databases.

## Key Features

- Multi-source data ingestion
- 20+ file format support
- AI tool integration via MCP
- Intelligent text chunking

## Use Cases

- Knowledge base creation
- Document search and retrieval
- AI-powered development workflows
EOF

# Create a basic configuration file
cat > config.yaml << 'EOF'
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536

projects:
  quickstart:
    project_id: "quickstart"
    display_name: "Quick Start Project"
    description: "Getting started with QDrant Loader"
    sources:
      localfile:
        sample_docs:
          base_url: "file://."
          include_paths: ["*.md"]
          enable_file_conversion: false
EOF

# Ingest the document
qdrant-loader ingest --workspace .
# Expected output:
# 📄 Processing documents from configured sources
# ✅ Ingested: 1 document, 4 chunks
# 🔍 Collection: quickstart
```

### Option B: Ingest a Git Repository

```bash
# Update config.yaml to include git source
cat > config.yaml << 'EOF'
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536

projects:
  quickstart:
    project_id: "quickstart"
    display_name: "Quick Start Project"
    description: "Getting started with QDrant Loader"
    sources:
      git:
        qdrant_docs:
          base_url: "https://github.com/qdrant/qdrant-client.git"
          branch: "main"
          include_paths: ["**/*.md", "**/*.rst"]
          exclude_paths: ["node_modules/**", ".git/**"]
          file_types: ["*.md", "*.rst"]
EOF

# Ingest the repository
qdrant-loader ingest --workspace .
# Expected output:
# 📁 Cloning repository...
# 📄 Processing: multiple files found
# ✅ Ingested: multiple documents and chunks
# 🔍 Collection: quickstart
```

### Option C: Ingest Local Directory

```bash
# Create a sample project structure
mkdir -p my-project/docs
cat > my-project/docs/overview.md << EOF
# My Project Overview
This is a sample project for testing QDrant Loader.
EOF

cat > my-project/docs/api.md << EOF
# API Documentation
Our API provides powerful search capabilities.
EOF

# Update config.yaml to include the directory
cat > config.yaml << 'EOF'
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536

projects:
  quickstart:
    project_id: "quickstart"
    display_name: "Quick Start Project"
    description: "Getting started with QDrant Loader"
    sources:
      localfile:
        project_docs:
          base_url: "file://./my-project"
          include_paths: ["**/*.md"]
          enable_file_conversion: false
EOF

# Ingest the entire directory
qdrant-loader ingest --workspace .
# Expected output:
# 📁 Scanning directory: my-project/
# 📄 Processing: 2 files found
# ✅ Ingested: 2 documents, multiple chunks
# 🔍 Collection: quickstart
```

### Verify Ingestion

```bash
# Check project status
qdrant-loader config --workspace .

# List configured projects
qdrant-loader config --workspace .
```

## 🤖 Step 3: Set Up MCP Server

### Start the MCP Server

```bash
# Start MCP server (keep this terminal open)
mcp-qdrant-loader
# Expected output:
# 🚀 QDrant Loader MCP Server starting...
# 📡 Server running on stdio
# 🔍 Available tools: search, hierarchy_search, attachment_search
# ✅ Ready for connections
```

### Test MCP Server

The MCP server communicates via JSON-RPC over stdio. It doesn't have traditional CLI flags like `--list-tools`. Instead, it provides tools that AI applications can discover and use.

## 🔧 Step 4: Connect AI Tool (Cursor IDE Example)

### Configure Cursor IDE

1. **Open Cursor IDE**
2. **Open Settings** (Cmd/Ctrl + ,)
3. **Navigate to Extensions** → **MCP Servers**
4. **Add new MCP server**:

```json
{
  "name": "qdrant-loader",
  "command": "mcp-qdrant-loader",
  "args": [],
  "env": {
    "QDRANT_URL": "http://localhost:6333",
    "QDRANT_COLLECTION_NAME": "quickstart",
    "LLM_API_KEY": "your-llm-api-key-here",
    "OPENAI_API_KEY": "your-openai-api-key-here",
    "MCP_DISABLE_CONSOLE_LOGGING": "true"
  }
}
```

1. **Save and restart** Cursor

### Test AI Integration

1. **Open a new chat** in Cursor
2. **Ask about your content**:

```text
Can you search for information about QDrant Loader features?
```

1. **Expected behavior**:
   - Cursor will use the MCP server to search your ingested documents
   - You'll see search results from your content
   - AI responses will be grounded in your actual documents

## 🔍 Step 5: Explore Search Capabilities

### Search via MCP

The search functionality is provided through the MCP server to AI tools. In your AI tool (Cursor), try these queries:

```text
1. "What are the key features mentioned in the documentation?"
2. "Find information about API endpoints"
3. "Search for installation instructions"
4. "What file formats are supported?"
```

### Direct Database Queries

For direct database access, you can use the test script:

```bash
# Query the database directly (if available)
python packages/qdrant-loader/tests/scripts/query_qdrant.py \
  --config config.yaml \
  --env .env \
  --search "QDrant Loader features"
```

## 🎉 Success! What's Next?

Congratulations! You now have QDrant Loader running with:

- ✅ **Documents ingested** into your vector database
- ✅ **MCP server running** and connected to AI tools
- ✅ **Search working** across your content
- ✅ **AI integration** providing intelligent responses

### Immediate Next Steps

1. **Ingest more content**:

   ```bash
   # Add your actual project documentation to config.yaml
   # Then run ingestion
   qdrant-loader ingest --workspace .
   ```

2. **Explore AI tool features**:
   - Ask complex questions about your codebase
   - Request code examples from your documentation
   - Get summaries of specific topics
   - Find related documents and concepts

3. **Configure additional data sources**:
   - [Confluence Integration](../users/detailed-guides/data-sources/confluence.md)
   - [JIRA Integration](../users/detailed-guides/data-sources/jira.md)
   - [Git Repository Setup](../users/detailed-guides/data-sources/git-repositories.md)

### Learn More

- **Core Concepts** - Summarized inline in Getting Started
- **[Basic Configuration](./basic-configuration.md)** - Customize your setup
- **[User Guides](../users/)** - Explore all features in detail
- **[MCP Server Guide](../users/detailed-guides/mcp-server/)** - Advanced AI integration

## 🔧 Troubleshooting Quick Start

### Common Issues

#### QDrant Connection Failed

**Problem**: `Cannot connect to QDrant at localhost:6333`

**Solution**:

```bash
# Check if QDrant is running
curl http://localhost:6333/health

# Start QDrant with Docker if not running
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Verify connection
qdrant-loader config --workspace .
```

#### LLM API Errors

**Problem**: `LLM API authentication failed` or `OpenAI API authentication failed`

**Solution**:

```bash
# Check API keys
echo $LLM_API_KEY
echo $OPENAI_API_KEY

# Test API key directly (OpenAI example)
curl -H "Authorization: Bearer $LLM_API_KEY" \
  https://api.openai.com/v1/models

# Update .env file with correct key
# For new configuration:
LLM_API_KEY=your-actual-api-key
# For legacy configuration:
OPENAI_API_KEY=your-actual-api-key
```

#### No Documents Found

**Problem**: `No documents found to ingest`

**Solution**:

```bash
# Check file path exists
ls -la sample-doc.md

# Check configuration file
cat config.yaml

# Use verbose mode for debugging
qdrant-loader ingest --workspace . --log-level DEBUG
```

#### MCP Server Not Connecting

**Problem**: AI tool can't connect to MCP server

**Solution**:

```bash
# Verify MCP server is running
ps aux | grep mcp-qdrant-loader

# Check MCP server logs
mcp-qdrant-loader --log-level DEBUG

# Restart MCP server
pkill -f mcp-qdrant-loader
mcp-qdrant-loader
```

#### Search Returns No Results

**Problem**: Search queries return empty results

**Solution**:

```bash
# Verify documents are ingested
qdrant-loader config --workspace .

# Check collection status
qdrant-loader config --workspace .

# Re-ingest if needed
qdrant-loader ingest --workspace . --log-level DEBUG
```

### Getting Help

If you encounter issues:

1. **Check logs**: `qdrant-loader ingest --workspace . --log-level DEBUG`
2. **Verify setup**: `qdrant-loader config --workspace .`
3. **Search issues**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
4. **Ask for help**: [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)

## 📋 Quick Start Checklist

- [ ] **Environment configured** with API keys
- [ ] **QDrant connection** verified
- [ ] **First documents ingested** successfully
- [ ] **Search working** with MCP integration
- [ ] **MCP server running** and accessible
- [ ] **AI tool connected** and responding
- [ ] **Ready to explore** advanced features

---

**🎉 Quick Start Complete!**

You're now ready to explore the full power of QDrant Loader. The next step is reviewing the Core Concepts summarized in Getting Started, or dive into the [User Guides](../users/) for specific features and workflows.
