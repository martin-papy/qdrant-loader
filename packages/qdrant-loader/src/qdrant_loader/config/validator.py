"""Configuration validation for multi-project support.

This module provides validation functionality for both legacy and multi-project
configurations, ensuring data integrity and catching common configuration errors.
"""

import re
from typing import Any, Dict, List, Set

from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ConfigValidator:
    """Validates configuration data for multi-project support."""

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate_structure(self, config_data: Dict[str, Any]) -> None:
        """Validate the overall configuration structure.

        Args:
            config_data: Raw configuration data

        Raises:
            ValueError: If configuration structure is invalid
        """
        logger.debug("Validating configuration structure")

        # Check for required sections
        if not isinstance(config_data, dict):
            raise ValueError("Configuration must be a dictionary")

        # Validate that we have either sources or projects, but configuration is valid either way
        has_sources = "sources" in config_data
        has_projects = "projects" in config_data

        if not has_sources and not has_projects:
            raise ValueError(
                "Configuration must contain either 'sources' (legacy) or 'projects' section"
            )

        # If we have projects section, validate it
        if has_projects:
            self._validate_projects_section(config_data["projects"])

        # If we have legacy sources, validate them
        if has_sources and not has_projects:
            self._validate_sources_section(config_data["sources"])

        # Validate global section if present
        if "global" in config_data:
            self._validate_global_section(config_data["global"])

        logger.debug("Configuration structure validation completed")

    def _validate_projects_section(self, projects_data: Any) -> None:
        """Validate the projects section.

        Args:
            projects_data: Projects configuration data

        Raises:
            ValueError: If projects section is invalid
        """
        if not isinstance(projects_data, dict):
            raise ValueError("'projects' section must be a dictionary")

        if not projects_data:
            raise ValueError("'projects' section cannot be empty")

        project_ids = set()
        collection_names = set()

        for project_id, project_config in projects_data.items():
            # Validate project ID
            self._validate_project_id(project_id)

            if project_id in project_ids:
                raise ValueError(f"Duplicate project ID: '{project_id}'")
            project_ids.add(project_id)

            # Validate individual project configuration
            self._validate_project_config(project_id, project_config)

            # Check for duplicate collection names
            if "collection_name" in project_config:
                collection_name = project_config["collection_name"]
                if collection_name in collection_names:
                    raise ValueError(
                        f"Duplicate collection name '{collection_name}' "
                        f"found in project '{project_id}'"
                    )
                collection_names.add(collection_name)

    def _validate_project_config(self, project_id: str, project_config: Any) -> None:
        """Validate individual project configuration.

        Args:
            project_id: Project identifier
            project_config: Project configuration data

        Raises:
            ValueError: If project configuration is invalid
        """
        if not isinstance(project_config, dict):
            raise ValueError(
                f"Project '{project_id}' configuration must be a dictionary"
            )

        # Validate required fields
        if "display_name" not in project_config:
            raise ValueError(f"Project '{project_id}' must have a 'display_name'")

        display_name = project_config["display_name"]
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError(
                f"Project '{project_id}' display_name must be a non-empty string"
            )

        # Validate optional fields
        if "description" in project_config:
            description = project_config["description"]
            if description is not None and not isinstance(description, str):
                raise ValueError(
                    f"Project '{project_id}' description must be a string or null"
                )

        if "collection_name" in project_config:
            collection_name = project_config["collection_name"]
            if not isinstance(collection_name, str) or not collection_name.strip():
                raise ValueError(
                    f"Project '{project_id}' collection_name must be a non-empty string"
                )
            self._validate_collection_name(collection_name)

        # Validate sources section if present
        if "sources" in project_config:
            self._validate_sources_section(project_config["sources"])

        # Validate overrides section if present
        if "overrides" in project_config:
            overrides = project_config["overrides"]
            if not isinstance(overrides, dict):
                raise ValueError(
                    f"Project '{project_id}' overrides must be a dictionary"
                )

    def _validate_sources_section(self, sources_data: Any) -> None:
        """Validate sources configuration.

        Args:
            sources_data: Sources configuration data

        Raises:
            ValueError: If sources configuration is invalid
        """
        if not isinstance(sources_data, dict):
            raise ValueError("'sources' section must be a dictionary")

        # Allow empty sources section for testing purposes
        # In production, users would typically have at least one source configured
        if not sources_data:
            logger.debug(
                "Sources section is empty - this is allowed but no data will be ingested"
            )
            return

        # Validate each source type
        for source_type, source_configs in sources_data.items():
            if not isinstance(source_configs, dict):
                raise ValueError(f"Source type '{source_type}' must be a dictionary")

            if not source_configs:
                raise ValueError(f"Source type '{source_type}' cannot be empty")

            # Validate each source configuration
            for source_name, source_config in source_configs.items():
                if not isinstance(source_config, dict):
                    raise ValueError(
                        f"Source '{source_name}' in '{source_type}' must be a dictionary"
                    )

                # Note: source_type and source fields are automatically injected by the parser
                # so we don't need to validate their presence here

    def _validate_global_section(self, global_data: Any) -> None:
        """Validate global configuration section.

        Args:
            global_data: Global configuration data

        Raises:
            ValueError: If global configuration is invalid
        """
        if not isinstance(global_data, dict):
            raise ValueError("'global' section must be a dictionary")

        # The actual validation of global config fields will be handled
        # by the GlobalConfig pydantic model, so we just do basic structure checks here

        # Validate qdrant section if present
        if "qdrant" in global_data:
            qdrant_config = global_data["qdrant"]
            if not isinstance(qdrant_config, dict):
                raise ValueError("'global.qdrant' must be a dictionary")

            if "collection_name" in qdrant_config:
                collection_name = qdrant_config["collection_name"]
                if not isinstance(collection_name, str) or not collection_name.strip():
                    raise ValueError(
                        "'global.qdrant.collection_name' must be a non-empty string"
                    )
                self._validate_collection_name(collection_name)

    def _validate_project_id(self, project_id: str) -> None:
        """Validate project ID format.

        Args:
            project_id: Project identifier to validate

        Raises:
            ValueError: If project ID is invalid
        """
        if not isinstance(project_id, str):
            raise ValueError("Project ID must be a string")

        if not project_id.strip():
            raise ValueError("Project ID cannot be empty")

        # Project IDs must be valid identifiers (alphanumeric + underscores + hyphens)
        pattern = r"^[a-zA-Z][a-zA-Z0-9_-]*$"
        if not re.match(pattern, project_id):
            raise ValueError(
                f"Invalid project ID '{project_id}'. "
                "Project IDs must start with a letter and contain only "
                "letters, numbers, underscores, and hyphens."
            )

        # Check for reserved project IDs
        reserved_ids = {"default", "global", "admin", "system"}
        if project_id.lower() in reserved_ids:
            logger.warning(
                f"Project ID '{project_id}' is reserved and may cause conflicts"
            )

    def _validate_source_name(self, source_name: str) -> None:
        """Validate source name format.

        Args:
            source_name: Source name to validate

        Raises:
            ValueError: If source name is invalid
        """
        if not isinstance(source_name, str):
            raise ValueError("Source name must be a string")

        if not source_name.strip():
            raise ValueError("Source name cannot be empty")

        # Source names should be valid identifiers
        pattern = r"^[a-zA-Z][a-zA-Z0-9_-]*$"
        if not re.match(pattern, source_name):
            raise ValueError(
                f"Invalid source name '{source_name}'. "
                "Source names must start with a letter and contain only "
                "letters, numbers, underscores, and hyphens."
            )

    def _validate_source_config(
        self, source_type: str, source_name: str, source_config: Any
    ) -> None:
        """Validate individual source configuration.

        Args:
            source_type: Type of the source
            source_name: Name of the source
            source_config: Source configuration data

        Raises:
            ValueError: If source configuration is invalid
        """
        if not isinstance(source_config, dict):
            raise ValueError(
                f"Source '{source_name}' of type '{source_type}' "
                "configuration must be a dictionary"
            )

        # Basic validation - specific source validation will be handled
        # by the individual source config classes
        if not source_config:
            raise ValueError(
                f"Source '{source_name}' of type '{source_type}' "
                "configuration cannot be empty"
            )

    def _validate_collection_name(self, collection_name: str) -> None:
        """Validate QDrant collection name format.

        Args:
            collection_name: Collection name to validate

        Raises:
            ValueError: If collection name is invalid
        """
        # QDrant collection names have specific requirements
        # They should be valid identifiers and not too long
        if len(collection_name) > 255:
            raise ValueError(
                f"Collection name '{collection_name}' is too long (max 255 characters)"
            )

        # Collection names should be valid identifiers
        pattern = r"^[a-zA-Z][a-zA-Z0-9_-]*$"
        if not re.match(pattern, collection_name):
            raise ValueError(
                f"Invalid collection name '{collection_name}'. "
                "Collection names must start with a letter and contain only "
                "letters, numbers, underscores, and hyphens."
            )
