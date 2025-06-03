"""Sources configuration.

This module defines the configuration for all data sources, including Git repositories,
Confluence spaces, Jira projects, and public documentation.
"""

from typing import TYPE_CHECKING, Any
from pydantic import BaseModel, ConfigDict, Field

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.types import SourceType

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
    from qdrant_loader.connectors.git.config import GitRepoConfig
    from qdrant_loader.connectors.jira.config import JiraProjectConfig
    from qdrant_loader.connectors.localfile.config import LocalFileConfig
    from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig


def _get_connector_config_classes():
    """Lazy import connector config classes to avoid circular dependencies."""
    from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
    from qdrant_loader.connectors.git.config import GitRepoConfig
    from qdrant_loader.connectors.jira.config import JiraProjectConfig
    from qdrant_loader.connectors.localfile.config import LocalFileConfig
    from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig

    return {
        "PublicDocsSourceConfig": PublicDocsSourceConfig,
        "GitRepoConfig": GitRepoConfig,
        "ConfluenceSpaceConfig": ConfluenceSpaceConfig,
        "JiraProjectConfig": JiraProjectConfig,
        "LocalFileConfig": LocalFileConfig,
    }


class SourcesConfig(BaseModel):
    """Configuration for all available data sources."""

    publicdocs: dict[str, Any] = Field(
        default_factory=dict, description="Public documentation sources"
    )
    git: dict[str, Any] = Field(
        default_factory=dict, description="Git repository sources"
    )
    confluence: dict[str, Any] = Field(
        default_factory=dict, description="Confluence space sources"
    )
    jira: dict[str, Any] = Field(
        default_factory=dict, description="Jira project sources"
    )
    localfile: dict[str, Any] = Field(
        default_factory=dict, description="Local file sources"
    )

    model_config = ConfigDict(arbitrary_types_allowed=False, extra="forbid")

    def __init__(self, **data):
        """Initialize SourcesConfig with proper connector config objects."""
        # Convert dictionaries to proper config objects
        processed_data = {}

        for field_name, field_value in data.items():
            if field_name in [
                "publicdocs",
                "git",
                "confluence",
                "jira",
                "localfile",
            ] and isinstance(field_value, dict):
                processed_data[field_name] = self._convert_source_configs(
                    field_name, field_value
                )
            else:
                processed_data[field_name] = field_value

        super().__init__(**processed_data)

    def _convert_source_configs(self, source_type: str, configs: dict) -> dict:
        """Convert dictionary configs to proper config objects."""
        config_classes = _get_connector_config_classes()
        converted = {}

        for name, config_data in configs.items():
            if isinstance(config_data, dict):
                # Get the appropriate config class
                if source_type == "publicdocs":
                    config_class = config_classes["PublicDocsSourceConfig"]
                elif source_type == "git":
                    config_class = config_classes["GitRepoConfig"]
                elif source_type == "confluence":
                    config_class = config_classes["ConfluenceSpaceConfig"]
                elif source_type == "jira":
                    config_class = config_classes["JiraProjectConfig"]
                elif source_type == "localfile":
                    config_class = config_classes["LocalFileConfig"]
                else:
                    # Unknown source type, keep as dict
                    converted[name] = config_data
                    continue

                # Create the config object - let validation errors propagate
                try:
                    converted[name] = config_class(**config_data)
                except (ImportError, AttributeError, TypeError) as e:
                    # Only catch import/type errors, not validation errors
                    # These indicate missing dependencies or code issues
                    converted[name] = config_data
                # Let ValidationError and other Pydantic errors propagate
            else:
                # Already a config object or other type
                converted[name] = config_data

        return converted

    def get_source_config(self, source_type: str, source: str) -> SourceConfig | None:
        """Get the configuration for a specific source.

        Args:
            source_type: Type of the source (publicdocs, git, confluence, jira)
            source: Name of the specific source configuration

        Returns:
            Optional[BaseModel]: The source configuration if it exists, None otherwise
        """
        source_dict = getattr(self, source_type, {})
        return source_dict.get(source)

    def to_dict(self) -> dict:
        """Convert the configuration to a dictionary."""
        return {
            SourceType.PUBLICDOCS: {
                name: config.model_dump() if hasattr(config, "model_dump") else config
                for name, config in self.publicdocs.items()
            },
            SourceType.GIT: {
                name: config.model_dump() if hasattr(config, "model_dump") else config
                for name, config in self.git.items()
            },
            SourceType.CONFLUENCE: {
                name: config.model_dump() if hasattr(config, "model_dump") else config
                for name, config in self.confluence.items()
            },
            SourceType.JIRA: {
                name: config.model_dump() if hasattr(config, "model_dump") else config
                for name, config in self.jira.items()
            },
            SourceType.LOCALFILE: {
                name: config.model_dump() if hasattr(config, "model_dump") else config
                for name, config in self.localfile.items()
            },
        }
