from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

try:
    from google import genai  # type: ignore
    from google.genai import types as genai_types  # type: ignore

    try:
        from google.genai import errors as genai_errors  # type: ignore
    except Exception:  # pragma: no cover - optional dependency surface
        genai_errors = None  # type: ignore
except Exception:  # pragma: no cover - optional dependency at this phase
    genai = None  # type: ignore
    genai_types = None  # type: ignore
    genai_errors = None  # type: ignore

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


def _map_gemini_exception(exc: Exception) -> LLMError:
    status_code: int | None = None
    if genai_errors is not None:
        try:
            if isinstance(exc, genai_errors.APIError):  # type: ignore[attr-defined]
                status_code = getattr(exc, "code", None) or getattr(
                    exc, "status_code", None
                )
        except Exception:
            pass

    if status_code is None:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)

    if isinstance(status_code, int):
        if status_code == 408 or status_code == 504:
            return LLMTimeoutError(str(exc))
        if status_code == 429:
            return RateLimitedError(str(exc))
        if status_code in (401, 403):
            return AuthError(str(exc))
        if 400 <= status_code < 500:
            return InvalidRequestError(str(exc))
        if status_code >= 500:
            return ServerError(str(exc))

    if isinstance(exc, TimeoutError):
        return LLMTimeoutError(str(exc))

    return ServerError(str(exc))


class _GeminiTokenCounter(TokenCounter):
    def __init__(self, client: Any, model: str):
        self._client = client
        self._model = model

    def count(self, text: str) -> int:
        if self._client is None:
            return len(text)
        try:
            response = self._client.models.count_tokens(
                model=self._model, contents=text
            )
            total = getattr(response, "total_tokens", None)
            if isinstance(total, int):
                return total
        except Exception:
            pass
        return len(text)


def _messages_to_contents(
    messages: list[dict[str, Any]],
) -> tuple[str | None, list[Any]]:
    """Convert OpenAI-style messages to (system_instruction, contents) for Gemini."""
    system_parts: list[str] = []
    contents: list[Any] = []
    for msg in messages:
        role = (msg.get("role") or "").lower()
        content = msg.get("content")
        if content is None:
            continue
        if not isinstance(content, str):
            content = str(content)
        if role == "system":
            system_parts.append(content)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        if genai_types is not None:
            contents.append(
                genai_types.Content(
                    role=gemini_role,
                    parts=[genai_types.Part.from_text(text=content)],
                )
            )
        else:
            contents.append({"role": gemini_role, "parts": [{"text": content}]})

    system_instruction = "\n".join(system_parts) if system_parts else None
    return system_instruction, contents


class GeminiEmbeddings(EmbeddingsClient):
    def __init__(
        self,
        client: Any,
        model: str,
        *,
        provider_label: str = "gemini",
        output_dimensionality: int | None = None,
    ):
        self._client = client
        self._model = model
        self._provider_label = provider_label
        self._output_dimensionality = output_dimensionality

    def _build_config(self) -> Any:
        if self._output_dimensionality is None or genai_types is None:
            return None
        return genai_types.EmbedContentConfig(
            output_dimensionality=self._output_dimensionality
        )

    def _wrap_inputs(self, inputs: list[str]) -> list[Any]:
        # gemini-embedding-2 aggregates a list of raw strings into ONE embedding.
        # Wrapping each input in its own Content forces one embedding per input.
        if genai_types is None:
            return list(inputs)
        return [
            genai_types.Content(parts=[genai_types.Part.from_text(text=text)])
            for text in inputs
        ]

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if not self._client:
            raise NotImplementedError("Gemini client not available")
        if not self._model:
            raise InvalidRequestError(
                "Gemini embeddings model is not configured. "
                "Set global.llm.models.embeddings in your config "
                "(e.g. 'gemini-embedding-2' or 'gemini-embedding-001')."
            )
        if not inputs:
            return []
        import asyncio

        config = self._build_config()
        call_kwargs: dict[str, Any] = {
            "model": self._model,
            "contents": self._wrap_inputs(inputs),
        }
        if config is not None:
            call_kwargs["config"] = config

        started = datetime.now(UTC)
        try:
            response = await asyncio.to_thread(
                self._client.models.embed_content, **call_kwargs
            )
            duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            try:
                logger.info(
                    "LLM request",
                    provider=self._provider_label,
                    operation="embeddings",
                    model=self._model,
                    inputs=len(inputs),
                    latency_ms=duration_ms,
                )
            except Exception:
                pass

            embeddings = getattr(response, "embeddings", None) or []
            vectors = [list(getattr(item, "values", []) or []) for item in embeddings]
            if len(vectors) != len(inputs):
                raise ServerError(
                    f"Gemini embed_content returned {len(vectors)} embeddings "
                    f"for {len(inputs)} inputs (expected 1:1). "
                    f"Verify the model id {self._model!r} supports per-input embeddings."
                )
            return vectors
        except Exception as exc:
            mapped = _map_gemini_exception(exc)
            try:
                logger.warning(
                    "LLM error",
                    provider=self._provider_label,
                    operation="embeddings",
                    model=self._model,
                    error=type(exc).__name__,
                )
            except Exception:
                pass
            raise mapped


class GeminiChat(ChatClient):
    def __init__(
        self,
        client: Any,
        model: str,
        *,
        provider_label: str = "gemini",
    ):
        self._client = client
        self._model = model
        self._provider_label = provider_label

    async def chat(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        if not self._client:
            raise NotImplementedError("Gemini client not available")

        model_name = kwargs.pop("model", self._model)
        if not model_name:
            raise InvalidRequestError(
                "Gemini chat model is not configured. "
                "Set global.llm.models.chat in your config "
                "(e.g. 'gemini-2.0-flash')."
            )
        system_instruction, contents = _messages_to_contents(messages)

        config_kwargs: dict[str, Any] = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        for src_key, dst_key in (
            ("temperature", "temperature"),
            ("top_p", "top_p"),
            ("max_tokens", "max_output_tokens"),
            ("stop", "stop_sequences"),
            ("seed", "seed"),
        ):
            if src_key in kwargs and kwargs[src_key] is not None:
                config_kwargs[dst_key] = kwargs[src_key]

        config = None
        if config_kwargs and genai_types is not None:
            config = genai_types.GenerateContentConfig(**config_kwargs)
        import asyncio

        started = datetime.now(UTC)
        try:
            call_kwargs: dict[str, Any] = {
                "model": model_name,
                "contents": contents,
            }
            if config is not None:
                call_kwargs["config"] = config

            response = await asyncio.to_thread(
                self._client.models.generate_content, **call_kwargs
            )
            duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            try:
                logger.info(
                    "LLM request",
                    provider=self._provider_label,
                    operation="chat",
                    model=model_name,
                    messages=len(messages),
                    latency_ms=duration_ms,
                )
            except Exception:
                pass

            text = getattr(response, "text", "") or ""

            usage_meta = getattr(response, "usage_metadata", None)
            normalized_usage = None
            if usage_meta is not None:
                normalized_usage = {
                    "prompt_tokens": getattr(usage_meta, "prompt_token_count", None),
                    "completion_tokens": getattr(
                        usage_meta, "candidates_token_count", None
                    ),
                    "total_tokens": getattr(usage_meta, "total_token_count", None),
                }

            return {
                "text": text,
                "raw": response,
                "usage": normalized_usage,
                "model": getattr(response, "model_version", model_name) or model_name,
            }
        except Exception as exc:
            mapped = _map_gemini_exception(exc)
            try:
                logger.warning(
                    "LLM error",
                    provider=self._provider_label,
                    operation="chat",
                    model=model_name,
                    error=type(exc).__name__,
                )
            except Exception:
                pass
            raise mapped


class GeminiProvider(LLMProvider):
    def __init__(self, settings: LLMSettings):
        self._settings = settings
        if genai is None:
            self._client = None
        else:
            kwargs: dict[str, Any] = {}
            if settings.api_key:
                kwargs["api_key"] = settings.api_key
            provider_opts = settings.provider_options or {}
            if provider_opts.get("vertexai"):
                kwargs["vertexai"] = True
                if provider_opts.get("project"):
                    kwargs["project"] = provider_opts["project"]
                if provider_opts.get("location"):
                    kwargs["location"] = provider_opts["location"]
            self._client = genai.Client(**kwargs)

    def embeddings(self) -> EmbeddingsClient:
        model = self._settings.models.get("embeddings", "")
        return GeminiEmbeddings(
            self._client,
            model,
            provider_label="gemini",
            output_dimensionality=self._settings.embeddings.vector_size,
        )

    def chat(self) -> ChatClient:
        model = self._settings.models.get("chat", "")
        return GeminiChat(self._client, model, provider_label="gemini")

    def tokenizer(self) -> TokenCounter:
        model = self._settings.models.get("chat") or self._settings.models.get(
            "embeddings", ""
        )
        return _GeminiTokenCounter(self._client, model)
