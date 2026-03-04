from __future__ import annotations

import logging
from typing import Any, List, Tuple

try:
    from sentence_transformers import CrossEncoder
    import torch
except ImportError:
    CrossEncoder = None


class CrossEncoderReranker:
    """Re-rank search results using a cross-encoder model."""

    def __init__(
        self,
        enabled: bool = True,
    ):
        self.model_name = "cross-encoder/ms-marco-MiniLM-L-12-v2"
        self.device = self._get_optimal_device()
        self.batch_size = 32
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

    def _get_optimal_device(self) -> str:
        """Check the device to run reranking on: CUDA -> MPS -> CPU"""
        if torch is None:
            return "cpu"

        if torch.cuda.is_available():
            return "cuda"

        # torch >= 1.12 and macOS supports Metal
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"

        return "cpu"

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