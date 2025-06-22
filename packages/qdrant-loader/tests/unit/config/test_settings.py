"""
Unit tests for the main Settings class and its interactions.
"""

import pytest
from qdrant_loader.config import GlobalConfig, Settings
from qdrant_loader.config.neo4j import Neo4jConfig
from qdrant_loader.config.qdrant import QdrantConfig


def test_settings_initialization_with_minimal_config():
    """
    Tests that the Settings class can be initialized with a minimal valid configuration.
    """
    qdrant_conf = QdrantConfig(url="http://localhost:6333", collection_name="test")
    global_conf = GlobalConfig(qdrant=qdrant_conf)
    settings = Settings(global_config=global_conf)

    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection_name == "test"
    assert settings.qdrant_api_key is None


def test_settings_properties_with_full_config():
    """
    Tests that the properties on the Settings object correctly reflect the
    nested configuration values.
    """
    qdrant_conf = QdrantConfig(
        url="http://qdrant-test:6333",
        api_key="test-key",
        collection_name="production",
    )
    neo4j_conf = Neo4jConfig(
        uri="bolt://neo4j-test:7687",
        user="neo4j",
        password="password",
        database="testdb",
    )
    # The real GlobalConfig loads an 'embedding' config, which in turn needs an openai_api_key
    # For this unit test, we can pass a dictionary that will be coerced.
    global_conf = GlobalConfig(
        qdrant=qdrant_conf,
        neo4j=neo4j_conf,
        embedding={"model": "text-embedding-ada-002", "api_key": "fake-key"},
    )
    settings = Settings(global_config=global_conf)

    # Test properties
    assert settings.qdrant_url == "http://qdrant-test:6333"
    assert settings.qdrant_collection_name == "production"
    assert settings.qdrant_api_key == "test-key"
    assert settings.neo4j_uri == "bolt://neo4j-test:7687"
    assert settings.neo4j_user == "neo4j"
    assert settings.neo4j_password == "password"
    assert settings.neo4j_database == "testdb"
    assert settings.openai_api_key == "fake-key"


def test_settings_fails_without_qdrant_config():
    """
    Tests that initializing Settings fails if the Qdrant config is missing
    from the GlobalConfig.
    """
    with pytest.raises(ValueError, match="Qdrant configuration is required"):
        # GlobalConfig defaults qdrant to None
        global_conf = GlobalConfig()
        Settings(global_config=global_conf)
