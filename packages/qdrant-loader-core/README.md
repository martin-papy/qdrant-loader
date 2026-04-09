# QDrant Loader Core

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader-core)](https://pypi.org/project/qdrant-loader-core/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader-core)](https://pypi.org/project/qdrant-loader-core/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Shared core library for the QDrant Loader ecosystem. It provides a provider‑agnostic LLM layer (embeddings and chat), configuration mapping, safe logging, and normalized error handling used by the CLI and MCP Server packages.

For provider, configuration, and architecture details, use the documentation links below.

## <img src="/assets/icons/library/target-icon.svg"  width="32" alt="What It Provides"> What It Provides

- Provider-agnostic LLM facade for OpenAI, Azure OpenAI, OpenAI-compatible endpoints, and Ollama
- Unified async APIs for embeddings and chat clients
- Typed configuration mapping via `LLMSettings.from_global_config(...)`
- Structured logging with secret redaction
- Normalized provider exceptions for predictable handling across backends

## <img src="/assets/icons/library/package-icon.svg"  width="32" alt="Installation"> Installation

```bash
pip install qdrant-loader-core
```

With extras:

```bash
pip install "qdrant-loader-core[openai]"
pip install "qdrant-loader-core[ollama]"
```

## <img src="/assets/icons/library/file-icon.svg"  width="32" alt="Logging"> Logging

Use built-in structured logging:

```python
from qdrant_loader_core.logging import LoggingConfig

LoggingConfig.setup(level="INFO", format="console", file=None)
logger = LoggingConfig.get_logger(__name__)
logger.info("LLM ready")
```

## <img src="/assets/icons/library/note-icon.svg"  width="32" alt="Notes"> Notes

- Secrets (API keys/tokens) are redacted in logs
- For MCP integrations, `MCP_DISABLE_CONSOLE_LOGGING=true` is recommended
- Environment variable reference: [Environment Variables](../../docs/users/configuration/environment-variables.md) - Required and optional environment variables for setup, authentication, and runtime behavior.

## <img src="/assets/icons/library/error-icon.svg"  width="32" alt="Error Handling"> Error Handling

Catch provider-normalized exceptions from `qdrant_loader_core.llm.errors`:

- `TimeoutError`
- `RateLimitedError`
- `InvalidRequestError`
- `AuthError`
- `ServerError`

## <img src="../../../assets/icons/library/book-icon.svg" width="32" alt="Book icon"> Canonical Documentation

- **[Monorepo overview](../../)** - Project structure, packages, and high-level navigation across the repository.
- **[Developer hub](../../docs/developers)** - Developer guides for architecture, testing, deployment, and contribution workflows.
- **[Architecture hub](../../docs/developers/architecture)** - System design, component interactions, and core technical decisions.
- **[User configuration reference](../../docs/users/configuration/config-file-reference.md)** - Complete config schema and practical setup examples.
- **[User error troubleshooting](../../docs/users/troubleshooting/error-messages-reference.md)** - Common error messages, root causes, and recommended fixes.

## <img src="/assets/icons/library/hand-sake-icon.svg" width="32" alt="Contributing icon"> Contributing

See **[CONTRIBUTING](../../CONTRIBUTING.md)** - Contribution guidelines, development standards, and pull request process.
