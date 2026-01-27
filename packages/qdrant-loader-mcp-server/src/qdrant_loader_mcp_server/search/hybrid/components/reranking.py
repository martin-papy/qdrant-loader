from __future__ import annotations

import logging
from typing import Any, List

from .cross_encoder_reranker import CrossEncoderReranker


class HybridReranker:
    """Hybrid reranker that optionally applies cross-encoder re-ranking."""
    def __init__(
        self,
        enabled: bool,
        model: str,
        device: str = "cpu",
        batch_size: int = 32,
    ):
        self.logger = logging.getLogger(__name__)

        if enabled:
            self.cross_encoder = CrossEncoderReranker(
                model_name=model,
                device=device,
                batch_size=batch_size,
                enabled=True,
            )
            self.logger.info("Cross-encoder reranker enabled")
        else:
            self.cross_encoder = None
            self.logger.info("Cross-encoder reranker disabled")

    def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: int | None = None,
        text_key: str = "text",
    ) -> List[Any]:

        if not results or self.cross_encoder is None:
            return results

        return self.cross_encoder.rerank(
            query=query,
            results=results,
            top_k=top_k,
            text_key=text_key,
        )
