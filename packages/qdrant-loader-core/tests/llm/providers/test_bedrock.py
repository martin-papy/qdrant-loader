import builtins
import importlib
import io
import json
import sys
import types
from importlib import import_module
from typing import Any

import pytest


def _make_llm_settings(model_id: str = "amazon.titan-embed-text-v2:0"):
    settings_mod = import_module("qdrant_loader_core.llm.settings")
    return settings_mod.LLMSettings(
        provider="bedrock",
        base_url=None,
        api_key=None,
        api_version=None,
        headers=None,
        models={"embeddings": model_id, "chat": ""},
        tokenizer="none",
        request=settings_mod.RequestPolicy(),
        rate_limits=settings_mod.RateLimitPolicy(),
        embeddings=settings_mod.EmbeddingPolicy(vector_size=1024),
        provider_options={
            "aws_region": "us-east-1",
            "model_id": model_id,
        },
    )


class _FakeBedrockClient:
    def __init__(self, response_body: bytes, raise_exc: Exception | None = None):
        self._response_body = response_body
        self._raise_exc = raise_exc

    def invoke_model(self, **kwargs):
        if self._raise_exc is not None:
            raise self._raise_exc
        return {"body": io.BytesIO(self._response_body)}


class _FakeBotocoreClientError(Exception):
    def __init__(self, response, operation_name: str):
        self.response = response
        self.operation_name = operation_name


class _FakeNoCredentialsError(Exception):
    pass


class _RecordingBedrockClient:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        body = json.loads(kwargs["body"])
        text = body["inputText"]
        vector = [1.0] * 1024 if text == "hello" else [2.0] * 1024
        return {"body": io.BytesIO(json.dumps({"embeddings": [vector]}).encode("utf-8"))}


class _FakeEndpointConnectionError(Exception):
    pass


class _FakeBotoCoreError(Exception):
    pass


def _make_boto3_stub(client: _FakeBedrockClient):
    mod = types.ModuleType("boto3")

    def client_factory(service_name: str, region_name: str | None = None):
        assert service_name == "bedrock-runtime"
        return client

    mod.client = client_factory
    return mod


def _make_botocore_stub():
    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")

    exceptions.BotoCoreError = _FakeBotoCoreError
    exceptions.ClientError = _FakeBotocoreClientError
    exceptions.EndpointConnectionError = _FakeEndpointConnectionError
    exceptions.NoCredentialsError = _FakeNoCredentialsError
    botocore.exceptions = exceptions
    return botocore, exceptions


def _reload_bedrock_module(monkeypatch, client: _FakeBedrockClient):
    boto3_stub = _make_boto3_stub(client)
    botocore_stub, exceptions_stub = _make_botocore_stub()
    monkeypatch.setitem(sys.modules, "boto3", boto3_stub)
    monkeypatch.setitem(sys.modules, "botocore", botocore_stub)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions_stub)

    mod = import_module("qdrant_loader_core.llm.providers.bedrock")
    return importlib.reload(mod)


@pytest.mark.asyncio
async def test_bedrock_provider_embed_success(monkeypatch):
    vector = [1.0] * 1024
    response_body = ("{" + f'"embeddings": [{json.dumps(vector)}]' + "}").encode("utf-8")

    client = _FakeBedrockClient(response_body=response_body)
    mod = _reload_bedrock_module(monkeypatch, client)

    settings = _make_llm_settings()
    provider = mod.BedrockProvider(settings)
    embeddings_client = provider.embeddings()

    vectors = await embeddings_client.embed(["hello"])

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024
    assert embeddings_client._provider_label == "bedrock"


@pytest.mark.asyncio
async def test_bedrock_provider_throttling_exception(monkeypatch):
    response = {
        "Error": {"Code": "ThrottlingException", "Message": "throttled"},
        "ResponseMetadata": {"HTTPStatusCode": 429},
    }
    exc = _FakeBotocoreClientError(response, "InvokeModel")
    client = _FakeBedrockClient(response_body=b"", raise_exc=exc)
    mod = _reload_bedrock_module(monkeypatch, client)

    settings = _make_llm_settings()
    provider = mod.BedrockProvider(settings)

    with pytest.raises(import_module("qdrant_loader_core.llm.errors").RateLimitedError):
        await provider.embeddings().embed(["hello"])


def test_bedrock_provider_invalid_model_id(monkeypatch):
    client = _FakeBedrockClient(response_body=b"{}")
    mod = _reload_bedrock_module(monkeypatch, client)

    with pytest.raises(import_module("qdrant_loader_core.llm.errors").InvalidRequestError):
        mod.BedrockProvider(_make_llm_settings(model_id="bad-model"))


@pytest.mark.asyncio
async def test_bedrock_provider_embed_multiple_inputs(monkeypatch):
    vector1 = [1.0] * 1024
    vector2 = [2.0] * 1024
    client = _RecordingBedrockClient()
    mod = _reload_bedrock_module(monkeypatch, client)

    settings = _make_llm_settings()
    provider = mod.BedrockProvider(settings)
    vectors = await provider.embeddings().embed(["hello", "world"])

    assert vectors == [vector1, vector2]
    assert len(client.calls) == 2
    assert {json.loads(call["body"])["inputText"] for call in client.calls} == {"hello", "world"}
    for call in client.calls:
        assert call["modelId"] == "amazon.titan-embed-text-v2:0"
        payload = json.loads(call["body"])
        assert payload["inputText"] in {"hello", "world"}
        assert payload == {"inputText": payload["inputText"]}


def test_bedrock_extract_embeddings_payload_variants():
    mod = import_module("qdrant_loader_core.llm.providers.bedrock")
    vector = [1.0, 2.0, 3.0]

    assert mod._extract_embeddings([vector]) == [vector]
    assert mod._extract_embeddings({"embedding": vector}) == [vector]
    assert mod._extract_embeddings({"embeddings": [vector]}) == [vector]
    assert mod._extract_embeddings({"data": [{"embedding": vector}, vector]}) == [vector, vector]

    with pytest.raises(import_module("qdrant_loader_core.llm.errors").InvalidRequestError):
        mod._extract_embeddings({"unknown": "payload"})

    with pytest.raises(import_module("qdrant_loader_core.llm.errors").InvalidRequestError, match="Invalid embedding element from Bedrock"):
        mod._extract_embeddings({"embedding": [1.0, None]})


@pytest.mark.asyncio
async def test_bedrock_provider_no_credentials_error(monkeypatch):
    exc = _FakeNoCredentialsError("no creds")
    client = _FakeBedrockClient(response_body=b"", raise_exc=exc)
    mod = _reload_bedrock_module(monkeypatch, client)

    settings = _make_llm_settings()
    provider = mod.BedrockProvider(settings)

    with pytest.raises(import_module("qdrant_loader_core.llm.errors").AuthError):
        await provider.embeddings().embed(["hello"])


@pytest.mark.asyncio
async def test_bedrock_provider_server_error_status_code(monkeypatch):
    response = {"ResponseMetadata": {"HTTPStatusCode": 500}}
    exc = _FakeBotocoreClientError(response, "InvokeModel")
    client = _FakeBedrockClient(response_body=b"", raise_exc=exc)
    mod = _reload_bedrock_module(monkeypatch, client)

    settings = _make_llm_settings()
    provider = mod.BedrockProvider(settings)

    with pytest.raises(import_module("qdrant_loader_core.llm.errors").ServerError):
        await provider.embeddings().embed(["hello"])


def test_bedrock_import_fallback_with_missing_boto3(monkeypatch):
    module_name = "qdrant_loader_core.llm.providers.bedrock"
    original_module = sys.modules.pop(module_name, None)

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "boto3":
            raise ImportError("no boto3")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        mod = import_module(module_name)
        assert mod.boto3 is None
        assert hasattr(mod, "ClientError")
    finally:
        sys.modules.pop(module_name, None)
        if original_module is not None:
            sys.modules[module_name] = original_module


@pytest.mark.asyncio
async def test_bedrock_provider_oversize_batch(monkeypatch):
    vector = [1.0] * 1024
    response_body = ("{" + f'"embeddings": [{json.dumps(vector)}]' + "}").encode("utf-8")
    client = _FakeBedrockClient(response_body=response_body)
    mod = _reload_bedrock_module(monkeypatch, client)

    settings = _make_llm_settings()
    provider = mod.BedrockProvider(settings)

    with pytest.raises(import_module("qdrant_loader_core.llm.errors").InvalidRequestError):
        await provider.embeddings().embed(["hello"] * (mod.BedrockEmbeddings.MAX_BATCH_SIZE + 1))


def test_factory_returns_bedrock_provider(monkeypatch):
    factory = import_module("qdrant_loader_core.llm.factory")
    settings = _make_llm_settings()
    provider = factory.create_provider(settings)
    assert provider.__class__.__name__ == "BedrockProvider"
