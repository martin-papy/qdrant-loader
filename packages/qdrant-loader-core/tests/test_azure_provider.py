from importlib import import_module

import pytest


class _DummyAzureOpenAI:
    last_kwargs: dict | None = None

    def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
        _DummyAzureOpenAI.last_kwargs = dict(kwargs)


def _make_settings(
    *,
    base_url: str,
    api_key: str | None,
    api_version: str | None,
    provider_options: dict | None,
):
    settings_mod = import_module("qdrant_loader_core.llm.settings")
    LLMSettings = settings_mod.LLMSettings
    RequestPolicy = settings_mod.RequestPolicy
    RateLimitPolicy = settings_mod.RateLimitPolicy
    EmbeddingPolicy = settings_mod.EmbeddingPolicy
    return LLMSettings(
        provider="azure_openai",
        base_url=base_url,
        api_key=api_key,
        api_version=api_version,
        headers=None,
        models={"embeddings": "emb", "chat": "chat"},
        tokenizer="none",
        request=RequestPolicy(),
        rate_limits=RateLimitPolicy(),
        embeddings=EmbeddingPolicy(vector_size=1536),
        provider_options=provider_options,
    )


@pytest.mark.asyncio
async def test_azure_provider_initializes_with_expected_kwargs(monkeypatch):
    # Patch the AzureOpenAI symbol used by the azure provider module
    azure_mod = import_module("qdrant_loader_core.llm.providers.azure_openai")
    monkeypatch.setattr(azure_mod, "AzureOpenAI", _DummyAzureOpenAI, raising=True)

    settings = _make_settings(
        base_url="https://myres.openai.azure.com",
        api_key="sk-123",
        api_version="2024-05-01-preview",
        provider_options={"azure_endpoint": "https://myres.openai.azure.com"},
    )

    factory = import_module("qdrant_loader_core.llm.factory")
    provider = factory.create_provider(settings)

    # Ensure our dummy client was instantiated
    assert _DummyAzureOpenAI.last_kwargs is not None
    assert _DummyAzureOpenAI.last_kwargs.get("api_key") == "sk-123"
    assert _DummyAzureOpenAI.last_kwargs.get("api_version") == "2024-05-01-preview"
    assert (
        _DummyAzureOpenAI.last_kwargs.get("azure_endpoint")
        == "https://myres.openai.azure.com"
    )

    # Provider should expose embeddings/chat clients (not invoked here)
    assert hasattr(provider, "embeddings")
    assert hasattr(provider, "chat")


def test_azure_provider_raises_on_bad_base_url():
    # Directly construct provider to assert validation errors
    provider_cls = import_module(
        "qdrant_loader_core.llm.providers.azure_openai"
    ).AzureOpenAIProvider

    bad_settings = _make_settings(
        base_url="https://myres.openai.azure.com/openai/deployments/foo",
        api_key="sk-123",
        api_version="2024-05-01-preview",
        provider_options=None,
    )
    with pytest.raises(ValueError):
        provider_cls(bad_settings)


def test_azure_provider_raises_on_missing_api_version():
    provider_cls = import_module(
        "qdrant_loader_core.llm.providers.azure_openai"
    ).AzureOpenAIProvider

    missing_ver = _make_settings(
        base_url="https://myres.openai.azure.com",
        api_key="sk-123",
        api_version=None,
        provider_options=None,
    )
    with pytest.raises(ValueError):
        provider_cls(missing_ver)
