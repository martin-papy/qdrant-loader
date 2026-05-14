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
except Exception:
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

        normalized.append([
            float(value)
            for value in vector
        ])

    return normalized


class BedrockTokenizer(TokenCounter):
    def count(self, text: str) -> int:
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
    ):
        self._client = client
        self._model_id = model_id
        self._expected_vector_size = expected_vector_size
        self._provisioned_throughput_arn = provisioned_throughput_arn
        self._provider_label = provider_label

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if self._client is None:
            raise NotImplementedError("Bedrock client not available")

        if len(inputs) > self.MAX_BATCH_SIZE:
            raise InvalidRequestError(
                f"Bedrock embedding batch size cannot exceed {self.MAX_BATCH_SIZE}"
            )

        if len(inputs) == 1:
            payload_body = {"inputText": inputs[0]}
        else:
            payload_body = {"inputText": inputs}

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

        started = datetime.now(UTC)
        try:
            response = await asyncio.to_thread(self._client.invoke_model, **invoke_kwargs)
            duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            try:
                logger.info(
                    "LLM request",
                    provider=self._provider_label,
                    operation="embeddings",
                    model=self._model_id,
                    latency_ms=duration_ms,
                    inputs=len(inputs),
                )
            except Exception:
                pass

            body_data = response.get("body") if isinstance(response, dict) else getattr(response, "body", None)
            if body_data is None:
                raise ServerError("Bedrock response body missing")

            if hasattr(body_data, "read"):
                body_bytes = body_data.read()
            else:
                body_bytes = body_data

            if isinstance(body_bytes, bytes):
                raw_text = body_bytes.decode("utf-8")
            elif isinstance(body_bytes, str):
                raw_text = body_bytes
            else:
                raise ServerError("Bedrock response body is not bytes or string")

            payload = json.loads(raw_text)
            embeddings = _extract_embeddings(payload)

            if self._expected_vector_size is not None:
                for vector in embeddings:
                    if len(vector) != self._expected_vector_size:
                        raise ServerError(
                            "Bedrock returned embedding vector with unexpected dimension"
                        )

            return embeddings
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
            raise mapped


class _BedrockChat(ChatClient):
    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Bedrock chat is not implemented")


class BedrockProvider(LLMProvider):
    def __init__(self, settings: LLMSettings):
        self._settings = settings
        provider_options = settings.provider_options or {}
        model_id = provider_options.get("model_id") or settings.models.get("embeddings")
        self._model_id = str(model_id) if model_id is not None else ""
        self._aws_region = provider_options.get("aws_region")
        self._provisioned_throughput_arn = provider_options.get("provisioned_throughput_arn")

        if not self._model_id:
            raise InvalidRequestError(
                "Bedrock provider requires 'model_id' in llm.provider_options or llm.models.embeddings"
            )
        if self._model_id != "amazon.titan-embed-text-v2:0":
            raise InvalidRequestError(
                "Bedrock provider only supports amazon.titan-embed-text-v2:0"
            )

        self._vector_size = settings.embeddings.vector_size or 1024
        self._client = (
            boto3.client("bedrock-runtime", region_name=self._aws_region)
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
        )

    def chat(self) -> ChatClient:
        return _BedrockChat()

    def tokenizer(self) -> TokenCounter:
        return BedrockTokenizer()
