import pytest
from qdrant_loader_core.graph.extractor.base_extractor import EntityExtractor
from qdrant_loader_core.graph.extractor.jira import JiraEntityExtractor


@pytest.fixture(autouse=True)
def reset_registry():
    EntityExtractor._registry.clear()


def test_registry_lookup():
    EntityExtractor.register_extractor("jira", JiraEntityExtractor)

    extractor = EntityExtractor.for_source("jira")

    assert isinstance(extractor, JiraEntityExtractor)


def test_registry_invalid():
    with pytest.raises(ValueError, match="No extractor registered"):
        EntityExtractor.for_source("unknown")


def test_register_duplicate_should_fail():
    EntityExtractor.register_extractor("jira", JiraEntityExtractor)

    with pytest.raises(ValueError, match="already registered"):
        EntityExtractor.register_extractor("jira", JiraEntityExtractor)
