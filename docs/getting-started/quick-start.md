# Quick Start Guide

This is the canonical onboarding path for QDrant Loader.

## What you will do

In one flow, you will:

- Install the packages
- Start QDrant
- Create a workspace
- Ingest your first content
- Connect AI tools through MCP

Estimated time: 10 to 15 minutes.

## Prerequisites

- Python 3.12+
- Docker (or an existing QDrant instance)
- One LLM provider key (OpenAI, Azure OpenAI, Ollama, or OpenAI-compatible)

## Step 1. Install packages

```bash
pip install qdrant-loader qdrant-loader-mcp-server
```

Verify:

```bash
qdrant-loader --version
mcp-qdrant-loader --version
```

If you need OS-specific install help, see [installation.md](./installation.md).

## Step 2. Start QDrant

Local Docker option:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Or use QDrant Cloud and copy URL/API key.

## Step 3. Create workspace

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

## Step 4. Configure environment

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

- LLM provider setup: [../users/configuration/llm-provider-guide.md](../users/configuration/llm-provider-guide.md)
- Environment variables: [../users/configuration/environment-variables.md](../users/configuration/environment-variables.md)

## Step 5. Add a minimal config and ingest

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
```

## Step 6. Start MCP server

```bash
mcp-qdrant-loader
```

Detailed integration guides:

- [../users/detailed-guides/mcp-server/setup-and-integration.md](../users/detailed-guides/mcp-server/setup-and-integration.md)
- [../users/detailed-guides/mcp-server/search-capabilities.md](../users/detailed-guides/mcp-server/search-capabilities.md)

## Step 7. Validate in your AI tool

In Cursor/Claude/Windsurf, run a query like:

"Search my docs for QDrant Loader quick start notes"

If results are returned from ingested content, setup is complete.

## Next steps

- Configuration deep dive: [../users/configuration/config-file-reference.md](../users/configuration/config-file-reference.md)
- Data sources: [../users/detailed-guides/data-sources/README.md](../users/detailed-guides/data-sources/README.md)
- Troubleshooting: [../users/troubleshooting/README.md](../users/troubleshooting/README.md)
