"""
Comprehensive unit tests for EntityExtractor.

This test suite covers:
- Entity extraction from text
- Batch processing
- Caching mechanisms
- Retry logic
- Statistics tracking
- Configuration handling
- Error scenarios
- Relationship extraction
- Background processing
"""

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Any

from qdrant_loader.core.entity_extractor import (
    EntityExtractor,
    ExtractionConfig,
    ExtractionResult,
    ExtractedEntity,
    ExtractedRelationship,
)
from qdrant_loader.core.types import EntityType, RelationshipType, TemporalInfo
from qdrant_loader.core.prompts.entity_prompts import PromptDomain, EntityPromptManager
from qdrant_loader.core.managers.graphiti_manager import GraphitiManager


class TestEntityExtractor:
    """Test cases for EntityExtractor."""

    @pytest.fixture
    def mock_graphiti_manager(self):
        """Create a mock GraphitiManager."""
        manager = Mock(spec=GraphitiManager)
        manager.add_episode = AsyncMock()
        manager.get_entities_from_episode = AsyncMock()
        manager.search_entities = AsyncMock()
        manager.get_nodes = AsyncMock()
        manager.llm_client = Mock()
        manager.llm_client.generate_response = AsyncMock()
        return manager

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create a mock EntityPromptManager."""
        manager = Mock(spec=EntityPromptManager)
        manager.get_domain_prompt = Mock(return_value="Test prompt")
        return manager

    @pytest.fixture
    def extraction_config(self):
        """Create a test extraction configuration."""
        return ExtractionConfig(
            enabled_entity_types=[
                EntityType.PERSON,
                EntityType.ORGANIZATION,
                EntityType.CONCEPT,
            ],
            batch_size=5,
            max_retries=2,
            retry_delay=0.1,
            confidence_threshold=0.5,
            max_text_length=1000,
            enable_caching=True,
            cache_ttl=300,
            max_concurrent_extractions=3,
            enable_background_processing=False,  # Disable for testing
        )

    @pytest_asyncio.fixture
    async def entity_extractor(
        self, mock_graphiti_manager, extraction_config, mock_prompt_manager
    ):
        """Create an EntityExtractor instance for testing."""
        extractor = EntityExtractor(
            graphiti_manager=mock_graphiti_manager,
            config=extraction_config,
            prompt_manager=mock_prompt_manager,
        )
        yield extractor
        # Cleanup after test
        await extractor.shutdown()

    @pytest.fixture
    def sample_entities(self):
        """Sample extracted entities for testing."""
        return [
            ExtractedEntity(
                name="John Doe",
                entity_type=EntityType.PERSON,
                confidence=0.9,
                context="John Doe is a software engineer",
                metadata={"uuid": "person-1"},
            ),
            ExtractedEntity(
                name="TechCorp",
                entity_type=EntityType.ORGANIZATION,
                confidence=0.8,
                context="TechCorp is a technology company",
                metadata={"uuid": "org-1"},
            ),
        ]

    @pytest.fixture
    def sample_graphiti_nodes(self):
        """Sample Graphiti nodes for testing."""
        node1 = Mock()
        node1.name = "John Doe"
        node1.uuid = "person-1"
        node1.id = "neo4j-123"
        node1.created_at = datetime.now(timezone.utc)
        node1.updated_at = datetime.now(timezone.utc)
        node1.source = "test"
        node1.episode_id = "episode-123"
        node1.context = "Software engineer"
        node1.labels = ["Person"]
        node1.properties = {"created": "2023-01-01"}
        node1.confidence = 0.9  # Add confidence as float
        # Explicitly set entity_type and type to None to prevent Mock auto-creation
        node1.entity_type = None
        node1.type = None

        node2 = Mock()
        node2.name = "TechCorp"
        node2.uuid = "org-1"
        node2.id = "neo4j-456"
        node2.created_at = datetime.now(timezone.utc)
        node2.updated_at = datetime.now(timezone.utc)
        node2.source = "test"
        node2.episode_id = "episode-123"
        node2.context = "Technology company"
        node2.labels = ["Organization"]
        node2.properties = {"created": "2023-01-01"}
        node2.confidence = 0.8  # Add confidence as float
        # Explicitly set entity_type and type to None to prevent Mock auto-creation
        node2.entity_type = None
        node2.type = None

        return [node1, node2]

    # Configuration and Initialization Tests
    @pytest.mark.asyncio
    async def test_entity_extractor_initialization(
        self, mock_graphiti_manager, extraction_config
    ):
        """Test EntityExtractor initialization."""
        extractor = EntityExtractor(
            graphiti_manager=mock_graphiti_manager,
            config=extraction_config,
        )

        assert extractor.graphiti_manager == mock_graphiti_manager
        assert extractor.config == extraction_config
        assert extractor.prompt_manager is not None
        assert isinstance(extractor._stats, dict)
        assert extractor._stats["total_extractions"] == 0
        
        # Cleanup
        await extractor.shutdown()

    @pytest.mark.asyncio
    async def test_entity_extractor_initialization_with_defaults(self, mock_graphiti_manager):
        """Test EntityExtractor initialization with default config."""
        # Create config with background processing disabled for testing
        config = ExtractionConfig(enable_background_processing=False)

        extractor = EntityExtractor(
            graphiti_manager=mock_graphiti_manager, config=config
        )

        assert extractor.config is not None
        assert isinstance(extractor.config, ExtractionConfig)
        assert extractor.prompt_manager is not None
        
        # Cleanup
        await extractor.shutdown()

    # Basic Entity Extraction Tests
    @pytest.mark.asyncio
    async def test_extract_entities_success(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test successful entity extraction."""
        text = "John Doe works at TechCorp as a software engineer."

        # Mock Graphiti manager responses
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = (
            sample_graphiti_nodes
        )

        # Disable custom prompts to use the Graphiti episode path
        result = await entity_extractor.extract_entities(text, use_custom_prompts=False)

        assert isinstance(result, ExtractionResult)
        assert result.source_text == text
        assert len(result.entities) == 2
        assert result.episode_id == "episode-123"
        assert result.processing_time > 0

        # Check entities
        entity_names = [e.name for e in result.entities]
        assert "John Doe" in entity_names
        assert "TechCorp" in entity_names

    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, entity_extractor):
        """Test entity extraction with empty text."""
        result = await entity_extractor.extract_entities("")

        assert isinstance(result, ExtractionResult)
        assert result.source_text == ""
        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "Empty text provided" in result.errors[0]

    @pytest.mark.asyncio
    async def test_extract_entities_text_too_long(self, entity_extractor):
        """Test entity extraction with text exceeding max length."""
        long_text = "A" * 2000  # Exceeds default max_text_length of 1000

        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = []

        result = await entity_extractor.extract_entities(long_text)

        # Text should be truncated
        assert len(result.source_text) == 1000
        assert result.source_text == "A" * 1000

    @pytest.mark.asyncio
    async def test_extract_entities_with_source_description(self, entity_extractor):
        """Test entity extraction with source description."""
        text = "Test content"
        source_desc = "Test document"

        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = []

        result = await entity_extractor.extract_entities(
            text, source_description=source_desc
        )

        assert result.metadata["source_description"] == source_desc

    @pytest.mark.asyncio
    async def test_extract_entities_with_reference_time(self, entity_extractor):
        """Test entity extraction with reference time."""
        text = "Test content"
        ref_time = datetime.now(timezone.utc)

        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = []

        result = await entity_extractor.extract_entities(text, reference_time=ref_time)

        assert result.metadata["reference_time"] == ref_time.isoformat()

    # Caching Tests
    @pytest.mark.asyncio
    async def test_extract_entities_cache_hit(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test cache hit during entity extraction."""
        text = "Test content for caching"

        # First extraction
        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = (
            sample_graphiti_nodes
        )

        result1 = await entity_extractor.extract_entities(text)

        # Second extraction should hit cache
        result2 = await entity_extractor.extract_entities(text)

        assert result1.source_text == result2.source_text
        assert len(result1.entities) == len(result2.entities)

        # Check statistics
        stats = entity_extractor.get_statistics()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_extract_entities_cache_disabled(
        self, mock_graphiti_manager, sample_graphiti_nodes
    ):
        """Test entity extraction with caching disabled."""
        config = ExtractionConfig(enable_caching=False, enable_background_processing=False)
        extractor = EntityExtractor(mock_graphiti_manager, config)

        try:
            text = "Test content"
            mock_graphiti_manager.add_episode.return_value = "episode-123"
            mock_graphiti_manager.get_entities_from_episode.return_value = (
                sample_graphiti_nodes
            )

            await extractor.extract_entities(text)
            await extractor.extract_entities(text)

            # No cache hits since caching is disabled
            stats = extractor.get_statistics()
            assert stats["cache_hits"] == 0
            assert stats["cache_misses"] == 2
        finally:
            await extractor.shutdown()

    def test_cache_key_generation(self, entity_extractor):
        """Test cache key generation."""
        key1 = entity_extractor._generate_cache_key("text1", "source1")
        key2 = entity_extractor._generate_cache_key("text1", "source1")
        key3 = entity_extractor._generate_cache_key("text2", "source1")

        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys
        assert len(key1) == 32  # MD5 hash length

    def test_cache_operations(self, entity_extractor, sample_entities):
        """Test cache storage and retrieval operations."""
        result = ExtractionResult(entities=sample_entities, source_text="test")
        cache_key = "test_key"

        # Store in cache
        entity_extractor._store_in_cache(cache_key, result)

        # Retrieve from cache
        cached_result = entity_extractor._get_from_cache(cache_key)

        assert cached_result is not None
        assert cached_result.source_text == result.source_text
        assert len(cached_result.entities) == len(result.entities)

    def test_cache_expiration(self, entity_extractor, sample_entities):
        """Test cache expiration."""
        result = ExtractionResult(entities=sample_entities, source_text="test")
        cache_key = "test_key"

        # Store in cache
        entity_extractor._store_in_cache(cache_key, result)

        # Manually expire the cache entry
        import time

        entity_extractor._cache_timestamps[cache_key] = (
            time.time() - 400
        )  # Older than TTL

        # Should return None for expired entry
        cached_result = entity_extractor._get_from_cache(cache_key)
        assert cached_result is None

    def test_clear_cache(self, entity_extractor, sample_entities):
        """Test cache clearing."""
        result = ExtractionResult(entities=sample_entities, source_text="test")
        entity_extractor._store_in_cache("key1", result)
        entity_extractor._store_in_cache("key2", result)

        assert len(entity_extractor._cache) == 2

        entity_extractor.clear_cache()

        assert len(entity_extractor._cache) == 0
        assert len(entity_extractor._cache_timestamps) == 0

    # Batch Processing Tests
    @pytest.mark.asyncio
    async def test_extract_entities_batch_success(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test successful batch entity extraction."""
        texts = ["Text 1", "Text 2"]

        # Mock Graphiti manager responses
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = (
            sample_graphiti_nodes
        )

        # Mock the extract_entities method to disable custom prompts
        original_extract_entities = entity_extractor.extract_entities

        async def mock_extract_entities(
            text,
            source_description=None,
            reference_time=None,
            domain=None,
            custom_prompt="",
            use_custom_prompts=True,
        ):
            return await original_extract_entities(
                text,
                source_description,
                reference_time,
                domain,
                custom_prompt,
                use_custom_prompts=False,
            )

        entity_extractor.extract_entities = mock_extract_entities

        results = await entity_extractor.extract_entities_batch(texts)

        assert len(results) == 2
        for result in results:
            assert isinstance(result, ExtractionResult)
            assert len(result.entities) == 2
            assert result.episode_id == "episode-123"

    @pytest.mark.asyncio
    async def test_extract_entities_batch_empty(self, entity_extractor):
        """Test batch extraction with empty list."""
        results = await entity_extractor.extract_entities_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_extract_entities_batch_with_descriptions(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test batch extraction with source descriptions."""
        texts = ["Text 1", "Text 2"]
        descriptions = ["Desc 1", "Desc 2"]

        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = (
            sample_graphiti_nodes
        )

        results = await entity_extractor.extract_entities_batch(texts, descriptions)

        assert len(results) == 2
        assert results[0].metadata.get("source_description") == "Desc 1"
        assert results[1].metadata.get("source_description") == "Desc 2"

    # Retry Logic Tests
    @pytest.mark.asyncio
    async def test_extract_with_retry_success_first_attempt(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test retry mechanism with success on first attempt."""
        text = "Test content"

        # Mock successful extraction
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = (
            sample_graphiti_nodes
        )

        result = await entity_extractor._extract_with_retry(
            text, use_custom_prompts=False
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 2
        assert result.episode_id == "episode-123"

    @pytest.mark.asyncio
    async def test_extract_with_retry_failure_then_success(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test retry mechanism with failure then success."""
        text = "Test content"

        # Mock first failure, then success
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.side_effect = [
            Exception("First attempt fails"),
            "episode-123",
        ]
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = (
            sample_graphiti_nodes
        )

        result = await entity_extractor._extract_with_retry(
            text, use_custom_prompts=False
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 2

    @pytest.mark.asyncio
    async def test_extract_with_retry_all_attempts_fail(self, entity_extractor):
        """Test retry mechanism when all attempts fail."""
        text = "Test content"

        # Mock all attempts failing
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.side_effect = Exception(
            "Always fails"
        )

        result = await entity_extractor._extract_with_retry(
            text, use_custom_prompts=False
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "Always fails" in result.errors[0]

    # Node Conversion Tests
    def test_convert_nodes_to_entities_success(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test converting Graphiti nodes to entities."""
        source_text = "Test text"

        entities = entity_extractor._convert_nodes_to_entities(
            sample_graphiti_nodes, source_text
        )

        assert len(entities) == 2
        assert entities[0].name == "John Doe"
        assert entities[0].entity_type == EntityType.PERSON
        assert entities[1].name == "TechCorp"
        assert entities[1].entity_type == EntityType.ORGANIZATION

    def test_convert_nodes_to_entities_with_neo4j_node(self, entity_extractor):
        """Test converting Neo4j nodes to entities."""
        # Create a mock Neo4j node
        mock_node = Mock()
        mock_node.name = "Test Entity"
        mock_node.uuid = Mock()
        mock_node.id = Mock()
        mock_node.created_at = Mock()
        mock_node.updated_at = Mock()
        mock_node.source = Mock()
        mock_node.episode_id = Mock()
        mock_node.context = Mock()
        mock_node.confidence = 0.9  # Add confidence score
        # Set neo4j_element_id to simulate Neo4j node
        mock_node.element_id = "neo4j-123"  # This is what the code checks for
        mock_node.neo4j_labels = ["Person"]
        mock_node.labels = ["Person"]  # Add labels for iteration
        mock_node.properties = {"created": "2023-01-01"}
        # Set entity_type and type to None explicitly
        mock_node.entity_type = None
        mock_node.type = None

        entities = entity_extractor._convert_nodes_to_entities([mock_node], "test")

        assert len(entities) == 1
        assert entities[0].entity_type == EntityType.PERSON
        assert entities[0].metadata["neo4j_element_id"] == "neo4j-123"

    def test_convert_nodes_to_entities_confidence_filtering(self, entity_extractor):
        """Test confidence filtering in node conversion."""
        # Create low confidence node
        low_conf_node = Mock()
        low_conf_node.name = "Low Confidence"
        low_conf_node.confidence = 0.3  # Below threshold
        low_conf_node.uuid = Mock()
        low_conf_node.id = Mock()
        low_conf_node.created_at = Mock()
        low_conf_node.updated_at = Mock()
        low_conf_node.source = Mock()
        low_conf_node.episode_id = Mock()
        low_conf_node.context = Mock()
        low_conf_node.labels = ["Person"]
        low_conf_node.properties = {}

        entities = entity_extractor._convert_nodes_to_entities([low_conf_node], "test")

        # Should be filtered out due to low confidence
        assert len(entities) == 0

    def test_convert_nodes_to_entities_disabled_types(self, entity_extractor):
        """Test filtering of disabled entity types."""
        # Create node with disabled entity type
        node = Mock()
        node.name = "Test Location"
        node.entity_type = "LOCATION"  # Not in enabled types
        node.confidence = 0.9

        entities = entity_extractor._convert_nodes_to_entities([node], "test")

        # Should be filtered out
        assert len(entities) == 0

    # Search Terms Extraction Tests
    def test_extract_search_terms(self, entity_extractor):
        """Test search term extraction."""
        text = "John Doe works at TechCorp"

        search_terms = entity_extractor._extract_search_terms(text)

        # Should extract meaningful terms and filter out common words
        assert "john" in search_terms.lower()
        assert "techcorp" in search_terms.lower()
        # "works" should be filtered out as it's a common word
        assert "works" not in search_terms.lower()

    def test_extract_search_terms_short_text(self, entity_extractor):
        """Test search terms extraction from short text."""
        text = "AI"

        terms = entity_extractor._extract_search_terms(text)

        # Should return original text for very short input
        assert terms == "AI"

    def test_extract_search_terms_no_meaningful_words(self, entity_extractor):
        """Test search terms extraction with no meaningful words."""
        text = "the and for are but not you all can"

        terms = entity_extractor._extract_search_terms(text)

        # Should return truncated original text as fallback
        assert len(terms) <= 50
        assert terms == text[:50]

    # LLM Response Parsing Tests
    def test_parse_llm_response_json_format(self, entity_extractor):
        """Test parsing LLM response in JSON format."""
        response = json.dumps(
            {
                "entities": [
                    {
                        "name": "John Doe",
                        "entity_type_id": 0,  # Maps to PERSON (first in enabled types)
                        "confidence": 0.9,
                        "context": "Software engineer",
                    },
                    {
                        "name": "TechCorp",
                        "entity_type_id": 1,  # Maps to ORGANIZATION
                        "confidence": 0.8,
                        "context": "Technology company",
                    },
                ]
            }
        )

        entities = entity_extractor._parse_llm_response_to_entities(
            response, "source text"
        )

        assert len(entities) == 2
        assert entities[0].name == "John Doe"
        assert entities[0].entity_type == EntityType.PERSON
        assert entities[1].name == "TechCorp"
        assert entities[1].entity_type == EntityType.ORGANIZATION

    def test_parse_llm_response_list_format(self, entity_extractor):
        """Test parsing LLM response as direct list."""
        response = json.dumps(
            [{"name": "Test Entity", "entity_type_id": 0, "confidence": 0.9}]
        )

        entities = entity_extractor._parse_llm_response_to_entities(
            response, "source text"
        )

        assert len(entities) == 1
        assert entities[0].name == "Test Entity"

    def test_parse_llm_response_confidence_filtering(self, entity_extractor):
        """Test confidence filtering during LLM response parsing."""
        response = json.dumps(
            {
                "entities": [
                    {"name": "High Conf", "entity_type_id": 0, "confidence": 0.9},
                    {
                        "name": "Low Conf",
                        "entity_type_id": 0,
                        "confidence": 0.3,  # Below threshold
                    },
                ]
            }
        )

        entities = entity_extractor._parse_llm_response_to_entities(
            response, "source text"
        )

        # Only high confidence entity should be included
        assert len(entities) == 1
        assert entities[0].name == "High Conf"

    def test_parse_llm_response_text_fallback(self, entity_extractor):
        """Test parsing LLM response with text fallback."""
        response = "John Doe is a person who works at TechCorp."
        source_text = "Test text"

        entities = entity_extractor._parse_llm_response_to_entities(
            response, source_text
        )

        assert len(entities) >= 1
        # Find the John Doe entity
        john_entity = next((e for e in entities if e.name == "John Doe"), None)
        assert john_entity is not None
        assert john_entity.entity_type == EntityType.PERSON

    def test_extract_entities_from_text_response(self, entity_extractor):
        """Test entity extraction from text response."""
        response = """
        Entity: John Doe (PERSON)
        Name: TechCorp (ORGANIZATION)
        Entity: Python (CONCEPT)
        """

        entities = entity_extractor._extract_entities_from_text_response(
            response, "source"
        )

        assert len(entities) == 3
        entity_names = [e.name for e in entities]
        assert "John Doe" in entity_names
        assert "TechCorp" in entity_names
        assert "Python" in entity_names

    # Statistics Tests
    def test_get_statistics(self, entity_extractor):
        """Test statistics retrieval."""
        stats = entity_extractor.get_statistics()

        assert isinstance(stats, dict)
        assert "total_extractions" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "failed_extractions" in stats
        assert "cache_hit_rate" in stats
        assert "cache_size" in stats
        assert "config" in stats

    def test_statistics_cache_hit_rate_calculation(self, entity_extractor):
        """Test cache hit rate calculation in statistics."""
        # Simulate some cache operations
        entity_extractor._stats["cache_hits"] = 3
        entity_extractor._stats["cache_misses"] = 7

        stats = entity_extractor.get_statistics()

        assert stats["cache_hit_rate"] == 0.3  # 3/(3+7)

    def test_statistics_cache_hit_rate_no_operations(self, entity_extractor):
        """Test cache hit rate when no cache operations occurred."""
        stats = entity_extractor.get_statistics()

        assert stats["cache_hit_rate"] == 0.0

    def test_reset_statistics(self, entity_extractor):
        """Test statistics reset."""
        # Set some statistics
        entity_extractor._stats["total_extractions"] = 5
        entity_extractor._stats["cache_hits"] = 2

        entity_extractor.reset_statistics()

        stats = entity_extractor.get_statistics()
        assert stats["total_extractions"] == 0
        assert stats["cache_hits"] == 0

    # Relationship Extraction Tests
    @pytest.mark.asyncio
    async def test_extract_relationships_success(
        self, entity_extractor, sample_entities
    ):
        """Test relationship extraction."""
        text = "John Doe works at TechCorp"

        # Mock LLM response for relationships
        mock_response = json.dumps(
            {
                "relationships": [
                    {
                        "source": "John Doe",
                        "target": "TechCorp",
                        "type": "belongs_to",  # Use valid RelationshipType enum value
                        "confidence": 0.9,
                        "evidence": "John Doe works at TechCorp",
                    }
                ]
            }
        )
        entity_extractor.graphiti_manager.llm_client.generate_response.return_value = (
            mock_response
        )

        relationships = await entity_extractor.extract_relationships(
            sample_entities, text
        )

        assert len(relationships) == 1
        assert relationships[0].source_entity == "John Doe"
        assert relationships[0].target_entity == "TechCorp"

    @pytest.mark.asyncio
    async def test_extract_relationships_insufficient_entities(self, entity_extractor):
        """Test relationship extraction with insufficient entities."""
        single_entity = [
            ExtractedEntity(
                name="John Doe", entity_type=EntityType.PERSON, confidence=0.9
            )
        ]

        relationships = await entity_extractor.extract_relationships(
            single_entity, "text"
        )

        assert len(relationships) == 0

    @pytest.mark.asyncio
    async def test_extract_relationships_no_llm_client(
        self, entity_extractor, sample_entities
    ):
        """Test relationship extraction when no LLM client is available."""
        entity_extractor.graphiti_manager.llm_client = None

        relationships = await entity_extractor.extract_relationships(
            sample_entities, "text"
        )

        assert len(relationships) == 0

    @pytest.mark.asyncio
    async def test_extract_relationships_llm_error(
        self, entity_extractor, sample_entities
    ):
        """Test relationship extraction when LLM call fails."""
        entity_extractor.graphiti_manager.llm_client.generate_response.side_effect = (
            Exception("LLM error")
        )

        relationships = await entity_extractor.extract_relationships(
            sample_entities, "text"
        )

        assert len(relationships) == 0

    def test_create_relationship_prompt(self, entity_extractor, sample_entities):
        """Test relationship prompt creation."""
        text = "John Doe works at TechCorp"

        prompt = entity_extractor._create_relationship_prompt(sample_entities, text)

        assert "John Doe" in prompt
        assert "TechCorp" in prompt
        assert text in prompt

    def test_get_relationship_description(self, entity_extractor):
        """Test relationship type descriptions."""
        desc = entity_extractor._get_relationship_description(RelationshipType.CONTAINS)
        assert isinstance(desc, str)
        assert len(desc) > 0

        # Test unknown relationship type
        desc_unknown = entity_extractor._get_relationship_description(
            RelationshipType.RELATED_TO
        )
        assert isinstance(desc_unknown, str)

    def test_parse_relationship_response_json(self, entity_extractor, sample_entities):
        """Test parsing relationship response in JSON format."""
        response = json.dumps(
            {
                "relationships": [
                    {
                        "source": "John Doe",
                        "target": "TechCorp",
                        "type": "belongs_to",
                        "confidence": 0.9,
                        "evidence": "works at",
                    }
                ]
            }
        )

        relationships = entity_extractor._parse_relationship_response(
            response, sample_entities, "source text"
        )

        assert len(relationships) == 1
        assert relationships[0].source_entity == "John Doe"
        assert relationships[0].target_entity == "TechCorp"

    def test_parse_relationship_response_text_fallback(
        self, entity_extractor, sample_entities
    ):
        """Test parsing relationship response with text fallback."""
        response = "John Doe -> TechCorp (belongs_to)"

        relationships = entity_extractor._parse_relationship_response(
            response, sample_entities, "source text"
        )

        assert len(relationships) == 1
        assert relationships[0].source_entity == "John Doe"
        assert relationships[0].target_entity == "TechCorp"

    def test_parse_relationship_response_invalid_entities(
        self, entity_extractor, sample_entities
    ):
        """Test parsing relationships with invalid entity references."""
        response = json.dumps(
            {
                "relationships": [
                    {
                        "source": "Unknown Entity",  # Not in sample_entities
                        "target": "TechCorp",
                        "type": "belongs_to",
                        "confidence": 0.9,
                    }
                ]
            }
        )

        relationships = entity_extractor._parse_relationship_response(
            response, sample_entities, "source text"
        )

        # Should be filtered out due to invalid entity reference
        assert len(relationships) == 0

    def test_extract_relationships_from_text_response(
        self, entity_extractor, sample_entities
    ):
        """Test extracting relationships from text response."""
        response = """
        John Doe -> TechCorp (belongs_to)
        TechCorp -> John Doe (employs)
        """

        relationships = entity_extractor._extract_relationships_from_text_response(
            response, sample_entities, "source text"
        )

        assert (
            len(relationships) >= 1
        )  # At least one valid relationship should be found

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_extract_entities_graphiti_error(self, entity_extractor):
        """Test handling of Graphiti errors."""
        text = "Test content"

        # Mock Graphiti error
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.side_effect = Exception(
            "Graphiti error"
        )

        result = await entity_extractor.extract_entities(text, use_custom_prompts=False)

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "Graphiti error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_perform_extraction_fallback_search(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test extraction with fallback to search."""
        text = "Test content"

        # Mock episode creation failure but search success
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.side_effect = Exception(
            "Episode failed"
        )
        entity_extractor.graphiti_manager.search_entities.return_value = (
            sample_graphiti_nodes
        )

        result = await entity_extractor._perform_extraction(
            text, use_custom_prompts=False
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 2
        # When episode creation fails, episode_id should be None
        assert result.episode_id is None
        # But entities should still be extracted via fallback search
        entity_names = [e.name for e in result.entities]
        assert "John Doe" in entity_names
        assert "TechCorp" in entity_names

    # Configuration Edge Cases
    def test_extraction_config_validation(self):
        """Test extraction configuration validation."""
        config = ExtractionConfig(
            enabled_entity_types=[EntityType.PERSON],
            confidence_threshold=0.7,
            max_retries=3,
        )

        assert EntityType.PERSON in config.enabled_entity_types
        assert config.confidence_threshold == 0.7
        assert config.max_retries == 3

    # Background Processing Tests (when enabled)
    def test_background_processing_disabled(self, entity_extractor):
        """Test that background processing is disabled in test config."""
        assert not entity_extractor.config.enable_background_processing
        assert len(entity_extractor._background_workers) == 0

    @pytest.mark.asyncio
    async def test_cleanup_resources(self, entity_extractor):
        """Test resource cleanup."""
        await entity_extractor.cleanup()
        # Just verify it doesn't raise an exception
        assert True

    # Integration-style Tests
    @pytest.mark.asyncio
    async def test_full_extraction_workflow(
        self, entity_extractor, sample_graphiti_nodes
    ):
        """Test complete extraction workflow."""
        text = "John Doe, a software engineer at TechCorp, is working on AI projects."

        # Mock all necessary responses
        entity_extractor.graphiti_manager.is_initialized = True
        entity_extractor.graphiti_manager.add_episode.return_value = "episode-123"
        entity_extractor.graphiti_manager.get_entities_from_episode.return_value = (
            sample_graphiti_nodes
        )

        result = await entity_extractor.extract_entities(text, use_custom_prompts=False)

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 2
        assert result.episode_id == "episode-123"
        assert result.processing_time > 0

        # Verify entity types and names
        entity_names = [e.name for e in result.entities]
        assert "John Doe" in entity_names
        assert "TechCorp" in entity_names
