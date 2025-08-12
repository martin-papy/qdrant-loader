"""Semantic query expansion using spaCy word vectors and entity matching."""

from dataclasses import dataclass
from typing import Any

from ...utils.logging import LoggingConfig
from .spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer

logger = LoggingConfig.get_logger(__name__)


@dataclass
class ExpansionResult:
    """Container for query expansion results."""

    original_query: str
    expanded_query: str
    expansion_terms: list[str]
    semantic_terms: list[str]
    entity_terms: list[str]
    concept_terms: list[str]
    expansion_weight: float  # Weight given to expansion terms (0-1)
    processing_time_ms: float


class EntityQueryExpander:
    """Semantic query expansion using spaCy entities and word vectors."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the entity query expander.

        Args:
            spacy_analyzer: SpaCy analyzer instance for semantic analysis
        """
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)

        # Expansion configuration
        self.max_semantic_expansions = 3  # Max semantic terms to add
        self.max_entity_expansions = 2  # Max entity-related terms to add
        self.max_concept_expansions = 2  # Max concept terms to add
        self.similarity_threshold = 0.6  # Minimum similarity for expansion

        # Domain-specific expansion dictionaries
        self.domain_expansions = {
            # Technical terms
            "api": ["interface", "endpoint", "service", "restful"],
            "database": ["db", "storage", "persistence", "data"],
            "authentication": ["auth", "login", "credentials", "security"],
            "authorization": ["access", "permissions", "roles", "security"],
            "architecture": ["design", "structure", "pattern", "system"],
            "performance": ["optimization", "speed", "efficiency", "tuning"],
            # Business terms
            "requirements": ["specs", "specifications", "needs", "criteria"],
            "documentation": ["docs", "guide", "manual", "reference"],
            "proposal": ["offer", "bid", "submission", "plan"],
            "evaluation": ["assessment", "review", "analysis", "comparison"],
            "vendor": ["supplier", "provider", "contractor", "partner"],
            # Content types
            "code": ["implementation", "function", "method", "script"],
            "table": ["data", "spreadsheet", "grid", "matrix"],
            "image": ["picture", "diagram", "screenshot", "visual"],
            "document": ["file", "paper", "report", "text"],
        }

        # Cache for expansion results
        self._expansion_cache: dict[str, ExpansionResult] = {}

    def expand_query(
        self, original_query: str, search_context: dict[str, Any] | None = None
    ) -> ExpansionResult:
        """Expand query using spaCy entities and document metadata.

        Args:
            original_query: The original search query
            search_context: Optional context containing document entities and metadata

        Returns:
            ExpansionResult containing the expanded query and metadata
        """
        import time

        start_time = time.time()

        # Check cache first
        cache_key = f"{original_query}:{str(search_context)}"
        if cache_key in self._expansion_cache:
            cached = self._expansion_cache[cache_key]
            logger.debug(f"Using cached expansion for: {original_query[:50]}...")
            return cached

        try:
            # Analyze the original query
            query_analysis = self.spacy_analyzer.analyze_query_semantic(original_query)

            # Collect expansion terms from different sources
            expansion_terms = []
            semantic_terms = []
            entity_terms = []
            concept_terms = []

            # 1. Semantic expansion using spaCy similarity
            semantic_terms = self._expand_with_semantic_similarity(
                query_analysis, search_context
            )
            expansion_terms.extend(semantic_terms)

            # 2. Entity-based expansion
            entity_terms = self._expand_with_entities(query_analysis, search_context)
            expansion_terms.extend(entity_terms)

            # 3. Concept-based expansion using noun chunks
            concept_terms = self._expand_with_concepts(query_analysis, search_context)
            expansion_terms.extend(concept_terms)

            # 4. Domain-specific expansion
            domain_terms = self._expand_with_domain_knowledge(query_analysis)
            expansion_terms.extend(domain_terms)

            # Remove duplicates and filter
            expansion_terms = self._filter_expansion_terms(
                expansion_terms, query_analysis.semantic_keywords
            )

            # Build expanded query with appropriate weighting
            expanded_query, expansion_weight = self._build_expanded_query(
                original_query, expansion_terms, query_analysis
            )

            # Create result
            processing_time_ms = (time.time() - start_time) * 1000

            result = ExpansionResult(
                original_query=original_query,
                expanded_query=expanded_query,
                expansion_terms=expansion_terms,
                semantic_terms=semantic_terms,
                entity_terms=entity_terms,
                concept_terms=concept_terms,
                expansion_weight=expansion_weight,
                processing_time_ms=processing_time_ms,
            )

            # Cache the result
            self._expansion_cache[cache_key] = result

            logger.debug(
                "🔥 Query expansion completed",
                original_query=original_query[:50],
                expansion_terms_count=len(expansion_terms),
                semantic_terms_count=len(semantic_terms),
                entity_terms_count=len(entity_terms),
                concept_terms_count=len(concept_terms),
                processing_time_ms=processing_time_ms,
            )

            return result

        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            # Return minimal expansion
            processing_time_ms = (time.time() - start_time) * 1000
            return ExpansionResult(
                original_query=original_query,
                expanded_query=original_query,
                expansion_terms=[],
                semantic_terms=[],
                entity_terms=[],
                concept_terms=[],
                expansion_weight=0.0,
                processing_time_ms=processing_time_ms,
            )

    def _expand_with_semantic_similarity(
        self, query_analysis: QueryAnalysis, search_context: dict[str, Any] | None
    ) -> list[str]:
        """Expand using semantic similarity with spaCy word vectors."""
        semantic_terms = []

        if not search_context or "document_entities" not in search_context:
            return semantic_terms

        try:
            document_entities = search_context["document_entities"]

            # Find semantically similar entities
            for entity in document_entities[:20]:  # Limit to avoid performance issues
                entity_text = (
                    entity
                    if isinstance(entity, str)
                    else entity.get("text", str(entity))
                )

                # Calculate similarity with query
                similarity = self.spacy_analyzer.semantic_similarity_matching(
                    query_analysis, entity_text
                )

                # Add if above threshold
                if similarity >= self.similarity_threshold:
                    # Extract meaningful words from entity
                    entity_words = self._extract_entity_words(entity_text)
                    semantic_terms.extend(entity_words)

                    if len(semantic_terms) >= self.max_semantic_expansions:
                        break

        except Exception as e:
            logger.warning(f"Semantic similarity expansion failed: {e}")

        return semantic_terms[: self.max_semantic_expansions]

    def _expand_with_entities(
        self, query_analysis: QueryAnalysis, search_context: dict[str, Any] | None
    ) -> list[str]:
        """Expand using related entities from the query and context."""
        entity_terms = []

        try:
            # Use entities from the query itself
            for entity_text, entity_type in query_analysis.entities:
                # Add synonyms based on entity type
                synonyms = self._get_entity_synonyms(entity_text, entity_type)
                entity_terms.extend(synonyms)

            # Use entities from search context if available
            if search_context and "related_entities" in search_context:
                related_entities = search_context["related_entities"]
                for entity in related_entities[:5]:  # Limit for performance
                    entity_text = (
                        entity
                        if isinstance(entity, str)
                        else entity.get("text", str(entity))
                    )
                    entity_words = self._extract_entity_words(entity_text)
                    entity_terms.extend(entity_words)

        except Exception as e:
            logger.warning(f"Entity-based expansion failed: {e}")

        return entity_terms[: self.max_entity_expansions]

    def _expand_with_concepts(
        self, query_analysis: QueryAnalysis, search_context: dict[str, Any] | None
    ) -> list[str]:
        """Expand using main concepts and noun chunks."""
        concept_terms = []

        try:
            # Use main concepts from query analysis
            for concept in query_analysis.main_concepts:
                # Extract individual words from concepts
                concept_words = self._extract_concept_words(concept)
                concept_terms.extend(concept_words)

            # Add related concepts if available in context
            if search_context and "related_concepts" in search_context:
                related_concepts = search_context["related_concepts"]
                for concept in related_concepts[:3]:
                    concept_words = self._extract_concept_words(str(concept))
                    concept_terms.extend(concept_words)

        except Exception as e:
            logger.warning(f"Concept-based expansion failed: {e}")

        return concept_terms[: self.max_concept_expansions]

    def _expand_with_domain_knowledge(self, query_analysis: QueryAnalysis) -> list[str]:
        """Expand using domain-specific knowledge."""
        domain_terms = []

        try:
            # Check if any query keywords match our domain expansions
            for keyword in query_analysis.semantic_keywords:
                if keyword in self.domain_expansions:
                    domain_terms.extend(self.domain_expansions[keyword])

            # Check main concepts for domain matches
            for concept in query_analysis.main_concepts:
                concept_lower = concept.lower().strip()
                if concept_lower in self.domain_expansions:
                    domain_terms.extend(self.domain_expansions[concept_lower])

        except Exception as e:
            logger.warning(f"Domain knowledge expansion failed: {e}")

        return domain_terms[:3]  # Limit domain expansions

    def _extract_entity_words(self, entity_text: str) -> list[str]:
        """Extract meaningful words from entity text."""
        # Simple extraction - split and filter
        words = entity_text.lower().split()
        return [word for word in words if len(word) > 2 and word.isalpha()]

    def _extract_concept_words(self, concept_text: str) -> list[str]:
        """Extract meaningful words from concept text."""
        # Use spaCy to process and extract meaningful terms
        try:
            doc = self.spacy_analyzer.nlp(concept_text)
            return [
                token.lemma_.lower()
                for token in doc
                if (
                    token.is_alpha
                    and not token.is_stop
                    and len(token.text) > 2
                    and token.pos_ in {"NOUN", "VERB", "ADJ"}
                )
            ]
        except Exception:
            # Fallback to simple splitting
            words = concept_text.lower().split()
            return [word for word in words if len(word) > 2 and word.isalpha()]

    def _get_entity_synonyms(self, entity_text: str, entity_type: str) -> list[str]:
        """Get synonyms for entities based on their type."""
        synonyms = []

        # Type-specific synonym mapping
        type_synonyms = {
            "ORG": lambda text: [
                text.lower(),
                f"{text.lower()} company",
                f"{text.lower()} organization",
            ],
            "PRODUCT": lambda text: [
                text.lower(),
                f"{text.lower()} software",
                f"{text.lower()} tool",
            ],
            "PERSON": lambda text: [
                text.lower(),
                f"{text.lower()} developer",
                f"{text.lower()} author",
            ],
            "GPE": lambda text: [text.lower(), f"{text.lower()} location"],
        }

        if entity_type in type_synonyms:
            try:
                synonyms = type_synonyms[entity_type](entity_text)
            except Exception:
                synonyms = [entity_text.lower()]
        else:
            synonyms = [entity_text.lower()]

        return synonyms[:2]  # Limit synonyms

    def _filter_expansion_terms(
        self, expansion_terms: list[str], original_keywords: list[str]
    ) -> list[str]:
        """Filter and deduplicate expansion terms."""
        # Remove duplicates and original keywords
        original_set = set(original_keywords)
        filtered_terms = []
        seen = set()

        for term in expansion_terms:
            term_clean = term.lower().strip()
            if (
                term_clean not in original_set
                and term_clean not in seen
                and len(term_clean) > 2
                and term_clean.isalpha()
            ):
                filtered_terms.append(term_clean)
                seen.add(term_clean)

        return filtered_terms[:5]  # Limit total expansions

    def _build_expanded_query(
        self,
        original_query: str,
        expansion_terms: list[str],
        query_analysis: QueryAnalysis,
    ) -> tuple[str, float]:
        """Build the expanded query with appropriate weighting."""
        if not expansion_terms:
            return original_query, 0.0

        # Determine expansion weight based on query characteristics
        if query_analysis.complexity_score > 0.5:
            # Complex queries get less expansion to avoid noise
            expansion_weight = 0.2
            max_terms = 2
        elif query_analysis.is_technical:
            # Technical queries benefit from more expansion
            expansion_weight = 0.4
            max_terms = 3
        else:
            # General queries get moderate expansion
            expansion_weight = 0.3
            max_terms = 3

        # Select best expansion terms
        selected_terms = expansion_terms[:max_terms]

        # Build expanded query
        expansion_part = " ".join(selected_terms)
        expanded_query = f"{original_query} {expansion_part}"

        return expanded_query, expansion_weight

    def clear_cache(self):
        """Clear expansion cache."""
        self._expansion_cache.clear()
        logger.debug("Cleared query expansion cache")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "expansion_cache_size": len(self._expansion_cache),
        }
