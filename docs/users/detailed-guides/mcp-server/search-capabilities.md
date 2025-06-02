# Search Capabilities Guide

This guide covers all the search capabilities available through the QDrant Loader MCP Server, helping you get the most out of your AI-powered knowledge search.

## 🎯 Overview

The QDrant Loader MCP Server provides three powerful search tools that enable AI assistants to find and retrieve information from your knowledge base with high precision and contextual awareness.

### Available Search Tools

1. **Semantic Search** - Basic similarity-based search across all documents
2. **Hierarchy Search** - Structure-aware search with document relationships
3. **Attachment Search** - Specialized search for file attachments

Each tool is optimized for different use cases and can be combined for comprehensive knowledge retrieval.

## 🔍 Semantic Search Tool

### Purpose

The semantic search tool performs similarity-based search across all ingested documents using vector embeddings. It understands the meaning behind queries, not just keyword matches.

### How It Works

```
Query: "How to deploy applications?"
    ↓
Vector Embedding: [0.1, -0.3, 0.8, ...]
    ↓
Similarity Search in QDrant
    ↓
Results: Documents about deployment, CI/CD, containers, etc.
```

### Parameters

```json
{
  "name": "search",
  "parameters": {
    "query": "string",              // Required: Search query or question
    "limit": 10,                    // Optional: Number of results (default: 5)
    "source_types": ["git", "confluence", "jira", "documentation", "localfile"], // Optional: Filter by source types
    "project_ids": ["project1", "project2"]  // Optional: Filter by specific projects
  }
}
```

### Example Queries

#### Basic Search

```
Query: "authentication methods"

Results:
1. [auth/jwt.md] JWT Token Authentication
   - Explains JWT implementation and best practices

2. [security/oauth.md] OAuth 2.0 Integration
   - OAuth flow and configuration

3. [api/auth-endpoints.md] Authentication API Endpoints
   - Login, logout, and token refresh endpoints
```

#### Filtered Search

```
Query: "deployment strategies"
Filters: source_types=["confluence"], project_ids=["devops-project"]

Results:
1. [Confluence: DevOps/Deployment] Blue-Green Deployment Strategy
   - Comprehensive guide to blue-green deployments

2. [Confluence: Architecture/Scaling] Canary Deployment Process
   - Step-by-step canary deployment guide
```

### Advanced Search Techniques

#### 1. Question-Based Queries

Instead of keywords, ask natural questions:

```
❌ "docker kubernetes deployment"
✅ "How do I deploy a Docker container to Kubernetes?"

❌ "API rate limit error"
✅ "What should I do when I get rate limit errors from the API?"
```

#### 2. Context-Rich Queries

Provide context for better results:

```
❌ "configuration"
✅ "How do I configure the authentication system for production?"

❌ "error handling"
✅ "What's the best way to handle database connection errors in our Python API?"
```

#### 3. Multi-Concept Queries

Combine multiple concepts:

```
"How to implement caching with Redis for our authentication system?"
"What are the security considerations for file uploads in our web application?"
"How to monitor performance of our microservices deployment?"
```

### Search Quality Optimization

#### Result Limit Guidelines

```yaml
# Quick answers
limit: 3-5           # Fast, focused results

# Comprehensive search
limit: 10-15         # Good coverage (recommended)

# Exhaustive search
limit: 20-50         # Maximum coverage
```

#### Source Type Filtering

```yaml
# Search specific sources
source_types: ["git"]           # Only Git repositories
source_types: ["confluence"]    # Only Confluence pages
source_types: ["jira"]          # Only JIRA issues
source_types: ["localfile"]     # Only local files
source_types: ["documentation"] # Only documentation

# Search multiple sources
source_types: ["git", "confluence"]  # Git and Confluence
source_types: ["jira", "confluence"] # JIRA and Confluence
```

#### Project Filtering

```yaml
# Search specific projects
project_ids: ["api-docs"]           # Only API documentation project
project_ids: ["team-knowledge"]     # Only team knowledge project

# Search multiple projects
project_ids: ["api-docs", "user-guides"]  # Multiple projects
```

## 🏗️ Hierarchy Search Tool

### Purpose

The hierarchy search tool understands document structure and relationships, making it ideal for navigating organized documentation like Confluence spaces or structured wikis.

### How It Works

```
Query: "API documentation structure"
    ↓
Semantic Search + Hierarchy Analysis
    ↓
Results with Parent-Child Relationships:
- API Documentation (root)
  ├── Authentication (child)
  ├── Endpoints (child)
  │   ├── User Management (grandchild)
  │   └── Data Operations (grandchild)
  └── Examples (child)
```

### Parameters

```json
{
  "name": "hierarchy_search",
  "parameters": {
    "query": "string",              // Required: Search query
    "limit": 10,                    // Optional: Number of results (default: 10)
    "organize_by_hierarchy": false, // Optional: Group results by structure (default: false)
    "hierarchy_filter": {           // Optional: Hierarchy-specific filters
      "depth": 3,                   // Filter by specific hierarchy depth
      "has_children": true,         // Filter by whether pages have children
      "parent_title": "API Documentation", // Filter by parent page title
      "root_only": false            // Show only root pages (no parent)
    }
  }
}
```

### Example Queries

#### Basic Hierarchy Search

```
Query: "API documentation"

Results:
1. API Documentation (Root)
   └── Children: Authentication, Endpoints, Examples

2. Authentication (Child of API Documentation)
   └── Children: JWT Guide, OAuth Setup

3. Endpoints (Child of API Documentation)
   └── Children: User Management, Data Operations
```

#### Filtered Hierarchy Search

```
Query: "deployment guides"
Filters: hierarchy_filter={"has_children": true, "depth": 1}

Results:
1. Deployment (Root - Depth 1)
   └── Children: AWS Deployment, Docker Deployment, CI/CD

2. Infrastructure (Root - Depth 1)
   └── Children: Monitoring, Scaling, Security
```

### Hierarchy Navigation Patterns

#### 1. Finding Document Structure

```
Query: "Show me the structure of our API documentation"
Purpose: Understand how documentation is organized
```

#### 2. Finding Parent-Child Relationships

```
Query: "What are all the deployment guides under Infrastructure?"
Purpose: Find all related documents in a hierarchy
```

#### 3. Finding Root Documents

```
Query: "What are the main sections of our knowledge base?"
Filters: hierarchy_filter={"root_only": true}
Purpose: Get top-level organization
```

## 📎 Attachment Search Tool

### Purpose

The attachment search tool specializes in finding file attachments and their parent documents, perfect for locating specific files, diagrams, or documents attached to pages.

### How It Works

```
Query: "architecture diagrams"
    ↓
Search Attachments + Parent Context
    ↓
Results:
- system-architecture.pdf (attached to Architecture Overview)
- api-flow-diagram.png (attached to API Documentation)
- deployment-diagram.svg (attached to Deployment Guide)
```

### Parameters

```json
{
  "name": "attachment_search",
  "parameters": {
    "query": "string",              // Required: Search query
    "limit": 10,                    // Optional: Number of results (default: 10)
    "include_parent_context": true, // Optional: Include parent document info (default: true)
    "attachment_filter": {          // Optional: Attachment-specific filters
      "file_type": "pdf",           // Filter by file type
      "file_size_min": 1024,        // Minimum file size in bytes
      "file_size_max": 10485760,    // Maximum file size in bytes
      "attachments_only": true,     // Show only attachments, not parent docs
      "author": "john.doe",         // Filter by attachment author
      "parent_document_title": "API Documentation" // Filter by parent document
    }
  }
}
```

### Example Queries

#### Basic Attachment Search

```
Query: "API documentation PDF"

Results:
1. api-reference-v2.pdf
   - Parent: API Documentation
   - Size: 2.3 MB
   - Type: PDF

2. api-examples.pdf
   - Parent: API Examples
   - Size: 1.1 MB
   - Type: PDF
```

#### Filtered Attachment Search

```
Query: "architecture diagrams"
Filters: attachment_filter={"file_type": "png", "file_size_min": 100000}

Results:
1. system-architecture.png
   - Parent: System Architecture
   - Size: 450 KB
   - Type: PNG

2. database-schema.png
   - Parent: Database Design
   - Size: 320 KB
   - Type: PNG
```

### Attachment Types and Use Cases

#### 1. Documentation Files

```
Query: "user manual PDF"
File Types: PDF, DOC, DOCX
Use Case: Finding comprehensive documentation
```

#### 2. Diagrams and Images

```
Query: "system architecture diagram"
File Types: PNG, JPG, SVG, PDF
Use Case: Finding visual documentation
```

#### 3. Data Files

```
Query: "configuration templates"
File Types: YAML, JSON, XML, CSV
Use Case: Finding configuration examples
```

#### 4. Presentations

```
Query: "project roadmap presentation"
File Types: PPT, PPTX, PDF
Use Case: Finding presentation materials
```

## 🎯 Search Strategy Best Practices

### 1. Choose the Right Tool

#### Use Semantic Search When

- Looking for general information across all documents
- Asking conceptual questions
- Need broad coverage of results
- Working with unstructured content

#### Use Hierarchy Search When

- Navigating structured documentation
- Understanding document organization
- Finding related documents in a hierarchy
- Working with Confluence or wiki-style content

#### Use Attachment Search When

- Looking for specific files or documents
- Need diagrams, presentations, or data files
- Want to find files by type or size
- Need parent document context for attachments

### 2. Optimize Your Queries

#### Be Specific and Contextual

```
❌ "error"
✅ "database connection timeout error in production"

❌ "config"
✅ "Redis configuration for caching in our Node.js application"
```

#### Use Natural Language

```
❌ "auth JWT token"
✅ "How do I implement JWT token authentication?"

❌ "deploy docker k8s"
✅ "What's the process for deploying Docker containers to Kubernetes?"
```

#### Combine Multiple Concepts

```
"How to monitor performance of our microservices in production?"
"What are the security best practices for file uploads in our web app?"
"How to implement rate limiting for our REST API endpoints?"
```

### 3. Use Filters Effectively

#### Source Type Filtering

```yaml
# For code-related questions
source_types: ["git"]

# For process documentation
source_types: ["confluence"]

# For issue tracking
source_types: ["jira"]

# For comprehensive search
source_types: ["git", "confluence", "jira"]
```

#### Project Filtering

```yaml
# For specific project context
project_ids: ["api-project"]

# For multiple related projects
project_ids: ["api-project", "frontend-project"]
```

#### Hierarchy Filtering

```yaml
# For top-level organization
hierarchy_filter: {"root_only": true}

# For specific depth
hierarchy_filter: {"depth": 2}

# For documents with children
hierarchy_filter: {"has_children": true}
```

#### Attachment Filtering

```yaml
# For specific file types
attachment_filter: {"file_type": "pdf"}

# For size constraints
attachment_filter: {"file_size_max": 5242880}  # 5MB

# For specific authors
attachment_filter: {"author": "tech.writer"}
```

## 🔧 Troubleshooting Search Issues

### Common Problems and Solutions

#### 1. No Results Found

**Problem**: Search returns empty results

**Solutions**:

- Verify documents are ingested: `qdrant-loader --workspace . project status`
- Try broader search terms
- Remove filters to expand search scope
- Check if the collection exists in QDrant

#### 2. Irrelevant Results

**Problem**: Search results don't match the query

**Solutions**:

- Use more specific search terms
- Add context to your query
- Use appropriate search tool for your use case
- Apply source type or project filters

#### 3. Missing Expected Documents

**Problem**: Known documents don't appear in results

**Solutions**:

- Check if documents are properly ingested
- Verify document content is searchable
- Try different search terms or synonyms
- Check if documents are in filtered sources/projects

#### 4. Slow Search Performance

**Problem**: Searches take too long

**Solutions**:

- Reduce the limit parameter
- Use more specific filters
- Check QDrant server performance
- Verify network connectivity

### Debug Search Queries

```bash
# Check QDrant collection status
curl http://localhost:6333/collections/documents

# Verify document count
curl http://localhost:6333/collections/documents/points/count

# Test direct QDrant search
curl -X POST http://localhost:6333/collections/documents/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.2, 0.3], "limit": 5}'
```

## 📊 Search Performance Optimization

### Best Practices for Performance

#### 1. Use Appropriate Limits

```yaml
# For quick answers
limit: 3-5

# For comprehensive results
limit: 10-15

# Avoid very large limits
limit: 50+  # Can be slow
```

#### 2. Apply Filters Early

```yaml
# Filter by source type
source_types: ["confluence"]

# Filter by project
project_ids: ["current-project"]

# Use hierarchy filters
hierarchy_filter: {"depth": 2}
```

#### 3. Optimize Query Specificity

```yaml
# Too broad (slow)
query: "documentation"

# Better (faster)
query: "API authentication documentation"

# Best (fastest)
query: "JWT authentication implementation guide"
```

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Setup and Integration](./setup-and-integration.md)** - Setting up the MCP server
- **[Cursor Integration](./cursor-integration.md)** - Cursor-specific setup
- **[Hierarchy Search](./hierarchy-search.md)** - Detailed hierarchy search guide
- **[Attachment Search](./attachment-search.md)** - Detailed attachment search guide

## 📋 Search Capabilities Checklist

### Understanding Search Tools

- [ ] **Semantic search** - Understand when to use for general queries
- [ ] **Hierarchy search** - Know when to use for structured content
- [ ] **Attachment search** - Recognize when to search for files

### Query Optimization

- [ ] **Natural language** - Use conversational queries
- [ ] **Specific context** - Provide relevant context in queries
- [ ] **Appropriate filters** - Apply source, project, and type filters

### Performance Optimization

- [ ] **Reasonable limits** - Use appropriate result limits
- [ ] **Effective filters** - Apply filters to narrow search scope
- [ ] **Query specificity** - Make queries specific and targeted

### Troubleshooting

- [ ] **Verify ingestion** - Ensure documents are properly ingested
- [ ] **Test connectivity** - Check QDrant server connectivity
- [ ] **Debug queries** - Use debug tools when needed

---

**Master the search capabilities to unlock the full power of your knowledge base!** 🔍

With these three search tools and optimization techniques, you can efficiently find any information in your knowledge base, whether it's code documentation, process guides, or specific files and attachments.
