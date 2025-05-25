# 🧠 Product Requirements Document (PRD)

## 📌 Product Name

QDrant Loader Monorepo - RAG Developer Context System

## 🎯 Goal

To build a comprehensive RAG (Retrieval-Augmented Generation) ecosystem that collects, processes, and serves technical content from multiple sources through a unified monorepo. The system consists of two main components:

1. **QDrant Loader**: Backend ingestion tool that vectorizes content from Confluence, Jira, Git repositories, public documentation, and local files
2. **MCP Server**: Model Context Protocol server that provides AI development tools (Cursor, Windsurf, etc.) with contextual, accurate assistance through semantic search

---

## 👤 Target Personas

| Persona | Description | Primary Interaction |
|---------|-------------|-------------------|
| **Developer** | Writes code in AI-powered IDEs and expects contextual assistance based on internal documentation and current tech stack | Indirect via MCP integration in Cursor/Windsurf |
| **DevOps Engineer** | Manages infrastructure and deployment pipelines, needs access to operational documentation | Direct CLI usage + MCP integration |
| **Technical Writer** | Creates and maintains documentation, needs to understand content coverage and gaps | CLI tools for analysis and validation |
| **Team Lead** | Oversees development processes and ensures knowledge sharing | Dashboard and reporting tools |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QDrant Loader Monorepo                  │
├─────────────────────────────────────────────────────────────┤
│  📦 qdrant-loader              │  🔌 qdrant-loader-mcp-server │
│  ├── Data Ingestion            │  ├── MCP Protocol            │
│  ├── Document Processing       │  ├── Semantic Search         │
│  ├── Vector Embedding          │  ├── Query Processing        │
│  ├── State Management          │  └── API Endpoints           │
│  └── CLI Interface             │                              │
├─────────────────────────────────────────────────────────────┤
│                    Shared Infrastructure                    │
│  ├── QDrant Vector Database    │  ├── Configuration System    │
│  ├── Embedding Models          │  ├── Logging & Monitoring    │
│  └── State Database (SQLite)   │  └── Testing Framework       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧭 User Interaction Models

| User Type | Tool | Interaction Method | Use Cases |
|-----------|------|-------------------|-----------|
| **Developer** | Cursor/Windsurf | MCP Protocol | Code assistance, documentation lookup, API reference |
| **Developer** | CLI | Direct commands | Data ingestion, status monitoring, troubleshooting |
| **DevOps** | CLI + Scripts | Automated pipelines | Scheduled ingestion, monitoring, maintenance |
| **Technical Writer** | CLI + API | Analysis tools | Content coverage analysis, gap identification |

---

## 📥 Data Sources & Ingestion Scope

### Supported Connectors

| Source | Scope Criteria | Included Content | Key Features |
|--------|----------------|------------------|--------------|
| **Git Repositories** | Selected repos/branches | README, docs/, code comments, design docs | Branch filtering, file type selection, commit metadata |
| **Confluence** | Selected spaces | Pages, attachments, comments, diagrams | Label-based filtering, version tracking, rich content |
| **Jira** | Selected projects | Tickets, descriptions, comments, attachments | Status filtering, incremental sync, relationship tracking |
| **Public Documentation** | Curated URLs | API docs, framework guides, tutorials | CSS selector extraction, version detection |
| **Local Files** | Selected directories | Markdown, code, docs, configuration files | Glob pattern matching, file type filtering |

### Advanced Processing Features

| Feature | Description | Benefits |
|---------|-------------|----------|
| **Intelligent Chunking** | Token-based chunking with semantic boundaries | Optimal context preservation |
| **Metadata Extraction** | Rich metadata including authors, dates, relationships | Enhanced search relevance |
| **Change Detection** | Incremental updates with state tracking | Efficient resource usage |
| **Content Cleaning** | HTML/Markdown normalization, code block preservation | Consistent content quality |
| **Batch Processing** | Optimized batch embedding with rate limiting | Scalable performance |

---

## 🔄 Ingestion & Update Strategy

### Ingestion Modes

| Mode | Trigger | Frequency | Use Case |
|------|---------|-----------|----------|
| **Manual** | CLI command | On-demand | Initial setup, troubleshooting |
| **Incremental** | CLI with state tracking | Regular intervals | Efficient updates |
| **Selective** | Source-specific commands | As needed | Targeted updates |
| **Automated** | CI/CD integration | Scheduled | Production maintenance |

### State Management

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Document State** | SQLite database | Track ingestion status, changes |
| **Ingestion History** | SQLite tables | Audit trail, rollback capability |
| **Change Detection** | File hashes, timestamps | Efficient incremental updates |
| **Error Recovery** | Retry mechanisms | Robust operation |

---

## 📦 Chunking & Processing Strategy

### Document Processing Pipeline

```
Raw Content → Cleaning → Chunking → Metadata → Embedding → Storage
     ↓            ↓         ↓          ↓          ↓         ↓
  HTML/MD     Normalize   Token     Extract    Vector    QDrant
  Parsing     Content     Based     Metadata   Generate  Database
```

### Chunking Configuration

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| **Chunk Size** | 500 tokens | 100-2000 | Balance context vs. precision |
| **Overlap** | 50 tokens | 0-200 | Maintain context continuity |
| **Batch Size** | 100 chunks | 10-500 | Optimize embedding performance |

### Metadata Schema

```yaml
document_metadata:
  core:
    - id: unique_identifier
    - title: document_title
    - source: source_identifier
    - source_type: [git, confluence, jira, publicdocs, localfile]
    - url: original_url
    - created_at: timestamp
    - updated_at: timestamp
  source_specific:
    git:
      - repository_url
      - branch
      - file_path
      - last_commit_author
      - last_commit_date
    confluence:
      - space_key
      - page_id
      - author
      - labels
      - comments
    jira:
      - project_key
      - issue_type
      - status
      - assignee
      - priority
```

---

## 🔐 Security & Access Control

### Authentication & Authorization

| Component | Method | Scope |
|-----------|--------|-------|
| **Confluence** | API Token + Email | Space-level access |
| **Jira** | API Token + Email | Project-level access |
| **Git Repositories** | Personal Access Token | Repository access |
| **QDrant** | API Key | Database access |
| **MCP Server** | Environment variables | Server configuration |

### Security Best Practices

| Practice | Implementation |
|----------|----------------|
| **Credential Management** | Environment variables, no hardcoding |
| **Access Logging** | Comprehensive audit trails |
| **Rate Limiting** | API call throttling |
| **Data Encryption** | TLS for all communications |
| **Minimal Permissions** | Least privilege access |

---

## 🔁 Update & Deduplication Strategy

### Content Management

| Strategy | Implementation | Benefits |
|----------|----------------|----------|
| **Deduplication** | Deterministic document IDs | Prevent duplicates |
| **Versioning** | Latest version only | Simplified management |
| **Incremental Updates** | Change detection + state tracking | Efficient processing |
| **Cleanup** | Automated removal of deleted content | Data consistency |

### Document ID Strategy

```
Document ID Format: {source_type}::{source}::{path/identifier}

Examples:
- git::my-repo::docs/api.md
- confluence::tech-space::123456
- jira::backend-project::PROJ-123
- publicdocs::api-docs::authentication
- localfile::project-docs::README.md
```

---

## ⚙️ Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Language** | Python | 3.12+ | Core implementation |
| **Vector DB** | QDrant | Latest | Vector storage & search |
| **Embeddings** | OpenAI / Local models | Various | Text vectorization |
| **State DB** | SQLite | 3.x | State management |
| **Protocol** | MCP | 2024-11-05 | AI tool integration |

### Dependencies

| Category | Libraries | Purpose |
|----------|-----------|---------|
| **Web APIs** | `requests`, `aiohttp` | HTTP client operations |
| **Atlassian** | `atlassian-python-api` | Confluence/Jira integration |
| **Git** | `gitpython` | Repository operations |
| **Parsing** | `beautifulsoup4`, `markdownify` | Content extraction |
| **Database** | `sqlalchemy`, `sqlite3` | State management |
| **ML/AI** | `openai`, `sentence-transformers` | Embeddings |
| **CLI** | `click`, `rich` | Command-line interface |

---

## 🔌 MCP Server Capabilities

### Protocol Implementation

| Feature | Status | Description |
|---------|--------|-------------|
| **Initialize** | ✅ Complete | Server initialization and capability negotiation |
| **Tools** | ✅ Complete | Search tool with advanced parameters |
| **Resources** | ✅ Complete | Document and source listing |
| **Prompts** | 🔄 Planned | Pre-defined query templates |
| **Logging** | 🔄 Planned | Request/response logging |

### Search Capabilities

| Feature | Description | Parameters |
|---------|-------------|------------|
| **Semantic Search** | Vector-based similarity search | `query`, `limit`, `threshold` |
| **Source Filtering** | Filter by source type or specific source | `source_types`, `sources` |
| **Metadata Filtering** | Filter by document metadata | `filters` object |
| **Hybrid Search** | Combine semantic + keyword search | `enable_hybrid` |
| **Result Ranking** | Relevance-based result ordering | `ranking_algorithm` |

---

## 📊 Success Metrics (KPIs)

### Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Ingestion Speed** | >1000 docs/minute | Documents processed per minute |
| **Search Latency** | <200ms | Average query response time |
| **Search Accuracy** | >85% relevance | User feedback on result quality |
| **System Uptime** | >99.5% | MCP server availability |
| **Storage Efficiency** | <10MB per 1000 docs | Vector database size optimization |

### User Experience Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **AI Accuracy** | Fewer hallucinations | Reduced incorrect suggestions |
| **Context Relevance** | >90% relevant results | User satisfaction surveys |
| **Developer Productivity** | 20% faster development | Time-to-completion metrics |
| **Knowledge Discovery** | Increased documentation usage | Search query analytics |

### Operational Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Error Rate** | <1% failed operations | Error tracking and alerting |
| **Resource Usage** | <4GB RAM, <50% CPU | System monitoring |
| **Data Freshness** | <24h lag | Time between source update and availability |

---

## 🛠️ Future Enhancements

### Short-term (Next 3 months)

- [ ] **Web UI**: Dashboard for ingestion monitoring and analytics
- [ ] **Advanced Caching**: Intelligent query result caching
- [ ] **Batch Operations**: Bulk document operations and management
- [ ] **Enhanced Filtering**: Advanced search filters and facets

### Medium-term (3-6 months)

- [ ] **Scheduled Ingestion**: Automated ingestion with cron-like scheduling
- [ ] **Multi-tenant Support**: Namespace isolation for different teams
- [ ] **Document Summarization**: AI-powered content summarization
- [ ] **Analytics Dashboard**: Usage analytics and insights

### Long-term (6+ months)

- [ ] **Distributed Processing**: Scale ingestion across multiple workers
- [ ] **Advanced AI Features**: Query expansion, intent recognition
- [ ] **Integration Ecosystem**: Plugins for additional tools and platforms
- [ ] **Enterprise Features**: SSO, advanced security, compliance

---

## 🎯 Success Criteria

### MVP Success (Current State)

- ✅ **Multi-source Ingestion**: All 5 connectors working reliably
- ✅ **MCP Integration**: Full Cursor/Windsurf compatibility
- ✅ **State Management**: Incremental updates and change detection
- ✅ **Documentation**: Comprehensive setup and usage guides
- ✅ **Testing**: >80% test coverage across both packages

### Production Ready

- [ ] **Performance**: Handle 100K+ documents efficiently
- [ ] **Reliability**: 99.9% uptime with error recovery
- [ ] **Scalability**: Support multiple concurrent users
- [ ] **Monitoring**: Comprehensive observability and alerting
- [ ] **Security**: Production-grade security controls

---

## 📝 Summary

The QDrant Loader Monorepo represents a complete RAG ecosystem designed to enhance developer productivity through AI-powered tools. By combining robust data ingestion capabilities with a standards-compliant MCP server, the system provides developers with contextual, accurate assistance based on their organization's actual documentation and codebase.

The monorepo structure enables coordinated development of both components while maintaining clear separation of concerns. The comprehensive connector ecosystem, intelligent processing pipeline, and flexible deployment options make it suitable for organizations of all sizes looking to implement AI-enhanced development workflows.

Key differentiators include:

- **Unified ecosystem** with coordinated releases and shared infrastructure
- **Production-ready** state management and incremental processing
- **Standards compliance** with MCP protocol for broad tool compatibility
- **Extensible architecture** supporting custom connectors and integrations
- **Comprehensive documentation** and testing for reliable operation
