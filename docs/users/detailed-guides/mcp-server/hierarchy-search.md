# Hierarchy Search Guide

This guide covers the hierarchy search capabilities of the QDrant Loader MCP Server, enabling you to navigate and understand the structure of your knowledge base with AI assistance.

## 🎯 Overview

The hierarchy search tool is designed for structured documentation where document relationships and organization matter. It's particularly powerful for:

- **Confluence spaces** with parent-child page relationships
- **Wiki systems** with hierarchical organization
- **Documentation sites** with nested structures

### Key Benefits

- **Structure Awareness**: Understands parent-child relationships between documents
- **Context Preservation**: Maintains hierarchical context in search results
- **Navigation Aid**: Helps explore and understand documentation organization
- **Completeness Checking**: Identifies gaps in documentation structure

## 🏗️ How Hierarchy Search Works

### Document Relationships

The hierarchy search tool understands document relationships in Confluence:

```
📁 Root Document
├── 📄 Child Document 1
│   ├── 📄 Grandchild 1.1
│   └── 📄 Grandchild 1.2
├── 📄 Child Document 2
│   ├── 📄 Grandchild 2.1
│   │   └── 📄 Great-grandchild 2.1.1
│   └── 📄 Grandchild 2.2
└── 📄 Child Document 3
```

### Search Process

```
Query: "API documentation structure"
    ↓
1. Semantic Search (find relevant documents)
    ↓
2. Hierarchy Analysis (understand relationships)
    ↓
3. Context Enrichment (add parent/child info)
    ↓
4. Structured Results (organized by hierarchy)
```

## 🔧 Hierarchy Search Parameters

### Available Parameters

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

### Parameter Details

#### Required Parameters

- **`query`** (string): The search query in natural language

#### Optional Parameters

- **`limit`** (integer): Maximum number of results to return (default: 10)
- **`organize_by_hierarchy`** (boolean): Group results by hierarchy structure (default: false)

#### Hierarchy Filter Options

- **`depth`** (integer): Filter by specific hierarchy depth (0 = root pages)
- **`has_children`** (boolean): Filter by whether pages have children
- **`parent_title`** (string): Filter by parent page title
- **`root_only`** (boolean): Show only root pages (no parent)

## 📊 Understanding Hierarchy Results

### Result Structure

Hierarchy search results include hierarchical information:

```json
{
  "results": [
    {
      "score": 0.89,
      "text": "This document covers authentication methods...",
      "source_type": "confluence",
      "source_title": "API Authentication",
      "source_url": "https://wiki.company.com/api/auth",
      "breadcrumb_text": "API Documentation > Security > Authentication",
      "depth": 2,
      "parent_title": "Security",
      "children_count": 3,
      "hierarchy_context": "Path: API Documentation > Security > Authentication | Depth: 2 | Children: 3"
    }
  ]
}
```

### Hierarchy Metadata

Each result includes hierarchy metadata:

- **Depth**: How deep in the hierarchy (0 = root)
- **Breadcrumb Text**: Full path from root to document
- **Parent Title**: Direct parent document title
- **Children Count**: Number of direct child documents
- **Hierarchy Context**: Formatted hierarchy information

## 🎯 Use Cases and Examples

### 1. Documentation Navigation

#### Finding Document Structure

```
Query: "Show me the structure of our API documentation"
Parameters: {
  "organize_by_hierarchy": true,
  "limit": 15
}

Results (organized by hierarchy):
📁 API Documentation (Root)
├── 📁 Getting Started
│   ├── 📄 Quick Start Guide
│   ├── 📄 Authentication Setup
│   └── 📄 First API Call
├── 📁 Endpoints
│   ├── 📁 User Management
│   │   ├── 📄 Create User
│   │   ├── 📄 Update User
│   │   └── 📄 Delete User
│   └── 📁 Data Operations
│       ├── 📄 Create Records
│       └── 📄 Query Data
└── 📁 Security
    ├── 📄 Authentication
    ├── 📄 Authorization
    └── 📄 Rate Limiting
```

#### Finding Related Documents

```
Query: "authentication"
Parameters: {
  "limit": 10
}

Results:
1. 📄 Authentication (api/security/authentication.md)
   Path: API Documentation > Security > Authentication
   
   Hierarchy Context:
   - Parent: Security
   - Children: 3 (JWT Tokens, OAuth 2.0, API Keys)
   - Depth: 2
```

### 2. Content Organization

#### Finding Where to Add New Content

```
Query: "Where should I add documentation about webhook security?"
Parameters: {
  "query": "webhook security",
  "limit": 10
}

AI Response using hierarchy search:
Based on your documentation structure, here are the best places to add webhook security documentation:

1. **Primary Location**: API Documentation > Security > Webhooks
   - Path: /api/security/webhooks/
   - This would be a new child under the Security section
   - Consistent with existing security documentation structure

2. **Alternative Location**: API Documentation > Webhooks > Security
   - Path: /api/webhooks/security/
   - If you have a dedicated Webhooks section
   - Would group all webhook-related content together

Recommendation: Create the main documentation under Security and add examples under the Examples section.
```

#### Checking Documentation Completeness

```
Query: "What sections are missing from our deployment documentation?"
Parameters: {
  "query": "deployment",
  "organize_by_hierarchy": true,
  "limit": 20
}

AI Response using hierarchy search:
Current deployment documentation structure:

📁 Deployment Documentation
├── 📄 Overview ✅
├── 📁 Environments
│   ├── 📄 Development ✅
│   ├── 📄 Staging ✅
│   └── 📄 Production ✅
├── 📁 Platforms
│   ├── 📄 AWS ✅
│   ├── 📄 Docker ✅
│   └── ❌ Kubernetes (MISSING)
└── ❌ Troubleshooting (MISSING SECTION)

Missing sections identified:
1. Kubernetes deployment guide
2. Entire troubleshooting section with common issues
3. Rollback procedures
4. Monitoring and alerting setup
```

### 3. Knowledge Discovery

#### Exploring Unfamiliar Areas

```
Query: "What do we have documented about microservices?"
Parameters: {
  "query": "microservices",
  "organize_by_hierarchy": true,
  "limit": 15
}

Results:
Found microservices documentation across multiple areas:

📁 Architecture Documentation
├── 📄 Microservices Overview
├── 📁 Service Design
│   ├── 📄 API Design Patterns
│   ├── 📄 Data Consistency
│   └── 📄 Service Communication
└── 📁 Deployment Patterns
    ├── 📄 Container Orchestration
    └── 📄 Service Mesh

📁 Development Guidelines
├── 📁 Backend Development
│   ├── 📄 Service Structure
│   └── 📄 Testing Microservices
└── 📁 DevOps
    ├── 📄 CI/CD for Services
    └── 📄 Monitoring Services
```

#### Understanding Document Relationships

```
Query: "How is our API documentation organized?"
Parameters: {
  "query": "API",
  "organize_by_hierarchy": true,
  "limit": 20
}

AI Response:
Your API documentation follows a logical hierarchy:

1. **Top Level**: API Documentation (Root)
   - Children: 5 main sections

2. **Getting Started Section**
   - Path: API Documentation > Getting Started
   - Purpose: Onboarding new developers
   - Children: Quick Start, Authentication Setup, First API Call

3. **Reference Section**
   - Path: API Documentation > Reference
   - Purpose: Complete API specification
   - Children: Endpoints (by category), Data Models, Error Codes

4. **Security Section**
   - Path: API Documentation > Security
   - Purpose: Security implementation
   - Children: Authentication, Authorization, Rate Limiting

This structure follows best practices with clear separation of concerns and logical progression from basic to advanced topics.
```

## 🔍 Advanced Hierarchy Search Techniques

### 1. Depth-Based Filtering

#### Finding Root Documents

```json
{
  "query": "documentation",
  "hierarchy_filter": {
    "root_only": true
  }
}
```

Results: Only top-level documents without parents

#### Finding Documents with Children

```json
{
  "query": "implementation",
  "hierarchy_filter": {
    "has_children": true
  }
}
```

Results: Only documents that have child documents (section overviews)

#### Finding Specific Depth

```json
{
  "query": "API",
  "hierarchy_filter": {
    "depth": 2
  }
}
```

Results: Only documents at exactly 2 levels deep

### 2. Parent-Based Navigation

#### Finding All Children of a Parent

```json
{
  "hierarchy_filter": {
    "parent_title": "API Documentation"
  },
  "organize_by_hierarchy": true
}
```

Results: All documents under "API Documentation" organized by structure

## 🎨 Hierarchy Visualization

### Tree Structure Display

When `organize_by_hierarchy: true`, results are displayed as a tree:

```
📁 Root Document
├── 📄 Child 1 (score: 0.89)
│   ├── 📄 Grandchild 1.1 (score: 0.85)
│   └── 📄 Grandchild 1.2 (score: 0.82)
├── 📄 Child 2 (score: 0.87)
│   └── 📄 Grandchild 2.1 (score: 0.79)
└── 📄 Child 3 (score: 0.84)
```

### Breadcrumb Navigation

Results include navigation paths:

```
Document: JWT Authentication
Path: API Documentation > Security > Authentication > JWT Authentication
```

### Relationship Indicators

Results show document relationships:

```
📄 Current Document: API Rate Limiting
├── 👆 Parent: Security Documentation
├── 👥 Siblings: Authentication, Authorization, CORS
├── 👶 Children: Rate Limit Policies, Implementation Guide
└── 🏠 Root: API Documentation
```

## 🔧 Optimization Strategies

### 1. Query Optimization

#### Structure-Focused Queries

```
✅ "Show me the structure of deployment documentation"
✅ "What are all the sections under API security?"
✅ "Find all child pages of the troubleshooting guide"

❌ "deployment"
❌ "security"
❌ "troubleshooting"
```

#### Relationship Queries

```
✅ "What documentation is related to user authentication?"
✅ "Find all sibling documents to the API reference"
✅ "Show me the parent and children of the deployment guide"
```

### 2. Parameter Optimization

#### For Structure Exploration

```json
{
  "organize_by_hierarchy": true,
  "limit": 20,
  "hierarchy_filter": {
    "has_children": true
  }
}
```

#### For Quick Navigation

```json
{
  "limit": 5,
  "hierarchy_filter": {
    "depth": 2
  }
}
```

#### For Completeness Checking

```json
{
  "organize_by_hierarchy": true,
  "limit": 50,
  "hierarchy_filter": {
    "has_children": true
  }
}
```

### 3. Performance Optimization

#### Limit Hierarchy Depth

```json
{
  "hierarchy_filter": {
    "depth": 3  // Focus on specific depth
  }
}
```

#### Control Result Size

```json
{
  "limit": 10  // Reasonable limit for performance
}
```

## 🎯 Best Practices

### 1. Query Design

- **Be specific about structure**: "Show me the organization of..." rather than just keywords
- **Use relationship terms**: "children", "parent", "siblings", "structure"
- **Ask navigation questions**: "Where should I add...", "What's under...", "How is ... organized?"

### 2. Parameter Selection

- **Use `organize_by_hierarchy: true`** for structure exploration
- **Limit depth** for performance with large hierarchies
- **Filter by `has_children`** for section overviews
- **Use `root_only`** for top-level organization

### 3. Result Interpretation

- **Follow breadcrumb paths** to understand document context
- **Check hierarchy depth** to understand document importance
- **Review children count** for section completeness
- **Examine parent context** for related content

### 4. Common Patterns

#### Documentation Audit

```json
{
  "query": "section overview",
  "organize_by_hierarchy": true,
  "hierarchy_filter": {
    "has_children": true
  }
}
```

#### Content Planning

```json
{
  "query": "where to add new content",
  "hierarchy_filter": {
    "parent_title": "API Documentation"
  }
}
```

#### Navigation Aid

```json
{
  "query": "find related documentation",
  "organize_by_hierarchy": true,
  "limit": 15
}
```

## 🔗 Integration with Other Search Tools

### Combining with Semantic Search

1. **Start with hierarchy search** to understand structure
2. **Use semantic search** for detailed content
3. **Return to hierarchy search** for related documents

### Combining with Attachment Search

1. **Use hierarchy search** to find document context
2. **Use attachment search** to find related files
3. **Combine results** for complete picture

### Search Strategy

```
1. Hierarchy Search: "What's the structure of deployment docs?"
   → Understand organization

2. Semantic Search: "Docker deployment best practices"
   → Find specific content

3. Hierarchy Search: "What else is under deployment documentation?"
   → Discover related content

4. Attachment Search: "deployment diagrams and scripts"
   → Find supporting files
```

## 🔗 Related Documentation

- **[MCP Server Overview](./README.md)** - Complete MCP server guide
- **[Search Capabilities](./search-capabilities.md)** - All search tools overview
- **[Attachment Search](./attachment-search.md)** - File attachment search
- **[Setup and Integration](./setup-and-integration.md)** - MCP server setup

## 📋 Hierarchy Search Checklist

- [ ] **Understand hierarchy structure** in your knowledge base
- [ ] **Use structure-focused queries** for navigation
- [ ] **Enable hierarchy organization** for structure exploration
- [ ] **Apply appropriate filters** for targeted results
- [ ] **Check parent-child relationships** for related content
- [ ] **Optimize parameters** for performance
- [ ] **Combine with other search tools** for comprehensive results

---

**Navigate your knowledge structure with confidence!** 🗺️

Hierarchy search transforms how you explore and understand your documentation. Instead of isolated search results, you get a complete picture of how information is organized, making it easier to find what you need and understand how it fits into the bigger picture.
