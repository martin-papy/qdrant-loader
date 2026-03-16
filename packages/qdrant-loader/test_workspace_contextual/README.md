# Test workspace: contextual embeddings

Use this workspace to run a full cmd-style test: **ingest** with `contextual_embedding.enabled: true`, then **retrieval** via the MCP server.

## Prerequisites

- **Qdrant** running (e.g. `docker run -p 6333:6333 qdrant/qdrant`)
- **OPENAI_API_KEY** set (embedding API)
- Python env with `qdrant-loader` and `qdrant-loader-mcp-server` installed (e.g. `pip install -e packages/qdrant-loader -e packages/qdrant-loader-mcp-server` from repo root), **or** a runner (e.g. UV) — see below.

## Quick run (PowerShell)

From repo root:

```powershell
cd packages\qdrant-loader\test_workspace_contextual
$env:OPENAI_API_KEY = "sk-..."   # your key
.\run_contextual_test.ps1
```

**Using UV** (when `python` / `qdrant-loader` are not on PATH): set a runner so the script invokes your tool instead of `python` / `qdrant-loader`. No UV or other tool names are hardcoded in the repo.

```powershell
# From repo root; script changes to repo root before running commands
$env:CONTEXTUAL_TEST_RUNNER = "uv run --project packages\qdrant-loader"
$env:CONTEXTUAL_TEST_MCP_RUNNER = "uv run --project packages\qdrant-loader-mcp-server"  # optional
$env:OPENAI_API_KEY = "sk-..."
.\run_contextual_test.ps1
```

This will:

1. **Init** the collection `contextual_test_collection` (drops if exists)
2. **Ingest** the single file `sample_data/sample_doc.txt` with contextual embedding **enabled** (chunks get prefix `[Document: sample_doc.txt | Source: localfile]` before embedding)
3. **Start the MCP server** on port 8080 for retrieval (Postman or Cursor)

## Manual steps (alternative)

```powershell
# 1) Set data path (forward slashes for file:// URL)
$env:CONTEXTUAL_TEST_DATA_DIR = (Resolve-Path .\sample_data).Path -replace '\\','/'

# 2) Init
qdrant-loader init --config .\config.yaml --force

# 3) Ingest
qdrant-loader ingest --config .\config.yaml --force

# 4) Start MCP (other terminal)
$env:QDRANT_COLLECTION_NAME = "contextual_test_collection"
mcp-qdrant-loader --transport http --port 8080
```

## Config

- **config.yaml**: `global.contextual_embedding.enabled: true`; one project with a localfile source pointing at `sample_data` via `CONTEXTUAL_TEST_DATA_DIR`.
- Collection name: `contextual_test_collection` (set `QDRANT_COLLECTION_NAME` when running MCP if you use a different name).

## Verifying

- After ingest, search via MCP (e.g. Postman) for something like “contextual embedding test”; you should get the chunk from `sample_doc.txt`. The vectors were built from text that includes the document title and source type in the prefix.
