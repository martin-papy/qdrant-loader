from __future__ import annotations

import json
from typing import Any

try:
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        EndpointConnectionError,
        NoCredentialsError,
    )
except ImportError:
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

from ..errors import (
    AuthError,
    InvalidRequestError,
    LLMError,
    RateLimitedError,
    ServerError,
)
from ..types import TokenCounter
from ..types import TokenCounter


def _map_bedrock_exception(exc: Exception) -> LLMError:
    """Map a botocore/boto3 exception into a qdrant_loader_core LLMError."""
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
    """Normalize Bedrock embedding response payloads into a list of float vectors."""
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
    """Fallback tokenizer that approximates token count by character length."""
    def count(self, text: str) -> int:
        # TODO:
        # Replace with a proper tokenizer for Bedrock models
        # (for example Anthropic tokenizer or HuggingFace AutoTokenizer
        # for Titan models). Current implementation matches the same
        # fallback behavior used in the OpenAI provider and counts
        # characters only, not actual model tokens.
        return len(text)
