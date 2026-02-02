from __future__ import annotations

import logging
from typing import Any, List, Tuple

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None


class CrossEncoderReranker:
    """Re-rank search results using a cross-encoder model."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        batch_size: int = 32,
        enabled: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.enabled = enabled

        self.model: CrossEncoder | None = None
        self.logger = logging.getLogger(__name__)

        if not self.enabled:
            self.logger.info("Cross-encoder reranking disabled")
            return

        if CrossEncoder is None:
            self.logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            self.enabled = False

    def _load_model(self) -> None:

        if self.model is not None:
            return

        try:
            self.logger.info(
                f"Loading cross-encoder model: {self.model_name} on {self.device}"
            )
            self.model = CrossEncoder(self.model_name, device=self.device)
            self.logger.info("Cross-encoder model loaded")
        except Exception as e:
            self.logger.error(f"Failed to load cross-encoder model: {e}")
            self.enabled = False
            self.model = None

    def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: int | None = None,
        text_key: str = "text",
    ) -> List[Any]:
        
        self.logger.debug(
            "Cross encoder rerank is excuting"
            f"query={query}, results={len(results)}"
        )

        if not self.enabled or not results:
            return results

        self._load_model()
        if self.model is None:
            return results

        try:
            texts_with_indices = self._extract_texts_with_indices(results, text_key)
            if not texts_with_indices:
                return results

            pairs = [(query, text) for (_idx, text) in texts_with_indices]

            scores = self.model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
            )

            # Map scores back to original results using saved indices
            mapped = [
                (results[idx], float(score))
                for (idx, _), score in zip(texts_with_indices, scores)
            ]

            ranked = sorted(
                mapped,
                key=lambda x: x[1],
                reverse=True,
            )

            if top_k is not None:
                ranked = ranked[:top_k]

            output = []
            for rank, (item, score) in enumerate(ranked, start=1):
                if isinstance(item, dict):
                    item["cross_encoder_score"] = float(score)
                    item["cross_encoder_rank"] = rank
                else:
                    setattr(item, "cross_encoder_score", float(score))
                    setattr(item, "cross_encoder_rank", rank)
                output.append(item)

            return output

        except Exception as e:
            self.logger.error(f"Cross-encoder reranking failed: {e}")
            return results

    def _extract_texts_with_indices(self, results: List[Any], text_key: str) -> List[Tuple[int, str]]:
        texts: List[Tuple[int, str]] = []

        for idx, r in enumerate(results):
            if isinstance(r, dict):
                text = r.get(text_key, "")
            elif hasattr(r, text_key):
                text = getattr(r, text_key)
            else:
                text = str(r)

            text = str(text).strip()
            if text:
                texts.append((idx, text[:1000]))

        return texts