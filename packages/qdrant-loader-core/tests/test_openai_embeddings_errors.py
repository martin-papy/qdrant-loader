import importlib
import sys
import types
from importlib import import_module

import pytest


def _make_stub(emb_exc=None, emb_exc_ctor: tuple[str, tuple, dict] | None = None):
    m = types.ModuleType("openai")

    class APIStatusError(Exception):
        def __init__(self, *args, status_code=None, response=None):  # type: ignore[no-untyped-def]
            super().__init__(*args)
            self.status_code = status_code
            self.response = response

    class AuthenticationError(Exception):
        pass

    class BadRequestError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class _Emb:
        def create(self, model, input):  # type: ignore[no-untyped-def]
            if emb_exc is not None:
                raise emb_exc
            if emb_exc_ctor is not None:
                name, args, kwargs = emb_exc_ctor
                cls_map = {
                    "RateLimitError": RateLimitError,
                    "APITimeoutError": APITimeoutError,
                    "AuthenticationError": AuthenticationError,
                    "BadRequestError": BadRequestError,
                    "APIStatusError": APIStatusError,
                    "APIConnectionError": APIConnectionError,
                }
                exc_cls = cls_map[name]
                raise exc_cls(*args, **kwargs)

    class OpenAI:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            self.embeddings = _Emb()
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=lambda **k: None)
            )

    m.OpenAI = OpenAI
    m.APIStatusError = APIStatusError
    m.AuthenticationError = AuthenticationError
    m.BadRequestError = BadRequestError
    m.RateLimitError = RateLimitError
    m.APIConnectionError = APIConnectionError
    m.APITimeoutError = APITimeoutError
    return m


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc_ctor,expected",
    [
        (("RateLimitError", ("rl",), {}), "RateLimitedError"),
        (("APITimeoutError", ("to",), {}), "TimeoutError"),
        (("AuthenticationError", ("auth",), {}), "AuthError"),
        (("BadRequestError", ("bad",), {}), "InvalidRequestError"),
        (("APIStatusError", ("429",), {"status_code": 429}), "RateLimitedError"),
        (("APIStatusError", ("401",), {"status_code": 401}), "AuthError"),
        (("APIStatusError", ("500",), {"status_code": 500}), "ServerError"),
        (("APIConnectionError", ("conn",), {}), "ServerError"),
    ],
)
async def test_openai_embeddings_error_mapping(monkeypatch, exc_ctor, expected):
    name, args, kwargs = exc_ctor
    # Build stub and reload provider; exception will be constructed by the stub module
    monkeypatch.setitem(
        sys.modules, "openai", _make_stub(emb_exc_ctor=(name, args, kwargs))
    )

    mod = import_module("qdrant_loader_core.llm.providers.openai")
    mod = importlib.reload(mod)

    settings_mod = import_module("qdrant_loader_core.llm.settings")
    settings = settings_mod.LLMSettings(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-1",
        api_version=None,
        headers=None,
        models={"embeddings": "text-embedding-3-small", "chat": "gpt-4o-mini"},
        tokenizer="none",
        request=settings_mod.RequestPolicy(),
        rate_limits=settings_mod.RateLimitPolicy(),
        embeddings=settings_mod.EmbeddingPolicy(vector_size=1536),
        provider_options=None,
    )

    provider = mod.OpenAIProvider(settings)
    with pytest.raises(Exception) as ei:
        await provider.embeddings().embed(["a", "b"])  # type: ignore[func-returns-value]
    assert ei.value.__class__.__name__ == expected
