from __future__ import annotations

import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


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
        - Legacy: global.embedding and file_conversion.markitdown
        """
        llm = (global_data or {}).get("llm") or {}
        if llm:
            return LLMSettings(
                provider=str(llm.get("provider")),
                base_url=llm.get("base_url"),
                api_key=llm.get("api_key"),
                api_version=llm.get("api_version"),
                headers=dict(llm.get("headers") or {}),
                models=dict(llm.get("models") or {}),
                tokenizer=str(llm.get("tokenizer", "none")),
                request=RequestPolicy(**(llm.get("request") or {})),
                rate_limits=RateLimitPolicy(**(llm.get("rate_limits") or {})),
                embeddings=EmbeddingPolicy(**(llm.get("embeddings") or {})),
                provider_options=dict(llm.get("provider_options") or {}),
            )

        # Legacy mapping
        embedding = (global_data or {}).get("embedding") or {}
        file_conv = (global_data or {}).get("file_conversion") or {}
        markit = (
            (file_conv.get("markitdown") or {}) if isinstance(file_conv, dict) else {}
        )

        endpoint = embedding.get("endpoint")
        # Detect Azure OpenAI in legacy endpoint to set provider accordingly
        endpoint_l = (endpoint or "").lower() if isinstance(endpoint, str) else ""
        host: str | None = None
        if endpoint_l:
            try:
                host = urlparse(endpoint_l).hostname or None
            except Exception:
                host = None
        is_azure = False
        if host:
            host_l = host.lower()
            is_azure = (
                host_l == "openai.azure.com"
                or host_l.endswith(".openai.azure.com")
                or host_l == "cognitiveservices.azure.com"
                or host_l.endswith(".cognitiveservices.azure.com")
            )
        if is_azure:
            provider = "azure_openai"
        elif "openai" in endpoint_l:
            provider = "openai"
        else:
            provider = "openai_compat"
        models = {
            "embeddings": embedding.get("model"),
        }
        if isinstance(markit.get("llm_model"), str):
            models["chat"] = markit.get("llm_model")

        # Emit deprecation warnings when relying on legacy fields
        try:
            if embedding or markit:
                warnings.warn(
                    (
                        "Using legacy configuration fields is deprecated. "
                        "Please migrate to 'global.llm' (see docs: configuration reference). "
                        "Mapped from: global.embedding.* and/or file_conversion.markitdown.*"
                    ),
                    category=DeprecationWarning,
                    stacklevel=2,
                )
        except Exception:
            # Best-effort warning; never break mapping
            pass

        return LLMSettings(
            provider=provider,
            base_url=endpoint,
            api_key=embedding.get("api_key"),
            api_version=None,
            headers=None,
            models=models,
            tokenizer=str(embedding.get("tokenizer", "none")),
            request=RequestPolicy(),
            rate_limits=RateLimitPolicy(),
            embeddings=EmbeddingPolicy(vector_size=embedding.get("vector_size")),
            provider_options=None,
        )
