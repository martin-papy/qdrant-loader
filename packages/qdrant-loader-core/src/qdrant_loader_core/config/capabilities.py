"""Qdrant collection vector-schema capabilities.

A Pydantic model describing what a live Qdrant collection supports, plus a
parser that converts a fetched ``CollectionInfo`` into that model. I/O is the
caller's responsibility — we don't wrap ``client.get_collection`` here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .sparse import SparseRuntimeConfig


class CollectionVectorCapabilities(BaseModel):
    """What a live Qdrant collection supports — derived from CollectionInfo."""

    model_config = ConfigDict(frozen=True)

    has_named_dense: bool = False
    has_sparse: bool = False

    @property
    def hybrid_ready(self) -> bool:
        """True when the collection has both a named dense vector and a sparse vector."""
        return self.has_named_dense and self.has_sparse


def parse_collection_capabilities(
    info: Any, runtime: SparseRuntimeConfig
) -> CollectionVectorCapabilities:
    """Inspect a Qdrant ``CollectionInfo`` against the runtime config.

    Resilient to both dict-shaped and Pydantic-model-shaped ``vectors`` /
    ``sparse_vectors`` fields, which differ across qdrant-client versions.
    """
    params = getattr(getattr(info, "config", None), "params", None)
    vectors = getattr(params, "vectors", None)
    sparse_vectors = getattr(params, "sparse_vectors", None)

    has_named_dense = runtime.dense_vector_name in _normalise_vector_map(vectors)
    has_sparse = runtime.sparse_vector_name in _normalise_vector_map(sparse_vectors)

    return CollectionVectorCapabilities(
        has_named_dense=has_named_dense, has_sparse=has_sparse
    )


def _normalise_vector_map(value: object) -> dict[str, Any]:
    """Coerce qdrant-client ``vectors`` / ``sparse_vectors`` field to a plain dict.

    Older client versions return plain dicts; newer ones may return Pydantic
    models. Anything that isn't a mapping and doesn't expose ``model_dump`` /
    ``dict`` is treated as empty.
    """
    if isinstance(value, dict):
        return value
    for attr in ("model_dump", "dict"):
        dumper = getattr(value, attr, None)
        if not callable(dumper):
            continue
        try:
            dumped = dumper()
        except Exception:
            return {}
        if isinstance(dumped, dict):
            return dumped
    return {}
