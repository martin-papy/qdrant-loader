# Installation Guide

This guide walks you through installing QDrant Loader and its MCP server on your system. Choose the installation method that best fits your needs.

Use this page only for platform-specific notes, dependency choices, and install troubleshooting.

Primary onboarding path: [Quick Start](./quick-start.md)

## 📋 Overview

- **`qdrant-loader`** - Main data ingestion and processing tool
- **`qdrant-loader-core`** - Shared core library with LLM abstraction (automatically installed as dependency)
- **`qdrant-loader-mcp-server`** - Model Context Protocol server for AI tool integration

The core library is automatically installed as a dependency. Most users will want both the main package and MCP server for the complete experience.

## 🚀 Package options

- Main package only:

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
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

##### Option 2: QDrant Cloud

Use QDrant Cloud and copy your cluster URL + API key into `.env`.

##### Option 3: Local Installation

Use the official QDrant installation guide for your platform.

## 🤖 Optional LLM extras

When installing from source or customizing environments, ensure provider dependencies are available.

- OpenAI/Azure/OpenAI-compatible:

```bash
pip install "qdrant-loader-core[openai]"
```

- Ollama:

```bash
pip install "qdrant-loader-core[ollama]"
```

## 🔄 Development environment (recommended)

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

## 🧠 Virtual environment note

With uv, you normally do not need to manually create or activate a virtual environment.
`uv sync` manages the project environment automatically.

Create and activate your own venv only if your team or tooling explicitly requires manual venv control.

## 📖 Platform-specific notes

- **Windows**: Use PowerShell and activate venv with `\.venv\Scripts\Activate.ps1`.
- **macOS/Linux**: Activate venv with `source .venv/bin/activate`.
- **Permissions**: If global pip install fails, prefer uv workflow or a project virtual environment.

For command-level options (`--workspace`, `--config`, `--env`), see [CLI Commands](../users/cli-reference/commands.md).

### Method 3: Virtual Environment (Isolated)

For users who want to keep QDrant Loader isolated:

```bash
python -m venv .venv
source .venv/bin/activate
pip install qdrant-loader qdrant-loader-mcp-server
```

## 📝 Installation Checklist

- [ ] **Python 3.12+** installed and accessible
- [ ] **QDrant database** running (Docker, Cloud, or local)
- [ ] **LLM API key** obtained and configured (OpenAI, Azure OpenAI, Ollama, or compatible)
- [ ] **qdrant-loader** package installed
- [ ] **qdrant-loader-mcp-server** package installed (if using MCP)
- [ ] `qdrant-loader --version` works
- [ ] `mcp-qdrant-loader --version` works (if MCP server installed)
- [ ] **Basic configuration** created
- [ ] **QDrant connection** tested
- [ ] You can run `qdrant-loader init --workspace .` without configuration errors
- [ ] **Ready for Quick Start** guide

## 📝 Verification checklist

- [ ] `qdrant-loader --version` works
- [ ] `mcp-qdrant-loader --version` works
- [ ] QDrant is reachable at configured URL
- [ ] LLM API key is set

Then continue with [Quick Start](./quick-start.md).

## 🔧 Install troubleshooting

- Python and dependency setup issues: [Troubleshooting](../users/troubleshooting)
- Configuration and environment variable errors: [Error Messages Reference](../users/troubleshooting/error-messages-reference.md)
- Complete configuration options: [Configuration File Reference](../users/configuration/config-file-reference.md)

## 🔗 Next Steps

After successful installation:

1. **[Quick Start Guide](./quick-start.md)** - Get up and running in 5 minutes
2. **[Core Concepts](./README.md#-core-concepts)** - Key concepts explained
3. **[Basic Configuration](./basic-configuration.md)** - Set up your first data sources
4. **[User Guides](../users/)** - Explore detailed feature documentation
