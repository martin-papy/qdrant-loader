# AGENTS.md

## Cursor Cloud specific instructions

### Overview

QDrant Loader is a Python 3.12+ monorepo with 3 packages under `packages/` plus a documentation website builder:

| Package | Path | CLI command |
|---------|------|-------------|
| `qdrant-loader-core` | `packages/qdrant-loader-core/` | (library only) |
| `qdrant-loader` | `packages/qdrant-loader/` | `qdrant-loader` |
| `qdrant-loader-mcp-server` | `packages/qdrant-loader-mcp-server/` | `mcp-qdrant-loader` |
| Website builder | `website/` | `python website/build.py` |

Dependency chain: `qdrant-loader-core` is used by both `qdrant-loader` and `qdrant-loader-mcp-server`.

### Running services

- **Activate venv first**: `source /workspace/venv/bin/activate`
- Standard dev commands are documented in the `Makefile` (run `make help` for a summary).
- Lint: `ruff check .` (or `make lint` for auto-fix mode)
- Format: `make format` (runs `black .`, `isort .`, `ruff check --fix .`)
- Tests per-package (from repo root):
  - Core: `cd packages/qdrant-loader-core && python -m pytest tests/ -v`
  - Loader unit: `cd packages/qdrant-loader && python -m pytest tests/unit -v`
  - MCP server unit: `cd packages/qdrant-loader-mcp-server && python -m pytest tests/unit -v`
  - Website: `PYTHONPATH="${PYTHONPATH}:$(pwd)/website" python -m pytest tests/ -v`
- All tests: `make test` (runs `pytest packages/`)
- Website build: `make docs`

### Gotchas

- The root `pyproject.toml` `[tool.pytest.ini_options]` sets `testpaths = ["tests"]` and `norecursedirs = ["packages"]`. Running `pytest` from the repo root only runs website tests. Use `make test` or `pytest packages/` to run package tests.
- Each sub-package has its own `pyproject.toml` with its own pytest config. Run tests from within the package directory (`cd packages/<pkg> && python -m pytest ...`) to use the correct config.
- Integration tests require external services (Qdrant, OpenAI API key, etc.) and are skipped in standard local runs. Unit tests are self-contained with mocks.
- The spaCy model `en_core_web_md` must be installed: `python -m spacy download en_core_web_md`.
- System dependency `ffmpeg` is required for audio file conversion tests in `qdrant-loader`.
- System dependencies `libcairo2-dev` and `libgirepository1.0-dev` are required for website favicon generation tests.
- A harmless `RequestsDependencyWarning` about urllib3/chardet version mismatch appears during MCP server commands; it does not affect functionality.
