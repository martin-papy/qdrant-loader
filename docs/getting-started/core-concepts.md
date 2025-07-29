# Core Concepts

Understanding these core concepts will help you make the most of QDrant Loader and troubleshoot issues effectively.

## 🎯 Overview

QDrant Loader transforms your documents into searchable, AI-accessible knowledge. This guide explains the key concepts behind how it works.

## 🧠 Vector Databases and Embeddings

### What are Vector Databases?

A **vector database** stores information as high-dimensional numerical vectors that represent the semantic meaning of text, images, or other data.

```
Traditional Database:
"QDrant Loader is powerful" → Stored as text

Vector Database:
"QDrant Loader is powerful" → [0.1, -0.3, 0.8, 0.2, ...] (1536 dimensions)
```

### Why Vector Databases?

| Traditional Search | Vector Search |
|-------------------|---------------|
| Exact keyword matching | Semantic meaning matching |
| "QDrant Loader" finds only exact matches | "document ingestion tool" finds QDrant Loader |
| Limited context understanding | Understands relationships and context |
| Boolean results (match/no match) | Similarity scores (0.0 to 1.0) |

### What are Embeddings?

**Embeddings** are numerical representations of text that capture semantic meaning. Similar concepts have similar embeddings.

```python
# Example embeddings (simplified to 3 dimensions)
"dog" → [0.8, 0.2, 0.1]
"puppy" → [0.7, 0.3, 0.1]  # Similar to "dog"
"car" → [0.1, 0.1, 0.9]    # Different from "dog"
```

### How QDrant Loader Uses Embeddings

1. **Text Chunking**: Documents are split into manageable chunks
2. **Embedding Generation**: Each chunk is converted to a vector using OpenAI's models
3. **Storage**: Vectors are stored in QDrant with metadata
4. **Search**: Query text is converted to a vector and matched against stored vectors

## 📄 Document Processing Pipeline

### Step 1: Data Source Connection

QDrant Loader connects to various data sources:

```
Data Sources → QDrant Loader → QDrant Database
     ↓
┌─────────────┐
│ Git Repos   │ ──┐
│ Confluence  │   │
│ JIRA        │   ├─→ QDrant Loader ──→ Vector Database
│ Local Files │   │
│ Public Docs │ ──┘
└─────────────┘
```

### Step 2: File Conversion

Documents are converted to plain text:

```
Input Formats → Conversion → Plain Text
     ↓
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ PDF         │    │              │    │             │
│ DOCX        │ ──→│ MarkItDown   │──→ │ Plain Text  │
│ PPTX        │    │ Conversion   │    │ Content     │
│ Images      │    │              │    │             │
└─────────────┘    └──────────────┘    └─────────────┘
```

### Step 3: Text Chunking

Large documents are split into smaller, manageable chunks:

```
Large Document → Intelligent Chunking → Smaller Chunks
     ↓
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ 50,000 words    │    │ Respect      │    │ Chunk 1     │
│ Technical Doc   │ ──→│ Boundaries   │──→ │ Chunk 2     │
│                 │    │ Preserve     │    │ Chunk 3     │
│                 │    │ Context      │    │ ...         │
└─────────────────┘    └──────────────┘    └─────────────┘
```

**Chunking Strategy**:

- **Respect boundaries**: Don't split sentences or code blocks
- **Maintain context**: Include overlapping content between chunks
- **Optimal size**: Balance between context and processing efficiency
- **Preserve structure**: Keep headings and formatting context

### Step 4: Embedding Generation

Each chunk is converted to a vector embedding:

```
Text Chunk → OpenAI API → Vector Embedding
     ↓
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ "QDrant Loader  │    │ OpenAI       │    │ [0.1, -0.3, │
│ is a powerful   │ ──→│ text-embed-  │──→ │  0.8, 0.2,  │
│ tool for..."    │    │ ding-3-small │    │  ...]       │
└─────────────────┘    └──────────────┘    └─────────────┘
```

### Step 5: Storage in QDrant

Vectors and metadata are stored in QDrant:

```
Vector + Metadata → QDrant Collection
     ↓
┌─────────────────┐    ┌──────────────────────────────┐
│ Vector:         │    │ QDrant Collection            │
│ [0.1, -0.3,...] │    │ ┌─────────┬─────────────────┐│
│                 │ ──→│ │ Vector  │ Metadata        ││
│ Metadata:       │    │ ├─────────┼─────────────────┤│
│ - Source file   │    │ │ [0.1..] │ file: doc.md    ││
│ - Chunk index   │    │ │ [0.3..] │ chunk: 1        ││
│ - Content       │    │ │ [0.8..] │ source: git     ││
└─────────────────┘    └─┴─────────┴─────────────────┘┘
```

## 🔍 Search and Retrieval

### How Search Works

1. **Query Processing**: Your search query is converted to a vector
2. **Similarity Search**: QDrant finds vectors most similar to your query
3. **Ranking**: Results are ranked by similarity score
4. **Metadata Filtering**: Results can be filtered by source, date, etc.

```
Search Query → Vector → QDrant Search → Ranked Results
     ↓
"API documentation" → [0.2, 0.7, ...] → QDrant → [
  {score: 0.95, content: "API endpoints...", source: "api.md"},
  {score: 0.87, content: "REST API guide...", source: "guide.md"},
  {score: 0.82, content: "Authentication...", source: "auth.md"}
]
```

### Search Types

#### 1. Semantic Search (via MCP Server)

Finds content based on meaning, not just keywords. Search is performed through the MCP server tools:

```bash
# Search is performed via MCP server tools in AI applications
# Basic semantic search
{
  "name": "search",
  "arguments": {
    "query": "authentication methods",
    "limit": 10
  }
}
```

#### 2. Hierarchy Search (via MCP Server)

Combines semantic search with document structure awareness:

```bash
# Hierarchy-aware search via MCP server
{
  "name": "hierarchy_search", 
  "arguments": {
    "query": "API authentication",
    "organize_by_hierarchy": true
  }
}
```

#### 3. Attachment Search (via MCP Server)

Search within file attachments and their parent documents:

```bash
# Attachment search via MCP server
{
  "name": "attachment_search",
  "arguments": {
    "query": "deployment scripts",
    "attachment_filter": {
      "file_type": "sh"
    }
  }
}
```

## 🤖 MCP Server and AI Integration

### What is MCP?

**Model Context Protocol (MCP)** is a standard for connecting AI tools to external data sources.

```
AI Tool (Cursor) ←→ MCP Server ←→ QDrant Database
     ↓
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ User asks:  │    │ MCP Server   │    │ QDrant      │
│ "How do I   │ ──→│ - Receives   │──→ │ - Searches  │
│ configure   │    │   query      │    │   vectors   │
│ QDrant?"    │    │ - Calls      │    │ - Returns   │
│             │ ←──│   search     │←── │   results   │
│ Gets answer │    │ - Formats    │    │             │
│ with context│    │   response   │    │             │
└─────────────┘    └──────────────┘    └─────────────┘
```

### MCP Tools Available

QDrant Loader provides several MCP tools:

#### 1. Search Tool

Basic semantic search across all documents:

```json
{
  "name": "search",
  "description": "Search across all ingested documents",
  "parameters": {
    "query": "search terms",
    "limit": 10,
    "source_types": ["git", "confluence"]
  }
}
```

#### 2. Hierarchy Search Tool

Search with document structure awareness:

```json
{
  "name": "hierarchy_search", 
  "description": "Search with document hierarchy context",
  "parameters": {
    "query": "search terms",
    "organize_by_hierarchy": true,
    "hierarchy_filter": {
      "depth": 3,
      "has_children": true
    }
  }
}
```

#### 3. Attachment Search Tool

Search file attachments and their parent documents:

```json
{
  "name": "attachment_search",
  "description": "Search file attachments",
  "parameters": {
    "query": "search terms",
    "attachment_filter": {
      "file_type": "pdf",
      "include_parent_context": true
    }
  }
}
```

## 📊 Data Sources and Connectors

### Supported Data Sources

| Source | Description | Use Cases |
|--------|-------------|-----------|
| **Git Repositories** | Clone and index Git repos | Code documentation, README files |
| **Confluence** | Connect to Confluence spaces | Team wikis, knowledge bases |
| **JIRA** | Index JIRA issues and comments | Project documentation, requirements |
| **Local Files** | Process local directories | Personal documents, project files |
| **Public Documentation** | Scrape public websites | External API docs, tutorials |

### How Connectors Work

Each data source has a specialized connector:

```python
# Simplified connector interface
class DataSourceConnector:
    def connect(self, config):
        """Establish connection to data source"""
        
    def discover(self):
        """Find all available documents"""
        
    def fetch(self, document_id):
        """Retrieve document content"""
        
    def get_metadata(self, document_id):
        """Extract document metadata"""
```

### Incremental Updates

QDrant Loader tracks changes and only processes new or modified content:

```
Initial Sync: All documents processed
     ↓
┌─────────────────┐    ┌──────────────┐
│ Document A      │ ──→│ Processed    │
│ Document B      │ ──→│ Processed    │
│ Document C      │ ──→│ Processed    │
└─────────────────┘    └──────────────┘

Incremental Sync: Only changes processed
     ↓
┌─────────────────┐    ┌──────────────┐
│ Document A      │ ──→│ Skipped      │ (unchanged)
│ Document B      │ ──→│ Updated      │ (modified)
│ Document D      │ ──→│ Added        │ (new)
└─────────────────┘    └──────────────┘
```

## ⚙️ Configuration and Customization

### Configuration Hierarchy

QDrant Loader uses a layered configuration system:

```
Environment Variables (highest priority)
     ↓
Configuration File (~/.qdrant-loader/config.yaml)
     ↓
Command Line Arguments
     ↓
Default Values (lowest priority)
```

### Project-Based Configuration

QDrant Loader uses a project-based configuration structure:

```yaml
# Multi-project configuration
projects:
  # Development project
  dev-project:
    project_id: "dev-project"
    display_name: "Development Documentation"
    description: "Development team documentation and code"
    
    sources:
      git:
        backend-repo:
          base_url: "https://github.com/company/backend"
          include_paths: ["docs/**", "README.md"]
          
      confluence:
        dev-space:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "DEV"
          token: "${CONFLUENCE_TOKEN}"
          
  # Production project  
  prod-project:
    project_id: "prod-project"
    display_name: "Production Documentation"
    description: "Production systems and operations"
    
    sources:
      confluence:
        ops-space:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "OPS"
          token: "${CONFLUENCE_TOKEN}"
```

### Key Configuration Areas

#### 1. Vector Database Settings

```yaml
qdrant:
  url: "http://localhost:6333"
  collection_name: "documents"
  vector_size: 1536
  distance_metric: "cosine"
```

#### 2. Embedding Configuration

```yaml
embedding:
  model: "text-embedding-3-small"
  api_key: "${OPENAI_API_KEY}"
  batch_size: 100
  endpoint: "https://api.openai.com/v1"
  vector_size: 1536
```

#### 3. Processing Settings

```yaml
chunking:
  chunk_size: 1500
  chunk_overlap: 200
  max_file_size: "10MB"
  supported_formats: ["md", "txt", "pdf", "docx"]
```

#### 4. Data Source Configuration

```yaml
sources:
  git:
    my-repo:
      base_url: "https://github.com/company/docs"
      branch: "main"
      include_paths: ["**/*.md", "**/*.rst"]
      exclude_paths: ["node_modules/", ".git/"]
  
  confluence:
    company-wiki:
      base_url: "https://company.atlassian.net/wiki"
      space_key: "DOCS"
      token: "${CONFLUENCE_TOKEN}"
      email: "${CONFLUENCE_EMAIL}"
```

## 🔧 Performance and Optimization

### Understanding Performance Factors

#### 1. Document Size and Chunking

- **Larger chunks**: Better context, slower processing
- **Smaller chunks**: Faster processing, less context
- **Optimal size**: 500-1500 tokens per chunk

#### 2. Embedding Model Choice

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| text-embedding-3-small | Fast | Good | Low |
| text-embedding-3-large | Slower | Better | Higher |
| text-embedding-ada-002 | Medium | Good | Medium |

#### 3. QDrant Configuration

```yaml
# Performance optimization
qdrant:
  # Use memory-mapped storage for large datasets
  storage_type: "mmap"
  
  # Optimize for search speed
  hnsw_config:
    m: 16
    ef_construct: 200
    
  # Batch operations
  batch_size: 100
```

### Monitoring Performance

```bash
# Check ingestion status
qdrant-loader project --workspace . status

# Monitor QDrant performance (direct API call)
curl http://localhost:6333/metrics

# Check collection statistics
qdrant-loader project --workspace . status --detailed
```

## 🔗 Integration Patterns

### Common Integration Scenarios

#### 1. Development Workflow

```
Code Changes → Git Push → Webhook → QDrant Loader → Updated Index
     ↓
Developer asks AI about code → MCP Server → Search → Contextual answers
```

#### 2. Documentation Workflow

```
Wiki Updates → Confluence → Scheduled Sync → QDrant Loader → Updated Index
     ↓
Support team searches → AI Tool → MCP Server → Accurate answers
```

#### 3. Knowledge Management

```
Multiple Sources → QDrant Loader → Unified Index → AI Tools
     ↓
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Git Repos   │    │              │    │ Cursor IDE  │
│ Confluence  │ ──→│ QDrant Loader│──→ │ Windsurf    │
│ JIRA        │    │              │    │ Claude      │
│ Local Docs  │    │              │    │ Custom Apps │
└─────────────┘    └──────────────┘    └─────────────┘
```

## 🎯 Best Practices

### 1. Data Organization

- **Use consistent naming**: Clear, descriptive file and folder names
- **Maintain structure**: Organize documents logically
- **Regular cleanup**: Remove outdated or duplicate content

### 2. Configuration Management

- **Environment-specific configs**: Different settings for dev/prod
- **Secure credentials**: Use environment variables for API keys
- **Version control**: Track configuration changes

### 3. Performance Optimization

- **Batch processing**: Process multiple documents together
- **Incremental updates**: Only sync changed content
- **Monitor resources**: Watch memory and API usage

### 4. Quality Assurance

- **Test search results**: Verify search quality regularly
- **Monitor accuracy**: Check AI responses for correctness
- **Update regularly**: Keep embeddings fresh with new content

## 🔍 Troubleshooting Concepts

### Common Issues and Concepts

#### 1. Poor Search Results

**Cause**: Embedding model mismatch or poor chunking
**Solution**: Adjust chunk size or try different embedding model

#### 2. Slow Performance

**Cause**: Large chunks, inefficient QDrant config, or API rate limits
**Solution**: Optimize chunking, tune QDrant, implement rate limiting

#### 3. Memory Issues

**Cause**: Processing too many large documents simultaneously
**Solution**: Reduce batch size, process in smaller chunks

#### 4. Inconsistent Results

**Cause**: Outdated embeddings or mixed content types
**Solution**: Re-index content, separate different content types

## 📚 Next Steps

Now that you understand the core concepts:

1. **[Basic Configuration](./basic-configuration.md)** - Set up your specific use case
2. **[User Guides](../users/)** - Explore detailed features
3. **[Data Source Guides](../users/detailed-guides/data-sources/)** - Configure specific connectors
4. **[MCP Server Guide](../users/detailed-guides/mcp-server/)** - Advanced AI integration

---

**Understanding these concepts will help you:**

- Configure QDrant Loader effectively for your use case
- Troubleshoot issues when they arise
- Optimize performance for your specific needs
- Make the most of AI tool integration
