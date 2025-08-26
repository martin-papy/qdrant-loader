from qdrant_loader_mcp_server.search.enhanced.cdi import (
    DocumentCluster,
    DocumentSimilarity,
)


def test_document_similarity_display_explanation_prefers_explicit_text():
    ds = DocumentSimilarity(
        doc1_id="a",
        doc2_id="b",
        similarity_score=0.5,
        explanation="explicit",
    )
    assert ds.get_display_explanation() == "explicit"


def test_document_cluster_summary_contains_key_fields():
    cluster = DocumentCluster(
        cluster_id="c1",
        name="Cluster",
        documents=["d1", "d2"],
    )
    summary = cluster.get_cluster_summary()
    assert summary["cluster_id"] == "c1"
    assert summary["name"] == "Cluster"
    assert summary["document_count"] == 2
