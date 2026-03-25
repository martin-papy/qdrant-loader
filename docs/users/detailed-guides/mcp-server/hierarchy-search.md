# Hierarchy Search Guide

This guide covers the hierarchy search capabilities of the QDrant Loader MCP Server, enabling you to navigate and understand the structure of your knowledge base with AI assistance.

## <img src="../../../../../assets/icons/library/target-icon.svg" width="32" alt="Overview"> Overview

The hierarchy search tool is designed specifically for **Confluence documents** where document relationships and organization matter. It's particularly powerful for:

- **Confluence spaces** with parent-child page relationships
- **Confluence documentation** with hierarchical organization
- **Confluence knowledge bases** with nested structures

### Key Benefits

- **Structure Awareness**: Understands parent-child relationships between documents
- **Context Preservation**: Maintains hierarchical context in search results
- **Navigation Aid**: Helps explore and understand documentation organization
- **Completeness Checking**: Identifies gaps in documentation structure

## 🏗️ How Hierarchy Search Works

### Document Relationships

The hierarchy search tool understands document relationships in Confluence:

```text
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

```text
Query: "API documentation structure"
          ↓
1. Semantic Search (find relevant Confluence documents)
          ↓
2. Hierarchy Analysis (understand relationships)
          ↓
3. Context Enrichment (add parent/child info)
          ↓
4. Structured Results (organized by hierarchy)
```

## <img src="../../../../../assets/icons/library/wrench-icon.svg" width="32" alt="Search"> Hierarchy Search Parameters

> **Important**: Hierarchy search currently only works with **Confluence documents**. Other document types (Git repositories, local files, etc.) do not contain the hierarchical metadata required for this search type.

### Available Parameters

```json
{
  "name": "hierarchy_search",
  "parameters": {
    "query": "string",  // Required: Search query
    "limit": 10,  // Optional: Number of results (default: 10)
    "organize_by_hierarchy": false,  // Optional: Group results by structure (default: false)
    "hierarchy_filter": {  // Optional: Hierarchy-specific filters
      "depth": 3,  // Filter by specific hierarchy depth
      "has_children": true,  // Filter by whether pages have children
      "parent_title": "API Documentation",  // Filter by parent page title
      "root_only": false  // Show only root pages (no parent)
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

## <img src="../../../../../assets/icons/library/test-tube-icon.svg" width="32" alt="Result"> Understanding Hierarchy Results

### Result Structure

Hierarchy search results are returned as formatted text with hierarchical information:

```text
Found 3 results:

📄 API Authentication (Score: 0.890)
📍 Path: API Documentation > Security > Authentication
🏗️ Path: API Documentation > Security > Authentication | Depth: 2 | Children: 3
⬇️ Children: 3
This document covers authentication methods for our REST API including OAuth 2.0, JWT tokens, and API keys...
🔗 https://wiki.company.com/api/auth

📄 OAuth Implementation (Score: 0.850)
📍 Path: API Documentation > Security > Authentication > OAuth
🏗️ Path: API Documentation > Security > Authentication > OAuth | Depth: 3 | Children: 2
OAuth 2.0 implementation guide with code examples and best practices...
🔗 https://wiki.company.com/api/auth/oauth
```

### Hierarchy Metadata

Each result includes hierarchy metadata displayed with icons:

- **📍 Path**: Full breadcrumb path from root to document (Confluence only)
- **🏗️ Hierarchy Context**: Formatted hierarchy information with depth and children count
- **⬇️ Children**: Number of direct child documents (when > 0)
- **🔗 URL**: Link to the source document

## <img src="../../../../../assets/icons/library/target-icon.svg" width="32" alt="Examples"> Use Cases and Examples

### 1. Documentation Navigation

#### Finding Document Structure

```text
Query: "Show me the structure of our API documentation"
Parameters: {
  "organize_by_hierarchy": true,
  "limit": 15
}
Results:
Found 8 results organized by hierarchy:

📁 **API Documentation** (5 results)
📄 API Documentation (Score: 0.920)
   Complete API reference and developer guide...
   🔗 https://wiki.company.com/api

📄 Getting Started (Score: 0.890)
   Quick start guide for new API developers...
   🔗 https://wiki.company.com/api/getting-started

📄 Authentication (Score: 0.870)
   Authentication methods and security guidelines...
   🔗 https://wiki.company.com/api/authentication

📄 User Management API (Score: 0.850)
   User creation, update, and deletion endpoints...
   🔗 https://wiki.company.com/api/users

📄 Rate Limiting (Score: 0.830)
   API rate limiting policies and headers...
   🔗 https://wiki.company.com/api/limits

📁 **Security Guidelines** (3 results)
📄 OAuth 2.0 Implementation (Score: 0.810)
   OAuth 2.0 flow implementation with examples...
   🔗 https://wiki.company.com/security/oauth
```

#### Finding Related Documents

```text
Query: "authentication"
Parameters: {
  "limit": 10
}
Results:
Found 3 results:

📄 Authentication Guide (Score: 0.890)
📍 Path: API Documentation > Security > Authentication
🏗️ Path: API Documentation > Security > Authentication | Depth: 2 | Children: 3
⬇️ Children: 3
This comprehensive authentication guide covers multiple authentication methods including OAuth 2.0, JWT tokens, and API keys. Each method includes implementation examples and security best practices...
🔗 https://wiki.company.com/api/security/authentication

📄 OAuth 2.0 Implementation (Score: 0.850)
📍 Path: API Documentation > Security > Authentication > OAuth 2.0
🏗️ Path: API Documentation > Security > Authentication > OAuth 2.0 | Depth: 3 | Children: 0
OAuth 2.0 flow implementation with step-by-step examples for web applications and mobile apps...
🔗 https://wiki.company.com/api/security/authentication/oauth
```

### 2. Content Organization

#### Finding Where to Add New Content

```text
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

```text
Query: "deployment documentation structure"
Parameters: {
  "query": "deployment",
  "organize_by_hierarchy": true,
  "limit": 20
}
Results:
Found 6 results organized by hierarchy:

📁 **Deployment Documentation** (6 results)
📄 Deployment Overview (Score: 0.920)
   Complete deployment guide for all environments...
   🔗 https://wiki.company.com/deployment

📄 Development Environment (Score: 0.890)
   Development environment setup and configuration...
   🔗 https://wiki.company.com/deployment/dev

📄 Production Deployment (Score: 0.880)
   Production deployment procedures and checklists...
   🔗 https://wiki.company.com/deployment/prod

📄 AWS Deployment Guide (Score: 0.870)
   AWS-specific deployment configuration and steps...
   🔗 https://wiki.company.com/deployment/aws

📄 Docker Deployment (Score: 0.860)
   Container deployment with Docker and Docker Compose...
   🔗 https://wiki.company.com/deployment/docker

📄 CI/CD Pipeline (Score: 0.850)
   Continuous integration and deployment pipeline setup...
   🔗 https://wiki.company.com/deployment/cicd

**Note**: Use this structure to identify gaps by comparing with your requirements.
```

### 3. Knowledge Discovery

#### Exploring Unfamiliar Areas

```text
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

```text
Query: "How is our API documentation organized?"
Parameters: {
  "query": "API documentation",
  "organize_by_hierarchy": true,
  "limit": 15
}
Results:
Found 8 results organized by hierarchy:

📁 **API Documentation** (8 results)
📄 API Documentation (Score: 0.950)
   Complete API reference and developer guide for our REST API...
   🔗 https://wiki.company.com/api

📄 Getting Started (Score: 0.920)
   Quick start guide for new API developers with examples...
   🔗 https://wiki.company.com/api/getting-started

📄 Authentication Setup (Score: 0.890)
   Authentication configuration and initial setup steps...
   🔗 https://wiki.company.com/api/getting-started/auth

📄 API Reference (Score: 0.910)
   Complete endpoint reference with parameters and responses...
   🔗 https://wiki.company.com/api/reference

📄 User Endpoints (Score: 0.880)
   User management API endpoints and data models...
   🔗 https://wiki.company.com/api/reference/users

📄 Security Guidelines (Score: 0.900)
   Security best practices and implementation guidelines...
   🔗 https://wiki.company.com/api/security

📄 Rate Limiting (Score: 0.870)
   API rate limiting policies and headers...
   🔗 https://wiki.company.com/api/security/rate-limits

📄 Error Handling (Score: 0.860)
   Error codes, messages, and handling best practices...
   🔗 https://wiki.company.com/api/errors
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

When `organize_by_hierarchy: true`, results are displayed grouped by root documents:

```text
Found 6 results organized by hierarchy:

📁 **API Documentation** (4 results)
📄 API Documentation (Score: 0.890)
   Complete guide to our REST API with authentication, endpoints, and examples...
   🔗 https://wiki.company.com/api

📄 Authentication Guide (Score: 0.850)
   Authentication methods including OAuth 2.0, JWT tokens, and API keys...
   🔗 https://wiki.company.com/api/auth

📄 OAuth Implementation (Score: 0.820)
   OAuth 2.0 implementation guide with code examples...
   🔗 https://wiki.company.com/api/auth/oauth

📄 Rate Limiting (Score: 0.800)
   API rate limiting policies and implementation details...
   🔗 https://wiki.company.com/api/limits

📁 **Developer Tools** (2 results)
📄 SDK Documentation (Score: 0.780)
   Software development kits for multiple programming languages...
   🔗 https://wiki.company.com/sdk
```

### Breadcrumb Navigation

Results include navigation paths:

```text
Document: JWT Authentication
Path: API Documentation > Security > Authentication > JWT Authentication
```

### Relationship Indicators

Results show document relationships through breadcrumb paths and hierarchy context:

```text
📄 API Rate Limiting (Score: 0.880)
📍 Path: API Documentation > Security > API Rate Limiting
🏗️ Path: API Documentation > Security > API Rate Limiting | Depth: 2 | Children: 2
⬇️ Children: 2
API rate limiting policies and implementation guidelines for preventing abuse...
🔗 https://wiki.company.com/api/security/rate-limiting
```

## 🔧 Optimization Strategies

### 1. Query Optimization

#### Structure-Focused Queries

```text
✅ "Show me the structure of deployment documentation"
✅ "What are all the sections under API security?"
✅ "Find all child pages of the troubleshooting guide"

❌ "deployment"
❌ "security"
❌ "troubleshooting"
```

#### Relationship Queries

```text
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

## <img src="../../../../../assets/icons/library/target-icon.svg" width="32" alt="Best Practice"> Best Practices

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

```text
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

## <img src="../../../../../assets/icons/library/note-icon.svg" width="32" alt="Checklist"> Hierarchy Search Checklist

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
