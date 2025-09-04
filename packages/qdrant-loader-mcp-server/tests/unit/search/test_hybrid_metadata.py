import pytest


@pytest.mark.unit
def test_extract_metadata_info_hierarchy(hybrid_search):
    metadata = {
        "parent_id": "parent-123",
        "parent_title": "Parent Document",
        "breadcrumb_text": "Root > Parent > Current",
        "depth": 2,
        "children": ["child1", "child2", "child3"],
    }

    info = hybrid_search._extract_metadata_info(metadata)
    assert info["parent_id"] == "parent-123"
    assert info["parent_title"] == "Parent Document"
    assert info["breadcrumb_text"] == "Root > Parent > Current"
    assert info["depth"] == 2
    assert info["children_count"] == 3
    assert "Path: Root > Parent > Current" in info["hierarchy_context"]
    assert "Depth: 2" in info["hierarchy_context"]
    assert "Children: 3" in info["hierarchy_context"]


@pytest.mark.unit
def test_extract_metadata_info_attachment(hybrid_search):
    metadata = {
        "is_attachment": True,
        "parent_document_id": "doc-456",
        "parent_document_title": "Project Plan",
        "attachment_id": "att-789",
        "original_filename": "requirements.pdf",
        "file_size": 2048000,
        "mime_type": "application/pdf",
        "author": "john.doe@company.com",
    }

    info = hybrid_search._extract_metadata_info(metadata)
    assert info["is_attachment"] is True
    assert info["parent_document_id"] == "doc-456"
    assert info["parent_document_title"] == "Project Plan"
    assert info["attachment_id"] == "att-789"
    assert info["original_filename"] == "requirements.pdf"


@pytest.mark.unit
def test_extract_metadata_info_minimal(hybrid_search):
    metadata = {}
    info = hybrid_search._extract_metadata_info(metadata)
    assert info["parent_id"] is None
    assert info["parent_title"] is None
    assert info["breadcrumb_text"] is None
    assert info["depth"] is None
    assert info["children_count"] is None
    assert info["hierarchy_context"] is None
    assert info["is_attachment"] is False
    assert info["attachment_context"] is None
