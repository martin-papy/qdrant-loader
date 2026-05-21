import pytest
from qdrant_loader_core.graph.registry import EntityExtractor


def test_registry_lookup():
    extractor = EntityExtractor.for_source("jira")
    assert extractor is not None


def test_registry_invalid():
    with pytest.raises(ValueError):
        EntityExtractor.for_source("unknown")
