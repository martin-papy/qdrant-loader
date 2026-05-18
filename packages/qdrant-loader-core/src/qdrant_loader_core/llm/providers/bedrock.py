from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

try:
    import boto3
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        EndpointConnectionError,
        NoCredentialsError,
    )
except ImportError:
    boto3 = None  # type: ignore[assignment]

    class _BedrockBaseError(Exception):
        pass

    class _BedrockClientError(_BedrockBaseError):
        pass

    class _BedrockNoCredentialsError(_BedrockBaseError):
        pass

    class _BedrockEndpointConnectionError(_BedrockBaseError):
        pass

    class _BedrockBotoCoreError(_BedrockBaseError):
        pass

    BotoCoreError = _BedrockBotoCoreError
    ClientError = _BedrockClientError
    EndpointConnectionError = _BedrockEndpointConnectionError
    NoCredentialsError = _BedrockNoCredentialsError

from ...logging import LoggingConfig
from ..errors import (
    AuthError,
    InvalidRequestError,
    LLMError,
    RateLimitedError,
    ServerError,
)
from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter

logger = LoggingConfig.get_logger(__name__)


def _map_bedrock_exception(exc: Exception) -> LLMError:
    if isinstance(exc, NoCredentialsError):
        return AuthError(str(exc))

    error_code = ""
    status_code = None
    if hasattr(exc, "response"):
        try:
            error_code = exc.response.get("Error", {}).get("Code", "")
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        except Exception:
            pass

    if error_code in ("ThrottlingException", "TooManyRequestsException", "Throttling"):
        return RateLimitedError(str(exc))
    if error_code in (
        "AccessDeniedException",
        "UnrecognizedClientException",
        "InvalidSignatureException",
    ):
        return AuthError(str(exc))
    if error_code in (
        "ValidationException",
        "InvalidParameterException",
        "ResourceNotFoundException",
        "ModelError",
        "UnsupportedOperationException",
    ):
        return InvalidRequestError(str(exc))
    if isinstance(exc, ClientError):
        if isinstance(status_code, int) and status_code >= 500:
            return ServerError(str(exc))
        if isinstance(status_code, int) and status_code >= 400:
            return InvalidRequestError(str(exc))
        return ServerError(str(exc))

    if isinstance(exc, EndpointConnectionError):
        return ServerError(str(exc))

    if isinstance(exc, BotoCoreError):
        return ServerError(str(exc))

    return ServerError(str(exc))

def _extract_embeddings(response_payload: Any) -> list[list[float]]:
    if not isinstance(response_payload, (dict, list)):
        raise InvalidRequestError(
            "Bedrock response has unexpected format"
        )

    raw_embeddings: list[Any]

    if isinstance(response_payload, list):
        raw_embeddings = response_payload

    elif "embedding" in response_payload:
        raw_embeddings = [response_payload["embedding"]]

    elif "embeddings" in response_payload:
        raw_embeddings = response_payload["embeddings"]

    elif (
        "data" in response_payload
        and isinstance(response_payload["data"], list)
    ):
        raw_embeddings = [
            item.get("embedding", item)
            if isinstance(item, dict)
            else item
            for item in response_payload["data"]
        ]

    else:
        raise InvalidRequestError(
            "Bedrock response did not contain embeddings"
        )

    normalized: list[list[float]] = []

    for vector in raw_embeddings:
        if isinstance(vector, dict):
            vector = vector.get("embedding", vector)

        if not isinstance(vector, list):
            raise InvalidRequestError(
                "Bedrock embedding payload must be a list of floats"
            )

        try:
            normalized.append([
                float(value)
                for value in vector
            ])
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError(
                f"Invalid embedding element from Bedrock: {exc}"
            ) from exc

    return normalized


class BedrockTokenizer(TokenCounter):
    def count(self, text: str) -> int:
        # TODO:
        # Replace with a proper tokenizer for Bedrock models
        # (for example Anthropic tokenizer or HuggingFace AutoTokenizer
        # for Titan models). Current implementation matches the same
        # fallback behavior used in the OpenAI provider and counts
        # characters only, not actual model tokens.
        return len(text)

class BedrockEmbeddings(EmbeddingsClient):
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

    def _build_invoke_kwargs(self, text: str) -> dict[str, Any]:
        payload_body = {
            "inputText": text
        }

        invoke_kwargs: dict[str, Any] = {
            "modelId": self._model_id,
            "contentType": "application/json",
            "accept": "application/json",
            "body": json.dumps(payload_body),
        }

        if self._provisioned_throughput_arn:
            invoke_kwargs["provisionedThroughputArn"] = (
                self._provisioned_throughput_arn
            )

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
                "Bedrock returned embedding vector with unexpected dimension"
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

            try:
                logger.info(
                    "LLM request",
                    provider=self._provider_label,
                    operation="embeddings",
                    model=self._model_id,
                    latency_ms=duration_ms,
                    inputs=1,
                )
            except Exception:
                pass

            raw_text = self._read_response_body(response)
            vector = self._parse_single_embedding(raw_text)
            self._validate_vector(vector)

            return vector

        except LLMError:
            raise

        except Exception as exc:
            mapped = _map_bedrock_exception(exc)

            try:
                logger.warning(
                    "LLM error",
                    provider=self._provider_label,
                    operation="embeddings",
                    model=self._model_id,
                    error=type(exc).__name__,
                )
            except Exception:
                pass

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

        semaphore = asyncio.Semaphore(
            self._concurrency
        )

        async def _one(text: str) -> list[float]:
            async with semaphore:
                return await self._invoke_single(text)

        return await asyncio.gather(
            *[_one(text) for text in inputs]
        )

class _BedrockChat(ChatClient):
    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Bedrock chat is not implemented")


class BedrockProvider(LLMProvider):
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

        self._concurrency = int(
            provider_options.get("concurrency", 8)
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
            or 1024
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
