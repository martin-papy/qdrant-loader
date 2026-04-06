# Installation Guide

Quick Start is now the primary setup flow.

Use this page only for platform-specific notes, dependency choices, and install troubleshooting.

Primary onboarding path: [quick-start.md](./quick-start.md)

## Package options

- Data ingestion only:

```bash
pip install qdrant-loader
```

- MCP server only:

```bash
pip install qdrant-loader-mcp-server
```

- Full experience (recommended):

```bash
pip install qdrant-loader qdrant-loader-mcp-server
```

## Optional LLM extras

When installing from source or customizing environments, ensure provider dependencies are available.

- OpenAI/Azure/OpenAI-compatible:

```bash
pip install "qdrant-loader-core[openai]"
```

- Ollama:

```bash
pip install "qdrant-loader-core[ollama]"
```

## Platform notes

### Windows

Use PowerShell or Command Prompt with Python 3.12+ and verify Scripts path is available.

```powershell
qdrant-loader --version
mcp-qdrant-loader --version
```

### macOS and Linux

Use virtual environments if system Python is managed.

```bash
python -m venv .venv
source .venv/bin/activate
pip install qdrant-loader qdrant-loader-mcp-server
```

## Verification checklist

- `qdrant-loader --version` works
- `mcp-qdrant-loader --version` works
- QDrant is reachable at configured URL
- LLM API key is set

Then continue with [quick-start.md](./quick-start.md).
