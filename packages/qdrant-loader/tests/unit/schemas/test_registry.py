"""Tests for schema registry."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from pydantic import Field

from qdrant_loader.schemas.registry import (
    SchemaRegistry,
    get_schema_registry,
    register_custom_schema,
    create_document_node,
    create_contains_edge,
)
from qdrant_loader.schemas.nodes import (
    DocumentNode,
    SourceNode,
    ConceptNode,
    PersonNode,
    OrganizationNode,
    ProjectNode,
    ChunkNode,
)
from qdrant_loader.schemas.edges import (
    DocumentRelationshipEdge,
    ContainsEdge,
    ReferencesEdge,
    AuthoredByEdge,
    BelongsToEdge,
    RelatedToEdge,
    DerivedFromEdge,
)


# Test schemas for validation
class CustomTestNode(EntityNode):
    """Test custom node for validation."""

    test_field: str = Field(default="default_value", description="Test field")


class CustomTestEdge(EntityEdge):
    """Test custom edge for validation."""

    test_field: str = Field(default="default_value", description="Test field")


class InvalidNode:
    """Invalid node that doesn't inherit from EntityNode."""

    pass


class InvalidEdge:
    """Invalid edge that doesn't inherit from EntityEdge."""

    pass


class TestSchemaRegistry:
    """Test SchemaRegistry class."""

    def test_initialization(self):
        """Test registry initialization."""
        registry = SchemaRegistry()

        assert not registry._initialized
        assert registry._node_schemas == {}
        assert registry._edge_schemas == {}
        assert registry._schema_metadata == {}

    def test_initialize_with_default_schemas(self):
        """Test registry initialization with default schemas."""
        registry = SchemaRegistry()
        registry.initialize()

        assert registry._initialized

        # Check node schemas
        expected_nodes = [
            "document",
            "source",
            "concept",
            "person",
            "organization",
            "project",
            "chunk",
        ]
        for node_name in expected_nodes:
            assert node_name in registry._node_schemas
            assert f"node:{node_name}" in registry._schema_metadata

        # Check edge schemas
        expected_edges = [
            "document_relationship",
            "contains",
            "references",
            "authored_by",
            "belongs_to",
            "related_to",
            "derived_from",
        ]
        for edge_name in expected_edges:
            assert edge_name in registry._edge_schemas
            assert f"edge:{edge_name}" in registry._schema_metadata

    def test_initialize_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        registry = SchemaRegistry()

        # First initialization
        registry.initialize()
        initial_node_count = len(registry._node_schemas)
        initial_edge_count = len(registry._edge_schemas)

        # Second initialization should not duplicate
        registry.initialize()
        assert len(registry._node_schemas) == initial_node_count
        assert len(registry._edge_schemas) == initial_edge_count

    def test_register_node_schema_valid(self):
        """Test registering a valid node schema."""
        registry = SchemaRegistry()

        registry.register_node_schema(
            "test_node",
            CustomTestNode,
            description="Test node schema",
            tags=["test", "custom"],
        )

        assert "test_node" in registry._node_schemas
        assert registry._node_schemas["test_node"] == CustomTestNode

        metadata = registry._schema_metadata["node:test_node"]
        assert metadata["type"] == "node"
        assert metadata["class"] == CustomTestNode
        assert metadata["description"] == "Test node schema"
        assert metadata["tags"] == ["test", "custom"]
        assert isinstance(metadata["registered_at"], datetime)

    def test_register_node_schema_invalid(self):
        """Test registering an invalid node schema."""
        registry = SchemaRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.register_node_schema("invalid_node", InvalidNode)  # type: ignore

        assert "must inherit from EntityNode" in str(exc_info.value)

    def test_register_edge_schema_valid(self):
        """Test registering a valid edge schema."""
        registry = SchemaRegistry()

        registry.register_edge_schema(
            "test_edge",
            CustomTestEdge,
            description="Test edge schema",
            tags=["test", "custom"],
        )

        assert "test_edge" in registry._edge_schemas
        assert registry._edge_schemas["test_edge"] == CustomTestEdge

        metadata = registry._schema_metadata["edge:test_edge"]
        assert metadata["type"] == "edge"
        assert metadata["class"] == CustomTestEdge
        assert metadata["description"] == "Test edge schema"
        assert metadata["tags"] == ["test", "custom"]
        assert isinstance(metadata["registered_at"], datetime)

    def test_register_edge_schema_invalid(self):
        """Test registering an invalid edge schema."""
        registry = SchemaRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.register_edge_schema("invalid_edge", InvalidEdge)  # type: ignore

        assert "must inherit from EntityEdge" in str(exc_info.value)

    @patch("qdrant_loader.schemas.registry.logger")
    def test_register_schema_override_warning(self, mock_logger):
        """Test that overriding schemas generates a warning."""
        registry = SchemaRegistry()

        # Register initial schema
        registry.register_node_schema("test_node", CustomTestNode)

        # Override with same name
        registry.register_node_schema("test_node", DocumentNode)

        # Check warning was logged
        mock_logger.warning.assert_called_with(
            "Overriding existing node schema: test_node"
        )

    def test_get_node_schema_existing(self):
        """Test getting an existing node schema."""
        registry = SchemaRegistry()
        registry.register_node_schema("test_node", CustomTestNode)

        result = registry.get_node_schema("test_node")
        assert result == CustomTestNode

    def test_get_node_schema_nonexistent(self):
        """Test getting a non-existent node schema."""
        registry = SchemaRegistry()

        result = registry.get_node_schema("nonexistent")
        assert result is None

    def test_get_edge_schema_existing(self):
        """Test getting an existing edge schema."""
        registry = SchemaRegistry()
        registry.register_edge_schema("test_edge", CustomTestEdge)

        result = registry.get_edge_schema("test_edge")
        assert result == CustomTestEdge

    def test_get_edge_schema_nonexistent(self):
        """Test getting a non-existent edge schema."""
        registry = SchemaRegistry()

        result = registry.get_edge_schema("nonexistent")
        assert result is None

    def test_list_node_schemas(self):
        """Test listing node schemas."""
        registry = SchemaRegistry()
        registry.register_node_schema("test_node1", CustomTestNode)
        registry.register_node_schema("test_node2", DocumentNode)

        schemas = registry.list_node_schemas()
        assert "test_node1" in schemas
        assert "test_node2" in schemas
        assert len(schemas) == 2

    def test_list_edge_schemas(self):
        """Test listing edge schemas."""
        registry = SchemaRegistry()
        registry.register_edge_schema("test_edge1", CustomTestEdge)
        registry.register_edge_schema("test_edge2", ContainsEdge)

        schemas = registry.list_edge_schemas()
        assert "test_edge1" in schemas
        assert "test_edge2" in schemas
        assert len(schemas) == 2

    def test_get_schema_info_existing(self):
        """Test getting schema info for existing schema."""
        registry = SchemaRegistry()
        registry.register_node_schema(
            "test_node",
            CustomTestNode,
            description="Test description",
            tags=["test"],
        )

        info = registry.get_schema_info("test_node", "node")
        assert info is not None
        assert info["type"] == "node"
        assert info["class"] == CustomTestNode
        assert info["description"] == "Test description"
        assert info["tags"] == ["test"]

    def test_get_schema_info_nonexistent(self):
        """Test getting schema info for non-existent schema."""
        registry = SchemaRegistry()

        info = registry.get_schema_info("nonexistent", "node")
        assert info is None

    def test_validate_schema_compatibility_valid_node(self):
        """Test schema compatibility validation for valid node."""
        registry = SchemaRegistry()

        result = registry.validate_schema_compatibility(CustomTestNode)
        assert result is True

    def test_validate_schema_compatibility_valid_edge(self):
        """Test schema compatibility validation for valid edge."""
        registry = SchemaRegistry()

        result = registry.validate_schema_compatibility(CustomTestEdge)
        assert result is True

    def test_validate_schema_compatibility_invalid(self):
        """Test schema compatibility validation for invalid schema."""
        registry = SchemaRegistry()

        # Test with invalid class that doesn't inherit from EntityNode/EntityEdge
        result = registry.validate_schema_compatibility(InvalidNode)  # type: ignore
        assert result is False

    def test_create_node_instance_existing_schema(self):
        """Test creating node instance with existing schema."""
        registry = SchemaRegistry()
        registry.register_node_schema("test_node", CustomTestNode)

        instance = registry.create_node_instance(
            "test_node",
            name="test",
            group_id="test_group",
            test_field="test_value",
        )

        assert instance is not None
        assert isinstance(instance, CustomTestNode)
        assert instance.name == "test"
        assert instance.group_id == "test_group"
        assert instance.test_field == "test_value"

    def test_create_node_instance_nonexistent_schema(self):
        """Test creating node instance with non-existent schema."""
        registry = SchemaRegistry()

        instance = registry.create_node_instance(
            "nonexistent", name="test", group_id="test_group"
        )

        assert instance is None

    def test_create_edge_instance_existing_schema(self):
        """Test creating edge instance with existing schema."""
        registry = SchemaRegistry()
        registry.register_edge_schema("test_edge", CustomTestEdge)

        instance = registry.create_edge_instance(
            "test_edge",
            group_id="test_group",
            source_node_uuid="source-uuid",
            target_node_uuid="target-uuid",
            name="test_edge_instance",
            fact="test fact",
            created_at=datetime.now(),
            test_field="test_value",
        )

        assert instance is not None
        assert isinstance(instance, CustomTestEdge)
        assert instance.group_id == "test_group"
        assert instance.source_node_uuid == "source-uuid"
        assert instance.target_node_uuid == "target-uuid"
        assert instance.name == "test_edge_instance"
        assert instance.fact == "test fact"
        assert instance.test_field == "test_value"

    def test_create_edge_instance_nonexistent_schema(self):
        """Test creating edge instance with non-existent schema."""
        registry = SchemaRegistry()

        instance = registry.create_edge_instance(
            "nonexistent",
            group_id="test_group",
            source_node_uuid="source-uuid",
            target_node_uuid="target-uuid",
            name="test",
            fact="test fact",
        )

        assert instance is None

    def test_get_schema_summary(self):
        """Test getting schema summary."""
        registry = SchemaRegistry()
        registry.register_node_schema("test_node", CustomTestNode)
        registry.register_edge_schema("test_edge", CustomTestEdge)

        summary = registry.get_schema_summary()

        assert summary["initialized"] is False
        assert summary["node_schemas"]["count"] == 1
        assert "test_node" in summary["node_schemas"]["schemas"]
        assert summary["edge_schemas"]["count"] == 1
        assert "test_edge" in summary["edge_schemas"]["schemas"]
        assert summary["total_schemas"] == 2


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_schema_registry_singleton(self):
        """Test that get_schema_registry returns singleton."""
        registry1 = get_schema_registry()
        registry2 = get_schema_registry()

        assert registry1 is registry2
        assert registry1._initialized

    @patch("qdrant_loader.schemas.registry.get_schema_registry")
    def test_register_custom_schema_node(self, mock_get_registry):
        """Test registering custom node schema."""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry

        register_custom_schema(
            "test_node",
            CustomTestNode,
            "node",
            description="Test description",
            tags=["test"],
        )

        mock_registry.register_node_schema.assert_called_once_with(
            "test_node", CustomTestNode, "Test description", ["test"]
        )

    @patch("qdrant_loader.schemas.registry.get_schema_registry")
    def test_register_custom_schema_edge(self, mock_get_registry):
        """Test registering custom edge schema."""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry

        register_custom_schema(
            "test_edge",
            CustomTestEdge,
            "edge",
            description="Test description",
            tags=["test"],
        )

        mock_registry.register_edge_schema.assert_called_once_with(
            "test_edge", CustomTestEdge, "Test description", ["test"]
        )

    @patch("qdrant_loader.schemas.registry.get_schema_registry")
    def test_register_custom_schema_invalid_type(self, mock_get_registry):
        """Test registering custom schema with invalid type."""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry

        with pytest.raises(ValueError) as exc_info:
            register_custom_schema("test", CustomTestNode, "invalid")

        assert "Invalid schema type:" in str(exc_info.value)
        assert "Must be 'node' or 'edge'" in str(exc_info.value)

    @patch("qdrant_loader.schemas.registry.get_schema_registry")
    def test_create_document_node(self, mock_get_registry):
        """Test creating document node."""
        mock_registry = MagicMock()
        mock_instance = MagicMock(spec=DocumentNode)
        mock_registry.create_node_instance.return_value = mock_instance
        mock_get_registry.return_value = mock_registry

        result = create_document_node("test", "test_group", file_type="pdf")

        mock_registry.create_node_instance.assert_called_once_with(
            "document", "test", "test_group", file_type="pdf"
        )
        assert result == mock_instance

    @patch("qdrant_loader.schemas.registry.get_schema_registry")
    def test_create_contains_edge(self, mock_get_registry):
        """Test creating contains edge."""
        mock_registry = MagicMock()
        mock_instance = MagicMock(spec=ContainsEdge)
        mock_registry.create_edge_instance.return_value = mock_instance
        mock_get_registry.return_value = mock_registry

        result = create_contains_edge(
            "test_group",
            "source-uuid",
            "target-uuid",
            "contains_edge",
            "contains fact",
            container_section="introduction",
        )

        mock_registry.create_edge_instance.assert_called_once_with(
            "contains",
            "test_group",
            "source-uuid",
            "target-uuid",
            "contains_edge",
            "contains fact",
            container_section="introduction",
        )
        assert result == mock_instance


class TestSchemaRegistryIntegration:
    """Integration tests for schema registry."""

    def test_full_workflow_with_default_schemas(self):
        """Test full workflow with default schemas."""
        registry = SchemaRegistry()
        registry.initialize()

        # Test creating document node
        doc_node = registry.create_node_instance(
            "document",
            name="test_document",
            group_id="test_group",
            file_type="pdf",
            file_size=1024,
        )

        assert doc_node is not None
        assert isinstance(doc_node, DocumentNode)
        assert doc_node.name == "test_document"
        assert doc_node.file_type == "pdf"

        # Test creating contains edge with required created_at field
        contains_edge = registry.create_edge_instance(
            "contains",
            group_id="test_group",
            source_node_uuid="source-uuid",
            target_node_uuid="target-uuid",
            name="contains_edge",
            fact="contains fact",
            created_at=datetime.now(),
            container_section="introduction",
        )

        assert contains_edge is not None
        assert isinstance(contains_edge, ContainsEdge)
        assert contains_edge.container_section == "introduction"

    def test_schema_metadata_tracking(self):
        """Test that schema metadata is properly tracked."""
        registry = SchemaRegistry()
        registry.initialize()

        # Check document schema metadata
        doc_info = registry.get_schema_info("document", "node")
        assert doc_info is not None
        assert doc_info["type"] == "node"
        assert doc_info["class"] == DocumentNode
        # Check that "document" (case-insensitive) is mentioned in description
        assert "document" in doc_info["description"].lower()
        assert isinstance(doc_info["registered_at"], datetime)

    def test_schema_listing_after_initialization(self):
        """Test schema listing after initialization."""
        registry = SchemaRegistry()
        registry.initialize()

        node_schemas = registry.list_node_schemas()
        edge_schemas = registry.list_edge_schemas()

        assert len(node_schemas) == 7
        assert len(edge_schemas) == 7

        expected_nodes = [
            "document",
            "source",
            "concept",
            "person",
            "organization",
            "project",
            "chunk",
        ]
        expected_edges = [
            "document_relationship",
            "contains",
            "references",
            "authored_by",
            "belongs_to",
            "related_to",
            "derived_from",
        ]

        for node in expected_nodes:
            assert node in node_schemas

        for edge in expected_edges:
            assert edge in edge_schemas

    def test_schema_summary_complete(self):
        """Test complete schema summary."""
        registry = SchemaRegistry()
        registry.initialize()

        summary = registry.get_schema_summary()

        assert summary["initialized"] is True
        assert summary["node_schemas"]["count"] == 7  # 7 default node schemas
        assert summary["edge_schemas"]["count"] == 7  # 7 default edge schemas
        assert summary["total_schemas"] == 14
        assert len(summary["node_schemas"]["schemas"]) == 7
        assert len(summary["edge_schemas"]["schemas"]) == 7
