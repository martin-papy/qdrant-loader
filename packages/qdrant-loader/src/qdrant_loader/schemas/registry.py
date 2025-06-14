"""Schema registry for custom Graphiti schemas.

This module provides a centralized registry for managing custom node and edge schemas,
including validation, registration, and schema discovery functionality.
"""

from datetime import datetime

from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode

from ..utils.logging import LoggingConfig
from .edges import (
    AuthoredByEdge,
    BelongsToEdge,
    ContainsEdge,
    DerivedFromEdge,
    DocumentRelationshipEdge,
    ReferencesEdge,
    RelatedToEdge,
)
from .nodes import (
    ChunkNode,
    ConceptNode,
    DocumentNode,
    OrganizationNode,
    PersonNode,
    ProjectNode,
    SourceNode,
)

logger = LoggingConfig.get_logger(__name__)


class SchemaRegistry:
    """Registry for managing custom Graphiti schemas.

    Provides centralized management of node and edge schemas, including
    registration, validation, and discovery functionality.
    """

    def __init__(self):
        """Initialize the schema registry."""
        self._node_schemas: dict[str, type[EntityNode]] = {}
        self._edge_schemas: dict[str, type[EntityEdge]] = {}
        self._schema_metadata: dict[str, dict] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the registry with default schemas."""
        if self._initialized:
            logger.debug("Schema registry already initialized")
            return

        logger.info("Initializing schema registry with custom schemas")

        # Register node schemas
        self.register_node_schema("document", DocumentNode)
        self.register_node_schema("source", SourceNode)
        self.register_node_schema("concept", ConceptNode)
        self.register_node_schema("person", PersonNode)
        self.register_node_schema("organization", OrganizationNode)
        self.register_node_schema("project", ProjectNode)
        self.register_node_schema("chunk", ChunkNode)

        # Register edge schemas
        self.register_edge_schema("document_relationship", DocumentRelationshipEdge)
        self.register_edge_schema("contains", ContainsEdge)
        self.register_edge_schema("references", ReferencesEdge)
        self.register_edge_schema("authored_by", AuthoredByEdge)
        self.register_edge_schema("belongs_to", BelongsToEdge)
        self.register_edge_schema("related_to", RelatedToEdge)
        self.register_edge_schema("derived_from", DerivedFromEdge)

        self._initialized = True
        logger.info(
            "Schema registry initialized with {len(self._node_schemas)} node schemas and {len(self._edge_schemas)} edge schemas"
        )

    def register_node_schema(
        self,
        schema_name: str,
        schema_class: type[EntityNode],
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Register a node schema.

        Args:
            schema_name: Unique name for the schema
            schema_class: The node schema class
            description: Optional description of the schema
            tags: Optional tags for categorization
        """
        if not issubclass(schema_class, EntityNode):
            raise ValueError("Schema class {schema_class} must inherit from EntityNode")

        if schema_name in self._node_schemas:
            logger.warning("Overriding existing node schema: {schema_name}")

        self._node_schemas[schema_name] = schema_class
        self._schema_metadata["node:{schema_name}"] = {
            "type": "node",
            "class": schema_class,
            "description": description or schema_class.__doc__,
            "tags": tags or [],
            "registered_at": datetime.now(),
        }

        logger.debug("Registered node schema: {schema_name}")

    def register_edge_schema(
        self,
        schema_name: str,
        schema_class: type[EntityEdge],
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Register an edge schema.

        Args:
            schema_name: Unique name for the schema
            schema_class: The edge schema class
            description: Optional description of the schema
            tags: Optional tags for categorization
        """
        if not issubclass(schema_class, EntityEdge):
            raise ValueError("Schema class {schema_class} must inherit from EntityEdge")

        if schema_name in self._edge_schemas:
            logger.warning("Overriding existing edge schema: {schema_name}")

        self._edge_schemas[schema_name] = schema_class
        self._schema_metadata["edge:{schema_name}"] = {
            "type": "edge",
            "class": schema_class,
            "description": description or schema_class.__doc__,
            "tags": tags or [],
            "registered_at": datetime.now(),
        }

        logger.debug("Registered edge schema: {schema_name}")

    def get_node_schema(self, schema_name: str) -> type[EntityNode] | None:
        """Get a registered node schema by name.

        Args:
            schema_name: Name of the schema to retrieve

        Returns:
            The node schema class or None if not found
        """
        return self._node_schemas.get(schema_name)

    def get_edge_schema(self, schema_name: str) -> type[EntityEdge] | None:
        """Get a registered edge schema by name.

        Args:
            schema_name: Name of the schema to retrieve

        Returns:
            The edge schema class or None if not found
        """
        return self._edge_schemas.get(schema_name)

    def list_node_schemas(self) -> list[str]:
        """List all registered node schema names.

        Returns:
            List of node schema names
        """
        return list(self._node_schemas.keys())

    def list_edge_schemas(self) -> list[str]:
        """List all registered edge schema names.

        Returns:
            List of edge schema names
        """
        return list(self._edge_schemas.keys())

    def get_schema_info(self, schema_name: str, schema_type: str) -> dict | None:
        """Get metadata about a schema.

        Args:
            schema_name: Name of the schema
            schema_type: Type of schema ('node' or 'edge')

        Returns:
            Schema metadata dictionary or None if not found
        """
        key = "{schema_type}:{schema_name}"
        return self._schema_metadata.get(key)

    def validate_schema_compatibility(
        self, schema_class: type[EntityNode | EntityEdge]
    ) -> bool:
        """Validate that a schema class is compatible with Graphiti.

        Args:
            schema_class: The schema class to validate

        Returns:
            True if compatible, False otherwise
        """
        try:
            # Check if it's a valid Pydantic model
            if not hasattr(schema_class, "model_fields"):
                return False

            # Check if it inherits from the correct base class
            if not (
                issubclass(schema_class, EntityNode)
                or issubclass(schema_class, EntityEdge)
            ):
                return False

            # Try to create a minimal instance to validate the schema
            if issubclass(schema_class, EntityNode):
                # EntityNode requires name and group_id
                test_instance = schema_class(name="test", group_id="test")
            else:
                # EntityEdge requires more fields
                test_instance = schema_class(
                    group_id="test",
                    source_node_uuid="test-source",
                    target_node_uuid="test-target",
                    created_at=datetime.now(),
                    name="test",
                    fact="test fact",
                )

            return True

        except Exception:
            logger.error("Schema validation failed for {schema_class}: {e}")
            return False

    def create_node_instance(
        self, schema_name: str, name: str, group_id: str, **kwargs
    ) -> EntityNode | None:
        """Create an instance of a registered node schema.

        Args:
            schema_name: Name of the registered schema
            name: Name for the node
            group_id: Group ID for the node
            **kwargs: Additional fields for the node

        Returns:
            Node instance or None if schema not found
        """
        schema_class = self.get_node_schema(schema_name)
        if not schema_class:
            logger.error("Node schema not found: {schema_name}")
            return None

        try:
            return schema_class(name=name, group_id=group_id, **kwargs)
        except Exception:
            logger.error("Failed to create node instance for {schema_name}: {e}")
            return None

    def create_edge_instance(
        self,
        schema_name: str,
        group_id: str,
        source_node_uuid: str,
        target_node_uuid: str,
        name: str,
        fact: str,
        **kwargs,
    ) -> EntityEdge | None:
        """Create an instance of a registered edge schema.

        Args:
            schema_name: Name of the registered schema
            group_id: Group ID for the edge
            source_node_uuid: UUID of the source node
            target_node_uuid: UUID of the target node
            name: Name for the edge
            fact: Fact description for the edge
            **kwargs: Additional fields for the edge

        Returns:
            Edge instance or None if schema not found
        """
        schema_class = self.get_edge_schema(schema_name)
        if not schema_class:
            logger.error("Edge schema not found: {schema_name}")
            return None

        try:
            return schema_class(
                group_id=group_id,
                source_node_uuid=source_node_uuid,
                target_node_uuid=target_node_uuid,
                name=name,
                fact=fact,
                **kwargs,
            )
        except Exception:
            logger.error("Failed to create edge instance for {schema_name}: {e}")
            return None

    def get_schema_summary(self) -> dict:
        """Get a summary of all registered schemas.

        Returns:
            Dictionary with schema counts and lists
        """
        return {
            "initialized": self._initialized,
            "node_schemas": {
                "count": len(self._node_schemas),
                "schemas": list(self._node_schemas.keys()),
            },
            "edge_schemas": {
                "count": len(self._edge_schemas),
                "schemas": list(self._edge_schemas.keys()),
            },
            "total_schemas": len(self._node_schemas) + len(self._edge_schemas),
        }


# Global schema registry instance
schema_registry = SchemaRegistry()


def get_schema_registry() -> SchemaRegistry:
    """Get the global schema registry instance.

    Returns:
        The global schema registry
    """
    if not schema_registry._initialized:
        schema_registry.initialize()
    return schema_registry


def register_custom_schema(
    schema_name: str,
    schema_class: type[EntityNode | EntityEdge],
    schema_type: str,
    description: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """Register a custom schema with the global registry.

    Args:
        schema_name: Unique name for the schema
        schema_class: The schema class
        schema_type: Type of schema ('node' or 'edge')
        description: Optional description
        tags: Optional tags for categorization
    """
    registry = get_schema_registry()

    if schema_type == "node":
        if not issubclass(schema_class, EntityNode):
            raise ValueError("Schema class must inherit from EntityNode for node type")
        registry.register_node_schema(schema_name, schema_class, description, tags)
    elif schema_type == "edge":
        if not issubclass(schema_class, EntityEdge):
            raise ValueError("Schema class must inherit from EntityEdge for edge type")
        registry.register_edge_schema(schema_name, schema_class, description, tags)
    else:
        raise ValueError("Invalid schema type: {schema_type}. Must be 'node' or 'edge'")


# Convenience functions for common operations
def create_document_node(name: str, group_id: str, **kwargs) -> DocumentNode | None:
    """Create a DocumentNode instance."""
    registry = get_schema_registry()
    result = registry.create_node_instance("document", name, group_id, **kwargs)
    return result if isinstance(result, DocumentNode) else None


def create_contains_edge(
    group_id: str, source_uuid: str, target_uuid: str, name: str, fact: str, **kwargs
) -> ContainsEdge | None:
    """Create a ContainsEdge instance."""
    registry = get_schema_registry()
    result = registry.create_edge_instance(
        "contains", group_id, source_uuid, target_uuid, name, fact, **kwargs
    )
    return result if isinstance(result, ContainsEdge) else None
