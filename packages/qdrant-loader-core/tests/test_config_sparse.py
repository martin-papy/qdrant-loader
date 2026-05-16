"""Unit tests for qdrant_loader_core.config.sparse + .capabilities."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from qdrant_loader_core.config import (
    CollectionVectorCapabilities,
    SparseRuntimeConfig,
    parse_collection_capabilities,
)


class _Info:
    """Minimal stand-in for a Qdrant ``CollectionInfo``."""

    def __init__(self, vectors, sparse_vectors):
        params = type("P", (), {})()
        params.vectors = vectors
        params.sparse_vectors = sparse_vectors
        config = type("C", (), {})()
        config.params = params
        self.config = config


def test_defaults_match_model_when_no_global_config() -> None:
    cfg = SparseRuntimeConfig.from_global_config(None)
    assert cfg == SparseRuntimeConfig()
    assert cfg.enabled is True
    assert cfg.model == "bm25"
    assert cfg.dense_vector_name == "dense"
    assert cfg.sparse_vector_name == "sparse"
    assert cfg.use_qdrant_hybrid is True


def test_defaults_when_llm_block_missing() -> None:
    assert SparseRuntimeConfig.from_global_config({}) == SparseRuntimeConfig()
    assert (
        SparseRuntimeConfig.from_global_config({"llm": None}) == SparseRuntimeConfig()
    )


def test_yaml_overrides_defaults() -> None:
    cfg = SparseRuntimeConfig.from_global_config(
        {
            "llm": {
                "sparse": {
                    "enabled": False,
                    "model": "bm25_lite",
                    "dense_vector_name": "vec",
                    "sparse_vector_name": "bow",
                },
                "retrieval": {"use_qdrant_hybrid": False},
            }
        }
    )
    assert cfg.enabled is False
    assert cfg.model == "bm25_lite"
    assert cfg.dense_vector_name == "vec"
    assert cfg.sparse_vector_name == "bow"
    assert cfg.use_qdrant_hybrid is False


def test_yaml_accepts_true_false_strings_case_insensitive() -> None:
    cfg = SparseRuntimeConfig.from_global_config(
        {
            "llm": {
                "sparse": {"enabled": "TRUE"},
                "retrieval": {"use_qdrant_hybrid": "true"},
            }
        }
    )
    assert cfg.enabled is True
    assert cfg.use_qdrant_hybrid is True


def test_retrieval_sparse_block_overrides_top_level_sparse() -> None:
    cfg = SparseRuntimeConfig.from_global_config(
        {
            "llm": {
                "sparse": {"model": "bm25"},
                "retrieval": {"sparse": {"model": "bm25_lite"}},
            }
        }
    )
    assert cfg.model == "bm25_lite"


def test_yaml_with_invalid_bool_string_raises() -> None:
    with pytest.raises(ValidationError):
        SparseRuntimeConfig.from_global_config({"llm": {"sparse": {"enabled": "yes"}}})


def test_yaml_with_numeric_bool_raises() -> None:
    # Pydantic's default lax coercion would accept 1/0 — our validator rejects.
    with pytest.raises(ValidationError):
        SparseRuntimeConfig.from_global_config({"llm": {"sparse": {"enabled": 1}}})


def test_yaml_with_empty_string_field_raises() -> None:
    with pytest.raises(ValidationError):
        SparseRuntimeConfig.from_global_config({"llm": {"sparse": {"model": ""}}})


def test_unknown_yaml_keys_are_silently_dropped() -> None:
    # YAML may carry extra keys (e.g. typos, forward-compat fields) — we only
    # construct from recognised fields, so the model's extra="forbid" doesn't
    # blow up on real-world configs.
    cfg = SparseRuntimeConfig.from_global_config(
        {"llm": {"sparse": {"enabled": False, "mystery_field": "x"}}}
    )
    assert cfg.enabled is False


def test_model_copy_returns_new_instance() -> None:
    base = SparseRuntimeConfig()
    updated = base.model_copy(update={"model": "bm25_lite"})
    assert base.model == "bm25"
    assert updated.model == "bm25_lite"
    assert base is not updated


def test_runtime_config_is_frozen() -> None:
    cfg = SparseRuntimeConfig()
    with pytest.raises(ValidationError):
        cfg.enabled = False  # type: ignore[misc]


def test_runtime_config_rejects_extra_fields_at_direct_construction() -> None:
    with pytest.raises(ValidationError):
        SparseRuntimeConfig(enabled=True, mystery_field="x")  # type: ignore[call-arg]


def test_parse_capabilities_detects_named_dense_and_sparse() -> None:
    runtime = SparseRuntimeConfig()
    info = _Info(vectors={"dense": {"size": 3}}, sparse_vectors={"sparse": object()})
    caps = parse_collection_capabilities(info, runtime)
    assert caps == CollectionVectorCapabilities(has_named_dense=True, has_sparse=True)
    assert caps.hybrid_ready is True


def test_parse_capabilities_handles_pydantic_like_objects() -> None:
    runtime = SparseRuntimeConfig()

    class _PydanticIsh:
        def __init__(self, payload):
            self._payload = payload

        def model_dump(self) -> dict:
            return self._payload

    info = _Info(
        vectors=_PydanticIsh({"dense": {"size": 3}}),
        sparse_vectors=_PydanticIsh({"sparse": {}}),
    )
    caps = parse_collection_capabilities(info, runtime)
    assert caps.has_named_dense is True
    assert caps.has_sparse is True


def test_parse_capabilities_dense_only_collection() -> None:
    runtime = SparseRuntimeConfig()
    info = _Info(vectors={"dense": {"size": 3}}, sparse_vectors=None)
    caps = parse_collection_capabilities(info, runtime)
    assert caps.has_named_dense is True
    assert caps.has_sparse is False
    assert caps.hybrid_ready is False


def test_parse_capabilities_respects_configured_names() -> None:
    runtime = SparseRuntimeConfig().model_copy(
        update={"dense_vector_name": "vec", "sparse_vector_name": "bow"}
    )
    info = _Info(vectors={"vec": {}}, sparse_vectors={"bow": {}})
    caps = parse_collection_capabilities(info, runtime)
    assert caps.has_named_dense is True
    assert caps.has_sparse is True
