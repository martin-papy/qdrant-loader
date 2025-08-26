from __future__ import annotations

import re
from typing import Any

from ....utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class LegacyConflictDetectorAdapter:
    """Adapter that hosts legacy/test-specific compatibility methods.

    This wraps a current `ConflictDetector` instance and provides
    the old compatibility helpers used by tests without bloating
    the main detector implementation.
    """

    def __init__(self, detector: Any):
        self.detector = detector
        self.logger = LoggingConfig.get_logger(__name__)

    def _find_contradiction_patterns(self, doc1, doc2):
        try:
            text1 = getattr(doc1, "text", getattr(doc1, "content", ""))
            text2 = getattr(doc2, "text", getattr(doc2, "content", ""))

            patterns = []

            # Version conflicts
            version_pattern = r"version\s+(\d+\.\d+\.\d+)"
            versions1 = re.findall(version_pattern, text1.lower())
            versions2 = re.findall(version_pattern, text2.lower())

            if versions1 and versions2 and versions1 != versions2:
                patterns.append(
                    {
                        "type": "version_conflict",
                        "reason": f"Version mismatch: {versions1[0]} vs {versions2[0]}",
                        "confidence": 0.8,
                    }
                )

            # Procedural conflicts
            conflict_indicators = [
                ("should not", "should"),
                ("avoid", "use"),
                ("deprecated", "recommended"),
                ("wrong", "correct"),
                ("never", "always"),
                ("must not", "must"),
                ("don't", "do"),
            ]

            for negative, positive in conflict_indicators:
                if (negative in text1.lower() and positive in text2.lower()) or (
                    negative in text2.lower() and positive in text1.lower()
                ):
                    patterns.append(
                        {
                            "type": "procedural_conflict",
                            "reason": f"Conflicting advice: '{negative}' vs '{positive}'",
                            "confidence": 0.8,
                        }
                    )

            return patterns
        except Exception as e:
            self.logger.warning(
                f"Error in compatibility method _find_contradiction_patterns: {e}"
            )
            return []

    def _detect_version_conflicts(self, doc1, doc2):
        try:
            text1 = getattr(doc1, "text", getattr(doc1, "content", ""))
            text2 = getattr(doc2, "text", getattr(doc2, "content", ""))

            import re

            version_pattern = r"(?:python|node|java|version)\s*(\d+\.\d+(?:\.\d+)?)"
            versions1 = re.findall(version_pattern, text1.lower())
            versions2 = re.findall(version_pattern, text2.lower())

            if versions1 and versions2:
                for v1 in versions1:
                    for v2 in versions2:
                        if v1 != v2:
                            return [
                                {
                                    "type": "version_conflict",
                                    "reason": f"Version mismatch: {v1} vs {v2}",
                                    "summary": f"Version mismatch: {v1} vs {v2}",
                                    "confidence": 0.8,
                                }
                            ]

            # Fallback to metadata analysis from detector
            try:
                has_conflict, reason, confidence = (
                    self.detector._analyze_metadata_conflicts(doc1, doc2)
                )
                if (
                    has_conflict
                    and isinstance(reason, str)
                    and "version" in reason.lower()
                ):
                    return [
                        {
                            "type": "version_conflict",
                            "reason": reason,
                            "confidence": confidence,
                        }
                    ]
            except Exception as exc:
                self.logger.exception(
                    "Metadata conflict analysis failed during version conflict detection",
                    exc_info=exc,
                )
            return []
        except Exception as e:
            self.logger.warning(f"Error in version conflict detection: {e}")
            return []

    def _detect_procedural_conflicts(self, doc1, doc2):
        try:
            text1 = getattr(doc1, "text", getattr(doc1, "content", ""))
            text2 = getattr(doc2, "text", getattr(doc2, "content", ""))

            procedural_conflicts = [
                ("should", "should not"),
                ("must", "must not"),
                ("manually", "automated"),
                ("always", "never"),
            ]

            for positive, negative in procedural_conflicts:
                if (positive in text1.lower() and negative in text2.lower()) or (
                    negative in text1.lower() and positive in text2.lower()
                ):
                    return [
                        {
                            "type": "procedural_conflict",
                            "reason": f"Conflicting procedures: '{positive}' vs '{negative}'",
                            "confidence": 0.8,
                        }
                    ]

            # Fallback to text analysis if available
            try:
                has_conflict, reason, confidence = (
                    self.detector._analyze_text_conflicts(doc1, doc2)
                )
                if has_conflict and any(
                    k in str(reason).lower()
                    for k in ["procedure", "process", "steps", "workflow"]
                ):
                    return [
                        {
                            "type": "procedural_conflict",
                            "reason": reason,
                            "confidence": confidence,
                        }
                    ]
            except Exception as exc:
                self.logger.exception(
                    "Text conflict analysis failed during procedural conflict detection",
                    exc_info=exc,
                )

            return []
        except Exception as e:
            self.logger.warning(f"Error in procedural conflict detection: {e}")
            return []


__all__ = [
    "LegacyConflictDetectorAdapter",
]
