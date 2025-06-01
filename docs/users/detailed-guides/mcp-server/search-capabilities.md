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
    "limit": 10,                    // Optional: Number of results (default: 10)
    "threshold": 0.7,               // Optional: Similarity threshold (0.0-1.0)
    "source_filter": "string",      // Optional: Filter by data source
    "project_filter": "string",     // Optional: Filter by project
    "date_filter": {                // Optional: Date range filter
      "start": "2024-01-01",
      "end": "2024-12-31"
    },
    "content_type": "string",       // Optional: Filter by content type
    "include_metadata": true,       // Optional: Include document metadata
    "include_content": true,        // Optional: Include document content
    "max_content_length": 500       // Optional: Limit content length
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
   - Similarity: 0.89

2. [security/oauth.md] OAuth 2.0 Integration
   - OAuth flow and configuration
   - Similarity: 0.85

3. [api/auth-endpoints.md] Authentication API Endpoints
   - Login, logout, and token refresh endpoints
   - Similarity: 0.82
```

#### Filtered Search

```
Query: "deployment strategies"
Filters: source_filter="confluence", date_filter={"start": "2024-01-01"}

Results:
1. [Confluence: DevOps/Deployment] Blue-Green Deployment Strategy
   - Updated: 2024-03-15
   - Comprehensive guide to blue-green deployments
   - Similarity: 0.91

2. [Confluence: Architecture/Scaling] Canary Deployment Process
   - Updated: 2024-02-20
   - Step-by-step canary deployment guide
   - Similarity: 0.87
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

#### Similarity Threshold Guidelines

```yaml
# High precision, fewer results
threshold: 0.8-1.0    # Very relevant results only

# Balanced precision and recall
threshold: 0.7-0.8    # Good balance (recommended)

# High recall, more results
threshold: 0.5-0.7    # Include potentially relevant results

# Exploratory search
threshold: 0.3-0.5    # Cast a wide net
```

#### Result Limit Guidelines

```yaml
# Quick answers
limit: 3-5           # Fast, focused results

# Comprehensive search
limit: 10-15         # Good coverage (recommended)

# Exhaustive search
limit: 20-50         # Maximum coverage
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
    "include_hierarchy": true,      // Optional: Include hierarchy info
    "depth": 3,                     // Optional: Maximum hierarchy depth
    "organize_by_hierarchy": false, // Optional: Group results by structure
    "parent_filter": "string",      // Optional: Filter by parent document
    "hierarchy_filter": {           // Optional: Hierarchy-specific filters
      "root_only": false,
      "has_children": true,
      "depth": 2
    }
  }
}
```

### Example Queries

#### Structure Navigation

```
Query: "Show me the structure of our deployment documentation"

Results (organized by hierarchy):
📁 Deployment Documentation
├── 📄 Overview (deployment/README.md)
├── 📁 Environments
│   ├── 📄 Development Setup (deployment/dev.md)
│   ├── 📄 Staging Environment (deployment/staging.md)
│   └── 📄 Production Deployment (deployment/prod.md)
├── 📁 Platforms
│   ├── 📄 AWS Deployment (deployment/aws.md)
│   ├── 📄 Docker Containers (deployment/docker.md)
│   └── 📄 Kubernetes Setup (deployment/k8s.md)
└── 📁 Troubleshooting
    ├── 📄 Common Issues (deployment/troubleshooting.md)
    └── 📄 Performance Problems (deployment/performance.md)
```

#### Parent-Child Relationships

```
Query: "Find all child pages under the API documentation"

Results:
Parent: API Documentation (api/README.md)
├── Authentication (api/auth.md)
├── User Endpoints (api/users.md)
├── Data Endpoints (api/data.md)
├── Error Handling (api/errors.md)
└── Rate Limiting (api/rate-limits.md)

Each child contains:
- Detailed implementation guides
- Code examples
- Best practices
```

### Hierarchy-Specific Use Cases

#### 1. Documentation Navigation

```
"What are all the sections in our onboarding documentation?"
"Show me the complete structure of the troubleshooting guides"
"Find all child pages under the security documentation"
```

#### 2. Content Organization

```
"Where should I add documentation about new API endpoints?"
"What's the hierarchy of our architecture documentation?"
"Show me all root-level documentation pages"
```

#### 3. Completeness Checking

```
"Are there any missing sections in our deployment documentation?"
"What topics are covered under the development guidelines?"
"Show me all leaf pages (pages with no children) in the API docs"
```

## 📎 Attachment Search Tool

### Purpose

The attachment search tool specializes in finding file attachments (PDFs, documents, spreadsheets, images) and their parent documents, with content extraction and metadata analysis.

### How It Works

```
Query: "architecture diagrams"
    ↓
Search Attachments + Parent Context
    ↓
Results:
1. system-architecture.pdf (attached to Architecture Overview)
2. database-schema.png (attached to Database Design)
3. api-flow-diagram.svg (attached to API Documentation)
```

### Parameters

```json
{
  "name": "attachment_search",
  "parameters": {
    "query": "string",              // Required: Search query
    "file_types": ["pdf", "docx"],  // Optional: Filter by file type
    "include_parent_context": true, // Optional: Include parent document
    "attachment_filter": {          // Optional: Attachment-specific filters
      "file_size_min": 1024,
      "file_size_max": 10485760,
      "author": "string",
      "created_after": "2024-01-01"
    }
  }
}
```

### Supported File Types

#### Document Files

- **PDF** (.pdf) - Full text extraction
- **Word** (.docx, .doc) - Content and metadata
- **PowerPoint** (.pptx, .ppt) - Slides and notes
- **Excel** (.xlsx, .xls) - Sheet data and formulas

#### Image Files

- **PNG** (.png) - OCR text extraction
- **JPEG** (.jpg, .jpeg) - OCR text extraction
- **SVG** (.svg) - Text and metadata
- **GIF** (.gif) - Basic metadata

#### Other Files

- **Text** (.txt, .md) - Full content
- **CSV** (.csv) - Data structure analysis
- **JSON** (.json) - Structure and content
- **YAML** (.yaml, .yml) - Configuration analysis

### Example Queries

#### Finding Specific File Types

```
Query: "architecture diagrams"
File Types: ["pdf", "png", "svg"]

Results:
1. 📄 system-architecture.pdf (2.3 MB)
   Parent: Architecture Overview
   Content: System components, data flow, security boundaries
   
2. 🖼️ database-schema.png (856 KB)
   Parent: Database Design
   Content: Entity relationships, table structures, indexes
   
3. 🖼️ api-flow-diagram.svg (234 KB)
   Parent: API Documentation
   Content: Request flow, authentication, response handling
```

#### Content-Based Search

```
Query: "performance metrics and benchmarks"
File Types: ["xlsx", "pdf"]

Results:
1. 📊 performance-benchmarks.xlsx (1.2 MB)
   Parent: Performance Testing
   Content: Load test results, response times, throughput data
   Sheets: ["API Benchmarks", "Database Performance", "Memory Usage"]
   
2. 📄 performance-analysis-q4.pdf (3.1 MB)
   Parent: Quarterly Reports
   Content: Performance trends, optimization recommendations
   Pages: 15, Created: 2024-01-15
```

#### Author and Date Filtering

```
Query: "deployment procedures"
Filters: {
  "author": "devops-team",
  "created_after": "2024-01-01",
  "file_types": ["pdf", "docx"]
}

Results:
1. 📄 deployment-runbook-v2.pdf (1.8 MB)
   Author: devops-team
   Created: 2024-02-15
   Parent: Deployment Documentation
   
2. 📄 rollback-procedures.docx (456 KB)
   Author: devops-team
   Created: 2024-01-20
   Parent: Emergency Procedures
```

### Advanced Attachment Features

#### 1. Content Extraction

The tool extracts and indexes content from attachments:

```
PDF Content: "To deploy the application, first ensure all dependencies..."
Excel Data: "Server response times: 95th percentile: 250ms, 99th percentile: 500ms"
Image OCR: "System Architecture Diagram - Web Layer, API Layer, Database Layer"
```

#### 2. Metadata Analysis

Rich metadata is extracted and searchable:

```json
{
  "filename": "api-documentation.pdf",
  "size": 2457600,
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z",
  "author": "technical-writing-team",
  "pages": 42,
  "content_type": "application/pdf",
  "parent_document": "API Reference Guide",
  "tags": ["api", "documentation", "reference"]
}
```

#### 3. Parent Context Integration

Results include context from the parent document:

```
Attachment: database-migration-script.sql
Parent Context: "This migration script updates the user table schema to support new authentication features. Run this script during the maintenance window scheduled for..."
```

## 🔧 Search Optimization Strategies

### 1. Query Optimization

#### Use Specific Terms

```
❌ "docs"
✅ "API documentation for user authentication"

❌ "config"
✅ "database configuration for production environment"
```

#### Include Context

```
❌ "error"
✅ "database connection error in Python application"

❌ "deployment"
✅ "Docker deployment to AWS ECS cluster"
```

### 2. Filter Optimization

#### Source Filtering

```json
{
  "source_filter": "confluence",     // Search only Confluence
  "source_filter": "git",           // Search only Git repositories
  "source_filter": "local"          // Search only local files
}
```

#### Date Filtering

```json
{
  "date_filter": {
    "start": "2024-01-01",          // Recent documents only
    "end": "2024-12-31"
  }
}
```

#### Content Type Filtering

```json
{
  "content_type": "markdown",        // Only Markdown files
  "content_type": "documentation",   // Only documentation
  "content_type": "code"            // Only code files
}
```

### 3. Result Optimization

#### Adjust Similarity Threshold

```json
{
  "threshold": 0.8,                 // High precision
  "threshold": 0.6,                 // Balanced
  "threshold": 0.4                  // High recall
}
```

#### Control Result Size

```json
{
  "limit": 5,                       // Quick answers
  "limit": 15,                      // Comprehensive
  "max_content_length": 300         // Shorter snippets
}
```

## 📊 Search Analytics and Monitoring

### Query Performance

Monitor search performance to optimize your knowledge base:

```bash
# View search performance logs
tail -f ~/.qdrant-loader/logs/mcp-server.log | grep "search_performance"

# Common metrics:
# - Query processing time
# - Number of results found
# - Similarity scores
# - Filter effectiveness
```

### Popular Queries

Track common queries to improve documentation:

```bash
# View most common search terms
grep "search_query" ~/.qdrant-loader/logs/mcp-analytics.log | \
  cut -d'"' -f4 | sort | uniq -c | sort -nr | head -20
```

### Search Quality Metrics

Monitor search quality indicators:

```yaml
# Good search quality indicators:
- High similarity scores (>0.7)
- Consistent result relevance
- Low "no results" rate
- Fast response times (<2s)

# Poor search quality indicators:
- Low similarity scores (<0.5)
- Irrelevant results
- High "no results" rate
- Slow response times (>5s)
```

## 🎯 Best Practices

### 1. Query Design

- **Be specific**: Include relevant context and details
- **Use natural language**: Ask questions as you would to a human
- **Combine concepts**: Include multiple related terms
- **Avoid jargon**: Use clear, descriptive language

### 2. Filter Usage

- **Start broad**: Begin with general queries, then add filters
- **Use source filters**: When you know where information should be
- **Apply date filters**: For recent or historical information
- **Combine filters**: Use multiple filters for precise results

### 3. Result Interpretation

- **Check similarity scores**: Higher scores indicate better matches
- **Review metadata**: Understand document context and freshness
- **Use hierarchy info**: Understand document relationships
- **Consider parent context**: For attachments and child documents

### 4. Iterative Search

- **Refine queries**: Adjust based on initial results
- **Try different tools**: Use hierarchy or attachment search for specific needs
- **Adjust thresholds**: Balance precision and recall
- **Follow up**: Ask clarifying questions based on results

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Hierarchy Search](./hierarchy-search.md)** - Detailed hierarchy search guide
- **[Attachment Search](./attachment-search.md)** - Detailed attachment search guide
- **[Cursor Integration](./cursor-integration.md)** - Using search in Cursor IDE

## 📋 Search Capabilities Checklist

- [ ] **Understand search tools** - Know when to use each tool
- [ ] **Optimize queries** - Use specific, contextual queries
- [ ] **Apply filters** - Use source, date, and content filters effectively
- [ ] **Adjust thresholds** - Balance precision and recall
- [ ] **Monitor performance** - Track search quality and speed
- [ ] **Iterate and refine** - Improve queries based on results

---

**Master your knowledge search capabilities!** 🔍

With these search tools and techniques, you can efficiently find any information in your knowledge base, whether it's buried in documentation, attached files, or complex hierarchical structures. The key is understanding which tool to use for each situation and how to craft effective queries.
