# Attachment Search Guide

This guide covers the attachment search capabilities of the QDrant Loader MCP Server, enabling you to find and work with file attachments across your knowledge base with AI assistance.

## 🎯 Overview

The attachment search tool specializes in finding file attachments and their associated documents. It's designed for knowledge bases that include:

- **PDF documents** with extracted text content
- **Office documents** (Word, Excel, PowerPoint)
- **Images** with OCR text extraction
- **Code files** and configuration files
- **Data files** (CSV, JSON, YAML)

### Key Benefits

- **Content Extraction**: Searches inside file contents, not just filenames
- **Parent Context**: Understands the relationship between attachments and their parent documents
- **File Type Intelligence**: Optimized search for different file formats
- **Metadata Awareness**: Searches file properties, authors, and creation dates

## 📎 How Attachment Search Works

### File Processing Pipeline

```text
File Attachment
    ↓
1. Content Extraction (text, metadata)
    ↓
2. OCR Processing (for images)
    ↓
3. Structure Analysis (for structured files)
    ↓
4. Vector Embedding (semantic search)
    ↓
5. Parent Context Integration
    ↓
6. Searchable Attachment Index
```

### Search Process

```text
Query: "architecture diagrams"
    ↓
1. Semantic Search (find relevant attachments)
    ↓
2. File Type Filtering (images, PDFs)
    ↓
3. Content Analysis (OCR text, metadata)
    ↓
4. Parent Context (associated documents)
    ↓
5. Ranked Results (by relevance and file type)
```

## 🔧 Attachment Search Parameters

### Basic Parameters

```json
{
  "name": "attachment_search",
  "parameters": {
    "query": "string",              // Required: Search query
    "limit": 10,                    // Optional: Number of results
    "file_types": ["pdf", "docx"],  // Optional: Filter by file type
    "include_parent_context": true  // Optional: Include parent document
  }
}
```

### Advanced Parameters

```json
{
  "name": "attachment_search",
  "parameters": {
    "query": "performance metrics dashboard",
    "limit": 15,
    "file_types": ["pdf", "xlsx", "png", "svg"],
    "include_parent_context": true,
    
    // Attachment-specific filters
    "attachment_filter": {
      "file_size_min": 1024,        // Minimum file size (bytes)
      "file_size_max": 10485760,    // Maximum file size (10MB)
      "author": "data-team",        // Filter by file author
      "created_after": "2024-01-01", // Files created after date
      "created_before": "2024-12-31", // Files created before date
      "modified_after": "2024-06-01", // Files modified after date
      "attachments_only": true      // Show only attachments, not parent docs
    },
    
    // Content filters
    "content_filter": {
      "has_text": true,             // Files with extractable text
      "has_images": true,           // Files containing images
      "has_tables": true,           // Files with table data
      "language": "en"              // Content language
    },
    
    // Result formatting
    "include_metadata": true,       // Include file metadata
    "include_preview": true,        // Include content preview
    "max_preview_length": 500,      // Limit preview length
    "show_file_path": true          // Show file location
  }
}
```

## 📁 Supported File Types

### Document Files

#### PDF Documents (.pdf)

- **Content**: Full text extraction
- **Metadata**: Title, author, creation date, page count
- **Features**: OCR for scanned PDFs, table extraction
- **Use Cases**: Reports, manuals, specifications

```json
{
  "file_type": "pdf",
  "content_extracted": "System Architecture Overview...",
  "metadata": {
    "pages": 42,
    "author": "Architecture Team",
    "created": "2024-01-15T10:30:00Z",
    "title": "Microservices Architecture Guide"
  }
}
```

#### Microsoft Word (.docx, .doc)

- **Content**: Text, headers, tables, comments
- **Metadata**: Author, last modified, word count
- **Features**: Style preservation, comment extraction
- **Use Cases**: Documentation, procedures, templates

#### Microsoft Excel (.xlsx, .xls)

- **Content**: Cell data, formulas, sheet names
- **Metadata**: Author, sheet count, last modified
- **Features**: Multi-sheet support, formula analysis
- **Use Cases**: Data analysis, metrics, configurations

#### Microsoft PowerPoint (.pptx, .ppt)

- **Content**: Slide text, notes, titles
- **Metadata**: Author, slide count, presentation title
- **Features**: Speaker notes, slide structure
- **Use Cases**: Presentations, training materials

### Image Files

#### PNG/JPEG Images (.png, .jpg, .jpeg)

- **Content**: OCR text extraction
- **Metadata**: Dimensions, creation date, camera info
- **Features**: Text recognition, diagram analysis
- **Use Cases**: Screenshots, diagrams, charts

#### SVG Graphics (.svg)

- **Content**: Text elements, metadata
- **Metadata**: Dimensions, creation tool
- **Features**: Vector text extraction
- **Use Cases**: Diagrams, icons, flowcharts

### Data Files

#### CSV Files (.csv)

- **Content**: Column headers, data structure
- **Metadata**: Row count, column count
- **Features**: Schema analysis, data profiling
- **Use Cases**: Data exports, configurations

#### JSON Files (.json)

- **Content**: Structure analysis, key extraction
- **Metadata**: File size, structure depth
- **Features**: Schema validation, nested data
- **Use Cases**: API responses, configurations

#### YAML Files (.yaml, .yml)

- **Content**: Configuration structure, values
- **Metadata**: File size, key count
- **Features**: Configuration analysis
- **Use Cases**: Config files, CI/CD definitions

### Code Files

#### Source Code (.py, .js, .java, .cpp)

- **Content**: Code structure, comments, functions
- **Metadata**: Line count, language, encoding
- **Features**: Syntax analysis, documentation extraction
- **Use Cases**: Code examples, libraries

## 🔍 Search Examples and Use Cases

### 1. Finding Specific File Types

#### Architecture Diagrams

```text
Query: "system architecture diagrams"
File Types: ["pdf", "png", "svg", "vsd"]

Results:
1. 📄 system-architecture-v2.pdf (2.3 MB)
   Parent: Architecture Documentation
   Content: "Microservices architecture with API gateway, service mesh..."
   Pages: 15, Created: 2024-02-15
   
2. 🖼️ database-schema.png (856 KB)
   Parent: Database Design
   OCR Text: "User Table, Product Table, Order Table, Foreign Keys..."
   Dimensions: 1920x1080, Created: 2024-01-20
   
3. 🖼️ api-flow-diagram.svg (234 KB)
   Parent: API Documentation
   Content: "Request → Authentication → Rate Limiting → Business Logic..."
   Vector Graphics: Text elements extracted
```

#### Performance Reports

```text
Query: "performance benchmarks and metrics"
File Types: ["xlsx", "pdf", "csv"]

Results:
1. 📊 q4-performance-report.xlsx (1.2 MB)
   Parent: Quarterly Reports
   Sheets: ["API Performance", "Database Metrics", "User Analytics"]
   Data: Response times, throughput, error rates
   
2. 📄 load-testing-results.pdf (3.1 MB)
   Parent: Testing Documentation
   Content: "Load test results show 95th percentile response time..."
   Charts: Performance graphs and trend analysis
   
3. 📊 daily-metrics.csv (456 KB)
   Parent: Monitoring Dashboard
   Columns: timestamp, response_time, requests_per_second, error_rate
   Rows: 8760 (hourly data for one year)
```

### 2. Content-Based Search

#### Finding Specific Information

```text
Query: "API rate limits and throttling policies"
File Types: ["pdf", "docx", "json", "yaml"]

Results:
1. 📄 api-rate-limiting-policy.pdf (1.8 MB)
   Parent: API Documentation
   Content: "Rate limiting is implemented using a token bucket algorithm..."
   Sections: Policy Overview, Implementation, Monitoring
   
2. 📄 rate-limit-config.yaml (12 KB)
   Parent: Configuration Files
   Content: "default_rate: 1000/hour, premium_rate: 5000/hour..."
   Structure: Hierarchical rate limit definitions
   
3. 📄 throttling-implementation.docx (890 KB)
   Parent: Development Guidelines
   Content: "Implementation guide for rate limiting middleware..."
   Sections: Setup, Configuration, Testing
```

#### Technical Specifications

```text
Query: "database schema and table structures"
File Types: ["sql", "png", "pdf", "xlsx"]

Results:
1. 📄 database-schema.sql (45 KB)
   Parent: Database Documentation
   Content: "CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR..."
   Tables: 23 tables with relationships
   
2. 🖼️ erd-diagram.png (1.1 MB)
   Parent: Database Design
   OCR Text: "Users, Products, Orders, Payments, Relationships..."
   Diagram: Entity Relationship Diagram
   
3. 📊 table-documentation.xlsx (567 KB)
   Parent: Database Documentation
   Sheets: ["Tables", "Columns", "Indexes", "Constraints"]
   Data: Complete schema documentation
```

### 3. Author and Date Filtering

#### Recent Updates by Team

```text
Query: "deployment procedures"
Filters: {
  "author": "devops-team",
  "created_after": "2024-01-01",
  "file_types": ["pdf", "docx", "md"]
}

Results:
1. 📄 deployment-runbook-v3.pdf (2.1 MB)
   Author: devops-team
   Created: 2024-03-15
   Parent: Operations Documentation
   Content: "Updated deployment procedures for Kubernetes..."
   
2. 📄 rollback-procedures.docx (678 KB)
   Author: devops-team
   Created: 2024-02-20
   Parent: Emergency Procedures
   Content: "Step-by-step rollback process for production..."
   
3. 📄 monitoring-setup.md (23 KB)
   Author: devops-team
   Created: 2024-01-25
   Parent: Monitoring Documentation
   Content: "Setting up Prometheus and Grafana for..."
```

#### Historical Documentation

```text
Query: "legacy system documentation"
Filters: {
  "created_before": "2022-01-01",
  "file_types": ["pdf", "doc"],
  "file_size_min": 1048576  // Files larger than 1MB
}

Results:
1. 📄 legacy-api-specification.pdf (5.2 MB)
   Created: 2021-06-15
   Parent: Historical Documentation
   Content: "Legacy REST API v1.0 specification..."
   Status: Archived, superseded by v2.0
   
2. 📄 old-deployment-guide.doc (3.8 MB)
   Created: 2020-11-30
   Parent: Archived Procedures
   Content: "Manual deployment process for legacy systems..."
   Status: Replaced by automated CI/CD
```

## 🔧 Advanced Attachment Features

### 1. Content Extraction and Analysis

#### Text Extraction

The tool extracts and indexes various types of content:

```text
PDF Content:
"To deploy the application to production, first ensure all dependencies 
are installed and the database migrations have been applied..."

Excel Data:
"Server response times: 95th percentile: 250ms, 99th percentile: 500ms
Database query performance: Average: 45ms, Max: 2.3s"

Image OCR:
"System Architecture Diagram
Web Layer → API Gateway → Microservices
Database Layer: PostgreSQL, Redis Cache"

Code Comments:
"# Configuration for production deployment
# This script handles the complete deployment pipeline
# including database migrations and service restarts"
```

#### Metadata Extraction

Rich metadata is extracted and made searchable:

```json
{
  "filename": "api-performance-analysis.xlsx",
  "file_type": "xlsx",
  "size": 2457600,
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z",
  "author": "performance-team",
  "sheets": ["Summary", "API Endpoints", "Database Queries", "Trends"],
  "row_count": 15420,
  "column_count": 12,
  "has_charts": true,
  "has_formulas": true,
  "parent_document": "Performance Testing Results",
  "tags": ["performance", "api", "metrics", "analysis"]
}
```

### 2. Parent Context Integration

Results include context from the parent document:

```text
Attachment: database-migration-script.sql
Parent Document: "Database Schema Updates v2.1"
Parent Context: "This migration script updates the user table schema to 
support new authentication features. Run this script during the 
maintenance window scheduled for Saturday 2AM UTC. Ensure you have 
a backup before proceeding..."

Related Attachments:
- rollback-script.sql (in same parent document)
- migration-test-results.pdf (in same parent document)
- schema-diff.png (visual comparison)
```

### 3. File Relationship Analysis

The tool understands relationships between files:

```text
Primary File: system-architecture.pdf
Related Files:
├── 📄 architecture-details.docx (detailed specifications)
├── 🖼️ component-diagram.png (visual representation)
├── 📊 performance-requirements.xlsx (technical requirements)
├── 📄 implementation-plan.pdf (development roadmap)
└── 📄 security-considerations.md (security analysis)

Relationship Types:
- Supplementary: Provides additional detail
- Visual: Graphical representation
- Data: Supporting metrics and requirements
- Implementation: How to build it
- Analysis: Security and risk assessment
```

## 🎯 Optimization Strategies

### 1. Query Optimization

#### File-Type Specific Queries

```text
✅ "Find Excel files with performance metrics"
✅ "Show me PDF documents about deployment"
✅ "Search for architecture diagrams in PNG or SVG format"

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
  "file_size_min": 1024,        // Exclude tiny files
  "file_size_max": 52428800     // Exclude files larger than 50MB
}
```

#### Date Range Filtering

```json
{
  "created_after": "2024-01-01",   // Recent files only
  "modified_after": "2024-06-01"   // Recently updated files
}
```

#### Author Filtering

```json
{
  "author": "architecture-team",   // Specific team
  "author": "john.doe"            // Specific person
}
```

### 3. Performance Optimization

#### Limit File Types

```json
{
  "file_types": ["pdf", "docx"],  // Only search specific types
  "attachments_only": true        // Skip parent document content
}
```

#### Control Preview Length

```json
{
  "max_preview_length": 200,      // Shorter previews
  "include_preview": false        // No content preview
}
```

#### Cache Settings

```json
{
  "cache_attachments": true,      // Cache attachment metadata
  "cache_ttl": 3600              // Cache for 1 hour
}
```

## 🎨 Result Interpretation

### Understanding Attachment Results

#### File Information

```text
📄 api-documentation.pdf (2.3 MB)
├── 📊 Metadata
│   ├── Pages: 42
│   ├── Author: technical-writing-team
│   ├── Created: 2024-01-15T10:30:00Z
│   └── Modified: 2024-01-20T14:45:00Z
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

### Combining Search Strategies

#### 1. Start with Semantic Search

```text
Query: "deployment procedures"
→ Find general documentation about deployment
```

#### 2. Use Attachment Search for Details

```text
Query: "deployment scripts and configurations"
File Types: ["sh", "yaml", "json", "sql"]
→ Find specific implementation files
```

#### 3. Use Hierarchy Search for Context

```text
Query: "deployment documentation structure"
→ Understand how deployment docs are organized
```

### Multi-Tool Workflow

```text
1. Semantic Search: "API authentication methods"
   → Understand authentication concepts

2. Attachment Search: "authentication configuration files"
   → Find implementation details

3. Hierarchy Search: "authentication documentation structure"
   → See how auth docs are organized

4. Attachment Search: "authentication examples and code"
   → Find practical examples
```

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Search Capabilities](./search-capabilities.md)** - All search tools overview
- **[Hierarchy Search](./hierarchy-search.md)** - Document structure navigation
- **[Setup and Integration](./setup-and-integration.md)** - MCP server setup

## 📋 Attachment Search Checklist

- [ ] **Understand file types** in your knowledge base
- [ ] **Use file-type specific queries** for targeted search
- [ ] **Apply appropriate filters** (size, date, author)
- [ ] **Include parent context** for complete understanding
- [ ] **Check file metadata** for quality and relevance
- [ ] **Combine with other search tools** for comprehensive results
- [ ] **Optimize performance** with appropriate limits

---

**Unlock the hidden knowledge in your files!** 📎

Attachment search reveals the wealth of information stored in your files - from detailed specifications in PDFs to data insights in spreadsheets to visual knowledge in diagrams. By understanding how to search and interpret file attachments, you can access the complete picture of your knowledge base.
