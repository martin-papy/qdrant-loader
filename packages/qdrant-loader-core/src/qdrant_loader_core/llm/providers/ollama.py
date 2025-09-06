from __future__ import annotations

from typing import Any

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore

from ...logging import LoggingConfig
from ..errors import (
    AuthError,
    InvalidRequestError,
    RateLimitedError,
    ServerError,
)
from ..errors import TimeoutError as LLMTimeoutError
from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter

logger = LoggingConfig.get_logger(__name__)


def _join_url(base: str | None, path: str) -> str:
    base = (base or "").rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}" if base else f"/{path}"


class OllamaEmbeddings(EmbeddingsClient):
    def __init__(
        self,
        base_url: str | None,
        model: str,
        headers: dict[str, str] | None,
        *,
        timeout_s: float | None = None,
        provider_options: dict[str, Any] | None = None,
    ):
        self._base_url = (base_url or "http://localhost:11434").rstrip("/")
        self._model = model
        self._headers = headers or {}
        self._timeout_s = float(timeout_s) if timeout_s is not None else 30.0
        self._provider_options = provider_options or {}

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if httpx is None:
            raise NotImplementedError("httpx not available for Ollama embeddings")

        # Prefer OpenAI-compatible if base_url seems to expose /v1
        use_v1 = "/v1" in (self._base_url or "")
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            try:
                if use_v1:
                    # OpenAI-compatible embeddings endpoint
                    url = _join_url(self._base_url, "/embeddings")
                    payload = {"model": self._model, "input": inputs}
                    resp = await client.post(url, json=payload, headers=self._headers)
                    resp.raise_for_status()
                    data = resp.json()
                    logger.info(
                        "LLM request",
                        provider="ollama",
                        operation="embeddings",
                        model=self._model,
                        base_host=self._base_url,
                        inputs=len(inputs),
                        # latency for v1 path hard to compute here; omitted for now
                    )
                    return [item["embedding"] for item in data.get("data", [])]
                else:
                    # Determine native endpoint preference: embed | embeddings | auto (default)
                    native_pref = str(
                        self._provider_options.get("native_endpoint", "auto")
                    ).lower()
                    prefer_embed = native_pref != "embeddings"

                    # Try batch embed first when preferred
                    if prefer_embed:
                        url = _join_url(self._base_url, "/api/embed")
                        payload = {"model": self._model, "input": inputs}
                        try:
                            resp = await client.post(
                                url, json=payload, headers=self._headers
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            vectors = data.get("embeddings")
                            if not isinstance(vectors, list) or (
                                len(vectors) != len(inputs)
                            ):
                                raise ValueError(
                                    "Invalid embeddings response from /api/embed"
                                )
                            # Normalize to list[list[float]]
                            norm = [list(vec) for vec in vectors]
                            logger.info(
                                "LLM request",
                                provider="ollama",
                                operation="embeddings",
                                model=self._model,
                                base_host=self._base_url,
                                inputs=len(inputs),
                                # latency for native batch path not measured in this stub
                            )
                            return norm
                        except httpx.HTTPStatusError as exc:
                            status = exc.response.status_code if exc.response else None
                            # Fallback for servers that don't support /api/embed
                            if status not in (404, 405, 501):
                                raise

                    # Per-item embeddings endpoint fallback or preference
                    url = _join_url(self._base_url, "/api/embeddings")
                    vectors2: list[list[float]] = []
                    for text in inputs:
                        payload = {"model": self._model, "input": text}
                        resp = await client.post(
                            url, json=payload, headers=self._headers
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        emb = data.get("embedding")
                        if emb is None and isinstance(data.get("data"), dict):
                            emb = data["data"].get("embedding")
                        if emb is None:
                            raise ValueError(
                                "Invalid embedding response from /api/embeddings"
                            )
                        vectors2.append(list(emb))
                    logger.info(
                        "LLM request",
                        provider="ollama",
                        operation="embeddings",
                        model=self._model,
                        base_host=self._base_url,
                        inputs=len(inputs),
                        # latency for per-item path not measured in this stub
                    )
                    return vectors2
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError(str(exc))
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response else None
                if status == 401:
                    raise AuthError(str(exc))
                if status == 429:
                    raise RateLimitedError(str(exc))
                if status and 400 <= status < 500:
                    raise InvalidRequestError(str(exc))
                raise ServerError(str(exc))
            except httpx.HTTPError as exc:
                raise ServerError(str(exc))


class OllamaChat(ChatClient):
    def __init__(
        self, base_url: str | None, model: str, headers: dict[str, str] | None
    ):
        self._base_url = base_url or "http://localhost:11434"
        self._model = model
        self._headers = headers or {}

    async def chat(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        if httpx is None:
            raise NotImplementedError("httpx not available for Ollama chat")

        # Prefer OpenAI-compatible if base_url exposes /v1
        use_v1 = "/v1" in (self._base_url or "")
        # Flatten messages to a single prompt for native API; preserve roles when possible
        if use_v1:
            url = _join_url(self._base_url, "/chat/completions")
            payload = {"model": self._model, "messages": messages}
            # Map common kwargs
            for k in ("temperature", "max_tokens", "top_p", "stop"):
                if k in kwargs and kwargs[k] is not None:
                    payload[k] = kwargs[k]
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    from datetime import UTC, datetime

                    started = datetime.now(UTC)
                    resp = await client.post(url, json=payload, headers=self._headers)
                    resp.raise_for_status()
                    data = resp.json()
                    text = ""
                    choices = data.get("choices") or []
                    if choices:
                        msg = (choices[0] or {}).get("message") or {}
                        text = msg.get("content", "") or ""
                    duration_ms = int(
                        (datetime.now(UTC) - started).total_seconds() * 1000
                    )
                    logger.info(
                        "LLM request",
                        provider="ollama",
                        operation="chat",
                        model=self._model,
                        base_host=self._base_url,
                        messages=len(messages),
                        latency_ms=duration_ms,
                    )
                    return {
                        "text": text,
                        "raw": data,
                        "usage": data.get("usage"),
                        "model": data.get("model", self._model),
                    }
                except httpx.TimeoutException as exc:
                    raise LLMTimeoutError(str(exc))
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code if exc.response else None
                    if status == 401:
                        raise AuthError(str(exc))
                    if status == 429:
                        raise RateLimitedError(str(exc))
                    if status and 400 <= status < 500:
                        raise InvalidRequestError(str(exc))
                    raise ServerError(str(exc))
                except httpx.HTTPError as exc:
                    raise ServerError(str(exc))
        else:
            # Native API
            url = _join_url(self._base_url, "/api/chat")
            payload = {
                "model": self._model,
                "messages": messages,
                "stream": False,
            }
            if "temperature" in kwargs and kwargs["temperature"] is not None:
                payload["options"] = {"temperature": kwargs["temperature"]}
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    from datetime import UTC, datetime

                    started = datetime.now(UTC)
                    resp = await client.post(url, json=payload, headers=self._headers)
                    resp.raise_for_status()
                    data = resp.json()
                    # Ollama native returns {"message": {"content": "..."}, ...}
                    text = ""
                    if isinstance(data.get("message"), dict):
                        text = data["message"].get("content", "") or ""
                    duration_ms = int(
                        (datetime.now(UTC) - started).total_seconds() * 1000
                    )
                    logger.info(
                        "LLM request",
                        provider="ollama",
                        operation="chat",
                        model=self._model,
                        base_host=self._base_url,
                        messages=len(messages),
                        latency_ms=duration_ms,
                    )
                    return {
                        "text": text,
                        "raw": data,
                        "usage": None,
                        "model": self._model,
                    }
                except httpx.TimeoutException as exc:
                    raise LLMTimeoutError(str(exc))
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code if exc.response else None
                    if status == 401:
                        raise AuthError(str(exc))
                    if status == 429:
                        raise RateLimitedError(str(exc))
                    if status and 400 <= status < 500:
                        raise InvalidRequestError(str(exc))
                    raise ServerError(str(exc))
                except httpx.HTTPError as exc:
                    raise ServerError(str(exc))


class OllamaTokenizer(TokenCounter):
    def count(self, text: str) -> int:
        return len(text)


class OllamaProvider(LLMProvider):
    def __init__(self, settings: LLMSettings):
        self._settings = settings

    def embeddings(self) -> EmbeddingsClient:
        model = self._settings.models.get("embeddings", "")
        timeout = (
            self._settings.request.timeout_s
            if self._settings and self._settings.request
            else 30.0
        )
        return OllamaEmbeddings(
            self._settings.base_url,
            model,
            self._settings.headers,
            timeout_s=timeout,
            provider_options=self._settings.provider_options,
        )

    def chat(self) -> ChatClient:
        model = self._settings.models.get("chat", "")
        return OllamaChat(self._settings.base_url, model, self._settings.headers)

    def tokenizer(self) -> TokenCounter:
        return OllamaTokenizer()
