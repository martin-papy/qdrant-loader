from importlib import import_module

import pytest


class _Resp:
    def __init__(self, status_code: int, json_data):
        self.status_code = status_code
        self._json = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            from importlib import import_module as _im

            _httpx = _im("qdrant_loader_core.llm.providers.ollama").httpx
            raise _httpx.HTTPStatusError("err", request=None, response=self)  # type: ignore[arg-type]

    def json(self):  # type: ignore[no-untyped-def]
        return self._json


class _Client:
    def __init__(self, responses=None, post_exc=None):
        self._responses = list(responses or [])
        self._post_exc = post_exc

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return False

    async def post(self, url, json=None, headers=None):  # type: ignore[no-untyped-def]
        if self._post_exc is not None:
            raise self._post_exc
        if not self._responses:
            raise AssertionError("No more responses queued")
        return self._responses.pop(0)


def _stub_httpx(*, responses=None, post_exc=None):
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
            return _Client(responses=responses, post_exc=post_exc)

    return _HTTPX


@pytest.mark.asyncio
async def test_chat_v1_success(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    data = {"choices": [{"message": {"content": "hello"}}], "model": "m", "usage": {}}
    monkeypatch.setattr(mod, "httpx", _stub_httpx(responses=[_Resp(200, data)]))
    chat = mod.OllamaChat("http://localhost:11434/v1", "m", None)
    out = await chat.chat([{"role": "user", "content": "hi"}])
    assert out["text"] == "hello"
    assert out["model"] == "m"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,exc_name",
    [
        (401, "AuthError"),
        (429, "RateLimitedError"),
        (400, "InvalidRequestError"),
        (500, "ServerError"),
    ],
)
async def test_chat_v1_http_status_mappings(monkeypatch, status, exc_name):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    monkeypatch.setattr(mod, "httpx", _stub_httpx(responses=[_Resp(status, {})]))
    chat = mod.OllamaChat("http://localhost:11434/v1", "m", None)
    with pytest.raises(Exception) as ei:
        await chat.chat([{"role": "user", "content": "x"}])
    assert ei.value.__class__.__name__ == exc_name


@pytest.mark.asyncio
async def test_chat_v1_timeout(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    stub = _stub_httpx()
    monkeypatch.setattr(mod, "httpx", stub)
    # Ensure AsyncClient raises the stub's own TimeoutException type
    monkeypatch.setattr(
        stub,
        "AsyncClient",
        staticmethod(lambda timeout: _Client(post_exc=stub.TimeoutException("to"))),
    )
    chat = mod.OllamaChat("http://localhost:11434/v1", "m", None)
    with pytest.raises(Exception) as ei:
        await chat.chat([{"role": "user", "content": "x"}])
    assert ei.value.__class__.__name__ == "TimeoutError"


@pytest.mark.asyncio
async def test_chat_v1_http_error(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    stub = _stub_httpx()
    monkeypatch.setattr(mod, "httpx", stub)
    monkeypatch.setattr(
        stub,
        "AsyncClient",
        staticmethod(lambda timeout: _Client(post_exc=stub.HTTPError("err"))),
    )
    chat = mod.OllamaChat("http://localhost:11434/v1", "m", None)
    with pytest.raises(Exception) as ei:
        await chat.chat([{"role": "user", "content": "x"}])
    assert ei.value.__class__.__name__ == "ServerError"


@pytest.mark.asyncio
async def test_chat_native_success(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    data = {"message": {"content": "world"}}
    monkeypatch.setattr(mod, "httpx", _stub_httpx(responses=[_Resp(200, data)]))
    chat = mod.OllamaChat("http://localhost:11434", "m", None)
    out = await chat.chat([{"role": "user", "content": "hi"}])
    assert out["text"] == "world"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,exc_name",
    [
        (401, "AuthError"),
        (429, "RateLimitedError"),
        (400, "InvalidRequestError"),
        (500, "ServerError"),
    ],
)
async def test_chat_native_http_status_mappings(monkeypatch, status, exc_name):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    monkeypatch.setattr(mod, "httpx", _stub_httpx(responses=[_Resp(status, {})]))
    chat = mod.OllamaChat("http://localhost:11434", "m", None)
    with pytest.raises(Exception) as ei:
        await chat.chat([{"role": "user", "content": "x"}])
    assert ei.value.__class__.__name__ == exc_name


@pytest.mark.asyncio
async def test_chat_native_timeout(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    stub = _stub_httpx()
    monkeypatch.setattr(mod, "httpx", stub)
    monkeypatch.setattr(
        stub,
        "AsyncClient",
        staticmethod(lambda timeout: _Client(post_exc=stub.TimeoutException("to"))),
    )
    chat = mod.OllamaChat("http://localhost:11434", "m", None)
    with pytest.raises(Exception) as ei:
        await chat.chat([{"role": "user", "content": "x"}])
    assert ei.value.__class__.__name__ == "TimeoutError"


@pytest.mark.asyncio
async def test_chat_native_http_error(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.providers.ollama")
    stub = _stub_httpx()
    monkeypatch.setattr(mod, "httpx", stub)
    monkeypatch.setattr(
        stub,
        "AsyncClient",
        staticmethod(lambda timeout: _Client(post_exc=stub.HTTPError("err"))),
    )
    chat = mod.OllamaChat("http://localhost:11434", "m", None)
    with pytest.raises(Exception) as ei:
        await chat.chat([{"role": "user", "content": "x"}])
    assert ei.value.__class__.__name__ == "ServerError"
