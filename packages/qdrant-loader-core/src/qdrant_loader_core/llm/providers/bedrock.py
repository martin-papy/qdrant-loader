from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

try:
    import boto3
except ImportError:
    boto3 = None  # type: ignore[assignment]

from ...logging import LoggingConfig
from ..errors import (
    InvalidRequestError,
    LLMError,
    ServerError,
)
from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter

# Re-exported exception types are intentionally kept here.
#
# They are used by:
# 1. Runtime exception mapping in _map_bedrock_exception()
# 2. Import fallback behavior when boto3 / botocore is unavailable
# 3. Unit tests that verify the module still exposes these symbols
#
# Do not remove these imports even if they appear unused, as they are
# part of the module contract and support graceful degradation.
from .bedrock_utils import (
    BedrockTokenizer,
    _extract_embeddings,
    _map_bedrock_exception,
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
)

logger = LoggingConfig.get_logger(__name__)

DEFAULT_VECTOR_SIZES: dict[str, int] = {
    "amazon.titan-embed-text-v2:0": 1024,
    "amazon.titan-embed-text-v1": 1536,
}


class BedrockEmbeddings(EmbeddingsClient):
    """Embeddings client for Bedrock Titan models, invoking one API call per input."""
    MAX_BATCH_SIZE = 1000

    def __init__(
        self,
        client: Any,
        model_id: str,
        expected_vector_size: int | None = None,
        *,
        provisioned_throughput_arn: str | None = None,
        provider_label: str = "bedrock",
        concurrency: int = 8,
    ):
        self._client = client
        self._model_id = model_id
        self._expected_vector_size = expected_vector_size
        self._provisioned_throughput_arn = provisioned_throughput_arn
        self._provider_label = provider_label
        self._concurrency = concurrency
        if self._concurrency < 1:
            raise InvalidRequestError(
                "Bedrock embeddings 'concurrency' must be a positive integer"
            )
        self._semaphore = asyncio.Semaphore(self._concurrency)

    def _build_invoke_kwargs(self, text: str) -> dict[str, Any]:
        payload_body = {
            "inputText": text
        }

        if self._model_id.startswith("amazon.titan-embed-text-v2") and self._expected_vector_size is not None:
            if self._expected_vector_size != DEFAULT_VECTOR_SIZES["amazon.titan-embed-text-v2:0"]:
                payload_body["dimensions"] = self._expected_vector_size

        invoke_kwargs: dict[str, Any] = {
            "modelId": self._provisioned_throughput_arn or self._model_id,
            "contentType": "application/json",
            "accept": "application/json",
            "body": json.dumps(payload_body),
        }

        return invoke_kwargs


    def _read_response_body(self, response: Any) -> str:
        body_data = (
            response.get("body")
            if isinstance(response, dict)
            else getattr(response, "body", None)
        )

        if body_data is None:
            raise ServerError(
                "Bedrock response body missing"
            )

        if hasattr(body_data, "read"):
            body_bytes = body_data.read()
        else:
            body_bytes = body_data

        if isinstance(body_bytes, bytes):
            return body_bytes.decode("utf-8")

        if isinstance(body_bytes, str):
            return body_bytes

        raise ServerError(
            "Bedrock response body is not bytes or string"
        )


    def _parse_single_embedding(
        self,
        raw_text: str,
    ) -> list[float]:
        payload = json.loads(raw_text)
        embeddings = _extract_embeddings(payload)

        if len(embeddings) != 1:
            raise ServerError(
                "Bedrock single request must return exactly one embedding"
            )

        return embeddings[0]


    def _validate_vector(
        self,
        vector: list[float],
    ) -> None:
        if (
            self._expected_vector_size is not None
            and len(vector) != self._expected_vector_size
        ):
            raise ServerError(
                f"Bedrock returned embedding vector with unexpected dimension: "
                f"expected {self._expected_vector_size}, got {len(vector)}"
            )


    async def _invoke_single(
        self,
        text: str,
    ) -> list[float]:
        invoke_kwargs = self._build_invoke_kwargs(text)
        started = datetime.now(UTC)

        try:
            response = await asyncio.to_thread(
                self._client.invoke_model,
                **invoke_kwargs,
            )

            duration_ms = int(
                (datetime.now(UTC) - started).total_seconds() * 1000
            )

            logger.info(
                "LLM request",
                provider=self._provider_label,
                operation="embeddings",
                model=self._model_id,
                latency_ms=duration_ms,
                inputs=1,
            )

            raw_text = self._read_response_body(response)
            vector = self._parse_single_embedding(raw_text)
            self._validate_vector(vector)

            return vector

        except LLMError:
            raise

        except Exception as exc:
            mapped = _map_bedrock_exception(exc)

            logger.warning(
                "LLM error",
                provider=self._provider_label,
                operation="embeddings",
                model=self._model_id,
                error=type(exc).__name__,
            )

            raise mapped from exc

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if self._client is None:
            raise NotImplementedError(
                "Bedrock client not available"
            )

        if not inputs:
            return []

        if len(inputs) > self.MAX_BATCH_SIZE:
            raise InvalidRequestError(
                f"Bedrock embedding batch size cannot exceed {self.MAX_BATCH_SIZE}"
            )

        async def _one(text: str) -> list[float]:
            async with self._semaphore:
                return await self._invoke_single(text)

        return await asyncio.gather(
            *[_one(text) for text in inputs]
        )

class _BedrockChat(ChatClient):
    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Bedrock chat is not implemented")


class BedrockProvider(LLMProvider):
    """LLM provider wrapper for AWS Bedrock Titan embedding models."""
    SUPPORTED_MODELS = frozenset({
        "amazon.titan-embed-text-v2:0",
        "amazon.titan-embed-text-v1",
        # "cohere.embed-english-v3",
    })

    def __init__(
        self,
        settings: LLMSettings,
        *,
        client: Any = None,
    ):
        self._settings = settings
        provider_options = settings.provider_options or {}

        model_id = (
            provider_options.get("model_id")
            or settings.models.get("embeddings")
        )

        self._model_id = (
            str(model_id)
            if model_id is not None
            else ""
        )

        self._aws_region = provider_options.get(
            "aws_region"
        )

        self._provisioned_throughput_arn = provider_options.get(
            "provisioned_throughput_arn"
        )

        try:
            self._concurrency = int(provider_options.get("concurrency", 8))
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError(
                "Bedrock provider 'concurrency' must be a positive integer"
            ) from exc

        if self._concurrency < 1:
            raise InvalidRequestError(
                "Bedrock provider 'concurrency' must be a positive integer"
            )

        if not self._model_id:
            raise InvalidRequestError(
                "Bedrock provider requires 'model_id' in "
                "llm.provider_options or llm.models.embeddings"
            )

        if self._model_id not in self.SUPPORTED_MODELS:
            raise InvalidRequestError(
                "Bedrock provider only supports "
                f"{sorted(self.SUPPORTED_MODELS)}, "
                f"got {self._model_id!r}"
            )

        self._vector_size = (
            settings.embeddings.vector_size
            if settings.embeddings.vector_size is not None
            else DEFAULT_VECTOR_SIZES.get(self._model_id, 1024)
        )

        self._client = client or (
            boto3.client(
                "bedrock-runtime",
                region_name=self._aws_region,
            )
            if boto3 is not None
            else None
        )

    def embeddings(self) -> EmbeddingsClient:
        return BedrockEmbeddings(
            self._client,
            self._model_id,
            self._vector_size,
            provisioned_throughput_arn=self._provisioned_throughput_arn,
            provider_label="bedrock",
            concurrency=self._concurrency,
        )

    def chat(self) -> ChatClient:
        raise NotImplementedError(
            "Bedrock provider does not support chat()"
        )

    def tokenizer(self) -> TokenCounter:
        return BedrockTokenizer()
    