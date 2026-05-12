import importlib
import io
import json
import sys
import types
from importlib import import_module

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

    class _FakeNoCredentialsError(Exception):
        pass

    class _FakeEndpointConnectionError(Exception):
        pass

    class _FakeBotoCoreError(Exception):
        pass

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
