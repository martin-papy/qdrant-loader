# Attachment Search Guide

This guide covers the attachment search capabilities of the QDrant Loader MCP Server, enabling you to find and work with file attachments across your knowledge base with AI assistance.

## 🎯 Overview

The attachment search tool specializes in finding file attachments and their associated documents. **Currently, this feature is specifically designed for Confluence sources** and includes:

- **PDF documents** with extracted text content
- **Office documents** (Word, Excel, PowerPoint)  
- **Images** with text extraction via MarkItDown
- **Code files** and configuration files
- **Data files** (CSV, JSON, YAML)

### Key Benefits

- **Content Extraction**: Searches inside file contents using MarkItDown conversion
- **Parent Context**: Understands the relationship between attachments and their parent Confluence pages
- **File Type Intelligence**: Optimized search for different file formats supported by MarkItDown
- **Metadata Awareness**: Searches file properties, authors, and creation dates from Confluence

### ⚠️ Important Limitations

- **Confluence Only**: Currently limited to Confluence attachments and documents
- **MarkItDown Dependency**: File conversion capabilities depend on MarkItDown library support
- **No OCR**: Text extraction from images relies on MarkItDown, not dedicated OCR processing

## 📎 How Attachment Search Works

### File Processing Pipeline

```text
Confluence Attachment
    ↓
1. File Detection (MIME type and extension analysis)
    ↓
2. MarkItDown Conversion (text extraction from various formats)
    ↓
3. Content Processing (markdown structure analysis)
    ↓
4. Vector Embedding (semantic search via OpenAI)
    ↓
5. Confluence Context Integration (parent page relationship)
    ↓
6. Searchable Attachment Index
```

### Search Process

```text
Query: "architecture diagrams"
    ↓
1. Semantic Search (find relevant Confluence attachments)
    ↓
2. Confluence Filter (only Confluence sources processed)
    ↓
3. File Type Filtering (based on MIME type and filename)
    ↓
4. Content Analysis (MarkItDown extracted text)
    ↓
5. Parent Context (associated Confluence pages)
    ↓
6. Ranked Results (by relevance and attachment metadata)
```

## 🔧 Attachment Search Parameters

### Available Parameters

```json
{
  "name": "attachment_search",
  "description": "Search for file attachments and their parent documents across Confluence sources",
  "parameters": {
    "query": "string",              // Required: Search query in natural language
    "limit": 10,                    // Optional: Number of results (default: 10)
    "include_parent_context": true, // Optional: Include parent document info (default: true)
    "attachment_filter": {          // Optional: Attachment-specific filters
      "attachments_only": true,     // Show only file attachments
      "parent_document_title": "API Documentation", // Filter by parent document title
      "file_type": "pdf",           // Filter by file type (e.g., 'pdf', 'xlsx', 'png')
      "file_size_min": 1024,        // Minimum file size in bytes
      "file_size_max": 10485760,    // Maximum file size in bytes
      "author": "data-team"         // Filter by attachment author
    }
  }
}
```

### Parameter Details

#### Required Parameters

- **`query`** (string): The search query in natural language

#### Optional Parameters

- **`limit`** (integer): Maximum number of results to return (default: 10)
- **`include_parent_context`** (boolean): Include parent document information (default: true)

#### Attachment Filter Options

- **`attachments_only`** (boolean): Show only file attachments
- **`parent_document_title`** (string): Filter by parent document title
- **`file_type`** (string): Filter by file type (e.g., 'pdf', 'xlsx', 'png')
- **`file_size_min`** (integer): Minimum file size in bytes
- **`file_size_max`** (integer): Maximum file size in bytes
- **`author`** (string): Filter by attachment author

## 📁 Supported File Types

The attachment search supports file types that can be processed by MarkItDown for text extraction:

### Document Files

#### PDF Documents (.pdf)
- **Content**: Text extraction via MarkItDown
- **Metadata**: Basic Confluence attachment metadata (author, size, date)
- **Features**: Text content search within PDF documents
- **Use Cases**: Reports, manuals, specifications

#### Microsoft Office Documents
- **Word Documents** (.docx, .doc): Text content extraction
- **Excel Spreadsheets** (.xlsx, .xls): Cell content and sheet data extraction  
- **PowerPoint Presentations** (.pptx, .ppt): Slide text and notes extraction
- **Metadata**: Author, file size, last modified date from Confluence
- **Use Cases**: Documentation, presentations, data analysis

### Image Files

#### Common Image Formats (.png, .jpg, .jpeg, .gif, .bmp, .tiff, .webp)
- **Content**: Text extraction via MarkItDown (limited capability)
- **Metadata**: File size, dimensions (basic), upload date from Confluence
- **Features**: Basic text recognition where supported by MarkItDown
- **Use Cases**: Screenshots, diagrams, charts (text extraction may be limited)

### Data and Text Files

#### CSV Files (.csv)
- **Content**: Column headers and data structure extraction
- **Features**: Data content made searchable
- **Use Cases**: Data exports, configuration data

#### Archive Files (.zip, .epub)
- **Content**: Archive content extraction where supported by MarkItDown
- **Features**: Basic content indexing

#### Plain Text Files (.txt)
- **Content**: Full text extraction
- **Features**: Complete content searchability

### Audio Files (Limited Support)
#### Audio Formats (.mp3, .wav)
- **Content**: Limited to metadata extraction only
- **Note**: Audio transcription is not supported

### Important Notes

- **Conversion Dependency**: All file processing depends on MarkItDown library capabilities
- **Text-Based Search**: Search operates on text content extracted by MarkItDown
- **Confluence Metadata**: File metadata comes from Confluence attachment properties
- **No Custom OCR**: No dedicated OCR processing beyond MarkItDown's built-in capabilities

## 🔍 Search Examples and Use Cases

### 1. Finding Specific File Types in Confluence

#### Architecture Diagrams

```text
Query: "system architecture diagrams"
Parameters: {
  "attachment_filter": {
    "file_type": "pdf"
  }
}

Results:
1. 📄 system-architecture-v2.pdf (2.3 MB)
   Parent: Architecture Documentation (Confluence)
   Content: "Microservices architecture with API gateway..."
   Author: architecture-team
   
2. 📄 database-schema.pdf (1.1 MB)
   Parent: Database Design (Confluence)
   Content: "User Table, Product Table, Order Table..."
   Author: database-team
```

#### Performance Reports

```text
Query: "performance benchmarks and metrics"
Parameters: {
  "attachment_filter": {
    "file_type": "xlsx"
  }
}

Results:
1. 📊 q4-performance-report.xlsx (1.2 MB)
   Parent: Quarterly Reports (Confluence)
   Content: Extracted spreadsheet data and metrics
   Author: performance-team
   
2. 📊 daily-metrics.xlsx (456 KB)
   Parent: Monitoring Dashboard (Confluence)
   Content: Response times, throughput, error rates data
   Author: devops-team
```

### 2. Content-Based Search in Confluence Attachments

#### Finding Specific Information

```text
Query: "API rate limits and throttling policies"
Parameters: {
  "limit": 10
}

Results:
1. 📄 api-rate-limiting-policy.pdf (1.8 MB)
   Parent: API Documentation (Confluence)
   Content: "Rate limiting implementation using token bucket..."
   
2. 📄 throttling-implementation.docx (890 KB)
   Parent: Development Guidelines (Confluence)
   Content: "Implementation guide for rate limiting middleware..."
```

### 3. Author and Date Filtering

#### Recent Updates by Team

```text
Query: "deployment procedures"
Parameters: {
  "attachment_filter": {
    "author": "devops-team"
  }
}

Results:
1. 📄 deployment-runbook-v3.pdf (2.1 MB)
   Author: devops-team
   Parent: Operations Documentation (Confluence)
   Content: "Updated deployment procedures for Kubernetes..."
   
2. 📄 rollback-procedures.docx (678 KB)
   Author: devops-team
   Parent: Emergency Procedures (Confluence)
   Content: "Step-by-step rollback process for production..."
```

#### Large Documents

```text
Query: "comprehensive documentation"
Parameters: {
  "attachment_filter": {
    "file_size_min": 1048576  // Files larger than 1MB
  }
}

Results:
1. 📄 complete-api-specification.pdf (5.2 MB)
   Parent: API Documentation (Confluence)
   Content: "Complete REST API specification with examples..."
   
2. 📄 system-architecture-guide.pdf (3.8 MB)
   Parent: Architecture Documentation (Confluence)
   Content: "Comprehensive system architecture documentation..."
```

## 🔧 Advanced Attachment Features

### 1. MarkItDown-Based Content Extraction

The attachment search uses MarkItDown for converting file content to searchable text:

```text
PDF Content Extraction:
"System Architecture Overview
This document describes our microservices architecture..."

Excel Data Extraction:
"Performance Metrics
Response Time: 250ms
Database Queries: 45ms average"

PowerPoint Content:
"Deployment Strategy
Slide 1: Overview
Slide 2: Implementation Steps..."

Word Document:
"API Documentation
Authentication endpoints require JWT tokens..."
```

### 2. Confluence Integration

Results include context from the parent Confluence page:

```text
Attachment: database-migration-script.sql
Parent Page: "Database Schema Updates v2.1"
Confluence Space: Development Documentation
Author: database-team
Upload Date: 2024-01-15

Parent Context: 
This migration script updates the user table schema to support 
new authentication features. Please run during maintenance window.

Related Attachments on Same Page:
- rollback-script.sql
- migration-test-results.md
```

### 3. Basic File Metadata

The search indexes available file metadata from Confluence:

```json
{
  "filename": "api-performance-analysis.xlsx",
  "file_type": "xlsx",
  "size": 2457600,
  "author": "performance-team",
  "parent_document": "Performance Testing Results",
  "confluence_space": "Engineering Docs",
  "upload_date": "2024-01-15T10:30:00Z"
}
```

### 4. Search Integration

Attachment search integrates with the broader search system:

- **Semantic Search**: Uses the same vector embeddings as regular document search
- **Relevance Scoring**: Combines content similarity with file metadata relevance
- **Parent Context**: Considers both attachment content and parent page context
- **Filter Support**: Allows filtering by file type, size, author, and parent page

## 🎯 Optimization Strategies

### 1. Query Optimization

#### File-Type Specific Queries

```text
✅ "Find Excel files with performance metrics"
✅ "Show me PDF documents about deployment"
✅ "Search for architecture diagrams in PNG format"

❌ "performance"
❌ "deployment"
❌ "architecture"
```

#### Content-Specific Queries

```text
✅ "Find documents containing database schema definitions"
✅ "Show me files with API endpoint documentation"
✅ "Search for configuration files with rate limiting settings"
```

### 2. Filter Optimization

#### File Size Filtering

```json
{
  "attachment_filter": {
    "file_size_min": 1024,        // Exclude tiny files
    "file_size_max": 52428800     // Exclude files larger than 50MB
  }
}
```

#### Author Filtering

```json
{
  "attachment_filter": {
    "author": "architecture-team"   // Specific team
  }
}
```

### 3. Performance Optimization

#### Limit File Types

```json
{
  "attachment_filter": {
    "file_type": "pdf",           // Only search specific types
    "attachments_only": true      // Skip parent document content
  }
}
```

#### Control Result Size

```json
{
  "limit": 5                      // Fewer results for faster response
}
```

## 🎨 Result Interpretation

### Understanding Attachment Results

#### File Information

```text
📄 api-documentation.pdf (2.3 MB)
├── 📊 Metadata
│   ├── Author: technical-writing-team
│   ├── File Type: application/pdf
│   └── Size: 2.3 MB
├── 🔍 Content Preview
│   └── "This document provides comprehensive API documentation..."
├── 📁 Parent Context
│   ├── Document: API Reference Guide
│   └── Section: Complete API Documentation
└── 🔗 Related Files
    ├── api-examples.json
    ├── postman-collection.json
    └── api-changelog.md
```

#### Similarity Scoring

Attachment search uses specialized similarity scoring:

```text
Content Similarity: 0.89    (text content match)
Metadata Similarity: 0.76   (file properties match)
Context Similarity: 0.82    (parent document relevance)
Overall Score: 0.85         (weighted combination)
```

### Quality Indicators

#### High-Quality Results

- **High content similarity** (>0.8)
- **Rich metadata** (author, creation date, etc.)
- **Clear parent context** (well-documented source)
- **Appropriate file size** (not too small or large)

#### Lower-Quality Results

- **Low content similarity** (<0.6)
- **Missing metadata** (unknown author, no dates)
- **Orphaned files** (no clear parent context)
- **Unusual file sizes** (very small or very large)

## 🔗 Integration with Other Search Tools

### Combining Search Strategies for Confluence

#### 1. Start with Semantic Search

```text
Query: "deployment procedures"
→ Find general documentation about deployment in all sources
```

#### 2. Use Attachment Search for Confluence Files

```text
Query: "deployment scripts and configurations"
Parameters: {
  "attachment_filter": {
    "file_type": "yml"
  }
}
→ Find specific implementation files in Confluence attachments
```

#### 3. Use Hierarchy Search for Confluence Structure

```text
Query: "deployment documentation structure"
→ Understand how deployment docs are organized in Confluence
```

### Multi-Tool Workflow Example

```text
1. Semantic Search: "API authentication methods"
   → Understand authentication concepts across all sources

2. Attachment Search: "authentication configuration files"
   → Find Confluence attachments with implementation details

3. Hierarchy Search: "authentication documentation structure"
   → See how auth docs are organized in Confluence

4. Attachment Search: "authentication examples and certificates"
   → Find practical examples and certificates in Confluence attachments
```

### When to Use Attachment Search

**✅ Use Attachment Search When:**
- Looking for files stored in Confluence
- Need to find specific file types (PDFs, Excel, Word docs)
- Want to search within file content, not just titles
- Need parent page context for attachments
- Working primarily with Confluence-based knowledge

**❌ Don't Use Attachment Search When:**
- Looking for Git repository files (use semantic search)
- Searching JIRA tickets (use semantic search)
- Need to search across all source types
- Looking for regular page content (use semantic or hierarchy search)

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Search Capabilities](./search-capabilities.md)** - All search tools overview
- **[Hierarchy Search](./hierarchy-search.md)** - Document structure navigation
- **[Setup and Integration](./setup-and-integration.md)** - MCP server setup

## 📋 Attachment Search Checklist

- [ ] **Understand Confluence attachments** in your knowledge base
- [ ] **Use file-type specific queries** for targeted search within Confluence
- [ ] **Apply appropriate filters** (size, author, file type, parent page)
- [ ] **Include parent context** for complete Confluence page understanding
- [ ] **Check file metadata** for quality and relevance
- [ ] **Combine with other search tools** for comprehensive results across all sources
- [ ] **Optimize performance** with appropriate limits
- [ ] **Understand MarkItDown limitations** for file content extraction

---

**Unlock the knowledge in your Confluence files!** 📎

Attachment search reveals the wealth of information stored in your Confluence attachments - from detailed specifications in PDFs to data insights in spreadsheets to presentation content in slides. By understanding how to search and interpret Confluence file attachments, you can access important content that might otherwise be buried in file repositories.

**Note**: This feature currently focuses on Confluence sources and uses MarkItDown for file content extraction. For files in other sources (Git repositories, JIRA, etc.), use the standard semantic search tool.
