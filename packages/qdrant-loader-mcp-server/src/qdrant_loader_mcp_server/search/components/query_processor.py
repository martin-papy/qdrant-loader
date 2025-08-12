"""Query processing logic for hybrid search."""

import re
from typing import Any

from ...utils.logging import LoggingConfig
from ..nlp.spacy_analyzer import SpaCyQueryAnalyzer


class QueryProcessor:
    """Handles query expansion and analysis for hybrid search."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the query processor.

        Args:
            spacy_analyzer: spaCy analyzer instance for semantic processing
        """
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)

        # Enhanced query expansions leveraging spaCy semantic understanding
        self.query_expansions = {
            "product requirements": [
                "PRD",
                "requirements document",
                "product specification",
            ],
            "requirements": ["specs", "requirements document", "features"],
            "architecture": ["system design", "technical architecture"],
            "UI": ["user interface", "frontend", "design"],
            "API": ["interface", "endpoints", "REST"],
            "database": ["DB", "data storage", "persistence"],
            "security": ["auth", "authentication", "authorization"],
            # Content-type aware expansions
            "code": ["implementation", "function", "method", "class"],
            "documentation": ["docs", "guide", "manual", "instructions"],
            "config": ["configuration", "settings", "setup"],
            "table": ["data", "spreadsheet", "excel", "csv"],
            "image": ["screenshot", "diagram", "chart", "visual"],
            "link": ["reference", "url", "external", "connection"],
        }

    async def expand_query(self, query: str) -> str:
        """Expand query with spaCy semantic understanding and related terms.

        Args:
            query: Original search query

        Returns:
            Expanded query with additional semantic terms
        """
        try:
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)

            # Start with original query
            expanded_query = query

            # Add semantic keywords for broader matching
            if query_analysis.semantic_keywords:
                # Add top semantic keywords
                semantic_terms = " ".join(query_analysis.semantic_keywords[:3])
                expanded_query = f"{query} {semantic_terms}"

            # Add main concepts for concept-based expansion
            if query_analysis.main_concepts:
                concept_terms = " ".join(query_analysis.main_concepts[:2])
                expanded_query = f"{expanded_query} {concept_terms}"

            if expanded_query != query:
                self.logger.debug(
                    "spaCy-enhanced query expansion",
                    original_query=query,
                    expanded_query=expanded_query,
                    semantic_keywords=query_analysis.semantic_keywords[:3],
                    main_concepts=query_analysis.main_concepts[:2],
                )

            return expanded_query

        except Exception as e:
            self.logger.warning(f"spaCy expansion failed, using fallback: {e}")
            return self._expand_query_fallback(query)

    async def expand_query_aggressive(self, query: str) -> str:
        """More aggressive query expansion for exploratory searches.

        Args:
            query: Original search query

        Returns:
            Aggressively expanded query with more semantic terms
        """
        try:
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)

            # Start with original query
            expanded_query = query

            # Add more semantic keywords (increased from 3 to 5)
            if query_analysis.semantic_keywords:
                semantic_terms = " ".join(query_analysis.semantic_keywords[:5])
                expanded_query = f"{query} {semantic_terms}"

            # Add more main concepts (increased from 2 to 4)
            if query_analysis.main_concepts:
                concept_terms = " ".join(query_analysis.main_concepts[:4])
                expanded_query = f"{expanded_query} {concept_terms}"

            # Add entity-based expansion
            if query_analysis.entities:
                entity_terms = " ".join([ent[0] for ent in query_analysis.entities[:3]])
                expanded_query = f"{expanded_query} {entity_terms}"

            self.logger.debug(
                "Aggressive query expansion for exploration",
                original_query=query,
                expanded_query=expanded_query,
                expansion_ratio=len(expanded_query.split()) / len(query.split()),
            )

            return expanded_query

        except Exception as e:
            self.logger.warning(f"Aggressive expansion failed, using standard: {e}")
            return await self.expand_query(query)

    def analyze_query(self, query: str) -> dict[str, Any]:
        """Analyze query using spaCy NLP for comprehensive understanding.

        Args:
            query: Search query to analyze

        Returns:
            Dictionary containing query analysis results
        """
        try:
            # Use spaCy analyzer for comprehensive query analysis
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)

            # Create enhanced query context using spaCy analysis
            context = {
                # Basic query characteristics
                "is_question": query_analysis.is_question,
                "is_broad": len(query.split()) < 5,
                "is_specific": len(query.split()) > 7,
                "is_technical": query_analysis.is_technical,
                "complexity_score": query_analysis.complexity_score,
                # spaCy-powered intent detection
                "probable_intent": query_analysis.intent_signals.get(
                    "primary_intent", "informational"
                ),
                "intent_confidence": query_analysis.intent_signals.get(
                    "confidence", 0.0
                ),
                "linguistic_features": query_analysis.intent_signals.get(
                    "linguistic_features", {}
                ),
                # Enhanced keyword extraction using spaCy
                "keywords": query_analysis.semantic_keywords,
                "entities": [
                    entity[0] for entity in query_analysis.entities
                ],  # Extract entity text
                "entity_types": [
                    entity[1] for entity in query_analysis.entities
                ],  # Extract entity labels
                "main_concepts": query_analysis.main_concepts,
                "pos_patterns": query_analysis.pos_patterns,
                # Store query analysis for later use
                "spacy_analysis": query_analysis,
            }

            # Enhanced content type preference detection using spaCy
            semantic_keywords_set = set(query_analysis.semantic_keywords)

            # Content type preference detection
            self._detect_content_preferences(context, semantic_keywords_set)

            self.logger.debug(
                "spaCy query analysis completed",
                intent=context["probable_intent"],
                confidence=context["intent_confidence"],
                entities_found=len(query_analysis.entities),
                keywords_extracted=len(query_analysis.semantic_keywords),
                processing_time_ms=query_analysis.processing_time_ms,
            )

            return context

        except Exception as e:
            self.logger.warning(f"spaCy analysis failed, using fallback: {e}")
            return self._analyze_query_fallback(query)

    def _detect_content_preferences(
        self, context: dict[str, Any], semantic_keywords_set: set[str]
    ) -> None:
        """Detect content type preferences from semantic keywords.

        Args:
            context: Query context to update with preferences
            semantic_keywords_set: Set of semantic keywords from query analysis
        """
        # Code preference detection
        code_keywords = {
            "code",
            "function",
            "implementation",
            "script",
            "method",
            "class",
            "api",
        }
        if semantic_keywords_set.intersection(code_keywords):
            context["prefers_code"] = True

        # Table/data preference detection
        table_keywords = {"table", "data", "excel", "spreadsheet", "csv", "sheet"}
        if semantic_keywords_set.intersection(table_keywords):
            context["prefers_tables"] = True

        # Image preference detection
        image_keywords = {"image", "diagram", "screenshot", "visual", "chart", "graph"}
        if semantic_keywords_set.intersection(image_keywords):
            context["prefers_images"] = True

        # Documentation preference detection
        doc_keywords = {
            "documentation",
            "doc",
            "guide",
            "manual",
            "instruction",
            "help",
        }
        if semantic_keywords_set.intersection(doc_keywords):
            context["prefers_docs"] = True

    def _expand_query_fallback(self, query: str) -> str:
        """Fallback query expansion using original expansion logic.

        Args:
            query: Original search query

        Returns:
            Expanded query using fallback logic
        """
        expanded_query = query
        lower_query = query.lower()

        for key, expansions in self.query_expansions.items():
            if key.lower() in lower_query:
                expansion_terms = " ".join(expansions)
                expanded_query = f"{query} {expansion_terms}"
                self.logger.debug(
                    "Expanded query (fallback)",
                    original_query=query,
                    expanded_query=expanded_query,
                )
                break

        return expanded_query

    def _analyze_query_fallback(self, query: str) -> dict[str, Any]:
        """Fallback query analysis using original regex patterns.

        Args:
            query: Search query to analyze

        Returns:
            Dictionary containing basic query analysis
        """
        context = {
            "is_question": bool(
                re.search(r"\?|what|how|why|when|who|where", query.lower())
            ),
            "is_broad": len(query.split()) < 5,
            "is_specific": len(query.split()) > 7,
            "probable_intent": "informational",
            "keywords": [
                word.lower() for word in re.findall(r"\b\w{3,}\b", query.lower())
            ],
        }

        lower_query = query.lower()
        if "how to" in lower_query or "steps" in lower_query:
            context["probable_intent"] = "procedural"
        elif any(
            term in lower_query for term in ["requirements", "prd", "specification"]
        ):
            context["probable_intent"] = "requirements"
        elif any(
            term in lower_query for term in ["architecture", "design", "structure"]
        ):
            context["probable_intent"] = "architecture"

        # Content type preferences (original logic)
        if any(
            term in lower_query
            for term in ["code", "function", "implementation", "script"]
        ):
            context["prefers_code"] = True
        if any(
            term in lower_query for term in ["table", "data", "excel", "spreadsheet"]
        ):
            context["prefers_tables"] = True
        if any(
            term in lower_query for term in ["image", "diagram", "screenshot", "visual"]
        ):
            context["prefers_images"] = True
        if any(
            term in lower_query for term in ["documentation", "docs", "guide", "manual"]
        ):
            context["prefers_docs"] = True

        return context
