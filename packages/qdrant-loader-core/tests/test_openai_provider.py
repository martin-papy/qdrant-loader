import importlib
import sys
import types
from importlib import import_module

import pytest


def _make_llm_settings():
    settings_mod = import_module("qdrant_loader_core.llm.settings")
    LLMSettings = settings_mod.LLMSettings
    RequestPolicy = settings_mod.RequestPolicy
    RateLimitPolicy = settings_mod.RateLimitPolicy
    EmbeddingPolicy = settings_mod.EmbeddingPolicy

    return LLMSettings(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-123",
        api_version=None,
        headers=None,
        models={"embeddings": "text-embedding-3-small", "chat": "gpt-4o-mini"},
        tokenizer="none",
        request=RequestPolicy(),
        rate_limits=RateLimitPolicy(),
        embeddings=EmbeddingPolicy(vector_size=1536),
        provider_options=None,
    )


def _make_openai_stub(
    *, emb_exc=None, chat_exc=None, chat_exc_ctor: tuple[str, tuple, dict] | None = None
):
    mod = types.ModuleType("openai")

    class APIConnectionError(Exception):
        pass

    class APIStatusError(Exception):
        def __init__(self, *args, status_code=None, response=None):  # type: ignore[no-untyped-def]
            super().__init__(*args)
            self.status_code = status_code
            self.response = response

    class APITimeoutError(Exception):
        pass

    class AuthenticationError(Exception):
        pass

    class BadRequestError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class _Embeddings:
        def create(self, model, input):  # type: ignore[no-untyped-def]
            if emb_exc is not None:
                raise emb_exc

            class _Item:
                def __init__(self, emb):
                    self.embedding = emb

            class _Resp:
                def __init__(self):
                    self.data = [_Item([1.0, 2.0]) for _ in input]

            return _Resp()

    class _ChatCreate:
        def create(self, model, messages, **kwargs):  # type: ignore[no-untyped-def]
            if chat_exc is not None:
                raise chat_exc
            if chat_exc_ctor is not None:
                name, args, kw = chat_exc_ctor
                cls_map = {
                    "RateLimitError": RateLimitError,
                    "APITimeoutError": APITimeoutError,
                    "AuthenticationError": AuthenticationError,
                    "BadRequestError": BadRequestError,
                    "APIStatusError": APIStatusError,
                    "APIConnectionError": APIConnectionError,
                }
                exc_cls = cls_map[name]
                raise exc_cls(*args, **kw)

            class _Msg:
                def __init__(self):
                    self.content = "hello"

            class _Choice:
                def __init__(self):
                    self.message = _Msg()

            class _Usage:
                def __init__(self):
                    self.prompt_tokens = 3
                    self.completion_tokens = 2
                    self.total_tokens = 5

            class _Resp:
                def __init__(self):
                    self.choices = [_Choice()]
                    self.usage = _Usage()
                    self.model = model

            return _Resp()

    class _Chat:
        def __init__(self):
            self.completions = _ChatCreate()

    class OpenAI:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            self._kwargs = kwargs
            self.embeddings = _Embeddings()
            self.chat = _Chat()

    # Export symbols
    mod.OpenAI = OpenAI
    mod.APIConnectionError = APIConnectionError
    mod.APIStatusError = APIStatusError
    mod.APITimeoutError = APITimeoutError
    mod.AuthenticationError = AuthenticationError
    mod.BadRequestError = BadRequestError
    mod.RateLimitError = RateLimitError

    return mod


def _reload_openai_provider(
    monkeypatch,
    *,
    emb_exc=None,
    chat_exc=None,
    chat_exc_ctor: tuple[str, tuple, dict] | None = None,
):
    # Inject our stub and reload the provider to pick up symbols
    stub = _make_openai_stub(
        emb_exc=emb_exc, chat_exc=chat_exc, chat_exc_ctor=chat_exc_ctor
    )
    monkeypatch.setitem(sys.modules, "openai", stub)

    mod = import_module("qdrant_loader_core.llm.providers.openai")
    mod = importlib.reload(mod)
    return mod


@pytest.mark.asyncio
async def test_openai_provider_success(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.providers.openai")
    # Ensure a clean reload with our stub
    mod = _reload_openai_provider(monkeypatch)

    provider = mod.OpenAIProvider(_make_llm_settings())

    # Embeddings path
    vectors = await provider.embeddings().embed(["a", "b"])
    assert vectors == [[1.0, 2.0], [1.0, 2.0]]

    # Chat path
    resp = await provider.chat().chat([{"role": "user", "content": "hi"}])
    assert resp["text"] == "hello"
    assert resp["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
    }
    assert resp["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc_ctor,expected_module_error",
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
async def test_openai_exception_mapping(monkeypatch, exc_ctor, expected_module_error):
    # Reload provider with stub configured to raise the desired exception
    mod = _reload_openai_provider(monkeypatch, chat_exc_ctor=exc_ctor)

    provider = mod.OpenAIProvider(_make_llm_settings())

    with pytest.raises(Exception) as ei:
        await provider.chat().chat([{"role": "user", "content": "hi"}])

    # The provider maps OpenAI exceptions to our internal LLMError hierarchy
    err_mod = import_module("qdrant_loader_core.llm.errors")
    mapped = ei.value
    assert isinstance(mapped, err_mod.LLMError)
    assert mapped.__class__.__name__ == expected_module_error
