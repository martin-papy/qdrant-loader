from __future__ import annotations

from ...components.search_result_models import HybridSearchResult


def apply_diversity_filtering(
    results: list[HybridSearchResult], diversity_factor: float, limit: int
) -> list[HybridSearchResult]:
    """Promote variety in the top-N results based on a diversity factor.

    Penalizes repeated source types, section types, and identical source/title pairs
    before selecting the final `limit` results, mirroring legacy behavior.

    Valid range for `diversity_factor` is [0.0, 1.0]. Values outside this range
    will raise a ValueError.
    """
    # Validate inputs
    if not (0.0 <= diversity_factor <= 1.0):
        raise ValueError(
            f"diversity_factor must be within [0.0, 1.0], got {diversity_factor}"
        )
    if diversity_factor == 0.0 or len(results) <= limit:
        return results[:limit]

    diverse_results: list[HybridSearchResult] = []
    used_source_types: set[str] = set()
    used_section_types: set[str] = set()
    used_sources: set[str] = set()

    # First pass: Take top results while ensuring diversity
    for result in results:
        if len(diverse_results) >= limit:
            break

        # Calculate diversity score
        diversity_score = 1.0

        # Penalize duplicate source types (less diversity)
        source_type = result.source_type
        if source_type in used_source_types:
            diversity_score *= 1.0 - diversity_factor * 0.3

        # Penalize duplicate section types
        section_type = result.section_type or "unknown"
        if section_type in used_section_types:
            diversity_score *= 1.0 - diversity_factor * 0.2

        # Penalize duplicate sources (same document/file)
        source_key = f"{result.source_type}:{result.source_title}"
        if source_key in used_sources:
            diversity_score *= 1.0 - diversity_factor * 0.4

        # Apply diversity penalty to score
        adjusted_score = result.score * diversity_score

        # Use original score to determine if we should include this result
        if len(diverse_results) < limit * 0.7 or adjusted_score >= result.score * 0.6:
            diverse_results.append(result)
            used_source_types.add(source_type)
            used_section_types.add(section_type)
            used_sources.add(source_key)

    # Second pass: Fill remaining slots with best remaining results
    remaining_slots = limit - len(diverse_results)
    if remaining_slots > 0:
        # Build an identifier set for O(1) membership checks while preserving order
        # Prefer a stable tuple key; fallback to object id if needed
        def _result_key(r: HybridSearchResult) -> tuple:
            return (
                r.document_id,
                r.source_type,
                r.source_title,
                r.section_type,
                r.section_title,
            )

        existing_keys = {_result_key(r) for r in diverse_results}
        remaining_results = [r for r in results if _result_key(r) not in existing_keys]
        diverse_results.extend(remaining_results[:remaining_slots])

    return diverse_results[:limit]
