"""Entity extraction module using Graphiti for LLM-based entity and relationship extraction."""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from graphiti_core.nodes import EpisodeType

from .graphiti_manager import GraphitiManager
from .prompts import EntityPromptManager
from .prompts.entity_prompts import PromptDomain
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class EntityType(Enum):
    """Supported entity types for extraction."""

    SERVICE = "Service"
    DATABASE = "Database"
    TEAM = "Team"
    PERSON = "Person"
    ORGANIZATION = "Organization"
    PROJECT = "Project"
    CONCEPT = "Concept"
    TECHNOLOGY = "Technology"
    API = "API"
    ENDPOINT = "Endpoint"


@dataclass
class ExtractedEntity:
    """Container for extracted entity information."""

    name: str
    entity_type: EntityType
    confidence: float = 0.0
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Container for entity extraction results."""

    entities: List[ExtractedEntity] = field(default_factory=list)
    processing_time: float = 0.0
    source_text: str = ""
    episode_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionConfig:
    """Configuration for entity extraction."""

    enabled_entity_types: List[EntityType] = field(
        default_factory=lambda: list(EntityType)
    )
    batch_size: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 3600  # seconds
    max_text_length: int = 10000
    confidence_threshold: float = 0.5
    enable_caching: bool = True


class EntityExtractor:
    """Entity extractor using Graphiti's LLM-based extraction."""

    def __init__(
        self,
        graphiti_manager: GraphitiManager,
        config: Optional[ExtractionConfig] = None,
        prompt_manager: Optional[EntityPromptManager] = None,
    ):
        """Initialize the entity extractor.

        Args:
            graphiti_manager: Initialized GraphitiManager instance
            config: Extraction configuration (uses defaults if not provided)
            prompt_manager: Prompt manager for custom prompts (creates default if not provided)
        """
        self.graphiti_manager = graphiti_manager
        self.config = config or ExtractionConfig()
        self.prompt_manager = prompt_manager or EntityPromptManager()
        self._cache: Dict[str, ExtractionResult] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # Statistics tracking
        self._stats = {
            "total_extractions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failed_extractions": 0,
            "total_entities_extracted": 0,
        }

        logger.info(
            f"EntityExtractor initialized with {len(self.config.enabled_entity_types)} enabled entity types"
        )

    async def extract_entities(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
        use_custom_prompts: bool = True,
    ) -> ExtractionResult:
        """Extract entities from text using Graphiti.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction
            domain: Domain for prompt selection (defaults to SOFTWARE_DEVELOPMENT)
            custom_prompt: Additional custom instructions for extraction
            use_custom_prompts: Whether to use custom domain-specific prompts

        Returns:
            ExtractionResult containing extracted entities
        """
        start_time = time.time()

        # Validate input
        if not text or not text.strip():
            logger.warning("Empty text provided for entity extraction")
            return ExtractionResult(
                source_text=text,
                processing_time=time.time() - start_time,
                errors=["Empty text provided"],
            )

        # Truncate text if too long
        if len(text) > self.config.max_text_length:
            logger.warning(
                f"Text too long ({len(text)} chars), truncating to {self.config.max_text_length}"
            )
            text = text[: self.config.max_text_length]

        # Check cache first
        cache_key = self._generate_cache_key(text, source_description)
        if self.config.enable_caching:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self._stats["cache_hits"] += 1
                logger.debug(f"Cache hit for extraction: {cache_key[:16]}...")
                return cached_result

        self._stats["cache_misses"] += 1
        self._stats["total_extractions"] += 1

        # Perform extraction with retry logic
        result = await self._extract_with_retry(
            text,
            source_description,
            reference_time,
            domain,
            custom_prompt,
            use_custom_prompts,
        )

        # Cache the result
        if self.config.enable_caching and not result.errors:
            self._store_in_cache(cache_key, result)

        # Update statistics
        self._stats["total_entities_extracted"] += len(result.entities)

        result.processing_time = time.time() - start_time
        logger.info(
            f"Extracted {len(result.entities)} entities in {result.processing_time:.2f}s"
        )

        return result

    async def extract_entities_batch(
        self,
        texts: List[str],
        source_descriptions: Optional[List[str]] = None,
        reference_times: Optional[List[datetime]] = None,
    ) -> List[ExtractionResult]:
        """Extract entities from multiple texts in batches.

        Args:
            texts: List of texts to extract entities from
            source_descriptions: Optional list of source descriptions
            reference_times: Optional list of reference times

        Returns:
            List of ExtractionResult objects
        """
        if not texts:
            return []

        logger.info(f"Starting batch entity extraction for {len(texts)} texts")

        # Prepare arguments - create proper lists with correct types
        actual_source_descriptions: List[Optional[str]] = []
        if source_descriptions is not None:
            actual_source_descriptions = [desc for desc in source_descriptions]
        else:
            actual_source_descriptions = [None] * len(texts)

        actual_reference_times: List[Optional[datetime]] = []
        if reference_times is not None:
            actual_reference_times = [time_ref for time_ref in reference_times]
        else:
            actual_reference_times = [None] * len(texts)

        # Process in batches
        results = []
        batch_size = self.config.batch_size

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_sources = actual_source_descriptions[i : i + batch_size]
            batch_times = actual_reference_times[i : i + batch_size]

            logger.debug(
                f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}"
            )

            # Process batch concurrently
            batch_tasks = [
                self.extract_entities(text, source, time_ref)
                for text, source, time_ref in zip(
                    batch_texts, batch_sources, batch_times
                )
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch extraction failed for text {i+j}: {result}")
                    error_result = ExtractionResult(
                        source_text=batch_texts[j],
                        errors=[f"Extraction failed: {str(result)}"],
                    )
                    results.append(error_result)
                    self._stats["failed_extractions"] += 1
                else:
                    results.append(result)

        logger.info(f"Batch extraction completed: {len(results)} results")
        return results

    async def _extract_with_retry(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
        use_custom_prompts: bool = True,
    ) -> ExtractionResult:
        """Extract entities with retry logic.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction

        Returns:
            ExtractionResult containing extracted entities
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await self._perform_extraction(
                    text,
                    source_description,
                    reference_time,
                    domain,
                    custom_prompt,
                    use_custom_prompts,
                )
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (
                        2**attempt
                    )  # Exponential backoff
                    logger.warning(
                        f"Extraction attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_retries + 1} extraction attempts failed"
                    )

        # All retries failed
        self._stats["failed_extractions"] += 1
        return ExtractionResult(
            source_text=text,
            errors=[
                f"Extraction failed after {self.config.max_retries + 1} attempts: {str(last_exception)}"
            ],
        )

    async def _perform_extraction(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
        use_custom_prompts: bool = True,
    ) -> ExtractionResult:
        """Perform the actual entity extraction using Graphiti.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction
            domain: Domain for prompt selection
            custom_prompt: Additional custom instructions for extraction
            use_custom_prompts: Whether to use custom domain-specific prompts

        Returns:
            ExtractionResult containing extracted entities
        """
        if not self.graphiti_manager.is_initialized:
            raise RuntimeError("GraphitiManager is not initialized")

        # Use custom prompts if enabled and available
        if use_custom_prompts and self.prompt_manager:
            try:
                return await self._perform_custom_prompt_extraction(
                    text, source_description, reference_time, domain, custom_prompt
                )
            except Exception as e:
                logger.warning(
                    f"Custom prompt extraction failed, falling back to default: {e}"
                )

        # Add episode to Graphiti for entity extraction
        episode_id = await self.graphiti_manager.add_episode(
            name=f"Entity extraction - {datetime.now(timezone.utc).isoformat()}",
            content=text,
            episode_type=EpisodeType.text,
            source_description=source_description or "Entity extraction source",
            reference_time=reference_time or datetime.now(timezone.utc),
        )

        # Wait a moment for Graphiti to process the episode and extract entities
        await asyncio.sleep(0.5)

        # Retrieve entities from the episode using the new search-based method
        try:
            # First try to get entities specifically from this episode
            entity_type_strings = [et.value for et in self.config.enabled_entity_types]
            nodes = await self.graphiti_manager.get_entities_from_episode(
                episode_id, entity_type_strings
            )

            # If no entities found from episode search, try a broader search with the text content
            if not nodes:
                logger.debug(
                    "No entities found from episode search, trying content-based search"
                )
                # Use key terms from the text for search
                search_terms = self._extract_search_terms(text)
                nodes = await self.graphiti_manager.search_entities(
                    query=search_terms, entity_types=entity_type_strings, limit=50
                )

        except Exception as e:
            logger.warning(f"Failed to retrieve entities from Graphiti: {e}")
            # Fallback to general node search
            nodes = await self.graphiti_manager.get_nodes(limit=50)

        entities = self._convert_nodes_to_entities(nodes, text)

        return ExtractionResult(
            entities=entities,
            source_text=text,
            episode_id=episode_id,
            metadata={
                "source_description": source_description,
                "reference_time": (
                    reference_time.isoformat() if reference_time else None
                ),
                "graphiti_episode_id": episode_id,
                "extraction_method": "graphiti_episode",
            },
        )

    def _extract_search_terms(self, text: str, max_terms: int = 5) -> str:
        """Extract key search terms from text for entity search.

        Args:
            text: Input text to extract terms from
            max_terms: Maximum number of terms to extract

        Returns:
            Space-separated search terms
        """
        # Simple keyword extraction - could be enhanced with NLP
        import re

        # Remove common words and extract meaningful terms
        words = re.findall(r"\b[A-Za-z]{3,}\b", text.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "its",
            "may",
            "new",
            "now",
            "old",
            "see",
            "two",
            "who",
            "boy",
            "did",
            "she",
            "use",
            "way",
            "will",
            "with",
            "this",
            "that",
            "have",
            "from",
            "they",
            "know",
            "want",
            "been",
            "good",
            "much",
            "some",
            "time",
            "very",
            "when",
            "come",
            "here",
            "just",
            "like",
            "long",
            "make",
            "many",
            "over",
            "such",
            "take",
            "than",
            "them",
            "well",
            "were",
        }

        meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]

        # Take the first max_terms unique words
        unique_terms = list(dict.fromkeys(meaningful_words))[:max_terms]

        return " ".join(unique_terms) if unique_terms else text[:50]

    def _convert_nodes_to_entities(
        self, nodes: List[Any], source_text: str
    ) -> List[ExtractedEntity]:
        """Convert Graphiti nodes to ExtractedEntity objects.

        Args:
            nodes: List of Graphiti nodes
            source_text: Original source text

        Returns:
            List of ExtractedEntity objects
        """
        entities = []

        for node in nodes:
            try:
                # Handle different node types from Graphiti search results
                # Graphiti search can return different types of objects

                # Extract basic node information
                if hasattr(node, "name"):
                    entity_name = node.name
                elif hasattr(node, "title"):
                    entity_name = node.title
                elif hasattr(node, "content"):
                    # For episode nodes, extract a meaningful name from content
                    entity_name = (
                        str(node.content)[:50] + "..."
                        if len(str(node.content)) > 50
                        else str(node.content)
                    )
                else:
                    entity_name = str(node)[:50]

                # Determine entity type
                entity_type = EntityType.CONCEPT  # Default fallback

                # Try to extract entity type from various possible attributes
                if hasattr(node, "entity_type"):
                    try:
                        entity_type = EntityType(node.entity_type)
                    except ValueError:
                        pass
                elif hasattr(node, "type"):
                    try:
                        entity_type = EntityType(node.type)
                    except ValueError:
                        pass
                elif hasattr(node, "labels") and node.labels:
                    # Neo4j nodes have labels
                    for label in node.labels:
                        try:
                            entity_type = EntityType(label)
                            break
                        except ValueError:
                            continue

                # Check if this entity type is enabled
                if entity_type not in self.config.enabled_entity_types:
                    continue

                # Extract confidence score
                confidence = 0.8  # Default confidence
                if hasattr(node, "confidence"):
                    confidence = float(node.confidence)
                elif hasattr(node, "score"):
                    confidence = float(node.score)
                elif hasattr(node, "relevance"):
                    confidence = float(node.relevance)

                # Extract context information
                context = ""
                if hasattr(node, "context"):
                    context = str(node.context)
                elif hasattr(node, "description"):
                    context = str(node.description)
                elif hasattr(node, "content"):
                    context = str(node.content)[:200]  # Truncate long content

                # Build metadata from available node attributes
                metadata = {}

                # Common attributes to extract
                for attr in [
                    "uuid",
                    "id",
                    "created_at",
                    "updated_at",
                    "source",
                    "episode_id",
                ]:
                    if hasattr(node, attr):
                        metadata[attr] = getattr(node, attr)

                # Handle Neo4j specific attributes
                if hasattr(node, "element_id"):
                    metadata["neo4j_element_id"] = node.element_id
                if hasattr(node, "labels"):
                    metadata["neo4j_labels"] = list(node.labels)
                if hasattr(node, "properties"):
                    metadata["properties"] = dict(node.properties)

                # Create ExtractedEntity
                entity = ExtractedEntity(
                    name=entity_name,
                    entity_type=entity_type,
                    confidence=confidence,
                    context=context,
                    metadata=metadata,
                )

                # Apply confidence threshold
                if entity.confidence >= self.config.confidence_threshold:
                    entities.append(entity)
                    logger.debug(
                        f"Extracted entity: {entity.name} ({entity.entity_type.value}) with confidence {entity.confidence}"
                    )

            except Exception as e:
                logger.warning(f"Failed to convert node to entity: {e}")
                logger.debug(f"Node attributes: {dir(node)}")
                continue

        logger.info(f"Successfully converted {len(entities)} nodes to entities")
        return entities

    async def _perform_custom_prompt_extraction(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
    ) -> ExtractionResult:
        """Perform entity extraction using custom prompts.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction
            domain: Domain for prompt selection
            custom_prompt: Additional custom instructions for extraction

        Returns:
            ExtractionResult containing extracted entities
        """
        # Set default domain
        extraction_domain = domain or PromptDomain.SOFTWARE_DEVELOPMENT

        # Generate custom prompt messages
        messages = self.prompt_manager.generate_entity_extraction_messages(
            content=text,
            entity_types=self.config.enabled_entity_types,
            domain=extraction_domain,
            custom_prompt=custom_prompt,
            extraction_hints=self.prompt_manager.get_extraction_hints_for_domain(
                extraction_domain
            ),
            reference_time=(reference_time or datetime.now(timezone.utc)).isoformat(),
        )

        # Use Graphiti's LLM client directly for extraction
        if not self.graphiti_manager.llm_client:
            raise RuntimeError("LLM client not available in GraphitiManager")

        # Call the LLM with custom prompts
        response = await self.graphiti_manager.llm_client.generate_response(messages)

        # Extract text content from response
        response_text = (
            response.get("content", "") if isinstance(response, dict) else str(response)
        )

        # Parse the response to extract entities
        entities = self._parse_llm_response_to_entities(response_text, text)

        # Create episode for tracking (optional)
        episode_id = None
        try:
            episode_id = await self.graphiti_manager.add_episode(
                name=f"Custom prompt extraction - {datetime.now(timezone.utc).isoformat()}",
                content=text,
                episode_type=EpisodeType.text,
                source_description=source_description
                or "Custom prompt entity extraction",
                reference_time=reference_time or datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(f"Failed to create episode for custom extraction: {e}")

        return ExtractionResult(
            entities=entities,
            source_text=text,
            episode_id=episode_id,
            metadata={
                "source_description": source_description,
                "reference_time": (
                    reference_time.isoformat() if reference_time else None
                ),
                "domain": extraction_domain.value,
                "custom_prompt": custom_prompt,
                "extraction_method": "custom_prompts",
            },
        )

    def _parse_llm_response_to_entities(
        self, response: str, source_text: str
    ) -> List[ExtractedEntity]:
        """Parse LLM response to extract entities.

        Args:
            response: LLM response text
            source_text: Original source text

        Returns:
            List of ExtractedEntity objects
        """
        entities = []

        try:
            # Try to parse as JSON first
            import json

            response_data = json.loads(response)

            if isinstance(response_data, dict) and "entities" in response_data:
                entity_list = response_data["entities"]
            elif isinstance(response_data, list):
                entity_list = response_data
            else:
                logger.warning("Unexpected response format from LLM")
                return entities

            for entity_data in entity_list:
                if isinstance(entity_data, dict):
                    name = entity_data.get("name", "")
                    entity_type_id = entity_data.get("entity_type_id", 0)
                    confidence = entity_data.get("confidence", 0.8)

                    # Map entity_type_id to EntityType
                    if entity_type_id < len(self.config.enabled_entity_types):
                        entity_type = self.config.enabled_entity_types[entity_type_id]
                    else:
                        entity_type = EntityType.CONCEPT  # Default fallback

                    # Apply confidence threshold
                    if confidence >= self.config.confidence_threshold and name:
                        entity = ExtractedEntity(
                            name=name,
                            entity_type=entity_type,
                            confidence=confidence,
                            context=entity_data.get("context", ""),
                            metadata={
                                "extraction_method": "custom_prompts",
                                "entity_type_id": entity_type_id,
                            },
                        )
                        entities.append(entity)

        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract entities from text
            logger.warning(
                "Failed to parse LLM response as JSON, attempting text parsing"
            )
            entities = self._extract_entities_from_text_response(response, source_text)

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")

        return entities

    def _extract_entities_from_text_response(
        self, response: str, source_text: str
    ) -> List[ExtractedEntity]:
        """Extract entities from text-based LLM response.

        Args:
            response: LLM response text
            source_text: Original source text

        Returns:
            List of ExtractedEntity objects
        """
        entities = []

        # Simple text parsing - look for entity patterns
        # This is a fallback method when JSON parsing fails
        lines = response.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for patterns like "Entity: Name (Type)"
            import re

            pattern = r"(?:Entity|Name):\s*([^(]+)\s*\(([^)]+)\)"
            match = re.search(pattern, line, re.IGNORECASE)

            if match:
                name = match.group(1).strip()
                type_str = match.group(2).strip().upper()

                # Try to map to EntityType
                try:
                    entity_type = EntityType(type_str)
                except ValueError:
                    entity_type = EntityType.CONCEPT

                if entity_type in self.config.enabled_entity_types:
                    entity = ExtractedEntity(
                        name=name,
                        entity_type=entity_type,
                        confidence=0.7,  # Default confidence for text parsing
                        context="",
                        metadata={
                            "extraction_method": "text_parsing_fallback",
                        },
                    )
                    entities.append(entity)

        return entities

    def _generate_cache_key(
        self, text: str, source_description: Optional[str] = None
    ) -> str:
        """Generate a cache key for the given text and source description.

        Args:
            text: Text content
            source_description: Optional source description

        Returns:
            Cache key string
        """
        content = f"{text}|{source_description or ''}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[ExtractionResult]:
        """Get extraction result from cache if not expired.

        Args:
            cache_key: Cache key

        Returns:
            Cached ExtractionResult or None if not found/expired
        """
        if cache_key not in self._cache:
            return None

        # Check if cache entry is expired
        timestamp = self._cache_timestamps.get(cache_key, 0)
        if time.time() - timestamp > self.config.cache_ttl:
            # Remove expired entry
            del self._cache[cache_key]
            del self._cache_timestamps[cache_key]
            return None

        return self._cache[cache_key]

    def _store_in_cache(self, cache_key: str, result: ExtractionResult) -> None:
        """Store extraction result in cache.

        Args:
            cache_key: Cache key
            result: ExtractionResult to cache
        """
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

        # Simple cache size management (keep last 1000 entries)
        if len(self._cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self._cache_timestamps.keys(), key=lambda k: self._cache_timestamps[k]
            )[
                :100
            ]  # Remove 100 oldest entries

            for key in oldest_keys:
                del self._cache[key]
                del self._cache_timestamps[key]

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Entity extraction cache cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics.

        Returns:
            Dictionary containing extraction statistics
        """
        cache_hit_rate = (
            self._stats["cache_hits"]
            / (self._stats["cache_hits"] + self._stats["cache_misses"])
            if (self._stats["cache_hits"] + self._stats["cache_misses"]) > 0
            else 0.0
        )

        return {
            **self._stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._cache),
            "config": {
                "batch_size": self.config.batch_size,
                "max_retries": self.config.max_retries,
                "cache_ttl": self.config.cache_ttl,
                "confidence_threshold": self.config.confidence_threshold,
                "enabled_entity_types": [
                    et.value for et in self.config.enabled_entity_types
                ],
            },
        }

    def reset_statistics(self) -> None:
        """Reset extraction statistics."""
        self._stats = {
            "total_extractions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failed_extractions": 0,
            "total_entities_extracted": 0,
        }
        logger.info("Entity extraction statistics reset")

    async def test_integration(self, test_text: Optional[str] = None) -> Dict[str, Any]:
        """Test the Graphiti integration with a sample text.

        Args:
            test_text: Optional test text to use for extraction

        Returns:
            Dictionary containing test results and statistics
        """
        if test_text is None:
            test_text = """
            Our microservice architecture includes a user authentication service 
            that connects to a PostgreSQL database. The API endpoints are documented 
            in our Confluence wiki, and the development team led by John Smith 
            maintains this critical component.
            """

        logger.info("Starting Graphiti integration test...")

        try:
            # Test the extraction process
            result = await self.extract_entities(
                text=test_text,
                source_description="Integration test",
                use_custom_prompts=False,  # Use default Graphiti extraction
            )

            test_results = {
                "success": True,
                "entities_extracted": len(result.entities),
                "episode_id": result.episode_id,
                "processing_time": result.processing_time,
                "errors": result.errors,
                "entity_details": [
                    {
                        "name": entity.name,
                        "type": entity.entity_type.value,
                        "confidence": entity.confidence,
                    }
                    for entity in result.entities
                ],
                "graphiti_manager_initialized": self.graphiti_manager.is_initialized,
                "extraction_statistics": self.get_statistics(),
            }

            logger.info(
                f"Integration test completed successfully. Extracted {len(result.entities)} entities."
            )
            return test_results

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "graphiti_manager_initialized": self.graphiti_manager.is_initialized,
                "extraction_statistics": self.get_statistics(),
            }
