"""Sources configuration.

This module defines the configuration for all data sources, including Git repositories,
Confluence spaces, Jira projects, and public documentation.
"""

from typing import TYPE_CHECKING
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

    publicdocs: dict[str, "PublicDocsSourceConfig"] = Field(
        default_factory=dict, description="Public documentation sources"
    )
    git: dict[str, "GitRepoConfig"] = Field(
        default_factory=dict, description="Git repository sources"
    )
    confluence: dict[str, "ConfluenceSpaceConfig"] = Field(
        default_factory=dict, description="Confluence space sources"
    )
    jira: dict[str, "JiraProjectConfig"] = Field(
        default_factory=dict, description="Jira project sources"
    )
    localfile: dict[str, "LocalFileConfig"] = Field(
        default_factory=dict, description="Local file sources"
    )

    model_config = ConfigDict(arbitrary_types_allowed=False, extra="forbid")

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
                name: config.model_dump() for name, config in self.publicdocs.items()
            },
            SourceType.GIT: {
                name: config.model_dump() for name, config in self.git.items()
            },
            SourceType.CONFLUENCE: {
                name: config.model_dump() for name, config in self.confluence.items()
            },
            SourceType.JIRA: {
                name: config.model_dump() for name, config in self.jira.items()
            },
            SourceType.LOCALFILE: {
                name: config.model_dump() for name, config in self.localfile.items()
            },
        }


# Rebuild the model to resolve forward references
def _rebuild_sources_config():
    """Rebuild SourcesConfig model to resolve forward references."""
    try:
        # Import the actual classes
        _get_connector_config_classes()
        # Rebuild the model with resolved references
        SourcesConfig.model_rebuild()
    except Exception:
        # If rebuild fails, it's not critical for basic functionality
        pass


# Call rebuild when module is imported
_rebuild_sources_config()
