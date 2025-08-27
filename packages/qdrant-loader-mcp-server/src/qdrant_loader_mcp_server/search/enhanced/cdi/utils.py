from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import TypeVar

import numpy as np

T = TypeVar("T")


def jaccard_similarity(a: Iterable[T], b: Iterable[T]) -> float:
    """Compute Jaccard similarity for two iterables (as sets).

    Provided as a pure helper. Not wired into the legacy module yet.
    """
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 0.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def extract_texts_from_mixed(
    items: Iterable[dict | str], key: str = "text"
) -> list[str]:
    """Extract lowercase texts from a mixed list of dicts or strings.

    Mirrors legacy behavior used in CDI but provides a shared, tested helper.
    """
    if items is None:
        return []
    texts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = str(item.get(key, "")).strip().lower()
            if value:
                texts.append(value)
        elif isinstance(item, str):
            value = item.strip().lower()
            if value:
                texts.append(value)
    return texts


def weighted_average(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Compute a weighted average for named scores with default weights.

    Any missing weights default to 0.1 to mirror lenient legacy combining rules.
    """
    if not scores:
        return 0.0
    total = 0.0
    total_w = 0.0
    for name, score in scores.items():
        w = weights.get(name, 0.1)
        total += score * w
        total_w += w
    return total / total_w if total_w > 0 else 0.0


# Common stop words used across similarity functions
STOP_WORDS_BASIC: set[str] = {
    "the",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
}

# Title-specific stop words used when extracting common words
TITLE_STOP_WORDS: set[str] = {
    "documentation",
    "guide",
    "overview",
    "introduction",
    "the",
    "and",
    "for",
    "with",
}

# Domain and architecture keyword groups
DOMAIN_KEYWORDS: list[list[str]] = [
    ["healthcare", "medical", "patient", "clinical"],
    ["finance", "payment", "banking", "financial"],
    ["ecommerce", "retail", "shopping", "commerce"],
    ["education", "learning", "student", "academic"],
    ["iot", "device", "sensor", "embedded"],
    ["mobile", "app", "ios", "android"],
]

ARCHITECTURE_PATTERNS: list[list[str]] = [
    ["microservices", "service", "microservice"],
    ["api", "rest", "graphql", "endpoint"],
    ["database", "data", "storage", "persistence"],
    ["authentication", "auth", "identity", "oauth"],
    ["messaging", "queue", "event", "pub-sub"],
    ["cache", "caching", "redis", "memory"],
    ["monitoring", "logging", "observability", "metrics"],
]

# Technology keyword lists (two variants to preserve legacy behavior)
TECH_KEYWORDS_SHARED: list[str] = [
    "react",
    "angular",
    "vue",
    "node",
    "node.js",
    "python",
    "java",
    "golang",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "postgres",
    "mysql",
    "mongodb",
    "jwt",
    "oauth",
    "rest",
    "graphql",
    "grpc",
]

TECH_KEYWORDS_COUNT: list[str] = [
    "react",
    "angular",
    "vue",
    "node",
    "node.js",
    "python",
    "java",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "postgres",
    "mysql",
    "mongodb",
    "jwt",
    "oauth",
]


def compute_common_title_words(titles: list[str], top_k: int = 10) -> list[str]:
    """Return top_k common title words excluding title stop words and short tokens."""
    title_words: list[str] = []
    for title in titles:
        title_words.extend((title or "").lower().split())
    common = [
        word
        for word, count in Counter(title_words).most_common(top_k)
        if len(word) > 3 and word not in TITLE_STOP_WORDS
    ]
    return common


def cosine_similarity(
    vec1: list[float] | Iterable[float], vec2: list[float] | Iterable[float]
) -> float:
    """Compute cosine similarity with numpy, guarding zero vectors.

    Mirrors legacy behavior in CDI.
    """
    try:
        a = np.array(list(vec1), dtype=float)
        b = np.array(list(vec2), dtype=float)
        mag_a = np.linalg.norm(a)
        mag_b = np.linalg.norm(b)
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (mag_a * mag_b))
    except Exception:
        return 0.0


def hierarchical_distance_from_breadcrumbs(
    breadcrumb1: str | None, breadcrumb2: str | None
) -> float:
    """Compute hierarchical relatedness score using breadcrumb overlap.

    Returns 0.7 for sibling docs (same parent, different leaf), otherwise Jaccard
    overlap of breadcrumb sets. Returns 0.0 if unavailable.
    """
    if not breadcrumb1 or not breadcrumb2:
        return 0.0
    parts1 = breadcrumb1.split(" > ")
    parts2 = breadcrumb2.split(" > ")
    if (
        len(parts1) == len(parts2)
        and len(parts1) > 1
        and parts1[:-1] == parts2[:-1]
        and parts1[-1] != parts2[-1]
    ):
        return 0.7
    set1 = set(parts1)
    set2 = set(parts2)
    if not set1 or not set2:
        return 0.0
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union if union > 0 else 0.0


def split_breadcrumb(breadcrumb: str | None) -> list[str]:
    """Split a breadcrumb string into parts using ' > ' delimiter, safely."""
    if not breadcrumb:
        return []
    return [part for part in breadcrumb.split(" > ") if part]


def cluster_key_from_breadcrumb(breadcrumb: str | None, levels: int = 2) -> str:
    """Build a cluster key from the first N breadcrumb levels."""
    parts = split_breadcrumb(breadcrumb)
    if not parts:
        return "root"
    if levels <= 0:
        return " > ".join(parts)
    return " > ".join(parts[:levels])


def format_hierarchy_cluster_name(context_key: str) -> str:
    """Format a human-readable cluster name for hierarchy-based clusters."""
    if context_key == "root":
        return "Root Documentation"
    parts = split_breadcrumb(context_key)
    if len(parts) == 1:
        return f"{parts[0]} Section"
    if len(parts) >= 2:
        return f"{parts[0]} > {parts[1]}"
    return f"{context_key} Hierarchy"


def clean_topic_name(topic: str) -> str:
    """Normalize topic names for display: trim and Title-Case if lowercase."""
    if not topic:
        return ""
    topic = topic.strip()
    if topic.islower():
        return topic.title()
    return topic


def categorize_cluster_size(size: int) -> str:
    """Map cluster size to human-readable bucket.

    Follows legacy thresholds: individual<=1, small<=3, medium<=8, large<=15, else very large.
    """
    if size <= 1:
        return "individual"
    if size <= 3:
        return "small"
    if size <= 8:
        return "medium"
    if size <= 15:
        return "large"
    return "very large"


def normalize_acronym(token: str) -> str:
    """Normalize common acronyms for display consistently across CDI modules.

    Falls back to Title Case when not in mapping and tolerates None/empty input.
    """
    mapping = {
        "oauth": "OAuth",
        "jwt": "JWT",
        "api": "API",
        "ui": "UI",
        "ux": "UX",
        "sql": "SQL",
    }
    t = (token or "").strip()
    lower = t.lower()
    return mapping.get(lower, t.title())
