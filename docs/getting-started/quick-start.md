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
### Set Up Workspace Directory
Create a workspace directory for your QDrant Loader project:
```bash
# Create workspace directory
mkdir my-qdrant-workspace
cd my-qdrant-workspace
# Create .env file with your credentials
cat > .env << EOF
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-openai-api-key-here
QDRANT_COLLECTION_NAME=quickstart
EOF
```
### Initialize Configuration
```bash
# Initialize workspace with default configuration
\1 init --workspace .
# Expected output:
# ✅ Collection initialized successfully: quickstart
```
### Test Connection
```bash
# Check project status
qdrant-loader project --workspace . status
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
cat > config.yaml << EOF
projects:
  quickstart:
    display_name: "Quick Start Project"
    description: "Getting started with QDrant Loader"
    collection_name: "quickstart"
    sources:
      localfile:
        sample_docs:
          path: "."
          include_patterns: ["*.md"]
          recursive: false
EOF
# Ingest the document
\1 ingest --workspace .
# Expected output:
# 📄 Processing documents from configured sources
# ✅ Ingested: 1 document, 4 chunks
# 🔍 Collection: quickstart
```
### Option B: Ingest a Git Repository
```bash
# Update config.yaml to include git source
cat > config.yaml << EOF
projects:
  quickstart:
    display_name: "Quick Start Project"
    description: "Getting started with QDrant Loader"
    collection_name: "quickstart"
    sources:
      git:
        qdrant_docs:
          url: "https://github.com/qdrant/qdrant-client"
          include_patterns: ["*.md", "*.rst"]
          exclude_patterns: ["node_modules/", ".git/"]
EOF
# Ingest the repository
\1 ingest --workspace .
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
cat > config.yaml << EOF
projects:
  quickstart:
    display_name: "Quick Start Project"
    description: "Getting started with QDrant Loader"
    collection_name: "quickstart"
    sources:
      localfile:
        project_docs:
          path: "my-project/"
          include_patterns: ["*.md"]
          recursive: true
EOF
# Ingest the entire directory
\1 ingest --workspace .
# Expected output:
# 📁 Scanning directory: my-project/
# 📄 Processing: 2 files found
# ✅ Ingested: 2 documents, multiple chunks
# 🔍 Collection: quickstart
```
### Verify Ingestion
```bash
# Check project status
qdrant-loader project --workspace . status
# List configured projects
qdrant-loader project --workspace . list
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
### Search via MCP
The search functionality is provided through the MCP server to AI tools. In your AI tool (Cursor), try these queries:
```
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
   \1 ingest --workspace .
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
qdrant-loader project --workspace . status
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
# Check configuration file
cat config.yaml
# Use verbose mode for debugging
\1 ingest --workspace . --log-level DEBUG
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
qdrant-loader project --workspace . status
# Check collection status
qdrant-loader project --workspace . list
# Re-ingest if needed
\1 ingest --workspace . --log-level DEBUG
```
### Getting Help
If you encounter issues:
1. **Check logs**: `\1 ingest --workspace . --log-level DEBUG`
2. **Verify setup**: `qdrant-loader project --workspace . status`
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
