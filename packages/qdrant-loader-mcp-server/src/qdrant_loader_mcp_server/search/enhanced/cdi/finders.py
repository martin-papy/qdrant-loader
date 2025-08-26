"""
Complementary Content Discovery for Cross-Document Intelligence.

This module implements advanced complementary content discovery that identifies
documents which enhance understanding of a target document through
requirements-implementation chains, abstraction gaps, and cross-functional relationships.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ....utils.logging import LoggingConfig
from ...models import SearchResult
from .extractors.similarity_helpers import (
    get_shared_entities_count as cdi_get_shared_entities_count,
)
from .extractors.similarity_helpers import (
    get_shared_technologies_count as cdi_get_shared_technologies_count,
)
from .extractors.similarity_helpers import (
    get_shared_topics_count as cdi_get_shared_topics_count,
)
from .extractors.similarity_helpers import (
    has_reusable_architecture_patterns as cdi_has_reusable_architecture_patterns,
)
from .extractors.similarity_helpers import (
    has_shared_entities as cdi_has_shared_entities,
)
from .extractors.similarity_helpers import (
    has_shared_technologies as cdi_has_shared_technologies,
)
from .extractors.similarity_helpers import has_shared_topics as cdi_has_shared_topics
from .extractors.similarity_helpers import (
    has_transferable_domain_knowledge as cdi_has_transferable_domain_knowledge,
)
from .models import ComplementaryContent

logger = LoggingConfig.get_logger(__name__)


class ComplementaryContentFinder:
    """Finds complementary content that would enhance understanding of a target document."""

    def __init__(
        self,
        similarity_calculator,
        knowledge_graph=None,
    ):
        """Initialize the complementary content finder."""
        self.similarity_calculator = similarity_calculator
        self.knowledge_graph = knowledge_graph
        self.logger = LoggingConfig.get_logger(__name__)

    def find_complementary_content(
        self,
        target_doc,
        candidate_docs,
        max_recommendations: int = 5,
    ) -> ComplementaryContent:
        """Find complementary content for a target document."""
        start_time = time.time()

        recommendations = []
        target_doc_id = f"{target_doc.source_type}:{target_doc.source_title}"

        self.logger.info(f"Finding complementary content for target: {target_doc_id}")
        self.logger.info(f"Target doc topics: {target_doc.topics}")
        self.logger.info(f"Target doc entities: {target_doc.entities}")
        self.logger.info(f"Analyzing {len(candidate_docs)} candidate documents")

        for candidate in candidate_docs:
            candidate_id = f"{candidate.source_type}:{candidate.source_title}"

            if candidate_id == target_doc_id:
                continue

            # Consolidated candidate analysis debug (reduces verbosity)
            self.logger.debug(
                "Analyzing candidate",
                candidate_id=candidate_id,
                topics_count=len(candidate.topics),
                entities_count=len(candidate.entities),
            )

            # Calculate complementary score
            complementary_score, reason = self._calculate_complementary_score(
                target_doc, candidate
            )

            self.logger.info(
                f"Complementary score for {candidate_id}: {complementary_score:.3f} - {reason}"
            )

            if (
                complementary_score > 0.15
            ):  # Lowered threshold for complementary content
                recommendations.append((candidate_id, complementary_score, reason))
            else:
                # Log why it didn't make the cut
                self.logger.debug(
                    f"Rejected {candidate_id}: score {complementary_score:.3f} below threshold 0.15"
                )

        # Sort by complementary score
        recommendations.sort(key=lambda x: x[1], reverse=True)

        processing_time = (time.time() - start_time) * 1000
        self.logger.info(
            f"Found {len(recommendations)} complementary recommendations in {processing_time:.2f}ms"
        )

        return ComplementaryContent(
            target_doc_id=target_doc_id,
            recommendations=recommendations[:max_recommendations],
            recommendation_strategy="mixed",
        )

    def _calculate_complementary_score(
        self, target_doc, candidate_doc
    ) -> tuple[float, str]:
        """Calculate how complementary a candidate document is to the target.

        Redesigned algorithm that prioritizes intra-project relationships while
        maintaining intelligent inter-project discovery capabilities.
        """
        self.logger.info(
            f"=== Scoring {candidate_doc.source_title} against {target_doc.source_title} ==="
        )

        same_project = target_doc.project_id == candidate_doc.project_id
        self.logger.info(
            f"Project context: target={target_doc.project_id}, candidate={candidate_doc.project_id}, same_project={same_project}"
        )

        if same_project:
            # Prioritize intra-project relationships
            score, reason = self._score_intra_project_complementary(
                target_doc, candidate_doc
            )

            # Boost for high topic relevance within project
            if score > 0 and self._has_high_topic_overlap(target_doc, candidate_doc):
                boosted_score = min(0.95, score * 1.2)
                self.logger.info(
                    f"✓ Intra-project topic boost: {score:.3f} → {boosted_score:.3f}"
                )
                score = boosted_score
                reason = f"{reason} (high topic relevance)"

        else:
            # Evaluate inter-project relationships
            score, reason = self._score_inter_project_complementary(
                target_doc, candidate_doc
            )

            # Apply cross-project penalty (inter-project content is less immediately useful)
            if score > 0:
                adjusted_score = score * 0.8
                self.logger.info(
                    f"✓ Inter-project penalty applied: {score:.3f} → {adjusted_score:.3f}"
                )
                score = adjusted_score
                reason = f"Inter-project: {reason}"

        self.logger.info(
            f"Final complementary score: {score:.3f} for {candidate_doc.source_title} - {reason}"
        )
        return score, reason

    def _score_intra_project_complementary(
        self, target_doc, candidate_doc
    ) -> tuple[float, str]:
        """Score complementary relationships within the same project."""
        factors = []

        # A. Requirements ↔ Implementation Chain
        if self._is_requirements_implementation_pair(target_doc, candidate_doc):
            factors.append((0.85, "requirements-implementation"))
            self.logger.info("✓ Found requirements-implementation pair")

        # B. Abstraction Level Differences
        abstraction_gap = self._calculate_abstraction_gap(target_doc, candidate_doc)
        if abstraction_gap > 0:
            score = 0.7 + (abstraction_gap * 0.1)
            factors.append(
                (score, f"Different abstraction levels (gap: {abstraction_gap})")
            )
            self.logger.info(
                f"✓ Abstraction gap: {abstraction_gap} → score: {score:.3f}"
            )

        # C. Cross-Functional Perspectives
        if self._has_cross_functional_relationship(target_doc, candidate_doc):
            factors.append((0.75, "Cross-functional perspectives"))
            self.logger.info("✓ Cross-functional relationship detected")

        # D. Topic Overlap with Different Document Types
        if self._has_shared_topics(
            target_doc, candidate_doc
        ) and self._has_different_document_types(target_doc, candidate_doc):
            shared_topics = self._get_shared_topics_count(target_doc, candidate_doc)
            score = min(0.65, 0.35 + (shared_topics * 0.1))
            factors.append(
                (
                    score,
                    f"Same topics, different document types ({shared_topics} topics)",
                )
            )
            self.logger.info(f"✓ Topic overlap with different doc types: {score:.3f}")

        return self._calculate_weighted_score(factors, target_doc, candidate_doc)

    def _score_inter_project_complementary(
        self, target_doc, candidate_doc
    ) -> tuple[float, str]:
        """Score complementary relationships between different projects."""
        factors = []

        # A. Similar Challenges/Solutions
        if self._has_similar_challenges(target_doc, candidate_doc):
            factors.append((0.8, "Similar challenges/solutions"))
            self.logger.info("✓ Similar challenges detected")

        # B. Domain Expertise Transfer
        if self._has_transferable_domain_knowledge(target_doc, candidate_doc):
            factors.append((0.75, "Transferable domain knowledge"))
            self.logger.info("✓ Transferable domain knowledge")

        # C. Architectural Patterns
        if self._has_reusable_architecture_patterns(target_doc, candidate_doc):
            factors.append((0.7, "Reusable architecture patterns"))
            self.logger.info("✓ Architecture patterns detected")

        # D. Shared Technologies/Standards
        if self._has_shared_technologies(target_doc, candidate_doc):
            shared_count = self._get_shared_technologies_count(
                target_doc, candidate_doc
            )
            score = min(0.6, 0.3 + (shared_count * 0.1))
            factors.append((score, f"Shared technologies ({shared_count} common)"))
            self.logger.info(f"✓ Shared technologies: {score:.3f}")

        return self._calculate_weighted_score(factors, target_doc, candidate_doc)

    def _calculate_weighted_score(
        self,
        factors: list[tuple[float, str]],
        target_doc=None,
        candidate_doc=None,
    ) -> tuple[float, str]:
        """Calculate weighted score from multiple factors."""
        if not factors:
            if target_doc and candidate_doc:
                return self._enhanced_fallback_scoring(target_doc, candidate_doc)
            else:
                return 0.0, "No complementary relationship found"

        # Sort factors by score but give priority to requirements-implementation relationships
        factors.sort(key=lambda x: x[0], reverse=True)

        # Check for high-priority relationships first
        for score, reason in factors:
            if "requirements-implementation" in reason.lower():
                # Requirements-implementation pairs get priority
                if len(factors) > 1:
                    secondary_boost = sum(s for s, r in factors if r != reason) * 0.1
                    final_score = min(0.95, score + secondary_boost)
                    primary_reason = f"{reason} (+{len(factors)-1} other factors)"
                else:
                    final_score = score
                    primary_reason = reason
                return final_score, primary_reason

        # Use the highest scoring factor as primary
        primary_score, primary_reason = factors[0]

        # Boost if multiple factors contribute
        if len(factors) > 1:
            secondary_boost = sum(score for score, _ in factors[1:]) * 0.1
            final_score = min(0.95, primary_score + secondary_boost)
            primary_reason = f"{primary_reason} (+{len(factors)-1} other factors)"
        else:
            final_score = primary_score

        return final_score, primary_reason

    def _is_requirements_implementation_pair(self, doc1, doc2) -> bool:
        """Detect if documents form a requirements -> implementation chain."""
        req_keywords = [
            "requirements",
            "specification",
            "user story",
            "feature",
            "functional",
        ]
        impl_keywords = [
            "implementation",
            "technical",
            "architecture",
            "api",
            "code",
            "development",
        ]

        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()

        doc1_is_req = any(keyword in title1 for keyword in req_keywords)
        doc1_is_impl = any(keyword in title1 for keyword in impl_keywords)
        doc2_is_req = any(keyword in title2 for keyword in req_keywords)
        doc2_is_impl = any(keyword in title2 for keyword in impl_keywords)

        # One is requirements, other is implementation
        is_req_impl_pair = (doc1_is_req and doc2_is_impl) or (
            doc1_is_impl and doc2_is_req
        )

        if not is_req_impl_pair:
            return False

        # For same-project documents, we don't require shared topics/entities
        # as the project context already provides relationship
        same_project = (
            getattr(doc1, "project_id", None) == getattr(doc2, "project_id", None)
            and getattr(doc1, "project_id", None) is not None
        )

        if same_project:
            return True

        # For different projects, require some shared context
        return self._has_shared_topics(doc1, doc2) or self._has_shared_entities(
            doc1, doc2
        )

    def _calculate_abstraction_gap(self, doc1: SearchResult, doc2: SearchResult) -> int:
        """Calculate difference in abstraction levels (0-3).
        0: Same level, 3: Maximum gap (e.g., epic vs implementation detail)
        """
        level1 = self._get_abstraction_level(doc1)
        level2 = self._get_abstraction_level(doc2)
        return abs(level1 - level2)

    def _get_abstraction_level(self, doc: SearchResult) -> int:
        """Determine abstraction level of document (0=highest, 3=lowest)."""
        title = doc.source_title.lower()

        # Level 0: High-level business/strategy
        if any(
            keyword in title
            for keyword in [
                "strategy",
                "vision",
                "overview",
                "executive",
                "business case",
            ]
        ):
            return 0

        # Level 1: Requirements/features
        if any(
            keyword in title
            for keyword in [
                "requirements",
                "features",
                "user story",
                "epic",
                "specification",
            ]
        ):
            return 1

        # Level 2: Design/architecture
        if any(
            keyword in title
            for keyword in [
                "design",
                "architecture",
                "workflow",
                "process",
                "wireframe",
            ]
        ):
            return 2

        # Level 3: Implementation details
        if any(
            keyword in title
            for keyword in [
                "implementation",
                "code",
                "api",
                "technical",
                "development",
                "configuration",
            ]
        ):
            return 3

        # Default to middle level
        return 2

    def _has_cross_functional_relationship(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> bool:
        """Detect business + technical, feature + security, etc."""
        business_keywords = [
            "business",
            "user",
            "requirements",
            "workflow",
            "process",
            "feature",
        ]
        technical_keywords = [
            "technical",
            "architecture",
            "api",
            "implementation",
            "code",
            "development",
        ]
        security_keywords = [
            "security",
            "authentication",
            "authorization",
            "compliance",
            "audit",
        ]

        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()

        # Business + Technical
        if (
            any(k in title1 for k in business_keywords)
            and any(k in title2 for k in technical_keywords)
        ) or (
            any(k in title2 for k in business_keywords)
            and any(k in title1 for k in technical_keywords)
        ):
            return True

        # Feature + Security
        if (
            any(k in title1 for k in ["feature", "functionality"])
            and any(k in title2 for k in security_keywords)
        ) or (
            any(k in title2 for k in ["feature", "functionality"])
            and any(k in title1 for k in security_keywords)
        ):
            return True

        return False

    def _has_different_document_types(self, doc1, doc2) -> bool:
        """Check if documents are of different types based on content and title."""
        type1 = self._classify_document_type(doc1)
        type2 = self._classify_document_type(doc2)
        return type1 != type2

    def _classify_document_type(self, doc) -> str:
        """Classify document as: user_story, technical_spec, architecture, compliance, testing, etc."""
        title = doc.source_title.lower()

        # Check more specific categories first to avoid conflicts
        if any(
            keyword in title
            for keyword in ["security", "compliance", "audit", "policy"]
        ):
            return "compliance"
        elif any(keyword in title for keyword in ["test", "testing", "qa", "quality"]):
            return "testing"
        elif any(keyword in title for keyword in ["tutorial", "how-to", "walkthrough"]):
            return "tutorial"
        elif any(keyword in title for keyword in ["reference", "manual"]):
            return "reference"
        elif any(keyword in title for keyword in ["example", "sample", "demo"]):
            return "example"
        elif any(keyword in title for keyword in ["user story", "epic", "feature"]):
            return "user_story"
        elif any(
            keyword in title
            for keyword in ["technical", "specification", "api", "implementation"]
        ):
            return "technical_spec"
        elif any(keyword in title for keyword in ["architecture", "design", "system"]):
            return "architecture"
        elif any(
            keyword in title
            for keyword in ["workflow", "process", "procedure", "guide"]
        ):
            return "process"
        elif any(
            keyword in title for keyword in ["requirement"]
        ):  # More general, check last
            return "user_story"
        else:
            return "general"

    def _has_high_topic_overlap(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents have high topic overlap (>= 3 shared topics)."""
        return self._get_shared_topics_count(doc1, doc2) >= 3

    def _has_similar_challenges(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Identify common challenge patterns (auth, scalability, compliance)."""
        challenge_patterns = [
            ["authentication", "login", "auth", "signin"],
            ["scalability", "performance", "optimization", "scale"],
            ["compliance", "regulation", "audit", "governance"],
            ["integration", "api", "interface", "connection"],
            ["security", "privacy", "protection", "safety"],
            ["migration", "upgrade", "transition", "conversion"],
        ]

        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()

        for pattern in challenge_patterns:
            if any(keyword in title1 for keyword in pattern) and any(
                keyword in title2 for keyword in pattern
            ):
                return True

        return False

    def _has_transferable_domain_knowledge(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> bool:
        """Check for transferable domain expertise between projects (delegates to CDI helper)."""
        return cdi_has_transferable_domain_knowledge(doc1, doc2)

    def _has_reusable_architecture_patterns(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> bool:
        """Identify reusable architecture patterns (delegates to CDI helper)."""
        return cdi_has_reusable_architecture_patterns(doc1, doc2)

    def _has_shared_technologies(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Identify shared technologies, frameworks, standards (delegates to CDI helper)."""
        return cdi_has_shared_technologies(doc1, doc2)

    def _get_shared_technologies_count(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> int:
        """Count shared technologies between documents (delegates to CDI helper)."""
        return cdi_get_shared_technologies_count(doc1, doc2)

    def _enhanced_fallback_scoring(
        self, target_doc, candidate_doc
    ) -> tuple[float, str]:
        """Enhanced fallback when advanced algorithms don't apply."""
        fallback_score = self._calculate_fallback_score(target_doc, candidate_doc)
        if fallback_score > 0:
            return fallback_score, "Basic content similarity"
        else:
            return 0.0, "No complementary relationship found"

    def _calculate_fallback_score(
        self, target_doc: SearchResult, candidate_doc: SearchResult
    ) -> float:
        """Fallback scoring for when advanced methods don't find relationships."""
        score = 0.0

        # Just having any shared topics at all
        if self._has_shared_topics(target_doc, candidate_doc):
            shared_count = self._get_shared_topics_count(target_doc, candidate_doc)
            score = max(score, 0.2 + (shared_count * 0.05))
            self.logger.debug(
                f"Fallback: {shared_count} shared topics → score: {score:.3f}"
            )

        # Just having any shared entities at all
        if self._has_shared_entities(target_doc, candidate_doc):
            shared_count = self._get_shared_entities_count(target_doc, candidate_doc)
            score = max(score, 0.15 + (shared_count * 0.05))
            self.logger.debug(
                f"Fallback: {shared_count} shared entities → score: {score:.3f}"
            )

        # Simple keyword overlap in titles
        target_words = set(target_doc.source_title.lower().split())
        candidate_words = set(candidate_doc.source_title.lower().split())
        common_words = target_words & candidate_words
        if len(common_words) > 1:  # More than just common words like "the", "and"
            score = max(score, 0.1 + (len(common_words) * 0.02))
            self.logger.debug(
                f"Fallback: {len(common_words)} common words in titles → score: {score:.3f}"
            )

        return min(score, 0.5)  # Cap fallback scores

    def _has_shared_entities(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents have shared entities (delegates to CDI helper)."""
        return cdi_has_shared_entities(doc1, doc2)

    def _has_shared_topics(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents have shared topics (delegates to CDI helper)."""
        return cdi_has_shared_topics(doc1, doc2)

    def _get_shared_topics_count(self, doc1: SearchResult, doc2: SearchResult) -> int:
        """Get the count of shared topics (delegates to CDI helper)."""
        return cdi_get_shared_topics_count(doc1, doc2)

    def _get_shared_entities_count(self, doc1: SearchResult, doc2: SearchResult) -> int:
        """Get the count of shared entities (delegates to CDI helper)."""
        return cdi_get_shared_entities_count(doc1, doc2)

    def _has_different_content_complexity(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> bool:
        """Check if documents have different levels of content complexity."""
        # Compare word counts if available
        wc1 = int(getattr(doc1, "word_count", 0) or 0)
        wc2 = int(getattr(doc2, "word_count", 0) or 0)

        # Guard against None or non-positive counts to avoid ZeroDivisionError
        if wc1 > 0 and wc2 > 0:
            ratio = max(wc1, wc2) / min(wc1, wc2)
            if ratio > 2.0:  # One document is significantly longer
                return True

        # Compare content features
        features1 = (doc1.has_code_blocks, doc1.has_tables, doc1.has_images)
        features2 = (doc2.has_code_blocks, doc2.has_tables, doc2.has_images)

        # Different if one has technical content and the other doesn't
        return features1 != features2

    def _get_complementary_content_type_score(
        self, target_doc: SearchResult, candidate_doc: SearchResult
    ) -> float:
        """Calculate score based on complementary content types."""
        score = 0.0

        # Technical + Business complement
        technical_keywords = [
            "api",
            "code",
            "implementation",
            "technical",
            "development",
            "architecture",
        ]
        business_keywords = [
            "requirements",
            "business",
            "specification",
            "user",
            "workflow",
            "process",
        ]

        target_title = target_doc.source_title.lower()
        candidate_title = candidate_doc.source_title.lower()

        target_is_technical = any(
            keyword in target_title for keyword in technical_keywords
        )
        target_is_business = any(
            keyword in target_title for keyword in business_keywords
        )
        candidate_is_technical = any(
            keyword in candidate_title for keyword in technical_keywords
        )
        candidate_is_business = any(
            keyword in candidate_title for keyword in business_keywords
        )

        # Technical document + Business document = complementary
        if (target_is_technical and candidate_is_business) or (
            target_is_business and candidate_is_technical
        ):
            score = max(score, 0.7)

        # Documentation + Implementation complement
        if (
            "documentation" in target_title and "implementation" in candidate_title
        ) or ("implementation" in target_title and "documentation" in candidate_title):
            score = max(score, 0.6)

        # Tutorial + Reference complement
        tutorial_keywords = [
            "tutorial",
            "guide",
            "how-to",
            "walkthrough",
            "quick start",
        ]
        reference_keywords = ["reference", "api", "specification", "manual", "docs"]
        target_is_tutorial = any(k in target_title for k in tutorial_keywords)
        target_is_reference = any(k in target_title for k in reference_keywords)
        candidate_is_tutorial = any(k in candidate_title for k in tutorial_keywords)
        candidate_is_reference = any(k in candidate_title for k in reference_keywords)
        if (target_is_tutorial and candidate_is_reference) or (
            target_is_reference and candidate_is_tutorial
        ):
            score = max(score, 0.6)

        # Requirements + Design complement
        if (
            "requirements" in target_title
            and ("design" in candidate_title or "architecture" in candidate_title)
        ) or (
            ("design" in target_title or "architecture" in target_title)
            and "requirements" in candidate_title
        ):
            score = max(score, 0.6)

        return score
