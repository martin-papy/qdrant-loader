from qdrant_loader.core.document import Document
from qdrant_loader_core.graph.extractor.confluence import ConfluenceEntityExtractor


def test_confluence_page():
    extractor = ConfluenceEntityExtractor()

    # Prepare a Document instance with normalized metadata the extractor expects
    metadata = {
        "space_key": "ENG",
        "author": "Bob",
        "labels": ["design"],
        "parent_id": None,
        "children": [{"id": "456"}],
    }

    doc = Document(
        title="Design Doc",
        content_type="page",
        content="Example content",
        source_type="confluence",
        source="confluence_instance",
        url="http://conf/page",
        metadata=metadata,
    )

    result = extractor.extract(doc)

    assert any(n.label == "Container" for n in result.nodes)
    assert any(e.edge_type == "BELONGS_TO" for e in result.edges)
