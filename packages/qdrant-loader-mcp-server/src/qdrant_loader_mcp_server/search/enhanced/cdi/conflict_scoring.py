from __future__ import annotations

from typing import Any


def analyze_text_conflicts(
    detector: Any, doc1: Any, doc2: Any
) -> tuple[bool, str, float]:
    """spaCy-driven textual conflict heuristics (extracted)."""
    try:
        doc1_analysis = detector.spacy_analyzer.analyze_query_semantic(doc1.content)
        doc2_analysis = detector.spacy_analyzer.analyze_query_semantic(doc2.content)

        doc1_entities = {ent[0].lower() for ent in doc1_analysis.entities}
        doc2_entities = {ent[0].lower() for ent in doc2_analysis.entities}
        doc1_keywords = {kw.lower() for kw in doc1_analysis.semantic_keywords}
        doc2_keywords = {kw.lower() for kw in doc2_analysis.semantic_keywords}

        entity_overlap = len(doc1_entities & doc2_entities) / max(
            len(doc1_entities | doc2_entities), 1
        )
        _keyword_overlap = len(doc1_keywords & doc2_keywords) / max(
            len(doc1_keywords | doc2_keywords), 1
        )

        conflict_indicators = [
            "should not",
            "avoid",
            "deprecated",
            "recommended",
            "best practice",
            "anti-pattern",
            "wrong",
            "correct",
            "instead",
            "better",
            "worse",
        ]

        doc1_indicators = sum(
            1 for indicator in conflict_indicators if indicator in doc1.content.lower()
        )
        doc2_indicators = sum(
            1 for indicator in conflict_indicators if indicator in doc2.content.lower()
        )

        if entity_overlap > 0.3 and (doc1_indicators > 0 or doc2_indicators > 0):
            confidence = min(
                entity_overlap * (doc1_indicators + doc2_indicators) / 10, 1.0
            )
            explanation = f"Similar topics with conflicting recommendations (overlap: {entity_overlap:.2f})"
            return True, explanation, confidence

        return False, "No textual conflicts detected", 0.0
    except Exception as e:  # pragma: no cover
        detector.logger.error(f"Error in text conflict analysis: {e}")
        return False, f"Text analysis error: {str(e)}", 0.0


def analyze_metadata_conflicts(
    detector: Any, doc1: Any, doc2: Any
) -> tuple[bool, str, float]:
    """Metadata-driven conflict heuristics (extracted)."""
    try:
        conflicts: list[tuple[str, float, str]] = []
        total_weight = 0.0

        doc1_date = getattr(doc1, "created_at", None)
        doc2_date = getattr(doc2, "created_at", None)
        if doc1_date and doc2_date:
            date_diff = abs((doc1_date - doc2_date).days)
            if date_diff > 365:
                conflicts.append(
                    ("date_conflict", 0.3, f"Documents created {date_diff} days apart")
                )
                total_weight += 0.3

        if doc1.source_type != doc2.source_type:
            source_conflicts = {("confluence", "git"): 0.2, ("jira", "confluence"): 0.1}
            conflict_key = tuple(sorted([doc1.source_type, doc2.source_type]))
            if conflict_key in source_conflicts:
                w = source_conflicts[conflict_key]
                conflicts.append(
                    (
                        "source_type_conflict",
                        w,
                        f"Different source types: {conflict_key}",
                    )
                )
                total_weight += w

        if (
            hasattr(doc1, "project_id")
            and hasattr(doc2, "project_id")
            and doc1.project_id != doc2.project_id
        ):
            conflicts.append(
                (
                    "project_conflict",
                    0.1,
                    f"Different projects: {doc1.project_id} vs {doc2.project_id}",
                )
            )
            total_weight += 0.1

        if conflicts and total_weight > 0.2:
            explanation = "; ".join([c[2] for c in conflicts])
            return True, explanation, min(total_weight, 1.0)

        return False, "No metadata conflicts detected", 0.0
    except Exception as e:  # pragma: no cover
        detector.logger.error(f"Error in metadata conflict analysis: {e}")
        return False, f"Metadata analysis error: {str(e)}", 0.0


def categorize_conflict(_detector: Any, patterns) -> str:
    if not patterns:
        return "unknown"
    for item in patterns:
        if isinstance(item, dict):
            pattern_text = item.get("type", "").lower()
        elif isinstance(item, tuple) and len(item) > 0:
            pattern_text = str(item[0]).lower()
        elif isinstance(item, str):
            pattern_text = item.lower()
        else:
            pattern_text = str(item).lower()

        if any(keyword in pattern_text for keyword in ["version", "deprecated"]):
            return "version"
        elif any(
            keyword in pattern_text
            for keyword in [
                "procedure",
                "process",
                "steps",
                "should",
                "must",
                "never",
                "always",
            ]
        ):
            return "procedural"
        elif any(
            keyword in pattern_text
            for keyword in [
                "data",
                "value",
                "number",
                "different values",
                "conflicting data",
            ]
        ):
            return "data"

    return "general"


def calculate_conflict_confidence(
    _detector: Any, patterns, doc1_score: float = 1.0, doc2_score: float = 1.0
) -> float:
    if not patterns:
        return 0.0
    confidences: list[float] = []
    for pattern in patterns:
        if isinstance(pattern, dict):
            confidences.append(pattern.get("confidence", 0.5))
        elif isinstance(pattern, tuple) and len(pattern) >= 2:
            try:
                confidences.append(float(pattern[1]))
            except (ValueError, IndexError):
                confidences.append(0.5)
        else:
            pattern_text = str(pattern).lower()
            if any(
                ind in pattern_text
                for ind in [
                    "conflict",
                    "incompatible",
                    "contradicts",
                    "different values",
                ]
            ):
                confidences.append(0.8)
            elif any(
                ind in pattern_text
                for ind in ["different approach", "alternative method"]
            ):
                confidences.append(0.6)
            elif any(ind in pattern_text for ind in ["unclear", "possibly different"]):
                confidences.append(0.3)
            else:
                confidences.append(0.5)
    pattern_strength = sum(confidences) / len(confidences) if confidences else 0.5
    doc_score_avg = (doc1_score + doc2_score) / 2
    return min(1.0, pattern_strength * doc_score_avg)
