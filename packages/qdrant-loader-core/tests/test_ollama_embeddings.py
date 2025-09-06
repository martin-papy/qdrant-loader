from importlib import import_module

import pytest


class _Resp:
    def __init__(self, status_code: int, json_data):
        self.status_code = status_code
        self._json = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            # Use the provider's patched httpx namespace so exception types match
            from importlib import import_module as _import_module

            _httpx = _import_module("qdrant_loader_core.llm.providers.ollama").httpx
            raise _httpx.HTTPStatusError("err", request=None, response=self)  # type: ignore[arg-type]

    def json(self):  # type: ignore[no-untyped-def]
        return self._json


class _Client:
    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return False

    async def post(self, url, json=None, headers=None):  # type: ignore[no-untyped-def]
        if not self._responses:
            raise AssertionError("No more responses queued")
        return self._responses.pop(0)


def _make_embeddings(base_url: str, provider_options=None):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    return mod.OllamaEmbeddings(
        base_url,
        model="m",
        headers=None,
        timeout_s=5.0,
        provider_options=provider_options or {},
    )


@pytest.mark.asyncio
async def test_v1_openai_compatible_parsing(monkeypatch):
    ollama_mod = import_module("qdrant_loader_core.llm.providers.ollama")
    # Patch httpx.AsyncClient to our stub returning OpenAI-compatible data
    data = {"data": [{"embedding": [1.0, 2.0]}]}

    class _HTTPX:
        class HTTPStatusError(Exception):
            def __init__(self, *args, request=None, response=None):  # type: ignore[no-untyped-def]
                super().__init__(*args)
                self.request = request
                self.response = response

        class TimeoutException(Exception):
            pass

        class HTTPError(Exception):
            pass

        @staticmethod
        def AsyncClient(timeout):  # type: ignore[no-untyped-def]
            return _Client([_Resp(200, data)])

    monkeypatch.setattr(ollama_mod, "httpx", _HTTPX)
    emb = _make_embeddings("http://localhost:11434/v1")
    vecs = await emb.embed(["a"])
    assert vecs == [[1.0, 2.0]]


@pytest.mark.asyncio
async def test_native_batch_embed_then_ok(monkeypatch):
    ollama_mod = import_module("qdrant_loader_core.llm.providers.ollama")
    batch = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    class _HTTPX2:
        class HTTPStatusError(Exception):
            def __init__(self, *args, request=None, response=None):  # type: ignore[no-untyped-def]
                super().__init__(*args)
                self.request = request
                self.response = response

        class TimeoutException(Exception):
            pass

        class HTTPError(Exception):
            pass

        @staticmethod
        def AsyncClient(timeout):  # type: ignore[no-untyped-def]
            return _Client([_Resp(200, batch)])

    monkeypatch.setattr(ollama_mod, "httpx", _HTTPX2)
    emb = _make_embeddings(
        "http://localhost:11434", provider_options={"native_endpoint": "embed"}
    )
    vecs = await emb.embed(["a", "b"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_native_embed_404_fallback_to_embeddings(monkeypatch):
    ollama_mod = import_module("qdrant_loader_core.llm.providers.ollama")
    # First call: /api/embed returns 404, then two calls to /api/embeddings succeed
    resp404 = _Resp(404, {"error": "not found"})
    item1 = _Resp(200, {"embedding": [9.0]})
    item2 = _Resp(200, {"data": {"embedding": [8.0]}})

    class _HTTPX3:
        class HTTPStatusError(Exception):
            def __init__(self, *args, request=None, response=None):  # type: ignore[no-untyped-def]
                super().__init__(*args)
                self.request = request
                self.response = response

        class TimeoutException(Exception):
            pass

        class HTTPError(Exception):
            pass

        @staticmethod
        def AsyncClient(timeout):  # type: ignore[no-untyped-def]
            return _Client([resp404, item1, item2])

    monkeypatch.setattr(ollama_mod, "httpx", _HTTPX3)
    emb = _make_embeddings(
        "http://localhost:11434", provider_options={"native_endpoint": "auto"}
    )
    vecs = await emb.embed(["x", "y"])
    assert vecs == [[9.0], [8.0]]


@pytest.mark.asyncio
async def test_invalid_batch_response_raises(monkeypatch):
    ollama_mod = import_module("qdrant_loader_core.llm.providers.ollama")
    bad = {"embeddings": [[0.1, 0.2]]}  # length 1 but inputs length 2

    class _HTTPX4:
        class HTTPStatusError(Exception):
            def __init__(self, *args, request=None, response=None):  # type: ignore[no-untyped-def]
                super().__init__(*args)
                self.request = request
                self.response = response

        class TimeoutException(Exception):
            pass

        class HTTPError(Exception):
            pass

        @staticmethod
        def AsyncClient(timeout):  # type: ignore[no-untyped-def]
            return _Client([_Resp(200, bad)])

    monkeypatch.setattr(ollama_mod, "httpx", _HTTPX4)
    emb = _make_embeddings(
        "http://localhost:11434", provider_options={"native_endpoint": "embed"}
    )
    with pytest.raises(ValueError):
        await emb.embed(["p", "q"])
