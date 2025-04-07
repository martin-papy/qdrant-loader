import pytest
from datetime import datetime
from qdrant_loader.core.document import Document

def test_document_creation():
    """Test basic document creation."""
    doc = Document(
        content="Test content",
        source="test_source",
        source_type="test_type"
    )
    
    assert doc.content == "Test content"
    assert doc.source == "test_source"
    assert doc.source_type == "test_type"
    assert doc.metadata is not None
    assert doc.metadata['source'] == "test_source"
    assert doc.metadata['source_type'] == "test_type"

def test_document_with_optional_fields():
    """Test document creation with optional fields."""
    now = datetime.now()
    doc = Document(
        content="Test content",
        source="test_source",
        source_type="test_type",
        url="http://example.com",
        last_updated=now,
        project="test_project",
        author="test_author"
    )
    
    assert doc.url == "http://example.com"
    assert doc.last_updated == now
    assert doc.project == "test_project"
    assert doc.author == "test_author"
    assert doc.metadata['url'] == "http://example.com"
    assert doc.metadata['last_updated'] == now.isoformat()
    assert doc.metadata['project'] == "test_project"
    assert doc.metadata['author'] == "test_author"

def test_document_with_custom_metadata():
    """Test document creation with custom metadata."""
    custom_metadata = {
        'custom_field': 'custom_value',
        'source': 'overridden_source'  # This should be overridden
    }
    
    doc = Document(
        content="Test content",
        source="test_source",
        source_type="test_type",
        metadata=custom_metadata
    )
    
    assert doc.metadata['custom_field'] == 'custom_value'
    assert doc.metadata['source'] == 'test_source'  # Should not be overridden 