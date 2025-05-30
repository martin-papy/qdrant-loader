# QDrant Loader MCP Server - Advanced Search Examples

This document provides comprehensive examples of the advanced search capabilities in the QDrant Loader MCP Server, including hierarchy-aware search and attachment-aware search.

## Overview

The MCP server provides three specialized search tools:

1. **`search`** - Standard semantic search with hierarchy and attachment context
2. **`hierarchy_search`** - Confluence-specific search with hierarchy filtering and organization
3. **`attachment_search`** - File-focused search with attachment filtering and parent document context

## Standard Search with Enhanced Context

### Basic Semantic Search

```bash
# Standard search with enhanced context
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"authentication implementation","limit":5}}}' | mcp-qdrant-loader
```

**Response includes:**

- Standard search results with relevance scoring
- Hierarchy context (breadcrumb paths, depth, children count)
- Attachment context (file metadata, parent document relationships)
- Visual indicators for navigation and file types

### Source-Filtered Search

```bash
# Search only Confluence with hierarchy context
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search","arguments":{"query":"API documentation","source_types":["confluence"],"limit":10}}}' | mcp-qdrant-loader

# Search local files with attachment context
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search","arguments":{"query":"configuration","source_types":["localfile"],"limit":8}}}' | mcp-qdrant-loader
```

## Hierarchy-Aware Search

### Document Structure Discovery

#### Find Root Documentation Pages

```bash
# Find all root pages (no parent) that have children
echo '{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"documentation","hierarchy_filter":{"root_only":true,"has_children":true},"organize_by_hierarchy":true,"limit":10}}}' | mcp-qdrant-loader
```

**Use Case:** Discover main documentation sections and entry points.

#### Navigate by Depth Level

```bash
# Find pages at depth level 1 (immediate children of root)
echo '{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"guide","hierarchy_filter":{"depth":1},"limit":15}}}' | mcp-qdrant-loader

# Find pages at depth level 2 (grandchildren of root)
echo '{"jsonrpc":"2.0","id":12,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"tutorial","hierarchy_filter":{"depth":2},"limit":20}}}' | mcp-qdrant-loader

# Find deep pages (depth 3+) for detailed content
echo '{"jsonrpc":"2.0","id":13,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"implementation","hierarchy_filter":{"depth":3},"limit":10}}}' | mcp-qdrant-loader
```

**Use Cases:**

- Understand documentation structure
- Find content at appropriate detail levels
- Navigate large documentation hierarchies

#### Find Children of Specific Parents

```bash
# Find all child pages of "Developer Guide"
echo '{"jsonrpc":"2.0","id":14,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"","hierarchy_filter":{"parent_title":"Developer Guide"},"limit":25}}}' | mcp-qdrant-loader

# Find API-related pages under "Technical Documentation"
echo '{"jsonrpc":"2.0","id":15,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"API","hierarchy_filter":{"parent_title":"Technical Documentation"},"limit":15}}}' | mcp-qdrant-loader
```

**Use Cases:**

- Explore specific documentation sections
- Find related content within a topic area
- Navigate from general to specific information

### Content Organization Analysis

#### Find Section Headers (Pages with Children)

```bash
# Find pages that have children (section headers)
echo '{"jsonrpc":"2.0","id":16,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"getting started","hierarchy_filter":{"has_children":true},"organize_by_hierarchy":true,"limit":10}}}' | mcp-qdrant-loader

# Find overview pages with multiple subtopics
echo '{"jsonrpc":"2.0","id":17,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"overview","hierarchy_filter":{"has_children":true},"limit":8}}}' | mcp-qdrant-loader
```

#### Find Leaf Content (Pages without Children)

```bash
# Find detailed implementation pages (no children)
echo '{"jsonrpc":"2.0","id":18,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"implementation","hierarchy_filter":{"has_children":false},"limit":20}}}' | mcp-qdrant-loader

# Find specific tutorials and how-to guides
echo '{"jsonrpc":"2.0","id":19,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"how to","hierarchy_filter":{"has_children":false},"limit":15}}}' | mcp-qdrant-loader
```

**Use Cases:**

- Find actionable, detailed content
- Locate specific procedures and tutorials
- Identify content that needs expansion

### Hierarchical Organization

```bash
# Organize search results by hierarchy structure
echo '{"jsonrpc":"2.0","id":20,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"security","organize_by_hierarchy":true,"limit":20}}}' | mcp-qdrant-loader

# Find and organize API documentation by structure
echo '{"jsonrpc":"2.0","id":21,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"API","hierarchy_filter":{"depth":2},"organize_by_hierarchy":true,"limit":15}}}' | mcp-qdrant-loader
```

**Benefits:**

- Visual tree-like structure display
- Understanding of content relationships
- Better navigation context

## Attachment-Aware Search

### File Type Discovery

#### Find Specific Document Types

```bash
# Find all PDF documents
echo '{"jsonrpc":"2.0","id":30,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"specification","attachment_filter":{"attachments_only":true,"file_type":"pdf"},"limit":15}}}' | mcp-qdrant-loader

# Find Excel spreadsheets and data files
echo '{"jsonrpc":"2.0","id":31,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"data","attachment_filter":{"attachments_only":true,"file_type":"xlsx"},"limit":10}}}' | mcp-qdrant-loader

# Find PowerPoint presentations
echo '{"jsonrpc":"2.0","id":32,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"presentation","attachment_filter":{"attachments_only":true,"file_type":"pptx"},"limit":8}}}' | mcp-qdrant-loader
```

#### Find Images and Diagrams

```bash
# Find PNG images (screenshots, diagrams)
echo '{"jsonrpc":"2.0","id":33,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"architecture","attachment_filter":{"attachments_only":true,"file_type":"png"},"limit":12}}}' | mcp-qdrant-loader

# Find JPEG images
echo '{"jsonrpc":"2.0","id":34,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"screenshot","attachment_filter":{"attachments_only":true,"file_type":"jpg"},"limit":10}}}' | mcp-qdrant-loader

# Find SVG diagrams
echo '{"jsonrpc":"2.0","id":35,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"diagram","attachment_filter":{"attachments_only":true,"file_type":"svg"},"limit":8}}}' | mcp-qdrant-loader
```

### File Size Management

#### Find Large Files for Cleanup

```bash
# Find files larger than 10MB
echo '{"jsonrpc":"2.0","id":40,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"file_size_min":10485760},"limit":25}}}' | mcp-qdrant-loader

# Find very large files (>50MB) for storage optimization
echo '{"jsonrpc":"2.0","id":41,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"file_size_min":52428800},"limit":10}}}' | mcp-qdrant-loader

# Find large PDFs specifically
echo '{"jsonrpc":"2.0","id":42,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"file_type":"pdf","file_size_min":5242880},"limit":20}}}' | mcp-qdrant-loader
```

#### Find Small Files for Quick Reference

```bash
# Find small files (under 1MB) for templates and quick reference
echo '{"jsonrpc":"2.0","id":43,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"template","attachment_filter":{"attachments_only":true,"file_size_max":1048576},"limit":15}}}' | mcp-qdrant-loader

# Find small configuration files
echo '{"jsonrpc":"2.0","id":44,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"config","attachment_filter":{"attachments_only":true,"file_size_max":102400},"limit":20}}}' | mcp-qdrant-loader
```

### Author and Ownership Tracking

#### Find Files by Author

```bash
# Find files uploaded by specific user
echo '{"jsonrpc":"2.0","id":50,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"author":"john.doe@company.com"},"limit":20}}}' | mcp-qdrant-loader

# Find project files by project manager
echo '{"jsonrpc":"2.0","id":51,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"project","attachment_filter":{"attachments_only":true,"author":"pm@company.com"},"limit":15}}}' | mcp-qdrant-loader

# Find recent uploads by new team members
echo '{"jsonrpc":"2.0","id":52,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"author":"new.employee@company.com"},"limit":25}}}' | mcp-qdrant-loader
```

### Parent Document Relationships

#### Find Attachments by Parent Document

```bash
# Find all attachments related to "Project Planning"
echo '{"jsonrpc":"2.0","id":60,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"parent_document_title":"Project Planning"},"include_parent_context":true,"limit":20}}}' | mcp-qdrant-loader

# Find files attached to API documentation
echo '{"jsonrpc":"2.0","id":61,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"parent_document_title":"API Reference"},"limit":15}}}' | mcp-qdrant-loader

# Find supporting materials for getting started guide
echo '{"jsonrpc":"2.0","id":62,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"getting started","attachment_filter":{"parent_document_title":"Getting Started Guide"},"include_parent_context":true,"limit":10}}}' | mcp-qdrant-loader
```

#### Find Documents with Attachments

```bash
# Find requirements documents with attachments
echo '{"jsonrpc":"2.0","id":63,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"requirements","attachment_filter":{"attachments_only":false},"include_parent_context":true,"limit":15}}}' | mcp-qdrant-loader

# Find documentation pages that have supporting files
echo '{"jsonrpc":"2.0","id":64,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"documentation","include_parent_context":true,"limit":20}}}' | mcp-qdrant-loader
```

## Combined Search Strategies

### Content Discovery Workflow

#### Step 1: Find Main Documentation Structure

```bash
# Find root documentation sections
echo '{"jsonrpc":"2.0","id":70,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"documentation","hierarchy_filter":{"root_only":true,"has_children":true},"organize_by_hierarchy":true,"limit":10}}}' | mcp-qdrant-loader
```

#### Step 2: Explore Specific Sections

```bash
# Find detailed content in a specific section
echo '{"jsonrpc":"2.0","id":71,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"getting started","hierarchy_filter":{"parent_title":"User Guide","has_children":false},"limit":15}}}' | mcp-qdrant-loader
```

#### Step 3: Find Supporting Materials

```bash
# Find attachments related to the topic
echo '{"jsonrpc":"2.0","id":72,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"getting started","attachment_filter":{"attachments_only":true},"include_parent_context":true,"limit":10}}}' | mcp-qdrant-loader
```

#### Step 4: Comprehensive Search

```bash
# Standard search for complete context
echo '{"jsonrpc":"2.0","id":73,"method":"tools/call","params":{"name":"search","arguments":{"query":"getting started guide","source_types":["confluence"],"limit":10}}}' | mcp-qdrant-loader
```

### File Management and Audit

#### Storage Optimization

```bash
# Find large files for cleanup
echo '{"jsonrpc":"2.0","id":80,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"file_size_min":10485760},"limit":50}}}' | mcp-qdrant-loader

# Find duplicate or similar files
echo '{"jsonrpc":"2.0","id":81,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"backup","attachment_filter":{"attachments_only":true},"limit":30}}}' | mcp-qdrant-loader
```

#### Content Organization Audit

```bash
# Find orphaned root pages (potential organization issues)
echo '{"jsonrpc":"2.0","id":82,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"","hierarchy_filter":{"root_only":true,"has_children":false},"limit":25}}}' | mcp-qdrant-loader

# Find pages with many children (potential splitting candidates)
echo '{"jsonrpc":"2.0","id":83,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"","hierarchy_filter":{"has_children":true},"organize_by_hierarchy":true,"limit":20}}}' | mcp-qdrant-loader
```

#### User Activity Analysis

```bash
# Find recent uploads by user
echo '{"jsonrpc":"2.0","id":84,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"author":"active.user@company.com"},"limit":30}}}' | mcp-qdrant-loader

# Find files without clear ownership
echo '{"jsonrpc":"2.0","id":85,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true},"limit":50}}}' | mcp-qdrant-loader
```

## Advanced Filtering Combinations

### Complex Multi-Criteria Searches

#### Find Specific Project Resources

```bash
# Find large PDF specifications for a specific project
echo '{"jsonrpc":"2.0","id":90,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"project alpha","attachment_filter":{"attachments_only":true,"file_type":"pdf","file_size_min":1048576},"include_parent_context":true,"limit":10}}}' | mcp-qdrant-loader

# Find Excel files by specific author for data analysis
echo '{"jsonrpc":"2.0","id":91,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"analysis","attachment_filter":{"attachments_only":true,"file_type":"xlsx","author":"data.analyst@company.com"},"limit":15}}}' | mcp-qdrant-loader
```

#### Find Documentation Gaps

```bash
# Find deep pages without children (potential expansion points)
echo '{"jsonrpc":"2.0","id":92,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"","hierarchy_filter":{"depth":3,"has_children":false},"limit":30}}}' | mcp-qdrant-loader

# Find sections with few supporting materials
echo '{"jsonrpc":"2.0","id":93,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"implementation","attachment_filter":{"attachments_only":false},"include_parent_context":true,"limit":20}}}' | mcp-qdrant-loader
```

## Use Case Examples

### For Developers

#### Find Code Documentation and Examples

```bash
# Find API documentation structure
echo '{"jsonrpc":"2.0","id":100,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"API","hierarchy_filter":{"has_children":true},"organize_by_hierarchy":true,"limit":15}}}' | mcp-qdrant-loader

# Find code examples and templates
echo '{"jsonrpc":"2.0","id":101,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"example","attachment_filter":{"attachments_only":true,"file_type":"txt"},"include_parent_context":true,"limit":10}}}' | mcp-qdrant-loader

# Find configuration files
echo '{"jsonrpc":"2.0","id":102,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"config","attachment_filter":{"attachments_only":true,"file_size_max":102400},"limit":20}}}' | mcp-qdrant-loader
```

### For Project Managers

#### Track Project Documentation

```bash
# Find project overview pages
echo '{"jsonrpc":"2.0","id":110,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"project","hierarchy_filter":{"root_only":true,"has_children":true},"organize_by_hierarchy":true,"limit":10}}}' | mcp-qdrant-loader

# Find project deliverables and documents
echo '{"jsonrpc":"2.0","id":111,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"deliverable","attachment_filter":{"attachments_only":true,"file_type":"pdf"},"include_parent_context":true,"limit":15}}}' | mcp-qdrant-loader

# Find status reports and updates
echo '{"jsonrpc":"2.0","id":112,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"status","attachment_filter":{"attachments_only":true,"author":"pm@company.com"},"limit":20}}}' | mcp-qdrant-loader
```

### For Content Managers

#### Audit Documentation Structure

```bash
# Find all root pages for structure review
echo '{"jsonrpc":"2.0","id":120,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"","hierarchy_filter":{"root_only":true},"organize_by_hierarchy":true,"limit":50}}}' | mcp-qdrant-loader

# Find large files for storage optimization
echo '{"jsonrpc":"2.0","id":121,"method":"tools/call","params":{"name":"attachment_search","arguments":{"query":"","attachment_filter":{"attachments_only":true,"file_size_min":5242880},"limit":30}}}' | mcp-qdrant-loader

# Find content without clear organization
echo '{"jsonrpc":"2.0","id":122,"method":"tools/call","params":{"name":"hierarchy_search","arguments":{"query":"","hierarchy_filter":{"depth":0,"has_children":false},"limit":25}}}' | mcp-qdrant-loader
```

## Integration with Cursor IDE

When using these search tools with Cursor, the AI assistant can:

1. **Understand Documentation Structure**: Navigate hierarchies intelligently
2. **Find Supporting Materials**: Locate relevant files and attachments
3. **Provide Contextual Assistance**: Use parent/child relationships for better understanding
4. **Manage Resources**: Help organize and optimize documentation and files

### Example Cursor Prompts

- "Find all API documentation and show me the structure"
- "What configuration files are available for this project?"
- "Show me all large PDF files that might need cleanup"
- "Find the getting started guide and all its supporting materials"
- "What are the main documentation sections and their subsections?"

The enhanced search capabilities make Cursor's AI assistance more intelligent and context-aware, providing better support for development and documentation tasks.
