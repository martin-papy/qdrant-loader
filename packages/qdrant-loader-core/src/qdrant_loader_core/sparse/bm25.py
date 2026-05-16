from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{2,}")
_DEFAULT_HASH_MOD = 2_147_483_647
_DEFAULT_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}


@dataclass(frozen=True)
class SparseVectorData:
    """Simple sparse vector representation."""

    indices: list[int]
    values: list[float]

    def is_empty(self) -> bool:
        return not self.indices


class BM25SparseEncoder:
    """Deterministic BM25-family sparse encoder using hashed token IDs."""

    def __init__(
        self,
        model: str = "bm25",
        *,
        hash_mod: int = _DEFAULT_HASH_MOD,
        stop_words: set[str] | None = None,
    ):
        self.model = (model or "bm25").strip().lower()
        self.hash_mod = max(10_000, int(hash_mod))
        self.stop_words = stop_words if stop_words is not None else _DEFAULT_STOP_WORDS

        if self.model in {"bm25_lite", "bm25-lite"}:
            self.k1 = 0.9
        else:
            self.k1 = 1.2

    def _tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        tokens = _TOKEN_RE.findall(text.lower())
        return [tok for tok in tokens if tok not in self.stop_words]

    def _token_to_index(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, byteorder="big", signed=False) % self.hash_mod
        return index + 1

    def _encode_with_weights(self, text: str, *, query_mode: bool) -> SparseVectorData:
        # Document mode applies BM25 TF saturation without the IDF term:
        # standard BM25 is IDF * (tf * (k1 + 1)) / (tf + k1); this encoder uses
        # only (tf * (k1 + 1)) / (tf + k1) because no corpus statistics are
        # available at encode time (hashed token IDs, single-document context).
        # Qdrant computes the sparse dot product server-side, so omitting IDF
        # keeps encoding deterministic and stateless at the cost of not
        # down-weighting common terms — acceptable since query-side weighting
        # (1 + log tf) and dense retrieval compensate in the hybrid pipeline.
        tokens = self._tokenize(text)
        if not tokens:
            return SparseVectorData(indices=[], values=[])

        counts = Counter(tokens)
        weighted: dict[int, float] = {}
        for token, tf in counts.items():
            index = self._token_to_index(token)
            if query_mode:
                weight = 1.0 + math.log(float(tf))
            else:
                tf_f = float(tf)
                weight = (tf_f * (self.k1 + 1.0)) / (tf_f + self.k1)
            weighted[index] = weighted.get(index, 0.0) + weight

        ordered = sorted(weighted.items(), key=lambda kv: kv[0])
        return SparseVectorData(
            indices=[idx for idx, _ in ordered],
            values=[float(val) for _, val in ordered],
        )

    def encode_document(self, text: str) -> SparseVectorData:
        return self._encode_with_weights(text, query_mode=False)

    def encode_query(self, text: str) -> SparseVectorData:
        return self._encode_with_weights(text, query_mode=True)
