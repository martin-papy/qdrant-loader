# Attachment-Aware Search Examples for MCP Server

This document demonstrates how to leverage the enhanced attachment search capabilities in the Qdrant Loader MCP Server for finding and working with file attachments and their parent documents.

## Overview

The MCP server now provides three search tools with attachment awareness:

1. **`search`** - Standard semantic search with attachment context
2. **`hierarchy_search`** - Confluence hierarchy search with attachment information  
3. **`attachment_search`** - Specialized search for file attachments and their relationships

## Enhanced Search Results with Attachment Information

All search results now include attachment information when applicable:

```json
{
  "score": 0.85,
  "text": "# Project Requirements\n\nDetailed project specifications...",
  "source_type": "confluence",
  "source_title": "Attachment: requirements.pdf",
  "source_url": "https://company.atlassian.net/wiki/download/attachments/123456/requirements.pdf",
  "is_attachment": true,
  "parent_document_id": "doc_123456",
  "parent_document_title": "Project Planning",
  "attachment_id": "att_789",
  "original_filename": "requirements.pdf",
  "file_size": 2048000,
  "mime_type": "application/pdf",
  "attachment_author": "project.manager@company.com",
  "attachment_context": "File: requirements.pdf | Size: 2.0 MB | Type: application/pdf | Author: project.manager@company.com"
}
```

## Standard Search with Attachment Context

The standard `search` tool now displays attachment information for file results:

### Example Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {
      "query": "project requirements",
      "source_types": ["confluence"],
      "limit": 5
    }
  }
}
```

### Enhanced Response Format

```
Found 3 results:

Score: 0.85
Text: # Project Requirements\n\nDetailed project specifications...
Source: confluence - Attachment: requirements.pdf
📎 Attachment: requirements.pdf
📋 File: requirements.pdf | Size: 2.0 MB | Type: application/pdf | Author: project.manager@company.com
📄 Attached to: Project Planning
📍 Path: Engineering > Projects > Project Planning
🏗️ Path: Engineering > Projects > Project Planning | Depth: 3 | Children: 0

Score: 0.78
Text: # Budget Spreadsheet\n\nProject budget breakdown...
Source: confluence - Attachment: budget.xlsx
📎 Attachment: budget.xlsx
📋 File: budget.xlsx | Size: 512.0 KB | Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | Author: finance@company.com
📄 Attached to: Project Planning
```

## Attachment Search Tool

The new `attachment_search` tool provides specialized capabilities for finding and filtering file attachments:

### 1. Find All Attachments

Search for any file attachments across all sources:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "documentation",
      "attachment_filter": {
        "attachments_only": true
      },
      "limit": 10
    }
  }
}
```

### 2. Find Attachments by File Type

Search for specific file types:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "design",
      "attachment_filter": {
        "attachments_only": true,
        "file_type": "pdf"
      },
      "limit": 10
    }
  }
}
```

### 3. Find Attachments by Parent Document

Search for attachments within a specific document:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "specifications",
      "attachment_filter": {
        "parent_document_title": "Project Planning"
      },
      "limit": 10
    }
  }
}
```

### 4. Find Large Files

Search for attachments above a certain size:

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "presentation",
      "attachment_filter": {
        "attachments_only": true,
        "file_size_min": 5242880
      },
      "limit": 10
    }
  }
}
```

### 5. Find Attachments by Author

Search for files uploaded by specific users:

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "report",
      "attachment_filter": {
        "attachments_only": true,
        "author": "analyst@company.com"
      },
      "limit": 10
    }
  }
}
```

### 6. Complex Attachment Filtering

Combine multiple filters for precise results:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "financial data",
      "attachment_filter": {
        "attachments_only": true,
        "file_type": "xlsx",
        "file_size_min": 102400,
        "file_size_max": 10485760,
        "author": "finance@company.com"
      },
      "include_parent_context": true,
      "limit": 15
    }
  }
}
```

## Use Cases and Benefits

### 1. **Document Discovery**

- Find all attachments related to a project or topic
- Discover supporting documents and files for any page
- Locate specific file types across your knowledge base

### 2. **Content Audit**

- Identify large files that might need cleanup
- Find duplicate or outdated attachments
- Analyze file distribution across projects

### 3. **Contextual Understanding**

- See which documents have supporting files
- Understand the relationship between pages and their attachments
- Find comprehensive documentation with both text and file resources

### 4. **File Management**

- Track who uploaded which files
- Find files by type, size, or author
- Locate attachments within specific documentation sections

## Advanced Search Patterns

### Finding Comprehensive Documentation

Search for pages that have both content and attachments:

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {
      "query": "API documentation",
      "source_types": ["confluence"],
      "limit": 20
    }
  }
}
```

Then filter results to find pages with attachments by looking for results that have `is_attachment: false` but mention attachments in the content.

### Finding Related Files

Use the parent document relationship to find all files related to a specific topic:

```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "*",
      "attachment_filter": {
        "parent_document_title": "API Documentation"
      },
      "limit": 50
    }
  }
}
```

### Content Gap Analysis

Find pages without attachments that might benefit from supporting files:

1. Search for main documentation pages
2. Filter for pages without attachments
3. Identify opportunities to add supporting materials

## Integration Examples

### Claude Desktop Integration

```
User: "Find all PDF attachments related to project requirements"

Claude: I'll search for PDF attachments related to project requirements.

[Uses attachment_search tool with file_type filter]

I found 5 PDF attachments related to project requirements:

**📎 requirements.pdf** (Score: 0.92)
📋 File: requirements.pdf | Size: 2.0 MB | Type: application/pdf | Author: project.manager@company.com
📄 Attached to: Project Planning
📍 Path: Engineering > Projects > Project Planning
Contains detailed functional and non-functional requirements...

**📎 technical-specs.pdf** (Score: 0.87)
📋 File: technical-specs.pdf | Size: 1.5 MB | Type: application/pdf | Author: tech.lead@company.com
📄 Attached to: Technical Architecture
📍 Path: Engineering > Projects > Technical Architecture
Technical specifications and system architecture details...

These documents provide comprehensive project requirements and technical specifications. Would you like me to search for related spreadsheets or presentations as well?
```

### Programmatic Integration

```python
import asyncio
from mcp_client import MCPClient

async def find_project_attachments():
    client = MCPClient()
    
    # Find all attachments for a specific project
    response = await client.call_tool("attachment_search", {
        "query": "project alpha",
        "attachment_filter": {
            "attachments_only": True
        },
        "include_parent_context": True,
        "limit": 20
    })
    
    # Process results
    for result in response["results"]:
        print(f"📎 {result['original_filename']}")
        print(f"   📄 Attached to: {result['parent_document_title']}")
        print(f"   📋 {result['attachment_context']}")
        print()

async def find_large_files():
    client = MCPClient()
    
    # Find files larger than 10MB
    response = await client.call_tool("attachment_search", {
        "query": "*",
        "attachment_filter": {
            "attachments_only": True,
            "file_size_min": 10485760  # 10MB
        },
        "limit": 10
    })
    
    # Analyze large files
    for result in response["results"]:
        size_mb = result['file_size'] / (1024 * 1024)
        print(f"📎 {result['original_filename']} ({size_mb:.1f} MB)")
        print(f"   📄 {result['parent_document_title']}")
        print()
```

## Best Practices

### 1. **Use Specific Filters**

- Combine multiple filters for precise results
- Use file type filters when looking for specific formats
- Apply size filters to find large or small files

### 2. **Leverage Parent Context**

- Always include parent document information for context
- Use parent document titles to understand file relationships
- Follow breadcrumb paths to understand document hierarchy

### 3. **Combine Search Tools**

- Use standard search for broad queries
- Use attachment search for file-specific queries
- Use hierarchy search for organizational context

### 4. **File Management Workflows**

- Regular audits using size and type filters
- Author-based searches for content ownership
- Parent document analysis for organization

## Conclusion

The enhanced attachment-aware search capabilities transform the MCP server into a comprehensive file and document discovery system. By understanding and leveraging the relationships between documents and their attachments, users can:

- **Find files more efficiently** with contextual understanding
- **Discover related content** through parent-child relationships
- **Manage file assets** with powerful filtering capabilities
- **Understand document structure** including supporting materials
- **Audit and organize content** across multiple sources

The attachment information is automatically extracted and stored during ingestion, requiring no additional configuration while providing immediate value for intelligent file discovery and management.
