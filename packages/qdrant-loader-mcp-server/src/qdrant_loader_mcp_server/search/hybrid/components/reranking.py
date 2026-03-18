from __future__ import annotations

import logging
from typing import Any

from .cross_encoder_reranker import CrossEncoderReranker


class HybridReranker:
    """Hybrid reranker that optionally applies cross-encoder re-ranking."""

    def __init__(
        self,
        enabled: bool = False,
        model: str = "cross-encoder/ms-marco-MiniLM-L-12-v2",
        device: str = "cpu",
        batch_size: int = 32,
    ):
        self.logger = logging.getLogger(__name__)
        self.cross_encoder = None

        if enabled:
            try:
                self.cross_encoder = CrossEncoderReranker(
                    model_name=model,
                    device=device,
                    batch_size=batch_size,
                    enabled=True,
                )
                self.logger.info("Cross-encoder reranker enabled")
            except Exception:
                self.logger.exception(
                    "Failed to initialize cross-encoder reranker; continuing without reranking"
                )
        else:
            self.logger.info("Cross-encoder reranker disabled")

    def rerank(
        self,
        query: str,
        results: list[Any],
        top_k: int | None = None,
        text_key: str = "text",
    ) -> list[Any]:

        if not results or self.cross_encoder is None:
            return results

        try:
            return self.cross_encoder.rerank(
                query=query,
                results=results,
                top_k=top_k,
                text_key=text_key,
            )
        except Exception:
            self.logger.exception(
                "Cross-encoder reranking failed; returning original ranking"
            )
            return results
