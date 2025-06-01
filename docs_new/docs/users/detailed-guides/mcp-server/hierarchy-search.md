# Hierarchy Search Guide

This guide covers the hierarchy search capabilities of the QDrant Loader MCP Server, enabling you to navigate and understand the structure of your knowledge base with AI assistance.

## 🎯 Overview

The hierarchy search tool is designed for structured documentation where document relationships and organization matter. It's particularly powerful for:

- **Confluence spaces** with parent-child page relationships
- **Wiki systems** with hierarchical organization
- **Documentation sites** with nested structures
- **File systems** with directory hierarchies

### Key Benefits

- **Structure Awareness**: Understands parent-child relationships between documents
- **Context Preservation**: Maintains hierarchical context in search results
- **Navigation Aid**: Helps explore and understand documentation organization
- **Completeness Checking**: Identifies gaps in documentation structure

## 🏗️ How Hierarchy Search Works

### Document Relationships

The hierarchy search tool understands several types of document relationships:

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

### Basic Parameters

```json
{
  "name": "hierarchy_search",
  "parameters": {
    "query": "string",              // Required: Search query
    "limit": 10,                    // Optional: Number of results
    "include_hierarchy": true,      // Optional: Include hierarchy info
    "depth": 3,                     // Optional: Maximum hierarchy depth
    "organize_by_hierarchy": false  // Optional: Group results by structure
  }
}
```

### Advanced Parameters

```json
{
  "name": "hierarchy_search",
  "parameters": {
    "query": "deployment procedures",
    "limit": 15,
    "include_hierarchy": true,
    "depth": 5,
    "organize_by_hierarchy": true,
    
    // Hierarchy-specific filters
    "hierarchy_filter": {
      "root_only": false,           // Show only root documents
      "has_children": true,         // Show only documents with children
      "depth": 2,                   // Filter by specific depth level
      "parent_title": "API Docs"    // Filter by parent document title
    },
    
    // Parent context
    "parent_filter": "string",      // Filter by parent document
    "include_siblings": true,       // Include sibling documents
    "include_ancestors": true,      // Include ancestor documents
    
    // Result formatting
    "show_breadcrumbs": true,       // Show document path
    "show_children_count": true,    // Show number of children
    "max_content_length": 300       // Limit content preview
  }
}
```

## 📊 Understanding Hierarchy Results

### Result Structure

Hierarchy search results include rich structural information:

```json
{
  "results": [
    {
      "document": {
        "title": "API Authentication",
        "content": "This document covers authentication methods...",
        "url": "https://wiki.company.com/api/auth",
        "similarity": 0.89
      },
      "hierarchy": {
        "depth": 2,
        "path": ["API Documentation", "Security", "Authentication"],
        "breadcrumbs": "API Documentation > Security > Authentication",
        "parent": {
          "title": "Security",
          "url": "https://wiki.company.com/api/security"
        },
        "children": [
          {
            "title": "JWT Tokens",
            "url": "https://wiki.company.com/api/auth/jwt"
          },
          {
            "title": "OAuth 2.0",
            "url": "https://wiki.company.com/api/auth/oauth"
          }
        ],
        "siblings": [
          {
            "title": "Authorization",
            "url": "https://wiki.company.com/api/authorization"
          },
          {
            "title": "Rate Limiting",
            "url": "https://wiki.company.com/api/rate-limiting"
          }
        ]
      }
    }
  ]
}
```

### Hierarchy Metadata

Each result includes hierarchy metadata:

- **Depth**: How deep in the hierarchy (0 = root)
- **Path**: Full path from root to document
- **Breadcrumbs**: Human-readable navigation path
- **Parent**: Direct parent document information
- **Children**: Direct child documents
- **Siblings**: Documents at the same level
- **Ancestors**: All parent documents up to root

## 🎯 Use Cases and Examples

### 1. Documentation Navigation

#### Finding Document Structure

```
Query: "Show me the structure of our API documentation"
Parameters: {
  "organize_by_hierarchy": true,
  "include_hierarchy": true,
  "depth": 4
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
│   ├── 📁 Data Operations
│   │   ├── 📄 Create Records
│   │   ├── 📄 Query Data
│   │   └── 📄 Bulk Operations
│   └── 📁 File Management
│       ├── 📄 Upload Files
│       └── 📄 Download Files
├── 📁 Security
│   ├── 📄 Authentication
│   ├── 📄 Authorization
│   └── 📄 Rate Limiting
└── 📁 Examples
    ├── 📄 Code Samples
    ├── 📄 Postman Collection
    └── 📄 SDK Usage
```

#### Finding Related Documents

```
Query: "authentication"
Parameters: {
  "include_siblings": true,
  "include_children": true
}

Results:
1. 📄 Authentication (api/security/authentication.md)
   Path: API Documentation > Security > Authentication
   
   Related Documents:
   Siblings:
   - Authorization (same level in Security)
   - Rate Limiting (same level in Security)
   
   Children:
   - JWT Tokens (authentication methods)
   - OAuth 2.0 (authentication methods)
   - API Keys (authentication methods)
   
   Parent Context:
   - Security (covers all security aspects)
```

### 2. Content Organization

#### Finding Where to Add New Content

```
Query: "Where should I add documentation about webhook security?"
Parameters: {
  "query": "webhook security",
  "include_hierarchy": true,
  "show_breadcrumbs": true
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

3. **Cross-Reference**: API Documentation > Examples > Webhook Security
   - Path: /api/examples/webhook-security/
   - For practical implementation examples
   - Links back to main security documentation

Recommendation: Create the main documentation under Security and add examples under the Examples section.
```

#### Checking Documentation Completeness

```
Query: "What sections are missing from our deployment documentation?"
Parameters: {
  "query": "deployment",
  "organize_by_hierarchy": true,
  "depth": 3
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
├── 📁 CI/CD
│   ├── 📄 GitHub Actions ✅
│   └── ❌ GitLab CI (MISSING)
└── ❌ Troubleshooting (MISSING SECTION)

Missing sections identified:
1. Kubernetes deployment guide
2. GitLab CI configuration
3. Entire troubleshooting section with common issues
4. Rollback procedures
5. Monitoring and alerting setup
```

### 3. Knowledge Discovery

#### Exploring Unfamiliar Areas

```
Query: "What do we have documented about microservices?"
Parameters: {
  "query": "microservices",
  "include_hierarchy": true,
  "organize_by_hierarchy": true
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

📁 Examples
└── 📁 Microservices Examples
    ├── 📄 User Service
    ├── 📄 Payment Service
    └── 📄 Notification Service
```

#### Understanding Document Relationships

```
Query: "How is our API documentation organized?"
Parameters: {
  "query": "API",
  "organize_by_hierarchy": true,
  "show_breadcrumbs": true,
  "include_children": true
}

AI Response:
Your API documentation follows a logical hierarchy:

1. **Top Level**: API Documentation (Root)
   - Breadcrumb: API Documentation
   - Children: 5 main sections

2. **Getting Started Section**
   - Breadcrumb: API Documentation > Getting Started
   - Purpose: Onboarding new developers
   - Children: Quick Start, Authentication Setup, First API Call

3. **Reference Section**
   - Breadcrumb: API Documentation > Reference
   - Purpose: Complete API specification
   - Children: Endpoints (by category), Data Models, Error Codes

4. **Security Section**
   - Breadcrumb: API Documentation > Security
   - Purpose: Security implementation
   - Children: Authentication, Authorization, Rate Limiting

5. **Examples Section**
   - Breadcrumb: API Documentation > Examples
   - Purpose: Practical implementation
   - Children: Code Samples, SDKs, Tutorials

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

#### Finding Leaf Documents

```json
{
  "query": "implementation",
  "hierarchy_filter": {
    "has_children": false
  }
}
```

Results: Only documents with no children (detailed implementation guides)

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

### 2. Parent-Child Navigation

#### Finding All Children

```json
{
  "parent_filter": "API Documentation",
  "include_children": true,
  "organize_by_hierarchy": true
}
```

Results: All documents under "API Documentation" organized by structure

#### Finding Siblings

```json
{
  "query": "authentication",
  "include_siblings": true
}
```

Results: Authentication document plus all documents at the same hierarchy level

### 3. Path-Based Search

#### Breadcrumb Navigation

```json
{
  "query": "deployment AWS",
  "show_breadcrumbs": true,
  "include_ancestors": true
}
```

Results include full navigation paths:

- Deployment > Cloud Providers > AWS > EC2 Deployment
- Deployment > Cloud Providers > AWS > Lambda Deployment

## 🎨 Hierarchy Visualization

### Tree Structure Display

When `organize_by_hierarchy: true`, results are displayed as a tree:

```
📁 Root Document
├── 📄 Child 1 (similarity: 0.89)
│   ├── 📄 Grandchild 1.1 (similarity: 0.85)
│   └── 📄 Grandchild 1.2 (similarity: 0.82)
├── 📄 Child 2 (similarity: 0.87)
│   └── 📄 Grandchild 2.1 (similarity: 0.79)
└── 📄 Child 3 (similarity: 0.84)
```

### Breadcrumb Navigation

When `show_breadcrumbs: true`, results include navigation paths:

```
Document: JWT Authentication
Path: API Documentation > Security > Authentication > JWT Authentication
Breadcrumb: API Docs > Security > Auth > JWT
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
  "depth": 4,
  "include_children": true,
  "show_breadcrumbs": true
}
```

#### For Quick Navigation

```json
{
  "limit": 5,
  "depth": 2,
  "include_siblings": true,
  "max_content_length": 200
}
```

#### For Completeness Checking

```json
{
  "organize_by_hierarchy": true,
  "include_children": true,
  "show_children_count": true,
  "depth": 10
}
```

### 3. Performance Optimization

#### Limit Hierarchy Depth

```json
{
  "depth": 3  // Prevent deep recursion
}
```

#### Control Result Size

```json
{
  "limit": 10,
  "max_content_length": 300
}
```

#### Cache Hierarchy Information

```json
{
  "cache_hierarchy": true,
  "cache_ttl": 3600
}
```

## 🎯 Best Practices

### 1. Query Design

- **Be specific about structure**: "Show me the organization of..." rather than just keywords
- **Use relationship terms**: "children", "parent", "siblings", "structure"
- **Ask navigation questions**: "Where should I add...", "What's under...", "How is ... organized?"

### 2. Parameter Selection

- **Use `organize_by_hierarchy: true`** for structure exploration
- **Include breadcrumbs** for navigation context
- **Limit depth** for performance with large hierarchies
- **Include siblings** for related content discovery

### 3. Result Interpretation

- **Follow breadcrumbs** to understand document context
- **Check hierarchy depth** to understand document importance
- **Review siblings** for related content
- **Examine children** for detailed information

### 4. Common Patterns

#### Documentation Audit

```json
{
  "query": "section overview",
  "organize_by_hierarchy": true,
  "include_children": true,
  "show_children_count": true
}
```

#### Content Planning

```json
{
  "query": "where to add new content",
  "include_hierarchy": true,
  "show_breadcrumbs": true,
  "include_siblings": true
}
```

#### Navigation Aid

```json
{
  "query": "find related documentation",
  "include_siblings": true,
  "include_children": true,
  "show_breadcrumbs": true
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
- [ ] **Include breadcrumbs** for navigation context
- [ ] **Check siblings and children** for related content
- [ ] **Optimize depth settings** for performance
- [ ] **Combine with other search tools** for comprehensive results

---

**Navigate your knowledge structure with confidence!** 🗺️

Hierarchy search transforms how you explore and understand your documentation. Instead of isolated search results, you get a complete picture of how information is organized, making it easier to find what you need and understand how it fits into the bigger picture.
