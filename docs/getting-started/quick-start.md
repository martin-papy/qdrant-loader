# Quick Start Guide

Get up and running with QDrant Loader in 5 minutes! This guide walks you through your first document ingestion and AI tool integration.

## <img src="../../../assets/icons/library/target-icon.svg" width="32" alt="What You'll Accomplish"> What You'll Accomplish

In one flow, you will:

- Install the packages
- Start QDrant
- Create a workspace
- Ingest your first content
- Connect AI tools through MCP

Estimated time: 10 to 15 minutes.

## <img src="../../../assets/icons/library/wrench-icon.svg" width="32" alt="Prerequisites"> Prerequisites

- Python 3.12+
- Docker (or an existing QDrant instance)
- One LLM provider key (OpenAI, Azure OpenAI, Ollama, or OpenAI-compatible)

## <img src="../../../assets/icons/library/rocket-icon.svg" width="32" alt="Install packages"> Step 1. Install packages

```bash
pip install qdrant-loader qdrant-loader-mcp-server
```

Verify:

```bash
qdrant-loader --version
mcp-qdrant-loader --version
```

If you need OS-specific install help, see [Installation Guide](./installation.md).

## <img src="../../../assets/icons/library/file-icon.svg" width="32" alt="Start QDrant"> Step 2. Start QDrant

Local Docker option:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Or use QDrant Cloud and copy URL/API key.

## <img src="../../../assets/icons/library/robot-icon.svg" width="32" alt="Create workspace"> Step 3. Create workspace

Recommended (wizard):

```bash
qdrant-loader setup --output-dir my-qdrant-workspace --mode default
cd my-qdrant-workspace
```

Alternative (manual):

```bash
mkdir my-qdrant-workspace
cd my-qdrant-workspace
qdrant-loader init --workspace .
```

Need more control over prompts and templates? See [CLI setup command options](../users/cli-reference/commands.md).

## <img src="../../../assets/icons/library/wrench-icon.svg" width="32" alt="Configure environment"> Step 4. Configure environment

Create or edit `.env`:

```bash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=quickstart

LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-openai-key
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini
```

Canonical configuration references:

- [LLM Provider Guide](../users/configuration/llm-provider-guide.md) - Pick the right provider profile and copy a known-good `.env` template.
- [Environment Variables Reference](../users/configuration/environment-variables.md) - Validate required keys fast and avoid common startup/auth errors.

## <img src="../../../assets/icons/library/file-icon.svg" width="32" alt="Add minimal config"> Step 5. Add a minimal config and ingest

Create `config.yaml`:

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "${LLM_PROVIDER}"
    base_url: "${LLM_BASE_URL}"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "${LLM_EMBEDDING_MODEL}"
      chat: "${LLM_CHAT_MODEL}"
    embeddings:
      vector_size: 1536

projects:
  quickstart:
    project_id: "quickstart"
    display_name: "Quick Start"
    sources:
      localfile:
        docs:
          base_url: "file://./docs"
          include_paths: ["**/*.md"]
```

Create sample content and ingest:

```bash
mkdir docs
printf "# Hello QDrant Loader\n\nThis is my first document.\n" > docs/sample.md
qdrant-loader ingest --workspace .
# Expected output:
# 📁 Scanning directory: my-project/
# 📄 Processing: 2 files found
# ✅ Ingested: 2 documents, multiple chunks
# 🔍 Collection: quickstart
```

For Git/Confluence/Jira and advanced source filters, see [Data Sources Guide](../users/detailed-guides/data-sources/).

## <img src="../../../assets/icons/library/book-icon.svg" width="32" alt="Start MCP server"> Step 6. Start MCP server

```bash
mcp-qdrant-loader
# Expected output:
# 🚀 QDrant Loader MCP Server starting...
# 📡 Server running on stdio
# 🔍 Available tools: search, hierarchy_search, attachment_search
# ✅ Ready for connections
```

Detailed integration guides:

- **[Setup and Integration Guide](../users/detailed-guides/mcp-server/setup-and-integration.md)** - Connect MCP in Cursor, Claude Desktop, and other clients step by step.
- **[Search Capabilities Guide](../users/detailed-guides/mcp-server/search-capabilities.md)** - Learn each search tool, parameters, and practical query patterns.

## <img src="../../../assets/icons/library/search-icon.svg" width="32" alt="Validate"> Step 7. Validate in your AI tool

In Cursor/Claude/Windsurf, run a query like:

"Search my docs for QDrant Loader quick start notes"

If results are returned from ingested content, setup is complete.

## <img src="../../../assets/icons/library/target-icon.svg" width="32" alt="Next steps"> Next steps

- [Configuration Reference](../users/configuration/config-file-reference.md) - Tune chunking, embeddings, and project-level behavior for production use.
- [Data Sources Guide](../users/detailed-guides/data-sources/) - Expand beyond local files with Git, Confluence, Jira, and public docs.
- [Troubleshooting Guide](../users/troubleshooting/) - Diagnose ingestion/search issues quickly with practical fix paths.

## <img src="../../../assets/icons/library/test-tube-icon.svg" width="32" alt="Completion checklist"> Quick Success Checklist

- [ ] `qdrant-loader --version` and `mcp-qdrant-loader --version` return successfully
- [ ] `qdrant-loader ingest --workspace .` finishes without errors
- [ ] MCP server starts with `mcp-qdrant-loader`
- [ ] Your AI tool returns results from ingested documents

---

**🎉 Quick Start Complete!**

You're now ready to explore the full power of QDrant Loader. The next step is reviewing the Core Concepts summarized in Getting Started, or dive into the [User Guides](../users/) for specific features and workflows.
