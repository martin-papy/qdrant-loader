# QDrant Loader Core

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader-core)](https://pypi.org/project/qdrant-loader-core/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader-core)](https://pypi.org/project/qdrant-loader-core/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Shared core library for the QDrant Loader ecosystem. It provides a provider‑agnostic LLM layer (embeddings and chat), configuration mapping, safe logging, and normalized error handling used by the CLI and MCP Server packages.

For provider, configuration, and architecture details, use the documentation links below.

## 🎯 What It Provides

- **Provider-agnostic LLM facade** for OpenAI, Azure OpenAI, OpenAI-compatible endpoints, and Ollama
- **Unified async APIs** for embeddings and chat clients
- **Typed settings and mapping**: `LLMSettings.from_global_config(...)` supports the new `global.llm` schema and maps legacy fields with deprecation warnings
- **Structured logging with redaction**: `LoggingConfig.setup(...)` masks secrets and reduces noisy logs
- **Normalized errors**: consistent exceptions across providers (`TimeoutError`, `RateLimitedError`, `InvalidRequestError`, `AuthError`, `ServerError`)
- **Optional dependencies** via extras: `openai`, `ollama`

## 📦 Installation

```bash
pip install qdrant-loader-core
```

With extras:

```bash
pip install "qdrant-loader-core[openai]"
pip install "qdrant-loader-core[ollama]"
```

## 📄 Logging

Use built-in structured logging:

```python
from qdrant_loader_core.logging import LoggingConfig

LoggingConfig.setup(level="INFO", format="console", file=None)
logger = LoggingConfig.get_logger(__name__)
logger.info("LLM ready", provider=settings.provider)
```

## 📝 Notes

- Secrets (keys/tokens) are masked in both stdlib and structlog output
- Noisy third‑party logs are toned down; Qdrant version checks are filtered
- For MCP integration, set `MCP_DISABLE_CONSOLE_LOGGING=true` to disable console output

## ❗ Error Handling

Catch provider-normalized exceptions from `qdrant_loader_core.llm.errors`:

- `TimeoutError` — request timed out
- `RateLimitedError` — rate limit exceeded
- `InvalidRequestError` — bad parameters or unsupported operation
- `AuthError` — authentication/authorization failed
- `ServerError` — transport/server failures

## 📚 Documentation

- **[Getting Started](../../docs/getting-started/)** - Quick start and core concepts
- **[Monorepo overview](../../)** - Project structure, packages, and high-level navigation across the repository.
- **[Quick start](../../docs/getting-started/quick-start.md)** - Fast setup path from install to first successful ingestion.
- **[User Guides](../../docs/users/)** - Detailed usage instructions
- **[Developer hub](../../docs/developers)** - Developer guides for architecture, testing, deployment, and contribution workflows.
- **[Architecture hub](../../docs/developers/architecture)** - System design, component interactions, and core technical decisions.
- **[Basic Configuration](../../docs/getting-started/basic-configuration.md)** - Getting started with configuration

## 🆘 Support

- **[Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community Q&A

## 🤝 Contributing

See **[CONTRIBUTING](../../CONTRIBUTING.md)** - Contribution guidelines, development standards, and pull request process.

## 📄 License

This project is licensed under the GNU GPLv3 - see the [LICENSE](../../LICENSE) file for details.

---

**Ready to get started?** Check out our [Quick Start Guide](../../docs/getting-started/quick-start.md) or browse the [complete documentation](../../docs/).
