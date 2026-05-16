"""Tests for the process-wide get_sparse_encoder cache."""

from __future__ import annotations

from qdrant_loader_core.sparse import BM25SparseEncoder, get_sparse_encoder


def test_get_sparse_encoder_returns_bm25_instance() -> None:
    encoder = get_sparse_encoder("bm25")
    assert isinstance(encoder, BM25SparseEncoder)
    assert encoder.model == "bm25"


def test_get_sparse_encoder_caches_by_model_name() -> None:
    a = get_sparse_encoder("bm25")
    b = get_sparse_encoder("bm25")
    assert a is b


def test_get_sparse_encoder_differs_across_model_names() -> None:
    a = get_sparse_encoder("bm25")
    b = get_sparse_encoder("bm25_lite")
    assert a is not b
    assert b.model == "bm25_lite"


def test_get_sparse_encoder_collapses_equivalent_model_names() -> None:
    canonical = get_sparse_encoder("bm25")
    for variant in ("BM25", " bm25 ", "Bm25"):
        assert get_sparse_encoder(variant) is canonical
    assert canonical.model == "bm25"
