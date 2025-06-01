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
- [ ] **OpenAI API key** ready
- [ ] **Basic terminal/command line** familiarity

## 🚀 Step 1: Initial Configuration

### Set Up Environment Variables

Create a `.env` file in your working directory:

```bash
# Create .env file with your credentials
cat > .env << EOF
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-openai-api-key-here
QDRANT_COLLECTION_NAME=quickstart
EOF
```

### Initialize Configuration

```bash
# Create default configuration
qdrant-loader config init

# Verify configuration
qdrant-loader config show
```

### Test Connection

```bash
# Test QDrant connection
qdrant-loader status

# Expected output:
# ✅ QDrant: Connected (http://localhost:6333)
# ✅ OpenAI: API key configured
# ✅ Collection: quickstart (ready)
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

# Ingest the document
qdrant-loader ingest --source local --path sample-doc.md

# Expected output:
# 📄 Processing: sample-doc.md
# ✅ Ingested: 1 document, 4 chunks, 1,024 tokens
# 🔍 Collection: quickstart (1 total documents)
```

### Option B: Ingest a Git Repository

```bash
# Ingest documentation from a public repository
qdrant-loader ingest --source git --url https://github.com/qdrant/qdrant-client

# Expected output:
# 📁 Cloning repository...
# 📄 Processing: 45 files found
# ✅ Ingested: 45 documents, 234 chunks, 15,678 tokens
# 🔍 Collection: quickstart (45 total documents)
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

# Ingest the entire directory
qdrant-loader ingest --source local --path my-project/

# Expected output:
# 📁 Scanning directory: my-project/
# 📄 Processing: 2 files found
# ✅ Ingested: 2 documents, 6 chunks, 512 tokens
# 🔍 Collection: quickstart (2 total documents)
```

### Verify Ingestion

```bash
# Check collection status
qdrant-loader status

# List ingested documents
qdrant-loader list

# Search your content
qdrant-loader search "QDrant Loader features"
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

In a new terminal:

```bash
# Test MCP server tools
mcp-qdrant-loader --list-tools

# Expected output:
# Available MCP Tools:
# - search: Semantic search across all documents
# - hierarchy_search: Search with document hierarchy
# - attachment_search: Search file attachments
```

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
    "OPENAI_API_KEY": "your-openai-api-key-here",
    "QDRANT_COLLECTION_NAME": "quickstart"
  }
}
```

5. **Save and restart** Cursor

### Test AI Integration

1. **Open a new chat** in Cursor
2. **Ask about your content**:

```
Can you search for information about QDrant Loader features?
```

3. **Expected behavior**:
   - Cursor will use the MCP server to search your ingested documents
   - You'll see search results from your content
   - AI responses will be grounded in your actual documents

## 🔍 Step 5: Explore Search Capabilities

### Basic Search

```bash
# Simple text search
qdrant-loader search "vector database"

# Search with filters
qdrant-loader search "API documentation" --limit 5

# Search specific collection
qdrant-loader search "features" --collection quickstart
```

### Advanced Search via MCP

In your AI tool (Cursor), try these queries:

```
1. "What are the key features mentioned in the documentation?"
2. "Find information about API endpoints"
3. "Search for installation instructions"
4. "What file formats are supported?"
```

### Search Results Format

```bash
# Example search output
qdrant-loader search "QDrant Loader"

# Results:
# 🔍 Search Results (3 found):
# 
# 1. sample-doc.md (score: 0.95)
#    "QDrant Loader is a powerful tool for ingesting documents..."
#    Source: local/sample-doc.md
# 
# 2. overview.md (score: 0.87)
#    "This is a sample project for testing QDrant Loader..."
#    Source: local/my-project/docs/overview.md
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
   # Add your actual project documentation
   qdrant-loader ingest --source local --path /path/to/your/docs
   
   # Connect to Confluence
   qdrant-loader ingest --source confluence --space "YOUR_SPACE"
   
   # Ingest from multiple Git repositories
   qdrant-loader ingest --source git --url https://github.com/your-org/repo1
   qdrant-loader ingest --source git --url https://github.com/your-org/repo2
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

- **[Core Concepts](./core-concepts.md)** - Understand how QDrant Loader works
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
qdrant-loader status
```

#### OpenAI API Errors

**Problem**: `OpenAI API authentication failed`

**Solution**:

```bash
# Check API key
echo $OPENAI_API_KEY

# Test API key directly
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# Update .env file with correct key
```

#### No Documents Found

**Problem**: `No documents found to ingest`

**Solution**:

```bash
# Check file path exists
ls -la sample-doc.md

# Check supported file types
qdrant-loader ingest --help

# Use verbose mode for debugging
qdrant-loader ingest --source local --path . --verbose
```

#### MCP Server Not Connecting

**Problem**: AI tool can't connect to MCP server

**Solution**:

```bash
# Verify MCP server is running
ps aux | grep mcp-qdrant-loader

# Check MCP server logs
mcp-qdrant-loader --verbose

# Restart MCP server
pkill -f mcp-qdrant-loader
mcp-qdrant-loader
```

#### Search Returns No Results

**Problem**: Search queries return empty results

**Solution**:

```bash
# Verify documents are ingested
qdrant-loader list

# Check collection status
qdrant-loader status

# Try broader search terms
qdrant-loader search "the" --limit 1

# Re-ingest if needed
qdrant-loader ingest --source local --path sample-doc.md --force
```

### Getting Help

If you encounter issues:

1. **Check logs**: `qdrant-loader --verbose`
2. **Verify setup**: `qdrant-loader config --check`
3. **Search issues**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
4. **Ask for help**: [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)

## 📋 Quick Start Checklist

- [ ] **Environment configured** with API keys
- [ ] **QDrant connection** verified
- [ ] **First documents ingested** successfully
- [ ] **Search working** with basic queries
- [ ] **MCP server running** and accessible
- [ ] **AI tool connected** and responding
- [ ] **Ready to explore** advanced features

---

**🎉 Quick Start Complete!**

You're now ready to explore the full power of QDrant Loader. The next step is understanding the [Core Concepts](./core-concepts.md) to make the most of your setup, or dive into the [User Guides](../users/) for specific features and workflows.
