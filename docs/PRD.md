# 🧠 Product Definition Requirements (PDR)

## 📌 Product Name

RAG Developer Context Ingestion System

## 🎯 Goal

To build a backend tool that collects and vectorizes technical content from multiple sources—Confluence, Jira, Git repositories, and public documentation—and stores it in a qDrant vector database. This vector DB will be queried via `mcp-server-qdrant` by the AI Agent in the Cursor IDE, enabling developers to receive highly contextual and accurate assistance.

---

## 👤 Target Persona

| Persona     | Description |
|-------------|-------------|
| **Developer** | Writes code in Cursor IDE and expects the integrated AI agent to suggest code and solutions based on real internal documentation and current tech stack usage. |
| **Operator** | A designated team member (DevRel/Infra/Staff Eng) responsible for manually triggering ingestion and keeping the vector DB updated. |

---

## 🧭 User Interaction Model

| User Type   | Interaction Method                      | Description |
|-------------|------------------------------------------|-------------|
| Developer   | Indirect (via MCP Agent inside Cursor IDE using `mcp-server-qdrant`) | No direct access to the ingestion system or DB |
| Operator    | Manual CLI/script trigger                | Runs ingestion pipeline locally, pushes to qDrant Cloud |

---

## 📥 Ingestion Scope

| Source         | Scope Criteria                        | Included Content |
|----------------|----------------------------------------|------------------|
| **Confluence** | Selected Spaces                        | All available pages, attachments, technical diagrams |
| **Jira**       | Selected Projects                      | All tickets (open/closed), including description, comments, labels |
| **Git Repos**  | Selected Repos                         | `README.md`, `/docs/`, code comments, design guides |
| **Public Docs**| Curated list of 3rd-party tools/frameworks | Documentation for APIs, libraries, and SDKs |

---

## 🔄 Ingestion Frequency

| Source         | Mode       | Trigger     |
|----------------|------------|-------------|
| All Sources    | Manual     | CLI or script executed by operator |

---

## 📦 Chunking & Preprocessing Strategy

| Step                  | Approach |
|------------------------|----------|
| **Chunking**           | Token-based chunks (e.g. 500–800 tokens with overlap) |
| **Metadata**           | Attach metadata: `source`, `source_type`, `url`, `last_updated`, `project`, `author` |
| **Cleaning**           | Strip HTML/Markdown tags, remove boilerplate, handle code blocks separately |
| **Normalization**      | Markdown unification, semantic title/tag boosting |

---

## 🔐 Security & Access Control

| Component            | Control Mechanism |
|----------------------|-------------------|
| Confluence Access    | API Key / Service Account |
| Jira Access          | API Key / Service Account |
| Git Repos            | SSH or Access Tokens |
| Public Docs          | Unauthenticated or scraping proxy (if needed) |
| qDrant Access        | API Key (Cloud-hosted endpoint) |
| Operator Restriction | Only specific user(s) allowed to trigger ingestion |
| Logging              | Logs timestamp, sources, # of documents, and errors per run |

---

## 🔁 Update & Deduplication Strategy

| Concern             | Strategy |
|---------------------|----------|
| **Deduplication**   | Overwrite previous entries for each unique document/source |
| **Versioning**      | Not retained (latest version only for clarity and performance) |
| **Entry IDs**       | Use deterministic IDs (`source-type::path/url`) for easy replacement |

---

## ⚙️ Technology Stack

| Component           | Tech/Tool                      | Notes |
|---------------------|-------------------------------|-------|
| Language            | Python                         | Core engine for pipeline |
| Vector DB           | qDrant (Cloud-hosted)          | Queried via MCP Server |
| Pipeline Execution  | Local CLI / Script             | Manual run by operator |
| Connectors          | `atlassian-python-api`, `jira`, `gitpython`, `beautifulsoup4`, `requests` ||
| Embedding Models    | OpenAI or HuggingFace models   | Configurable as needed |
| Vector Server Layer | `mcp-server-qdrant`            | Already integrated with Cursor |

---

## 📊 Success Metrics (KPI)

| Metric                         | Desired Outcome |
|--------------------------------|-----------------|
| **AI Error Reduction**         | Fewer hallucinations and incorrect code suggestions |
| **Code Quality**               | AI respects internal conventions and architecture |
| **Library Usage Awareness**    | AI correctly suggests usage of approved 3rd-party tools and frameworks |
| **Developer Satisfaction**     | Qualitative improvements noted in feedback loops |

---

## 🛠️ Future Enhancements (Out of Scope for MVP)

- Scheduled/automatic syncing (e.g. via Airflow or GitHub Actions)
- Web UI for ingestion monitoring
- Versioning or content diffing
- Multi-tenant qDrant namespacing
- Document summarization during ingest
- Priority weighting / reranking by document type

---

## 📝 Summary

This RAG ingestion tool is an internal backend pipeline designed to fuel developer productivity through high-context AI completions in Cursor. By enriching qDrant with relevant, real-time content from multiple sources and maintaining a high standard of preprocessing and metadata, we empower the MCP Agent to assist with more accurate, context-aware code generation.
