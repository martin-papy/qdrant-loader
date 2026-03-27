# QDrant Loader Core

[![PyPI](https://img.shields.io/pypi/v/qdrant-loader-core)](https://pypi.org/project/qdrant-loader-core/)
[![Python](https://img.shields.io/pypi/pyversions/qdrant-loader-core)](https://pypi.org/project/qdrant-loader-core/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Shared core library for the QDrant Loader ecosystem. It provides a provider‑agnostic LLM layer (embeddings and chat), configuration mapping, safe logging, and normalized error handling used by the CLI and MCP Server packages.

## <img src="../../../assets/icons/library/target-icon.svg"  width="32" alt="What It Provides"> What It Provides

- **Provider‑agnostic LLM facade**: OpenAI, Azure OpenAI, OpenAI‑compatible, and Ollama
- **Unified async APIs**:
  - `EmbeddingsClient.embed(inputs: list[str]) -> list[list[float]]`
  - `ChatClient.chat(messages: list[dict], **kwargs) -> dict`
  - `TokenCounter.count(text: str) -> int`
- **Typed settings and mapping**: `LLMSettings.from_global_config(...)` supports the new `global.llm` schema and maps legacy fields with deprecation warnings
- **Structured logging with redaction**: `LoggingConfig.setup(...)` masks secrets and reduces noisy logs
- **Normalized errors**: consistent exceptions across providers (`TimeoutError`, `RateLimitedError`, `InvalidRequestError`, `AuthError`, `ServerError`)
- **Optional dependencies** via extras: `openai`, `ollama`

## <img src="../../../assets/icons/library/package-icon.svg"  width="32" alt="Installation"> Installation

```bash
# Minimal core
pip install qdrant-loader-core

# With OpenAI/Azure OpenAI support
pip install "qdrant-loader-core[openai]"

# With Ollama support
pip install "qdrant-loader-core[ollama]"

# From source (development)
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader
pip install -e packages/qdrant-loader-core
```

## <img src="../../../assets/icons/library/rocket-icon.svg"  width="32" alt="Quick Start">  Quick Start

Example using the new `global.llm` schema:

```yaml
global:
  llm:
    provider: "openai"            # openai | azure_openai | ollama | openai_compat
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
```

```python
import asyncio
from qdrant_loader_core.llm.settings import LLMSettings
from qdrant_loader_core.llm.factory import create_provider

global_config = {
    "llm": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "${LLM_API_KEY}",
        "models": {"embeddings": "text-embedding-3-small", "chat": "gpt-4o-mini"},
    }
}

settings = LLMSettings.from_global_config(global_config)
provider = create_provider(settings)

async def main() -> None:
    vectors = await provider.embeddings().embed(["hello", "world"])  # list[list[float]]
    reply = await provider.chat().chat([
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Say hi!"},
    ])
    print(len(vectors), reply["text"])  # 2 "Hi!" (example)

asyncio.run(main())
```

## <img src="../../../assets/icons/library/plug-icon.svg"  width="32" alt="Supported Providers"> Supported Providers

- **OpenAI** (`[openai]` extra): Uses the official `openai` Python SDK. Configure with `base_url`, `api_key`, and `models.chat`/`models.embeddings`.
- **Azure OpenAI** (`[openai]` extra): Requires `api_version`. Auto‑detected when the host is `*.openai.azure.com` or `*.cognitiveservices.azure.com`. Optional `provider_options.azure_endpoint` overrides the endpoint.
- **OpenAI‑compatible** (`[openai]` extra): Any endpoint exposing OpenAI‑style `/v1` APIs. Set `provider: openai_compat` (or rely on `base_url` containing `openai`).
- **Ollama** (`[ollama]` extra): Works with native `/api` and OpenAI‑compatible `/v1` endpoints. Optional `provider_options.native_endpoint: auto | embed | embeddings` selects native behavior.

## <img src="../../../assets/icons/library/wrench-icon.svg"  width="32" alt="Configuration Mapping"> Configuration Mapping

`LLMSettings.from_global_config(...)` accepts a parsed dict for `global` and supports:

- **New schema (recommended)**: `global.llm`
  - `provider`, `base_url`, `api_key`, `api_version` (Azure), `headers`
  - `models`: `{ embeddings, chat }`
  - `tokenizer`
  - `request`: `{ timeout_s, max_retries, backoff_s_min, backoff_s_max }`
  - `rate_limits`: `{ rpm, tpm, concurrency }`
  - `embeddings`: `{ vector_size }`
  - `provider_options`: provider‑specific opts (e.g., `azure_endpoint`, `native_endpoint`)

- **Legacy mapping (deprecated)**: `global.embedding.*` and `file_conversion.markitdown.llm_model`
  - Maps to provider + models (embeddings/chat), emits a deprecation warning
  - Prefer migrating to `global.llm` for clarity and future features

## <img src="../../../assets/icons/library/file-icon.svg"  width="32" alt="Logging"> Logging

Use the built‑in structured logging with redaction:

```python
from qdrant_loader_core.logging import LoggingConfig

LoggingConfig.setup(level="INFO", format="console", file=None)
logger = LoggingConfig.get_logger(__name__)
logger.info("LLM ready", provider=settings.provider)
```

## <img src="../../../assets/icons/library/note-icon.svg"  width="32" alt="Notes"> Notes

- Secrets (keys/tokens) are masked in both stdlib and structlog output
- Noisy third‑party logs are toned down; Qdrant version checks are filtered
- For MCP integration, set `MCP_DISABLE_CONSOLE_LOGGING=true` to disable console output

## <img src="../../../assets/icons/library/error-icon.svg"  width="32" alt="Error Handling"> Error Handling

Catch provider‑normalized exceptions from `qdrant_loader_core.llm.errors`:

- `TimeoutError` — request timed out
- `RateLimitedError` — rate limit exceeded
- `InvalidRequestError` — bad parameters or unsupported operation
- `AuthError` — authentication/authorization failed
- `ServerError` — transport/server failures

## <img src="../../../assets/icons/library/book-icon.svg"  width="32" alt="Documentation"> Documentation

- **[Website](https://qdrant-loader.net)** — Project site and guides
- **[Core package docs](https://qdrant-loader.net/docs/packages/core/README.html)** — Package‑specific page
- **[Monorepo docs](../../docs/)** — Source documentation in this repository

## <img src="../../../assets/icons/library/hand-sake-icon.svg"  width="32" alt="Contributing"> Contributing

This package is part of the QDrant Loader monorepo. See the [main contributing guide](../../CONTRIBUTING.md).

## <img src="../../../assets/icons/library/hand-sake-icon.svg"  width="32" alt="Support"> Support

- **Issues**: <https://github.com/martin-papy/qdrant-loader/issues>
- **Discussions**: <https://github.com/martin-papy/qdrant-loader/discussions>

## <img src="../../../assets/icons/library/file-icon.svg"  width="32" alt="License"> License

Licensed under the GNU GPLv3 — see [LICENSE](../../LICENSE).
