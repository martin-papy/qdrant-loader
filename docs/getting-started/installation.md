# Installation Guide

Quick Start is now the primary setup flow.

Use this page only for platform-specific notes, dependency choices, and install troubleshooting.

Primary onboarding path: [quick-start.md](./quick-start.md)

## Package options

The core library is automatically installed as a dependency. Most users will want both the main package and MCP server for the complete experience.

## 🔧 Prerequisites

### System Requirements

| Component   | Minimum                          | Recommended     |
| ----------- | -------------------------------- | --------------- |
| **Python**  | 3.12+                            | 3.12+           |
| **Memory**  | 4GB RAM                          | 8GB+ RAM        |
| **Storage** | 2GB free                         | 10GB+ free      |
| **OS**      | Windows 10+, macOS 10.15+, Linux | Latest versions |

### Required Services

#### QDrant Vector Database

QDrant Loader requires a QDrant instance to store vectors and metadata.

##### Option 1: Docker

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

## Development environment (recommended)

Use this short workflow:

- Dev adds a new library: `uv add <package>`
- Pull latest code: `uv sync`
- CI/Prod: `uv sync --frozen`

Setup commands:

```bash
# Initial workspace setup
uv sync --all-packages --all-extras

# Verify installation
uv run qdrant-loader --version
uv run mcp-qdrant-loader --version
```

When you need a new dependency during development:

```bash
uv add fastapi
uv sync
```

## Virtual environment note

With uv, you normally do not need to manually create or activate a virtual environment.
`uv sync` manages the project environment automatically.

Create and activate your own venv only if your team or tooling explicitly requires manual venv control.

### Method 3: Virtual Environment (Isolated)

For users who want to keep QDrant Loader isolated:

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
