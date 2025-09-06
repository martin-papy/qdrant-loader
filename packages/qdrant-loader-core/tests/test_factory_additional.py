from importlib import import_module


def _settings(provider: str, base_url: str | None = None):
    settings = import_module("qdrant_loader_core.llm.settings")
    return settings.LLMSettings(
        provider=provider,
        base_url=base_url,
        api_key=None,
        api_version=None,
        headers=None,
        models={"embeddings": "m", "chat": "c"},
        tokenizer="none",
        request=settings.RequestPolicy(),
        rate_limits=settings.RateLimitPolicy(),
        embeddings=settings.EmbeddingPolicy(),
        provider_options=None,
    )


def test_factory_routes_to_noop_on_openai_init_failure(monkeypatch):
    factory = import_module("qdrant_loader_core.llm.factory")
    openai_mod = import_module("qdrant_loader_core.llm.providers.openai")

    class _BadProvider(openai_mod.OpenAIProvider):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    monkeypatch.setattr(factory, "OpenAIProvider", _BadProvider)

    provider = factory.create_provider(
        _settings("openai", base_url="https://api.openai.com/v1")
    )
    # Should return a noop provider which raises NotImplementedError on use
    emb = provider.embeddings()
    chat = provider.chat()
    tok = provider.tokenizer()
    assert tok.count("abc") == 3
    import asyncio

    import pytest

    async def _run():
        with pytest.raises(NotImplementedError):
            await emb.embed(["x"])  # type: ignore[func-returns-value]
        with pytest.raises(NotImplementedError):
            await chat.chat([{"role": "user", "content": "hi"}])  # type: ignore[func-returns-value]

    asyncio.get_event_loop().run_until_complete(_run())


def test_factory_azure_error_returns_noop(monkeypatch):
    factory = import_module("qdrant_loader_core.llm.factory")
    azure_mod = import_module("qdrant_loader_core.llm.providers.azure_openai")

    class _BadAzure(azure_mod.AzureOpenAIProvider):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    # If Azure provider is importable, force failure path
    if getattr(factory, "AzureOpenAIProvider", None) is not None:
        monkeypatch.setattr(factory, "AzureOpenAIProvider", _BadAzure)
        provider = factory.create_provider(
            _settings("azure_openai", base_url="https://x.openai.azure.com")
        )
        assert provider.__class__.__name__ == "_NoopProvider"


def test_factory_routes_ollama_by_host_local():
    factory = import_module("qdrant_loader_core.llm.factory")
    provider = factory.create_provider(_settings("", base_url="http://127.0.0.1:11434"))
    # Should be OllamaProvider
    assert provider.__class__.__name__ == "OllamaProvider"
