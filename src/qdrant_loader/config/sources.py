"""Sources configuration.

This module defines the configuration for all data sources, including Git repositories,
Confluence spaces, Jira projects, and public documentation.
"""

from pydantic import BaseModel, Field

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.connectors.public_docs.config import PublicDocsSourceConfig


class SourcesConfig(BaseModel):
    """Configuration for all available data sources."""

    public_docs: dict[str, PublicDocsSourceConfig] = Field(
        default_factory=dict, description="Public documentation sources"
    )
    git_repos: dict[str, GitRepoConfig] = Field(
        default_factory=dict, description="Git repository sources"
    )
    confluence: dict[str, ConfluenceSpaceConfig] = Field(
        default_factory=dict, description="Confluence space sources"
    )
    jira: dict[str, JiraProjectConfig] = Field(
        default_factory=dict, description="Jira project sources"
    )

    def get_source_config(self, source_type: str, source_name: str) -> SourceConfig | None:
        """Get the configuration for a specific source.

        Args:
            source_type: Type of the source (public_docs, git_repos, confluence, jira)
            source_name: Name of the specific source configuration

        Returns:
            Optional[BaseModel]: The source configuration if it exists, None otherwise
        """
        source_dict = getattr(self, source_type, {})
        return source_dict.get(source_name)

    def to_dict(self) -> dict:
        """Convert the configuration to a dictionary."""
        return {
            "public_docs": {name: config.model_dump() for name, config in self.public_docs.items()},
            "git_repos": {name: config.model_dump() for name, config in self.git_repos.items()},
            "confluence": {name: config.model_dump() for name, config in self.confluence.items()},
            "jira": {name: config.model_dump() for name, config in self.jira.items()},
        }
