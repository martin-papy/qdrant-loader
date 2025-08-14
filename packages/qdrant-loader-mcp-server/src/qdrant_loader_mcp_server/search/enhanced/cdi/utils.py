from __future__ import annotations

from typing import Iterable, TypeVar

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


