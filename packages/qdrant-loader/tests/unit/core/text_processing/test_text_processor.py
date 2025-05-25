"""Unit tests for the text processor."""

import pytest
from qdrant_loader.core.text_processing.text_processor import TextProcessor


@pytest.fixture
def text_processor(test_settings):
    """Create a TextProcessor instance for testing.

    Args:
        test_settings: Test settings fixture from conftest.py
    """
    return TextProcessor(test_settings)


def test_process_text(text_processor):
    """Test the process_text method."""
    text = "Apple Inc. is headquartered in Cupertino, California. The company was founded by Steve Jobs."

    result = text_processor.process_text(text)

    # Check that all expected keys are present
    assert "tokens" in result
    assert "entities" in result
    assert "pos_tags" in result
    assert "chunks" in result

    # Check that entities are extracted correctly
    entities = result["entities"]
    assert any("Apple Inc." in entity[0] for entity in entities)
    assert any("Cupertino" in entity[0] for entity in entities)
    assert any("California" in entity[0] for entity in entities)
    assert any("Steve Jobs" in entity[0] for entity in entities)


def test_get_entities(text_processor):
    """Test the get_entities method."""
    text = "Microsoft Corporation is based in Redmond, Washington."

    entities = text_processor.get_entities(text)

    # Check that entities are extracted correctly
    assert any("Microsoft Corporation" in entity[0] for entity in entities)
    assert any("Redmond" in entity[0] for entity in entities)
    assert any("Washington" in entity[0] for entity in entities)


def test_get_pos_tags(text_processor):
    """Test the get_pos_tags method."""
    text = "The quick brown fox jumps over the lazy dog."

    pos_tags = text_processor.get_pos_tags(text)

    # Check that we get POS tags for each word
    assert len(pos_tags) > 0
    assert all(isinstance(tag, tuple) for tag in pos_tags)
    assert all(len(tag) == 2 for tag in pos_tags)


def test_split_into_chunks(text_processor, test_settings):
    """Test the split_into_chunks method with default settings."""
    text = "This is a test. " * 50  # Create a longer text

    chunks = text_processor.split_into_chunks(text)

    # Check that text is split into chunks
    assert len(chunks) > 1
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert all(len(chunk) > 0 for chunk in chunks)

    # Verify chunks respect the configured size
    max_chunk_size = test_settings.global_config.chunking.chunk_size
    assert all(len(chunk) <= max_chunk_size for chunk in chunks)


def test_split_into_chunks_with_custom_size(text_processor):
    """Test the split_into_chunks method with custom chunk size."""
    text = "This is a test. " * 50
    custom_size = 50

    chunks = text_processor.split_into_chunks(text, chunk_size=custom_size)

    # Check that chunks are approximately the right size
    assert len(chunks) > 1
    assert all(
        len(chunk) <= custom_size * 1.5 for chunk in chunks
    )  # Allow some flexibility
