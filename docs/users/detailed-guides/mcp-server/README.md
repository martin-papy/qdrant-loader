# MCP Server Guide

The QDrant Loader MCP (Model Context Protocol) Server enables seamless integration with AI development tools like Cursor IDE, Windsurf, and Claude Desktop. This guide covers everything you need to know about setting up and using our **intelligent search system**.

## 🎯 Overview

The MCP Server acts as a bridge between your AI tools and your QDrant Loader knowledge base, providing **intelligent search capabilities** that go beyond simple keyword matching. Our system includes semantic understanding, hierarchy navigation, attachment analysis, and cross-document intelligence.

### What is MCP?

**Model Context Protocol (MCP)** is an open standard that allows AI applications to securely connect to external data sources. It enables your AI tools to access and search your knowledge base in real-time.

### Key Capabilities

✅ **Enhanced Semantic Search** - AI-powered similarity search with context understanding  
✅ **Hierarchy-Aware Navigation** - Structure-aware search with document relationships  
✅ **Intelligent Attachment Search** - File and document search with content analysis  
✅ **Cross-Document Intelligence** - Relationship analysis, conflict detection, and clustering  
✅ **Real-Time Integration** - Live access from your AI development environment  
✅ **Multi-Source Support** - Works with Git, Confluence, JIRA, and local files

## 🚀 Quick Start

### 1. Prerequisites

- **QDrant Loader** installed and configured with documents ingested
- **AI Development Tool** that supports MCP (Cursor, Claude Desktop, etc.)
- **OpenAI API Key** for semantic search capabilities

### 2. Install MCP Server

```bash
# Install the MCP server package
pip install qdrant-loader-mcp-server

# Verify installation
mcp-qdrant-loader --version
```

### 3. Configure Your AI Tool

#### For Cursor IDE

Add to your MCP servers configuration:

```json
{
  "name": "mcp-qdrant-loader",
  "command": "mcp-qdrant-loader",
  "args": [],
  "env": {
    "QDRANT_URL": "http://localhost:6333",
    "OPENAI_API_KEY": "your-openai-api-key",
    "QDRANT_COLLECTION_NAME": "documents"
  }
}
```

#### For Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your-openai-api-key",
        "QDRANT_COLLECTION_NAME": "documents"
      }
    }
  }
}
```

### 4. Test Integration

Open your AI tool and try:

```text
"Search my knowledge base for authentication implementation examples"
```

The AI should use the MCP server to search your documents and provide contextual answers.

## 🔍 Available Search Tools

### Core Search Capabilities

#### 1. **Semantic Search**

AI-powered search that understands meaning beyond keywords.

```text
Example: "How do I implement secure user authentication?"
→ Finds: Implementation guides, security best practices, code examples
```

#### 2. **Hierarchy Search**

Navigate document structures and understand relationships.

```text
Example: "Show me the structure of our API documentation"
→ Returns: Document hierarchy with navigation context and completeness analysis
```

#### 3. **Attachment Search**

Search files and attachments with intelligent content analysis.

```text
Example: "Find architecture diagrams related to microservices"
→ Locates: PDFs, images, and documents with content intelligence
```

### 🔥 Cross-Document Intelligence

#### 4. **Document Relationship Analysis**

Comprehensive analysis of how documents relate to each other.

```text
Example: Analyze relationships in "API authentication documentation"
→ Discovers: Implementation dependencies, reference patterns, usage flows
```

#### 5. **Document Similarity Detection**

Find documents with similar content for comparison or deduplication.

```text
Example: Find documents similar to "API Rate Limiting Guide"
→ Identifies: Related guides, alternative implementations, comparative content
```

#### 6. **Conflict Detection**

Identify contradictions and inconsistencies across documents.

```text
Example: Detect conflicts in "authentication policies"
→ Finds: Contradictory requirements, inconsistent configurations, policy conflicts
```

#### 7. **Complementary Content Discovery**

Find content that enhances and supports a target document.

```text
Example: Find content that complements "User Authentication API Specification"
→ Suggests: Implementation guides, testing procedures, troubleshooting docs
```

#### 8. **Document Clustering**

Group related documents by topic, purpose, and relationships.

```text
Example: Cluster "API documentation" by topic
→ Creates: Authentication cluster, Implementation cluster, Troubleshooting cluster
```

## 🎯 Integration Examples

### Development Workflow with Cursor

**Understanding Code Architecture:**

```text
You: "How does our authentication system work and what are the dependencies?"

AI Response: (Using semantic + relationship analysis)
I'll search your knowledge base for authentication information and analyze the relationships.

Found Core Authentication Components:
1. [Authentication Service] JWT token management and validation
2. [User Database] User credential storage and retrieval
3. [API Gateway] Authentication middleware and routing
4. [Security Policy] Authentication requirements and standards

Relationship Analysis Shows:
- Authentication Service depends on User Database for credential validation
- API Gateway uses Authentication Service for request authorization
- All components must comply with Security Policy requirements
- Testing procedures cover integration between all components

This gives you a complete view of your authentication architecture and dependencies.
```

**Documentation Quality Assessment:**

```text
You: "Are there any inconsistencies in our deployment documentation?"

AI Response: (Using conflict detection)
I'll analyze your deployment documentation for conflicts and inconsistencies.

Conflicts Found:
🚨 Environment Configuration Mismatch:
- Production Setup Guide: Database pool size = 50 connections
- Performance Tuning Doc: Recommends 200 connections for production
- Impact: Production may be under-configured for optimal performance

🚨 Deployment Process Differences:
- Deployment Manual: 3-step approval process required
- Quick Deploy Guide: Shows 1-step deployment
- Impact: Inconsistent deployment procedures

Recommendations:
1. Update Production Setup Guide with performance-optimized settings
2. Standardize deployment procedures across all documentation
3. Create single source of truth for configuration values
```

**Feature Implementation Planning:**

```text
You: "I need to implement real-time notifications - what should I review?"

AI Response: (Using complementary content discovery)
I'll find content that complements real-time notification implementation.

Complementary Content Found:
Implementation Foundation (High Relevance):
1. WebSocket Connection Management - Existing patterns you can extend
2. User Preference System - For notification settings and delivery
3. Authentication Context - For secure real-time connections

Architecture Considerations (Medium Relevance):
4. Database Event Triggers - For notification generation
5. Message Queue System - For reliable notification delivery
6. Monitoring Setup - For real-time system health

Support Documentation (Supporting):
7. Performance Testing - Real-time system load testing
8. Troubleshooting Guide - WebSocket and real-time issues

This gives you a complete foundation for implementing notifications effectively.
```

## ⚙️ Configuration

### Environment Variables

```bash
# Required Configuration
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-openai-api-key

# Optional Configuration
QDRANT_COLLECTION_NAME=documents  # Default: "documents"
QDRANT_API_KEY=your-qdrant-cloud-key  # For QDrant Cloud
MCP_DISABLE_CONSOLE_LOGGING=true  # Recommended for development tools
```

### Multi-Project Setup

For teams with multiple knowledge bases:

```json
{
  "mcpServers": {
    "project-docs": {
      "command": "mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION_NAME": "project_docs",
        "OPENAI_API_KEY": "your-openai-api-key"
      }
    },
    "team-knowledge": {
      "command": "mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION_NAME": "team_knowledge",
        "OPENAI_API_KEY": "your-openai-api-key"
      }
    }
  }
}
```

## 🔧 Troubleshooting

### Common Issues

#### MCP Server Not Starting

```bash
# Check if package is installed
which mcp-qdrant-loader

# Verify environment variables
echo $QDRANT_URL
echo $OPENAI_API_KEY

# Test QDrant connection
curl http://localhost:6333/health
```

#### No Search Results

```bash
# Verify documents are ingested
qdrant-loader project status --workspace .

# Check collection exists
curl http://localhost:6333/collections/documents
```

#### Performance Issues

- Use appropriate `limit` parameters (5-15 for most searches)
- Filter by `source_types` when possible
- Enable console logging to debug query processing

### Getting Help

- **[Setup Guide](./setup-and-integration.md)** - Complete setup instructions
- **[Search Capabilities](./search-capabilities.md)** - Detailed feature documentation
- **Cursor Integration** - Coming later
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions

## 🚀 Advanced Usage

### Multi-Tool Search Strategies

**Complete Feature Investigation:**

1. Start with **Semantic Search** to understand the topic
2. Use **Hierarchy Search** to explore documentation structure
3. Apply **Relationship Analysis** to understand dependencies
4. Use **Conflict Detection** to identify inconsistencies

**Documentation Quality Audit:**

1. **Hierarchy Search** for structure analysis and gap identification
2. **Conflict Detection** for inconsistency identification
3. **Similarity Detection** for duplication review
4. **Complementary Content** for completeness assessment

**Implementation Planning:**

1. **Semantic Search** for existing patterns and examples
2. **Complementary Content** for supporting documentation
3. **Relationship Analysis** for dependency understanding
4. **Clustering** for organizing related resources

### Performance Optimization

#### Search Efficiency

- Use specific queries rather than broad terms
- Apply source type filters when appropriate
- Set reasonable limits for cross-document analysis

#### Result Quality

- Provide context in your search queries
- Use natural language for better semantic understanding
- Combine multiple search tools for comprehensive results

## 📋 Integration Checklist

### Setup Requirements

- [ ] **QDrant Loader** installed and configured
- [ ] **Documents ingested** into QDrant database
- [ ] **MCP server package** installed
- [ ] **AI development tool** with MCP support
- [ ] **OpenAI API key** configured

### Configuration

- [ ] **MCP server** added to tool configuration
- [ ] **Environment variables** properly set
- [ ] **Collection name** matches ingested documents
- [ ] **Connection** tested and working

### Functionality Testing

- [ ] **Basic semantic search** working
- [ ] **Hierarchy search** navigating document structures
- [ ] **Attachment search** finding files and documents
- [ ] **Cross-document analysis** detecting relationships
- [ ] **Performance** acceptable for daily use

### Team Deployment

- [ ] **Configuration standardized** across team
- [ ] **Best practices** documented and shared
- [ ] **Security considerations** addressed
- [ ] **Troubleshooting procedures** established

---

**Transform your AI development workflow with intelligent knowledge access!** 🚀

The MCP Server brings your entire knowledge base into your AI development environment, enabling contextual assistance, intelligent exploration, and comprehensive understanding. Your AI tools can now provide answers grounded in your specific project knowledge, making development more informed and efficient.

**Ready to unlock the power of your knowledge base?** Start with our **[Setup Guide](./setup-and-integration.md)** or jump into **[Search Capabilities](./search-capabilities.md)** to explore what's possible! ✨
