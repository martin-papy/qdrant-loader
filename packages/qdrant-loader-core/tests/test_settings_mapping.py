from importlib import import_module


def test_from_global_config_new_schema_minimal():
    LLMSettings = import_module("qdrant_loader_core.llm.settings").LLMSettings
    cfg = {
        "llm": {
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "key",
            "models": {"embeddings": "text-embedding-3-small", "chat": "gpt-4o"},
            "tokenizer": "cl100k_base",
            "request": {"timeout_s": 10, "max_retries": 2},
            "rate_limits": {"rpm": 100, "concurrency": 2},
            "embeddings": {
                "vector_size": 1536,
                "max_tokens_per_request": 12000,
                "max_tokens_per_chunk": 4000,
            },
        }
    }
    s = LLMSettings.from_global_config(cfg)
    assert s.provider == "openai"
    assert s.base_url == "https://api.openai.com/v1"
    assert s.api_key == "key"
    assert s.models["embeddings"] == "text-embedding-3-small"
    assert s.models["chat"] == "gpt-4o"
    assert s.embeddings.vector_size == 1536
    assert s.embeddings.max_tokens_per_request == 12000
    assert s.embeddings.max_tokens_per_chunk == 4000
    assert s.request.timeout_s == 10
    assert s.rate_limits.rpm == 100


def test_from_global_config_legacy_mapping_embedding_only():
    LLMSettings = import_module("qdrant_loader_core.llm.settings").LLMSettings
    cfg = {
        "embedding": {
            "endpoint": "http://localhost:11434/v1",
            "model": "nomic-embed-text",
            "api_key": None,
            "tokenizer": "none",
            "vector_size": 768,
        }
    }
    s = LLMSettings.from_global_config(cfg)
    assert s.provider in ("openai_compat", "openai")
    assert s.base_url == "http://localhost:11434/v1"
    assert s.models["embeddings"] == "nomic-embed-text"
    assert s.embeddings.vector_size == 768
    assert s.tokenizer == "none"


def test_from_global_config_new_schema_vector_size_from_string():
    LLMSettings = import_module("qdrant_loader_core.llm.settings").LLMSettings
    cfg = {
        "llm": {
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "key",
            "tokenizer": "cl100k_base",
            "models": {"embeddings": "text-embedding-3-small"},
            "embeddings": {"vector_size": "1536"},
        },
    }
    s = LLMSettings.from_global_config(cfg)
    assert s.provider == "openai"
    assert s.models["embeddings"] == "text-embedding-3-small"
    assert s.embeddings.vector_size == 1536
