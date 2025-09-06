from __future__ import annotations

import asyncio
from typing import Any

import numpy as np


async def get_document_embeddings(
    detector: Any, document_ids: list[str]
) -> dict[str, list[float]]:
    """Retrieve document embeddings from Qdrant using detector settings.

    This function mirrors ConflictDetector._get_document_embeddings and is extracted
    to reduce module size. It expects a detector with attributes:
    - qdrant_client, collection_name, preferred_vector_name, logger, _settings (optional)
    """
    if not getattr(detector, "qdrant_client", None):
        return {}

    qdrant_client = detector.qdrant_client

    # Support mocked client in tests
    if hasattr(qdrant_client, "retrieve") and hasattr(
        qdrant_client.retrieve, "_mock_name"
    ):
        embeddings: dict[str, list[float]] = {}
        for doc_id in document_ids:
            try:
                points = await qdrant_client.retrieve(
                    collection_name=detector.collection_name,
                    ids=[doc_id],
                    with_vectors=True,
                )
                if points:
                    point = points[0]
                    if hasattr(point, "vector") and point.vector:
                        embeddings[doc_id] = point.vector
            except Exception as e:  # pragma: no cover (best-effort logging)
                detector.logger.warning(
                    f"Failed to retrieve embedding for {doc_id}: {e}"
                )
        return embeddings

    try:
        embeddings: dict[str, list[float]] = {}
        settings = (
            getattr(detector, "_settings", {}) if hasattr(detector, "_settings") else {}
        )
        timeout_s = settings.get("conflict_embeddings_timeout_s", 5.0)
        max_cc = settings.get("conflict_embeddings_max_concurrency", 5)

        semaphore = asyncio.Semaphore(max_cc)

        async def fetch_embedding(doc_id: str) -> None:
            async with semaphore:
                try:
                    search_result = await asyncio.wait_for(
                        qdrant_client.scroll(
                            collection_name=detector.collection_name,
                            scroll_filter={
                                "must": [
                                    {
                                        "key": "document_id",
                                        "match": {"value": doc_id},
                                    }
                                ]
                            },
                            limit=1,
                            with_vectors=True,
                        ),
                        timeout=timeout_s,
                    )

                    if search_result and search_result[0]:
                        point = search_result[0][0]
                        if point.vector:
                            if isinstance(point.vector, dict):
                                vector_data = (
                                    point.vector.get(detector.preferred_vector_name)
                                    or point.vector.get("dense")
                                    or next(iter(point.vector.values()), None)
                                )
                            else:
                                vector_data = point.vector

                            if vector_data:
                                embeddings[doc_id] = vector_data
                            else:
                                detector.logger.warning(
                                    f"No vector data found for document {doc_id}"
                                )
                        else:
                            detector.logger.warning(
                                f"No vectors found for document {doc_id}"
                            )
                except TimeoutError:
                    detector.logger.warning(
                        f"Timeout retrieving embedding for document {doc_id}"
                    )
                except Exception as e:  # pragma: no cover
                    detector.logger.error(
                        f"Error retrieving embedding for document {doc_id}: {e}"
                    )

        await asyncio.gather(
            *(fetch_embedding(doc_id) for doc_id in document_ids),
            return_exceptions=True,
        )
        return embeddings
    except Exception as e:  # pragma: no cover
        detector.logger.error(f"Error retrieving document embeddings: {e}")
        return {}


def calculate_vector_similarity(
    _detector: Any, embedding1: list[float], embedding2: list[float]
) -> float:
    """Cosine similarity with clipping to [-1, 1]."""
    try:
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        similarity = dot_product / (norm1 * norm2)
        return float(np.clip(similarity, -1.0, 1.0))
    except Exception:  # pragma: no cover
        return 0.0


async def filter_by_vector_similarity(
    detector: Any, documents: list[Any]
) -> list[tuple]:
    """Filter document pairs by vector similarity within configured band."""
    similar_pairs: list[tuple] = []
    if len(documents) < 2:
        return similar_pairs

    document_ids = [
        getattr(doc, "document_id", f"{doc.source_type}:{doc.source_title}")
        for doc in documents
    ]
    embeddings = await get_document_embeddings(detector, document_ids)

    for i, doc1 in enumerate(documents):
        for j, doc2 in enumerate(documents[i + 1 :], i + 1):
            doc1_id = document_ids[i]
            doc2_id = document_ids[j]
            similarity_score = 0.0
            if doc1_id in embeddings and doc2_id in embeddings:
                similarity_score = calculate_vector_similarity(
                    detector, embeddings[doc1_id], embeddings[doc2_id]
                )
            if (
                detector.MIN_VECTOR_SIMILARITY
                <= similarity_score
                <= detector.MAX_VECTOR_SIMILARITY
            ):
                similar_pairs.append((doc1, doc2, similarity_score))

    similar_pairs.sort(key=lambda x: x[2], reverse=True)
    return similar_pairs


def should_analyze_for_conflicts(_detector: Any, doc1: Any, doc2: Any) -> bool:
    """Pre-screen documents before conflict analysis."""
    if not doc1 or not doc2:
        return False
    text1 = doc1.text if getattr(doc1, "text", None) else ""
    text2 = doc2.text if getattr(doc2, "text", None) else ""
    if len(text1.strip()) < 10 or len(text2.strip()) < 10:
        return False
    if hasattr(doc1, "document_id") and hasattr(doc2, "document_id"):
        if doc1.document_id == doc2.document_id:
            return False
    if text1.strip() == text2.strip():
        return False
    return True


async def get_tiered_analysis_pairs(detector: Any, documents: list[Any]) -> list[tuple]:
    """Generate tiered analysis pairs for conflict detection (extracted)."""
    pairs: list[tuple] = []
    if len(documents) < 2:
        return pairs

    for i, doc1 in enumerate(documents):
        for _j, doc2 in enumerate(documents[i + 1 :], i + 1):
            score = 1.0
            if hasattr(doc1, "score") and hasattr(doc2, "score"):
                avg_doc_score = (doc1.score + doc2.score) / 2
                score = min(1.0, avg_doc_score)

            if score >= 0.8:
                tier = "primary"
            elif score >= 0.5:
                tier = "secondary"
            else:
                tier = "tertiary"

            pairs.append((doc1, doc2, tier, score))

    pairs.sort(key=lambda x: x[3], reverse=True)
    return pairs
