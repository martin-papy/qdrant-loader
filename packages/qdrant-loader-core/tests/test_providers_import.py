import importlib


def test_openai_provider_importable():
    mod = importlib.import_module("qdrant_loader_core.llm.providers.openai")
    assert hasattr(mod, "OpenAIProvider")


def test_ollama_provider_importable():
    mod = importlib.import_module("qdrant_loader_core.llm.providers.ollama")
    assert hasattr(mod, "OllamaProvider")
