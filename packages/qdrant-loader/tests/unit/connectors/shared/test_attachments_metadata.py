from __future__ import annotations

from types import SimpleNamespace

from qdrant_loader.connectors.shared.attachments.metadata import (
    confluence_attachment_to_metadata,
    jira_attachment_to_metadata,
    normalize_attachment_metadata,
)


def test_normalize_attachment_metadata_basic():
    meta = {
        "id": "123",
        "filename": "file.txt",
        "size": 42,
        "mime_type": "text/plain",
        "download_url": "http://x/y",
        "created": "2024-01-01",
    }
    att = normalize_attachment_metadata(meta, parent_id="P")
    assert att.id == "123"
    assert att.parent_document_id == "P"
    assert att.filename == "file.txt"
    assert att.size == 42
    assert att.mime_type == "text/plain"
    assert att.download_url == "http://x/y"


def test_jira_attachment_to_metadata():
    att = SimpleNamespace(
        id="A1",
        filename="doc.pdf",
        size=100,
        mime_type="application/pdf",
        content_url="http://dl",
        created=None,
        author=SimpleNamespace(display_name="Alice"),
    )
    m = jira_attachment_to_metadata(att, parent_id="ISSUE-1")
    assert m.id == "A1"
    assert m.parent_document_id == "ISSUE-1"
    assert m.filename == "doc.pdf"
    assert m.author == "Alice"


def test_confluence_attachment_to_metadata_download_url_building():
    data = {
        "id": "c1",
        "title": "conf.txt",
        "metadata": {"mediaType": {"name": "text/plain", "size": 12}},
        "_links": {"download": "/download/attachments/123/conf.txt"},
        "version": {"by": {"displayName": "Bob"}},
        "history": {"createdDate": "2024-01-01"},
    }
    m = confluence_attachment_to_metadata(data, base_url="http://conf", parent_id="P")
    assert m is not None
    assert m.download_url == "http://conf/download/attachments/123/conf.txt"
    assert m.mime_type == "text/plain"







