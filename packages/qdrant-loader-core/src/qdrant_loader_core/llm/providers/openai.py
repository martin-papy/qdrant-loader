from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

try:
    from openai import OpenAI  # type: ignore

    # New-style exception classes (OpenAI Python SDK >=1.x)
    try:  # nested to avoid failing entirely on older clients
        from openai import (  # type: ignore
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            RateLimitError,
        )
    except Exception:  # pragma: no cover - optional dependency surface
        APIConnectionError = APIStatusError = APITimeoutError = AuthenticationError = BadRequestError = RateLimitError = ()  # type: ignore
except Exception:  # pragma: no cover - optional dependency at this phase
    OpenAI = None  # type: ignore
    APIConnectionError = APIStatusError = APITimeoutError = AuthenticationError = BadRequestError = RateLimitError = ()  # type: ignore

from ...logging import LoggingConfig
from ..errors import (
    AuthError,
    InvalidRequestError,
    LLMError,
    RateLimitedError,
    ServerError,
)
from ..errors import TimeoutError as LLMTimeoutError
from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter

logger = LoggingConfig.get_logger(__name__)


def _safe_host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).hostname or None
    except Exception:
        return None


def _map_openai_exception(exc: Exception) -> LLMError:
    try:
        # Rate limit
        if RateLimitError and isinstance(exc, RateLimitError):  # type: ignore[arg-type]
            return RateLimitedError(str(exc))
        # Timeout
        if APITimeoutError and isinstance(exc, APITimeoutError):  # type: ignore[arg-type]
            return LLMTimeoutError(str(exc))
        # Auth
        if AuthenticationError and isinstance(exc, AuthenticationError):  # type: ignore[arg-type]
            return AuthError(str(exc))
        # Bad request / invalid params
        if BadRequestError and isinstance(exc, BadRequestError):  # type: ignore[arg-type]
            return InvalidRequestError(str(exc))
        # API status error (typically non-2xx)
        if APIStatusError and isinstance(exc, APIStatusError):  # type: ignore[arg-type]
            # Best-effort: check for status code
            status_code = getattr(exc, "status_code", None) or getattr(
                getattr(exc, "response", None), "status_code", None
            )
            if isinstance(status_code, int) and 400 <= status_code < 500:
                if status_code == 429:
                    return RateLimitedError(str(exc))
                if status_code in (401, 403):
                    return AuthError(str(exc))
                return InvalidRequestError(str(exc))
            return ServerError(str(exc))
        # Connection-level errors
        if APIConnectionError and isinstance(exc, APIConnectionError):  # type: ignore[arg-type]
            return ServerError(str(exc))
    except Exception:
        pass
    # Fallback
    return ServerError(str(exc))


class _OpenAITokenCounter(TokenCounter):
    def __init__(self, tokenizer: str):
        self._tokenizer = tokenizer

    def count(self, text: str) -> int:
        # Phase 0: fallback to naive length; real tiktoken impl to come later
        return len(text)


class OpenAIEmbeddings(EmbeddingsClient):
    def __init__(
        self,
        client: Any,
        model: str,
        base_host: str | None,
        *,
        provider_label: str = "openai",
    ):
        self._client = client
        self._model = model
        self._base_host = base_host
        self._provider_label = provider_label

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if not self._client:
            raise NotImplementedError("OpenAI client not available")
        # Use thread offloading to keep async interface consistent with sync client
        import asyncio

        started = datetime.now(UTC)
        try:
            response = await asyncio.to_thread(
                self._client.embeddings.create, model=self._model, input=inputs
            )
            duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            try:
                logger.info(
                    "LLM request",
                    provider=self._provider_label,
                    operation="embeddings",
                    model=self._model,
                    base_host=self._base_host,
                    inputs=len(inputs),
                    latency_ms=duration_ms,
                )
            except Exception:
                pass
            return [item.embedding for item in response.data]
        except Exception as exc:  # Normalize errors
            mapped = _map_openai_exception(exc)
            try:
                logger.warning(
                    "LLM error",
                    provider=self._provider_label,
                    operation="embeddings",
                    model=self._model,
                    base_host=self._base_host,
                    error=type(exc).__name__,
                )
            except Exception:
                pass
            raise mapped


class OpenAIChat(ChatClient):
    def __init__(
        self,
        client: Any,
        model: str,
        base_host: str | None,
        *,
        provider_label: str = "openai",
    ):
        self._client = client
        self._model = model
        self._base_host = base_host
        self._provider_label = provider_label

    async def chat(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        if not self._client:
            raise NotImplementedError("OpenAI client not available")

        # Normalize kwargs to OpenAI python client parameters
        create_kwargs: dict[str, Any] = {}
        for key in (
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "seed",
            "response_format",
        ):
            if key in kwargs and kwargs[key] is not None:
                create_kwargs[key] = kwargs[key]

        # Allow model override per-call
        model_name = kwargs.pop("model", self._model)

        import asyncio

        # The OpenAI python client call is sync for chat.completions
        started = datetime.now(UTC)
        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=model_name,
                messages=messages,
                **create_kwargs,
            )
            duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            try:
                logger.info(
                    "LLM request",
                    provider=self._provider_label,
                    operation="chat",
                    model=model_name,
                    base_host=self._base_host,
                    messages=len(messages),
                    latency_ms=duration_ms,
                )
            except Exception:
                pass

            # Normalize to provider-agnostic dict
            choice0 = (
                response.choices[0] if getattr(response, "choices", None) else None
            )
            text = ""
            if choice0 is not None:
                message = getattr(choice0, "message", None)
                if message is not None:
                    text = getattr(message, "content", "") or ""

            usage = getattr(response, "usage", None)
            normalized_usage = None
            if usage is not None:
                normalized_usage = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                }

            return {
                "text": text,
                "raw": response,
                "usage": normalized_usage,
                "model": getattr(response, "model", model_name),
            }
        except Exception as exc:
            mapped = _map_openai_exception(exc)
            try:
                logger.warning(
                    "LLM error",
                    provider=self._provider_label,
                    operation="chat",
                    model=model_name,
                    base_host=self._base_host,
                    error=type(exc).__name__,
                )
            except Exception:
                pass
            raise mapped


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: LLMSettings):
        self._settings = settings
        self._base_host = _safe_host(settings.base_url)
        if OpenAI is None:
            self._client = None
        else:
            kwargs: dict[str, Any] = {}
            if settings.base_url:
                kwargs["base_url"] = settings.base_url
            if settings.api_key:
                kwargs["api_key"] = settings.api_key
            self._client = OpenAI(**kwargs)

    def embeddings(self) -> EmbeddingsClient:
        model = self._settings.models.get("embeddings", "")
        return OpenAIEmbeddings(
            self._client, model, self._base_host, provider_label="openai"
        )

    def chat(self) -> ChatClient:
        model = self._settings.models.get("chat", "")
        return OpenAIChat(self._client, model, self._base_host, provider_label="openai")

    def tokenizer(self) -> TokenCounter:
        return _OpenAITokenCounter(self._settings.tokenizer)
