"""Sources configuration.

This module defines the configuration for all data sources, including Git repositories,
Confluence spaces, Jira projects, and public documentation.
"""

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from ..connectors.git.config import GitRepoConfig
from ..connectors.jira.config import JiraProjectConfig
from ..connectors.confluence.config import ConfluenceSpaceConfig
from ..connectors.public_docs.config import PublicDocsSourceConfig


class SourcesConfig(BaseModel):
    """Configuration for all available data sources."""
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid"
    )
    
    public_docs: Dict[str, PublicDocsSourceConfig] = Field(
        default_factory=dict,
        description="Public documentation sources"
    )
    git_repos: Dict[str, GitRepoConfig] = Field(
        default_factory=dict,
        description="Git repository sources"
    )
    confluence: Dict[str, ConfluenceSpaceConfig] = Field(
        default_factory=dict,
        description="Confluence space sources"
    )
    jira: Dict[str, JiraProjectConfig] = Field(
        default_factory=dict,
        description="Jira project sources"
    )
    
    def get_source_config(self, source_type: str, source_name: str) -> Optional[BaseModel]:
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
            "public_docs": {
                name: config.dict()
                for name, config in self.public_docs.items()
            },
            "git_repos": {
                name: config.dict()
                for name, config in self.git_repos.items()
            },
            "confluence": {
                name: config.dict()
                for name, config in self.confluence.items()
            },
            "jira": {
                name: config.dict()
                for name, config in self.jira.items()
            }
        }