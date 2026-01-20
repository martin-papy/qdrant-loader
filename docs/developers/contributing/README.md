# Best Practices for qdrant-loader

> **Author:** nguyen.vu@cbtw.tech

This guide outlines Pythonic patterns and AI engineering best practices for the qdrant-loader project.

## 1. Pythonic Code Standards

### 1.1. Avoid Class-Level Anti-Patterns

- **No Redundant `__new__`**: Do not override `__new__` unless you are implementing a strict Singleton or working with immutable types. Standard service initialization belongs in `__init__`.
- **Explicit over Implicit**: Avoid "monkey-patching" (e.g., overwriting a local class with one from another package via try/except). Use explicit dependencies.

### 1.2. Type Hinting & Structural Subtyping

- **Protocols over Base Classes**: Use `typing.Protocol` for defining interfaces (e.g., `ChunkingStrategy`). This follows the "Go-style" duck typing which is more flexible for a plugin-based architecture.
- **Pydantic for Data/Config**: Use Pydantic models for all data structures and configuration. Avoid passing around raw dictionaries.

### 1.3. Dependency Injection (DI)

**Granular Injection**: Do not pass the entire `Settings` or `GlobalConfig` object to every service. Pass only the specific sub-config or primitives the service needs. This makes unit testing significantly easier.

```python
# BAD: Monolithic config passing
def __init__(self, settings: Settings):
    self.chunk_size = settings.global_config.chunking.chunk_size

# GOOD: Granular injection
def __init__(self, chunk_size: int, overlap: int):
    self.chunk_size = chunk_size
```

## 2. AI & RAG Best Practices

### 2.1. Metadata Hygiene

- **Strict Schemas**: Every document ingested must have a consistent metadata schema. If a new field is added, update the Document model and relevant extractors.
- **Provenance**: Always preserve the "source of truth" (URL, file path, line number) in metadata to enable high-quality citations in the RAG retrieval phase.

### 2.2. Embedding Drift Management

- **Versioned Collections**: If you change the embedding model (e.g., moving from OpenAI `text-embedding-3-small` to `3-large`), you must create a new Qdrant collection. Vectors are not compatible across different models or dimensions.

### 2.3. Evaluation-First Development

**Ragas/G-Eval**: Before merging a change to the `HybridSearchEngine` or `Reranker`, run an evaluation suite. Aim for improvements in:

- **Faithfulness**: The answer is derived only from context.
- **Answer Relevance**: The answer directly addresses the query.
- **Context Precision**: The retrieved documents are relevant.

## 3. Architecture & Monorepo Management

### 3.1. Package Isolation

- **Core is Sacred**: `qdrant-loader-core` should have zero dependencies on `qdrant-loader` or `qdrant-loader-mcp-server`. It is the foundational abstraction layer.
- **Circular Dependencies**: Use `from __future__ import annotations` and local imports inside methods if absolutely necessary to break circular loops, but prefer refactoring to a shared utility.

### 3.2. Logging & Observability

- **Centralized Logging**: Use the `LoggingConfig` from core. Do not initialize standard `logging.getLogger(__name__)` manually if you need structured logs.
- **Traceability**: Every MCP request should have a unique `request_id` passed through the search engine to help debug multi-step retrieval chains.

## 4. Testing Standards

### 4.1. Mocking External APIs

- **No Real LLM Calls in Unit Tests**: Always use `unittest.mock` or `pytest-mock` to stub LLM providers. Use the `_NoopProvider` in core as a base for mocks.
- **VCR.py / Pytest-Recording**: For integration tests, use VCR-style recording to capture and replay real Qdrant/LLM interactions to ensure deterministic test results.

### 4.2. Algorithmic Validation

- **Similarity Thresholds**: When testing search tools, include cases that specifically check the "boundary" of your similarity thresholds (e.g., verifying a 0.69 score is excluded if the threshold is 0.7).

## 5. Summary Checklist

For reviewer to recheck everytime a PR comes up:

- [ ] Is the PR code type-hinted and linted?
- [ ] Did it avoid redundant class overrides like `__new__`?
- [ ] Are services using granular dependency injection?
- [ ] If the commiter modified the retrieval logic, did they run a RAG evaluation?
- [ ] Are PR's new logs structured and redact-protected?

---
