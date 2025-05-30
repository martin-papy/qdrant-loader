# Hierarchy Search Examples for MCP Server

This document demonstrates how to leverage the enhanced hierarchy search capabilities in the Qdrant Loader MCP Server for more meaningful and contextual search results.

## Overview

The MCP server now provides two search tools:

1. **`search`** - Standard semantic search across all data sources
2. **`hierarchy_search`** - Advanced Confluence-specific search with hierarchy awareness

## Enhanced Search Results

All search results now include hierarchy information for Confluence documents:

```json
{
  "score": 0.85,
  "text": "API authentication documentation...",
  "source_type": "confluence",
  "source_title": "Authentication Methods",
  "source_url": "https://company.atlassian.net/wiki/spaces/API/pages/123456",
  "parent_id": "111111",
  "parent_title": "API Documentation",
  "breadcrumb_text": "Developer Guide > API Documentation",
  "depth": 2,
  "children_count": 3,
  "hierarchy_context": "Path: Developer Guide > API Documentation | Depth: 2 | Children: 3"
}
```

## Standard Search with Hierarchy Context

The standard `search` tool now displays hierarchy information for Confluence results:

### Example Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {
      "query": "API authentication",
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
Text: API authentication documentation explains how to authenticate...
Source: confluence - Authentication Methods
📍 Path: Developer Guide > API Documentation
🏗️ Path: Developer Guide > API Documentation | Depth: 2 | Children: 3
⬆️ Parent: API Documentation
⬇️ Children: 3

Score: 0.78
Text: OAuth 2.0 implementation details for secure API access...
Source: confluence - OAuth Implementation
📍 Path: Developer Guide > API Documentation > Authentication Methods
🏗️ Path: Developer Guide > API Documentation > Authentication Methods | Depth: 3 | Children: 0
⬆️ Parent: Authentication Methods
```

## Hierarchical Search Tool

The new `hierarchy_search` tool provides advanced filtering and organization capabilities:

### 1. Filter by Hierarchy Depth

Find all root-level documentation sections:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "documentation",
      "hierarchy_filter": {
        "depth": 0
      },
      "limit": 10
    }
  }
}
```

### 2. Find Pages Under Specific Parent

Search within a specific documentation section:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "configuration",
      "hierarchy_filter": {
        "parent_title": "API Documentation"
      },
      "limit": 10
    }
  }
}
```

### 3. Find Root Pages Only

Get only top-level documentation sections:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "guide",
      "hierarchy_filter": {
        "root_only": true
      },
      "limit": 5
    }
  }
}
```

### 4. Find Pages with Children

Locate comprehensive sections that have sub-pages:

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "tutorial",
      "hierarchy_filter": {
        "has_children": true
      },
      "limit": 10
    }
  }
}
```

### 5. Organize Results by Hierarchy

Group search results by their hierarchical structure:

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "API",
      "organize_by_hierarchy": true,
      "limit": 15
    }
  }
}
```

#### Hierarchical Organization Response

```
Found 8 results organized by hierarchy:

📁 **Developer Guide** (5 results)
📄 API Documentation | Path: Developer Guide | Depth: 1 | Children: 4 (Score: 0.92)
   Complete API documentation including authentication, endpoints, and examples...
   🔗 https://company.atlassian.net/wiki/spaces/DEV/pages/111111

  📄 Authentication Methods | Path: Developer Guide > API Documentation | Depth: 2 | Children: 3 (Score: 0.85)
     API authentication documentation explains how to authenticate...
     🔗 https://company.atlassian.net/wiki/spaces/DEV/pages/123456

    📄 OAuth Implementation | Path: Developer Guide > API Documentation > Authentication Methods | Depth: 3 | Children: 0 (Score: 0.78)
       OAuth 2.0 implementation details for secure API access...
       🔗 https://company.atlassian.net/wiki/spaces/DEV/pages/789012

📁 **User Manual** (3 results)
📄 API Usage Examples | Path: User Manual | Depth: 1 | Children: 2 (Score: 0.76)
   Examples of how to use our API in different scenarios...
   🔗 https://company.atlassian.net/wiki/spaces/USER/pages/345678
```

## Advanced Use Cases

### 1. Content Gap Analysis

Find sections that might need more detailed documentation:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "setup installation",
      "hierarchy_filter": {
        "depth": 1,
        "has_children": false
      },
      "limit": 10
    }
  }
}
```

### 2. Documentation Structure Overview

Get an overview of main documentation sections:

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "*",
      "hierarchy_filter": {
        "root_only": true
      },
      "organize_by_hierarchy": true,
      "limit": 20
    }
  }
}
```

### 3. Find Related Content

Search for content at the same hierarchy level:

```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "troubleshooting",
      "hierarchy_filter": {
        "depth": 2,
        "parent_title": "User Guide"
      },
      "limit": 10
    }
  }
}
```

## Benefits of Hierarchy-Aware Search

### 1. **Better Context Understanding**

- Users can see where content fits in the overall documentation structure
- Breadcrumb navigation helps understand the content's purpose and scope

### 2. **Improved Content Discovery**

- Find related content by exploring parent and child relationships
- Discover comprehensive sections vs. detailed implementation pages

### 3. **Efficient Navigation**

- Quickly identify if a page is a high-level overview or detailed implementation
- Understand the depth and scope of available documentation

### 4. **Content Organization**

- Group search results by documentation sections
- Visualize the hierarchical structure of search results

### 5. **Quality Assessment**

- Identify sections that might need more detailed sub-pages
- Find orphaned content that might need better organization

## Integration Examples

### Claude Desktop Integration

When using with Claude Desktop, the hierarchy information provides rich context:

```
User: "Find API authentication documentation"

Claude: I'll search for API authentication documentation in your knowledge base.

[Uses hierarchy_search tool]

Based on the search results, I found comprehensive API authentication documentation:

**Main Documentation (Developer Guide > API Documentation)**
📄 Authentication Methods (Score: 0.85)
- Located at: Developer Guide > API Documentation  
- Has 3 child pages with detailed implementations
- Covers overview of all authentication methods

**Detailed Implementation (Developer Guide > API Documentation > Authentication Methods)**
📄 OAuth Implementation (Score: 0.78)
- Located at: Developer Guide > API Documentation > Authentication Methods
- Leaf page with specific OAuth 2.0 details
- No child pages - contains implementation specifics

The documentation is well-organized with a clear hierarchy. The main "Authentication Methods" page provides an overview, while "OAuth Implementation" contains the specific technical details you might need.

Would you like me to search for more specific authentication topics or explore the related child pages?
```

### Programmatic Integration

For applications integrating with the MCP server:

```python
import asyncio
import json
from mcp_client import MCPClient

async def search_with_hierarchy():
    client = MCPClient()
    
    # Standard search with hierarchy context
    response = await client.call_tool("search", {
        "query": "API rate limiting",
        "source_types": ["confluence"],
        "limit": 5
    })
    
    # Process results with hierarchy information
    for result in response["results"]:
        print(f"📄 {result['source_title']}")
        if result.get('breadcrumb_text'):
            print(f"   📍 {result['breadcrumb_text']}")
        if result.get('hierarchy_context'):
            print(f"   🏗️ {result['hierarchy_context']}")
        print()

async def hierarchical_search():
    client = MCPClient()
    
    # Find all root documentation sections
    response = await client.call_tool("hierarchy_search", {
        "query": "documentation",
        "hierarchy_filter": {"root_only": True},
        "organize_by_hierarchy": True,
        "limit": 10
    })
    
    # Display organized results
    print(response["content"][0]["text"])
```

## Best Practices

### 1. **Use Hierarchy Filters Strategically**

- Use `root_only: true` to find main documentation sections
- Use `depth` filtering to find content at specific organizational levels
- Use `has_children: true` to find comprehensive overview pages

### 2. **Leverage Hierarchical Organization**

- Enable `organize_by_hierarchy: true` for complex searches
- Helps users understand the structure of available documentation
- Useful for content audits and gap analysis

### 3. **Combine with Standard Search**

- Use standard search for broad queries across all sources
- Use hierarchy search for Confluence-specific organizational queries
- Hierarchy context enhances understanding of any search result

### 4. **Content Discovery Patterns**

- **Top-down**: Start with root pages, then drill down to specifics
- **Bottom-up**: Find specific content, then explore parent context
- **Lateral**: Find content at the same hierarchy level for related topics

## Conclusion

The enhanced hierarchy search capabilities transform the MCP server from a simple search tool into an intelligent documentation navigation system. By understanding and leveraging the hierarchical structure of Confluence content, users can:

- **Find content more efficiently** with contextual understanding
- **Discover related information** through parent-child relationships  
- **Understand documentation structure** at a glance
- **Identify content gaps** and organizational opportunities
- **Navigate complex knowledge bases** with confidence

The hierarchy information is automatically extracted and stored, requiring no additional configuration while providing immediate value for more intelligent search and content discovery.
