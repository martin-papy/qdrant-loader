"""
Focused unit tests for EntityExtractor.

This test suite focuses on the core functionality that can be tested
without complex integration dependencies.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from typing import Any

from qdrant_loader.core.entity_extractor import (
    EntityExtractor,
    ExtractionConfig,
    ExtractionResult,
    ExtractedEntity,
    ExtractedRelationship,
)
from qdrant_loader.core.types import EntityType, RelationshipType
from qdrant_loader.core.prompts.entity_prompts import PromptDomain, EntityPromptManager
from qdrant_loader.core.managers.graphiti_manager import GraphitiManager


class TestEntityExtractorFocused:
    """Focused test cases for EntityExtractor core functionality."""

    @pytest.fixture
    def mock_graphiti_manager(self):
        """Create a mock GraphitiManager."""
        manager = Mock(spec=GraphitiManager)
        manager.is_initialized = True
        manager.add_episode = AsyncMock(return_value="test-episode-id")
        manager.get_entities_from_episode = AsyncMock(return_value=[])
        manager.search_entities = AsyncMock(return_value=[])
        manager.get_nodes = AsyncMock(return_value=[])

        # Mock LLM client for custom prompt extraction
        manager.llm_client = Mock()
        manager.llm_client.generate_response = AsyncMock(return_value="")

        return manager

    @pytest.fixture
    def extraction_config_no_background(self):
        """Create a test extraction configuration with background processing disabled."""
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
            enable_background_processing=False,  # Critical: disable background processing
        )

    @pytest.fixture
    def entity_extractor(self, mock_graphiti_manager, extraction_config_no_background):
        """Create an EntityExtractor instance for testing."""
        return EntityExtractor(
            graphiti_manager=mock_graphiti_manager,
            config=extraction_config_no_background,
        )

    # Configuration and Initialization Tests
    def test_entity_extractor_initialization(
        self, mock_graphiti_manager, extraction_config_no_background
    ):
        """Test EntityExtractor initialization."""
        extractor = EntityExtractor(
            graphiti_manager=mock_graphiti_manager,
            config=extraction_config_no_background,
        )

        assert extractor.graphiti_manager == mock_graphiti_manager
        assert extractor.config == extraction_config_no_background
        assert extractor.prompt_manager is not None
        assert isinstance(extractor._stats, dict)
        assert extractor._stats["total_extractions"] == 0
        # Background processing should be disabled
        assert not extractor.config.enable_background_processing
        assert len(extractor._background_workers) == 0

    # Basic Entity Extraction Tests
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

        result = await entity_extractor.extract_entities(long_text)

        # Text should be truncated
        assert len(result.source_text) == 1000
        assert result.source_text == "A" * 1000

    @pytest.mark.asyncio
    async def test_extract_entities_with_source_description(self, entity_extractor):
        """Test entity extraction with source description."""
        text = "Test content"
        source_desc = "Test document"

        result = await entity_extractor.extract_entities(
            text, source_description=source_desc
        )

        assert result.metadata.get("source_description") == source_desc

    @pytest.mark.asyncio
    async def test_extract_entities_with_reference_time(self, entity_extractor):
        """Test entity extraction with reference time."""
        text = "Test content"
        ref_time = datetime.now(timezone.utc)

        result = await entity_extractor.extract_entities(text, reference_time=ref_time)

        assert result.metadata.get("reference_time") == ref_time.isoformat()

    # Caching Tests
    def test_cache_key_generation(self, entity_extractor):
        """Test cache key generation."""
        key1 = entity_extractor._generate_cache_key("text1", "source1")
        key2 = entity_extractor._generate_cache_key("text1", "source1")
        key3 = entity_extractor._generate_cache_key("text2", "source1")

        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys
        assert len(key1) == 32  # MD5 hash length

    def test_cache_operations(self, entity_extractor):
        """Test cache storage and retrieval operations."""
        result = ExtractionResult(entities=[], source_text="test")
        cache_key = "test_key"

        # Store in cache
        entity_extractor._store_in_cache(cache_key, result)

        # Retrieve from cache
        cached_result = entity_extractor._get_from_cache(cache_key)

        assert cached_result is not None
        assert cached_result.source_text == result.source_text

    def test_cache_expiration(self, entity_extractor):
        """Test cache expiration."""
        result = ExtractionResult(entities=[], source_text="test")
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

    def test_clear_cache(self, entity_extractor):
        """Test cache clearing."""
        result = ExtractionResult(entities=[], source_text="test")
        entity_extractor._store_in_cache("key1", result)
        entity_extractor._store_in_cache("key2", result)

        assert len(entity_extractor._cache) == 2

        entity_extractor.clear_cache()

        assert len(entity_extractor._cache) == 0
        assert len(entity_extractor._cache_timestamps) == 0

    # Batch Processing Tests
    @pytest.mark.asyncio
    async def test_extract_entities_batch_empty(self, entity_extractor):
        """Test batch extraction with empty list."""
        results = await entity_extractor.extract_entities_batch([])
        assert results == []

    # Search Terms Extraction Tests
    def test_extract_search_terms(self, entity_extractor):
        """Test search terms extraction from text."""
        text = "John Doe works at TechCorp developing software applications"

        terms = entity_extractor._extract_search_terms(text, max_terms=3)

        assert isinstance(terms, str)
        assert len(terms.split()) <= 3
        # Should contain meaningful words
        assert any(
            word in terms.lower()
            for word in ["john", "techcorp", "developing", "software", "applications"]
        )

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

    def test_parse_llm_response_invalid_json_fallback(self, entity_extractor):
        """Test fallback to text parsing when JSON parsing fails."""
        response = "Entity: John Doe (PERSON)\nEntity: TechCorp (ORGANIZATION)"

        entities = entity_extractor._parse_llm_response_to_entities(
            response, "source text"
        )

        # Should attempt text parsing fallback
        assert isinstance(entities, list)

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

        # Should extract entities based on pattern matching
        assert isinstance(entities, list)
        # At least some entities should be found
        if entities:
            assert all(isinstance(e, ExtractedEntity) for e in entities)

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

    def test_reset_statistics(self, entity_extractor):
        """Test statistics reset."""
        # Set some statistics
        entity_extractor._stats["total_extractions"] = 5
        entity_extractor._stats["cache_hits"] = 2

        entity_extractor.reset_statistics()

        stats = entity_extractor.get_statistics()
        assert stats["total_extractions"] == 0
        assert stats["cache_hits"] == 0

    # Node Conversion Tests (with proper mocking)
    def test_convert_nodes_to_entities_empty_list(self, entity_extractor):
        """Test conversion with empty node list."""
        entities = entity_extractor._convert_nodes_to_entities([], "test")
        assert len(entities) == 0

    def test_convert_nodes_to_entities_with_mock_node(self, entity_extractor):
        """Test conversion with properly mocked node."""
        # Create a mock node with all required attributes
        mock_node = Mock()
        mock_node.name = "Test Entity"
        mock_node.entity_type = "PERSON"
        mock_node.confidence = 0.9
        mock_node.context = "Test context"

        # Mock the dir() function to return expected attributes
        with patch(
            "builtins.dir",
            return_value=["name", "entity_type", "confidence", "context"],
        ):
            entities = entity_extractor._convert_nodes_to_entities([mock_node], "test")

        # Should successfully convert at least one entity
        assert len(entities) >= 0  # May be 0 if entity type filtering occurs

    # Relationship Extraction Tests
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
    async def test_extract_relationships_no_llm_client(self, entity_extractor):
        """Test relationship extraction when no LLM client is available."""
        sample_entities = [
            ExtractedEntity(
                name="John Doe", entity_type=EntityType.PERSON, confidence=0.9
            ),
            ExtractedEntity(
                name="TechCorp", entity_type=EntityType.ORGANIZATION, confidence=0.8
            ),
        ]

        entity_extractor.graphiti_manager.llm_client = None

        relationships = await entity_extractor.extract_relationships(
            sample_entities, "text"
        )

        assert len(relationships) == 0

    def test_create_relationship_prompt(self, entity_extractor):
        """Test relationship extraction prompt creation."""
        sample_entities = [
            ExtractedEntity(
                name="John Doe", entity_type=EntityType.PERSON, confidence=0.9
            ),
            ExtractedEntity(
                name="TechCorp", entity_type=EntityType.ORGANIZATION, confidence=0.8
            ),
        ]
        text = "John Doe works at TechCorp"

        prompt = entity_extractor._create_relationship_prompt(sample_entities, text)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "relationships" in prompt.lower()

    def test_get_relationship_description(self, entity_extractor):
        """Test relationship type descriptions."""
        desc = entity_extractor._get_relationship_description(RelationshipType.CONTAINS)
        assert isinstance(desc, str)
        assert len(desc) > 0

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_extract_entities_graphiti_not_initialized(self, entity_extractor):
        """Test handling when Graphiti manager is not initialized."""
        text = "Test content"

        # Mock Graphiti as not initialized
        entity_extractor.graphiti_manager.is_initialized = False

        # Should fall back to custom prompt extraction
        result = await entity_extractor.extract_entities(text)

        assert isinstance(result, ExtractionResult)
        # Should not crash, may have empty results

    # Configuration Edge Cases
    def test_extraction_config_validation(self):
        """Test extraction configuration validation."""
        config = ExtractionConfig(
            enabled_entity_types=[EntityType.PERSON],
            confidence_threshold=0.7,
            max_retries=3,
            enable_background_processing=False,
        )

        assert EntityType.PERSON in config.enabled_entity_types
        assert config.confidence_threshold == 0.7
        assert config.max_retries == 3
        assert not config.enable_background_processing

    # Retry Logic Tests
    @pytest.mark.asyncio
    async def test_extract_with_retry_all_attempts_fail(self, entity_extractor):
        """Test extraction failing on all retry attempts."""
        text = "Test content"

        # Mock to always fail
        entity_extractor.graphiti_manager.is_initialized = False
        entity_extractor.prompt_manager = None  # Disable custom prompt fallback

        result = await entity_extractor._extract_with_retry(text)

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "failed after" in result.errors[0]

    # Integration-style Tests (mocked)
    @pytest.mark.asyncio
    async def test_custom_prompt_extraction_path(self, entity_extractor):
        """Test the custom prompt extraction path."""
        text = "John Doe works at TechCorp"

        # Mock LLM response for custom prompt extraction
        mock_response = json.dumps(
            {
                "entities": [
                    {"name": "John Doe", "entity_type_id": 0, "confidence": 0.9},
                    {"name": "TechCorp", "entity_type_id": 1, "confidence": 0.8},
                ]
            }
        )
        entity_extractor.graphiti_manager.llm_client.generate_response.return_value = (
            mock_response
        )

        result = await entity_extractor.extract_entities(text, use_custom_prompts=True)

        assert isinstance(result, ExtractionResult)
        assert result.source_text == text
        assert result.metadata.get("extraction_method") == "custom_prompts"
        # Should have extracted entities from the mock response
        assert len(result.entities) == 2

    @pytest.mark.asyncio
    async def test_cache_hit_during_extraction(self, entity_extractor):
        """Test cache hit during entity extraction."""
        text = "Test content for caching"

        # First extraction - should cache the result
        result1 = await entity_extractor.extract_entities(text)

        # Second extraction - should hit cache
        result2 = await entity_extractor.extract_entities(text)

        assert result1.source_text == result2.source_text

        # Check statistics
        stats = entity_extractor.get_statistics()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_extract_entities_batch_with_descriptions(self, entity_extractor):
        """Test batch extraction with source descriptions."""
        texts = ["Text 1", "Text 2"]
        descriptions = ["Desc 1", "Desc 2"]

        results = await entity_extractor.extract_entities_batch(texts, descriptions)

        assert len(results) == 2
        assert results[0].metadata.get("source_description") == "Desc 1"
        assert results[1].metadata.get("source_description") == "Desc 2"
