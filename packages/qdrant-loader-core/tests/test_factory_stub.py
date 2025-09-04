from importlib import import_module

import pytest


def _minimal_settings():
    LLMSettings = import_module("qdrant_loader_core.llm.settings").LLMSettings
    RequestPolicy = import_module("qdrant_loader_core.llm.settings").RequestPolicy
    RateLimitPolicy = import_module("qdrant_loader_core.llm.settings").RateLimitPolicy
    EmbeddingPolicy = import_module("qdrant_loader_core.llm.settings").EmbeddingPolicy
    return LLMSettings(
        provider="openai_compat",
        base_url="http://localhost:11434/v1",
        api_key=None,
        api_version=None,
        headers=None,
        models={"embeddings": "nomic-embed-text"},
        tokenizer="none",
        request=RequestPolicy(),
        rate_limits=RateLimitPolicy(),
        embeddings=EmbeddingPolicy(vector_size=768),
        provider_options=None,
    )


@pytest.mark.asyncio
async def test_factory_returns_provider_with_expected_interfaces():
    create_provider = import_module("qdrant_loader_core.llm.factory").create_provider
    provider = create_provider(_minimal_settings())
    emb = provider.embeddings()
    chat = provider.chat()
    tok = provider.tokenizer()

    assert hasattr(emb, "embed")
    assert hasattr(chat, "chat")
    assert tok.count("abc") == 3

    with pytest.raises(NotImplementedError):
        await emb.embed(["hello"])
    with pytest.raises(NotImplementedError):
        await chat.chat([{"role": "user", "content": "hi"}])
