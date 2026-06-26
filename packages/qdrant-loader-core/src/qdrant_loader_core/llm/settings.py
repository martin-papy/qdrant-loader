from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass
class RequestPolicy:
    timeout_s: float = 30.0
    max_retries: int = 3
    backoff_s_min: float = 1.0
    backoff_s_max: float = 30.0


@dataclass
class RateLimitPolicy:
    rpm: int | None = None
    tpm: int | None = None
    concurrency: int = 5


@dataclass
class EmbeddingPolicy:
    vector_size: int | None = None
    batch_size: int = 100
    max_tokens_per_request: int = 8000
    max_tokens_per_chunk: int = 8000


def _to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _to_int_with_default(value: Any, default: int) -> int:
    parsed = _to_int_or_none(value)
    if parsed is None or parsed <= 0:
        return default
    return parsed


@dataclass
class LLMSettings:
    provider: str
    base_url: str | None
    api_key: str | None
    headers: dict[str, str] | None
    models: dict[str, str]
    tokenizer: str
    request: RequestPolicy
    rate_limits: RateLimitPolicy
    embeddings: EmbeddingPolicy
    api_version: str | None = None
    provider_options: dict[str, Any] | None = None

    @staticmethod
    def from_global_config(global_data: Mapping[str, Any]) -> LLMSettings:
        """Construct settings from a parsed global configuration dict.

        Supports two schemas:
        - New: global.llm
        """
        embedding = (global_data or {}).get("embedding") or {}
        llm = (global_data or {}).get("llm") or {}

        # Emit deprecation warnings when relying on legacy fields
        if embedding:
            raise ValueError(
                "Configuration error: 'global.embedding' is no longer supported. "
                "Please migrate your configuration to the 'global.llm' format."
            )

        if not llm:
            raise ValueError(
                "Missing required 'global.llm' configuration. "
                "'global.embedding' is no longer supported. "
                "Please migrate your configuration to the new 'global.llm' format."
            )

        embeddings_cfg = dict(llm.get("embeddings") or {})
        request_cfg = dict(llm.get("request") or {})
        return LLMSettings(
            provider=str(llm.get("provider")),
            base_url=llm.get("base_url"),
            api_key=llm.get("api_key"),
            api_version=llm.get("api_version"),
            headers=dict(llm.get("headers") or {}),
            models=dict(llm.get("models") or {}),
            tokenizer=str(llm.get("tokenizer", "none")),
            request=RequestPolicy(**request_cfg),
            rate_limits=RateLimitPolicy(**(llm.get("rate_limits") or {})),
            embeddings=EmbeddingPolicy(
                vector_size=_to_int_or_none(embeddings_cfg.get("vector_size")),
                batch_size=_to_int_with_default(embeddings_cfg.get("batch_size"), 100),
                max_tokens_per_request=_to_int_with_default(
                    embeddings_cfg.get(
                        "max_tokens_per_request",
                        request_cfg.get("max_input_tokens"),
                    ),
                    8000,
                ),
                max_tokens_per_chunk=_to_int_with_default(
                    embeddings_cfg.get("max_tokens_per_chunk"),
                    8000,
                ),
            ),
            provider_options=dict(llm.get("provider_options") or {}),
        )
