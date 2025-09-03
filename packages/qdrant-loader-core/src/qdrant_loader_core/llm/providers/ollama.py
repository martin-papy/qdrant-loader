from __future__ import annotations

from typing import Any
import logging

import json

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore

from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter
from ..errors import (
    LLMError,
    TimeoutError as LLMTimeoutError,
    RateLimitedError,
    InvalidRequestError,
    AuthError,
    ServerError,
)

logger = logging.getLogger(__name__)


def _join_url(base: str | None, path: str) -> str:
    base = (base or "").rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}" if base else f"/{path}"


class OllamaEmbeddings(EmbeddingsClient):
    def __init__(self, base_url: str | None, model: str, headers: dict[str, str] | None):
        self._base_url = base_url or "http://localhost:11434"
        self._model = model
        self._headers = headers or {}

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if httpx is None:
            raise NotImplementedError("httpx not available for Ollama embeddings")

        # Prefer OpenAI-compatible if base_url seems to expose /v1
        use_v1 = "/v1" in (self._base_url or "")
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                        extra={
                            "provider": "ollama",
                            "operation": "embeddings",
                            "model": self._model,
                            "base_host": self._base_url,
                            "inputs": len(inputs),
                        },
                    )
                    return [item["embedding"] for item in data.get("data", [])]
                else:
                    # Native Ollama endpoint (one input at a time)
                    url = _join_url(self._base_url, "/api/embeddings")
                    vectors: list[list[float]] = []
                    for text in inputs:
                        payload = {"model": self._model, "input": text}
                        resp = await client.post(url, json=payload, headers=self._headers)
                        resp.raise_for_status()
                        data = resp.json()
                        # Some Ollama versions return {"embedding": [...]} or {"data": {"embedding": [...]}}
                        emb = data.get("embedding")
                        if emb is None and isinstance(data.get("data"), dict):
                            emb = data["data"].get("embedding")
                        if emb is None:
                            raise ValueError("Invalid embedding response from Ollama")
                        vectors.append(list(emb))
                    logger.info(
                        "LLM request",
                        extra={
                            "provider": "ollama",
                            "operation": "embeddings",
                            "model": self._model,
                            "base_host": self._base_url,
                            "inputs": len(inputs),
                        },
                    )
                    return vectors
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
    def __init__(self, base_url: str | None, model: str, headers: dict[str, str] | None):
        self._base_url = base_url or "http://localhost:11434"
        self._model = model
        self._headers = headers or {}

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
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
                    resp = await client.post(url, json=payload, headers=self._headers)
                    resp.raise_for_status()
                    data = resp.json()
                    text = ""
                    choices = data.get("choices") or []
                    if choices:
                        msg = (choices[0] or {}).get("message") or {}
                        text = msg.get("content", "") or ""
                    logger.info(
                        "LLM request",
                        extra={
                            "provider": "ollama",
                            "operation": "chat",
                            "model": self._model,
                            "base_host": self._base_url,
                            "messages": len(messages),
                        },
                    )
                    return {"text": text, "raw": data, "usage": data.get("usage"), "model": data.get("model", self._model)}
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
                    resp = await client.post(url, json=payload, headers=self._headers)
                    resp.raise_for_status()
                    data = resp.json()
                    # Ollama native returns {"message": {"content": "..."}, ...}
                    text = ""
                    if isinstance(data.get("message"), dict):
                        text = data["message"].get("content", "") or ""
                    logger.info(
                        "LLM request",
                        extra={
                            "provider": "ollama",
                            "operation": "chat",
                            "model": self._model,
                            "base_host": self._base_url,
                            "messages": len(messages),
                        },
                    )
                    return {"text": text, "raw": data, "usage": None, "model": self._model}
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
        return OllamaEmbeddings(self._settings.base_url, model, self._settings.headers)

    def chat(self) -> ChatClient:
        model = self._settings.models.get("chat", "")
        return OllamaChat(self._settings.base_url, model, self._settings.headers)

    def tokenizer(self) -> TokenCounter:
        return OllamaTokenizer()
