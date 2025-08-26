from __future__ import annotations

import logging

from ....models import SearchResult
from ..models import SimilarityMetric
from ..utils import (
    ARCHITECTURE_PATTERNS,
    DOMAIN_KEYWORDS,
    STOP_WORDS_BASIC,
    TECH_KEYWORDS_COUNT,
    TECH_KEYWORDS_SHARED,
    extract_texts_from_mixed,
    weighted_average,
)


def _normalize_runtime(value: str) -> str:
    """Normalize runtime/technology variants to canonical names.

    - Returns "node.js" for any of {"node", "nodejs", "node.js"}
    - Otherwise returns the lowercased cleaned input
    """
    v = (value or "").lower()
    return "node.js" if v in {"node", "nodejs", "node.js"} else v


def get_shared_entities(doc1: SearchResult, doc2: SearchResult) -> list[str]:
    ents1 = extract_texts_from_mixed(doc1.entities)
    ents2 = extract_texts_from_mixed(doc2.entities)
    return list(set(ents1) & set(ents2))


def get_shared_topics(doc1: SearchResult, doc2: SearchResult) -> list[str]:
    topics1 = extract_texts_from_mixed(doc1.topics)
    topics2 = extract_texts_from_mixed(doc2.topics)
    return list(set(topics1) & set(topics2))


def combine_metric_scores(metric_scores: dict[SimilarityMetric, float]) -> float:
    if not metric_scores:
        return 0.0
    weights = {
        SimilarityMetric.ENTITY_OVERLAP: 0.25,
        SimilarityMetric.TOPIC_OVERLAP: 0.25,
        SimilarityMetric.METADATA_SIMILARITY: 0.20,
        SimilarityMetric.CONTENT_FEATURES: 0.15,
        SimilarityMetric.HIERARCHICAL_DISTANCE: 0.10,
        SimilarityMetric.SEMANTIC_SIMILARITY: 0.05,
    }
    # Convert Enum keys to string names for generic helper
    scores_as_named = {m.value: s for m, s in metric_scores.items()}
    return weighted_average(scores_as_named, {k.value: v for k, v in weights.items()})


def calculate_semantic_similarity_spacy(
    spacy_analyzer, text1: str, text2: str
) -> float:
    """Compute spaCy vector similarity on truncated texts, mirroring legacy behavior.

    Only expected, recoverable errors are handled; unexpected exceptions propagate.
    """
    logger = logging.getLogger(__name__)
    try:
        doc1_analyzed = spacy_analyzer.nlp((text1 or "")[:500])
        doc2_analyzed = spacy_analyzer.nlp((text2 or "")[:500])
        return float(doc1_analyzed.similarity(doc2_analyzed))
    except (AttributeError, ValueError, OSError) as e:
        logger.error(
            "spaCy similarity failed (recoverable): %s | len1=%d len2=%d",
            e,
            len(text1 or ""),
            len(text2 or ""),
        )
        return 0.0
    except Exception:
        # Let unexpected exceptions bubble up for visibility
        raise


def calculate_text_similarity(doc1: SearchResult, doc2: SearchResult) -> float:
    """Legacy-style text similarity using stopword-filtered Jaccard."""
    text1 = (doc1.text or "").lower()
    text2 = (doc2.text or "").lower()
    words1 = set(text1.split())
    words2 = set(text2.split())
    words1 -= STOP_WORDS_BASIC
    words2 -= STOP_WORDS_BASIC
    if not words1 or not words2:
        return 0.0
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    return intersection / union if union > 0 else 0.0


def extract_context_snippet(text: str, keyword: str, max_length: int = 150) -> str:
    """Extract a context snippet around a keyword from text (legacy-compatible)."""
    import re

    keyword_lower = (keyword or "").lower()
    pattern = r"\b" + re.escape(keyword_lower) + r"\b"

    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        words = keyword_lower.split()
        for word in words:
            word_pattern = r"\b" + re.escape(word) + r"\b"
            match = re.search(word_pattern, text, re.IGNORECASE)
            if match:
                keyword = word
                break

    if not match:
        return (text or "")[:max_length].strip()

    keyword_start = match.start()
    snippet_start = max(0, keyword_start - max_length // 2)
    snippet_end = min(len(text), keyword_start + len(keyword) + max_length // 2)
    snippet = text[snippet_start:snippet_end].strip()

    sentences = snippet.split(".")
    if len(sentences) > 1:
        for i, sentence in enumerate(sentences):
            if keyword.lower() in sentence.lower():
                start_idx = max(0, i - 1) if i > 0 else 0
                end_idx = min(len(sentences), i + 2)
                snippet = ".".join(
                    s.strip() for s in sentences[start_idx:end_idx]
                ).strip()
                break

    return snippet


def have_semantic_similarity(doc1: SearchResult, doc2: SearchResult) -> bool:
    """Heuristic semantic similarity based on title overlap and key terms."""
    title1 = (doc1.source_title or "").lower()
    title2 = (doc2.source_title or "").lower()
    if title1 and title2:
        title_words1 = set(title1.split())
        title_words2 = set(title2.split())
        if title_words1 & title_words2:
            return True

    key_terms = [
        "authentication",
        "security",
        "login",
        "password",
        "access",
        "user",
        "interface",
        "design",
        "app",
        "mobile",
    ]
    text1_lower = (doc1.text or "").lower()
    text2_lower = (doc2.text or "").lower()
    terms_in_doc1 = [term for term in key_terms if term in text1_lower]
    terms_in_doc2 = [term for term in key_terms if term in text2_lower]
    return len(set(terms_in_doc1) & set(terms_in_doc2)) >= 2


def has_shared_entities(doc1: SearchResult, doc2: SearchResult) -> bool:
    return len(set(get_shared_entities(doc1, doc2))) > 0


def has_shared_topics(doc1: SearchResult, doc2: SearchResult) -> bool:
    return len(set(get_shared_topics(doc1, doc2))) > 0


def get_shared_entities_count(doc1: SearchResult, doc2: SearchResult) -> int:
    return len(set(get_shared_entities(doc1, doc2)))


def get_shared_topics_count(doc1: SearchResult, doc2: SearchResult) -> int:
    return len(set(get_shared_topics(doc1, doc2)))


def has_transferable_domain_knowledge(doc1: SearchResult, doc2: SearchResult) -> bool:
    title1 = (doc1.source_title or "").lower()
    title2 = (doc2.source_title or "").lower()
    for domain in DOMAIN_KEYWORDS:
        if any(k in title1 for k in domain) and any(k in title2 for k in domain):
            return True
    return False


def has_reusable_architecture_patterns(doc1: SearchResult, doc2: SearchResult) -> bool:
    title1 = (doc1.source_title or "").lower()
    title2 = (doc2.source_title or "").lower()
    for pattern in ARCHITECTURE_PATTERNS:
        if any(k in title1 for k in pattern) and any(k in title2 for k in pattern):
            return True
    return False


def has_shared_technologies(doc1: SearchResult, doc2: SearchResult) -> bool:
    # Reuse the shared extraction logic for consistency across helpers
    ents1 = set(extract_texts_from_mixed(getattr(doc1, "entities", []) or []))
    ents2 = set(extract_texts_from_mixed(getattr(doc2, "entities", []) or []))

    if {_normalize_runtime(e) for e in ents1} & {_normalize_runtime(e) for e in ents2}:
        return True

    title1 = (doc1.source_title or "").lower()
    title2 = (doc2.source_title or "").lower()
    return any(k in title1 and k in title2 for k in TECH_KEYWORDS_SHARED)


def get_shared_technologies_count(doc1: SearchResult, doc2: SearchResult) -> int:
    entities1 = set(extract_texts_from_mixed(getattr(doc1, "entities", []) or []))
    entities2 = set(extract_texts_from_mixed(getattr(doc2, "entities", []) or []))

    shared_entities = {_normalize_runtime(e) for e in entities1} & {
        _normalize_runtime(e) for e in entities2
    }
    if shared_entities:
        return len(shared_entities)

    title1 = (doc1.source_title or "").lower()
    title2 = (doc2.source_title or "").lower()
    return sum(1 for k in TECH_KEYWORDS_COUNT if k in title1 and k in title2)


def calculate_entity_overlap(doc1: SearchResult, doc2: SearchResult) -> float:
    """Calculate entity overlap between documents (Jaccard)."""
    entities1 = extract_texts_from_mixed(getattr(doc1, "entities", []) or [])
    entities2 = extract_texts_from_mixed(getattr(doc2, "entities", []) or [])
    if not entities1 or not entities2:
        return 0.0
    set1 = set(entities1)
    set2 = set(entities2)
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union if union > 0 else 0.0


def calculate_topic_overlap(doc1: SearchResult, doc2: SearchResult) -> float:
    """Calculate topic overlap between documents (Jaccard)."""
    topics1 = extract_texts_from_mixed(getattr(doc1, "topics", []) or [])
    topics2 = extract_texts_from_mixed(getattr(doc2, "topics", []) or [])
    if not topics1 or not topics2:
        return 0.0
    set1 = set(topics1)
    set2 = set(topics2)
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union if union > 0 else 0.0


def calculate_metadata_similarity(doc1: SearchResult, doc2: SearchResult) -> float:
    """Calculate metadata similarity combining project/source/features/word count."""
    similarity_factors: list[float] = []

    if getattr(doc1, "project_id", None) and getattr(doc2, "project_id", None):
        similarity_factors.append(1.0 if doc1.project_id == doc2.project_id else 0.0)

    similarity_factors.append(0.5 if doc1.source_type == doc2.source_type else 0.0)

    features1 = [
        getattr(doc1, "has_code_blocks", False),
        getattr(doc1, "has_tables", False),
        getattr(doc1, "has_images", False),
        getattr(doc1, "has_links", False),
    ]
    features2 = [
        getattr(doc2, "has_code_blocks", False),
        getattr(doc2, "has_tables", False),
        getattr(doc2, "has_images", False),
        getattr(doc2, "has_links", False),
    ]
    min_len = min(len(features1), len(features2))
    if min_len == 0:
        feature_similarity = 0.0
    else:
        feature_similarity = sum(
            f1 == f2 for f1, f2 in zip(features1, features2, strict=False)
        ) / float(min_len)
    similarity_factors.append(feature_similarity)

    if getattr(doc1, "word_count", None) and getattr(doc2, "word_count", None):
        min_words = min(doc1.word_count, doc2.word_count)
        max_words = max(doc1.word_count, doc2.word_count)
        similarity_factors.append(min_words / max_words if max_words > 0 else 0.0)

    return (
        (sum(similarity_factors) / len(similarity_factors))
        if similarity_factors
        else 0.0
    )


def calculate_content_features_similarity(
    doc1: SearchResult, doc2: SearchResult
) -> float:
    """Calculate content features similarity (read time, depth, content flags)."""
    read_time_similarity = 0.0
    if getattr(doc1, "estimated_read_time", None) and getattr(
        doc2, "estimated_read_time", None
    ):
        min_time = min(doc1.estimated_read_time, doc2.estimated_read_time)
        max_time = max(doc1.estimated_read_time, doc2.estimated_read_time)
        read_time_similarity = min_time / max_time if max_time > 0 else 0.0

    depth_similarity = 0.0
    if (
        getattr(doc1, "depth", None) is not None
        and getattr(doc2, "depth", None) is not None
    ):
        depth_diff = abs(doc1.depth - doc2.depth)
        depth_similarity = max(0.0, 1.0 - depth_diff / 5.0)

    feature_factors = [read_time_similarity, depth_similarity]
    return sum(feature_factors) / len(feature_factors) if feature_factors else 0.0
