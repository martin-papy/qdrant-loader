from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator, ConfigDict, ValidationError, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv
import structlog

# Load environment variables from .env file
load_dotenv()

class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""
    model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model to use"
    )
    batch_size: int = Field(
        default=100,
        description="Number of texts to embed in a single batch"
    )

class GlobalConfig(BaseModel):
    """Global configuration for all sources."""
    chunking: Dict[str, int] = Field(
        default={"size": 500, "overlap": 50},
        description="Default chunking configuration"
    )
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Default embedding configuration"
    )
    logging: Dict[str, str] = Field(
        default={"level": "INFO", "format": "json", "file": "qdrant-loader.log"},
        description="Logging configuration"
    )

    @field_validator("logging")
    @classmethod
    def validate_logging(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        valid_formats = ["json", "plain"]
        
        if v["level"].upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        if v["format"] not in valid_formats:
            raise ValueError(f"Log format must be one of {valid_formats}")
        return v

class SelectorsConfig(BaseModel):
    """Configuration for HTML content extraction selectors."""
    content: str = Field(default="article, main, .content", description="Main content container selector")
    remove: List[str] = Field(
        default=["nav", "header", "footer", ".sidebar"],
        description="Elements to remove from the content"
    )
    code_blocks: str = Field(default="pre code", description="Code blocks selector")

class PublicDocsSourceConfig(BaseModel):
    """Configuration for a single public documentation source."""
    base_url: str = Field(..., description="Base URL of the documentation website")
    version: str = Field(..., description="Specific version of the documentation to fetch")
    content_type: str = Field(default="html", description="Content type of the documentation")
    path_pattern: Optional[str] = Field(
        default=None,
        description="Specific path pattern to match documentation pages"
    )
    exclude_paths: List[str] = Field(
        default=[],
        description="List of paths to exclude from processing"
    )
    selectors: SelectorsConfig = Field(
        default_factory=SelectorsConfig,
        description="CSS selectors for content extraction"
    )
    auto_detect_version: bool = Field(
        default=False,
        description="Whether to automatically detect the latest version"
    )
    version_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern to extract version from URLs or content"
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        valid_types = ["html", "markdown"]
        if v.lower() not in valid_types:
            raise ValueError(f"content_type must be one of {valid_types}")
        return v.lower()

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")

    def detect_version(self) -> str:
        """Detect the latest version of the documentation if auto_detect_version is True."""
        if not self.auto_detect_version:
            return self.version

        try:
            import requests
            from bs4 import BeautifulSoup
            import re

            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            if self.version_pattern:
                # Search for version in the page content
                version_match = re.search(self.version_pattern, response.text)
                if version_match:
                    return version_match.group(1)

            # Try to find version in common locations
            version_selectors = [
                ".version", "#version", "[data-version]",
                "meta[name='version']", "meta[property='version']"
            ]

            for selector in version_selectors:
                element = soup.select_one(selector)
                if element:
                    version = element.get_text().strip() or element.get("content", "").strip()
                    if version:
                        return version

            # If no version found, return the configured version
            return self.version

        except Exception as e:
            logger = structlog.get_logger()
            logger.warning("Failed to detect version automatically", error=str(e))
            return self.version

class PublicDocsConfig(BaseModel):
    """Configuration for all public documentation sources."""
    sources: Dict[str, PublicDocsSourceConfig] = Field(
        default_factory=dict,
        description="Dictionary of documentation sources"
    )

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "PublicDocsConfig":
        """Load configuration from a YAML file."""
        try:
            with open(yaml_path, "r") as f:
                config_data = yaml.safe_load(f)
            return cls(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load public docs configuration: {str(e)}")

class GitRepoConfig(BaseModel):
    """Configuration for a Git repository source."""
    url: str = Field(..., description="Repository URL")
    branch: str = Field(default="main", description="Branch to process")
    include_paths: List[str] = Field(
        default=["**"],
        description="Paths to include in processing"
    )
    exclude_paths: List[str] = Field(
        default=[],
        description="Paths to exclude from processing"
    )
    file_types: List[str] = Field(
        default=["md", "rst", "txt"],
        description="File types to process"
    )

class ConfluenceConfig(BaseModel):
    """Configuration for a Confluence space source."""
    space_key: str = Field(..., description="Space key")
    content_types: List[str] = Field(
        default=["page", "blogpost"],
        description="Content types to process"
    )
    include_labels: List[str] = Field(
        default=[],
        description="Labels to include"
    )
    exclude_labels: List[str] = Field(
        default=[],
        description="Labels to exclude"
    )

class JiraConfig(BaseModel):
    """Configuration for a Jira project source."""
    project_key: str = Field(..., description="Project key")
    issue_types: List[str] = Field(
        default=[],
        description="Issue types to process"
    )
    include_statuses: List[str] = Field(
        default=[],
        description="Statuses to include"
    )

class SourcesConfig(BaseModel):
    """Configuration for all sources."""
    global_config: GlobalConfig = Field(
        default_factory=GlobalConfig,
        description="Global configuration"
    )
    public_docs: Dict[str, PublicDocsSourceConfig] = Field(
        default_factory=dict,
        description="Public documentation sources"
    )
    git_repos: Dict[str, GitRepoConfig] = Field(
        default_factory=dict,
        description="Git repository sources"
    )
    confluence: Dict[str, ConfluenceConfig] = Field(
        default_factory=dict,
        description="Confluence space sources"
    )
    jira: Dict[str, JiraConfig] = Field(
        default_factory=dict,
        description="Jira project sources"
    )

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "SourcesConfig":
        """Load configuration from a YAML file.
        
        Args:
            yaml_path: Path to the configuration YAML file (e.g., config.yaml)
            
        Returns:
            SourcesConfig: The loaded configuration
            
        Raises:
            ValueError: If the configuration file cannot be loaded or is invalid
        """
        try:
            with open(yaml_path, "r") as f:
                config_data = yaml.safe_load(f)
            
            # Rename 'global' to 'global_config' to avoid Python keyword conflict
            if "global" in config_data:
                config_data["global_config"] = config_data.pop("global")
            
            return cls(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load sources configuration: {str(e)}")

class Settings(BaseSettings):
    """Configuration settings for the QDrant Loader."""
    
    # qDrant Configuration
    QDRANT_URL: str = Field(..., description="qDrant server URL")
    QDRANT_API_KEY: str = Field(..., description="qDrant API key")
    QDRANT_COLLECTION_NAME: str = Field(..., description="qDrant collection name")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    @field_validator("QDRANT_URL", "QDRANT_API_KEY", "QDRANT_COLLECTION_NAME", "OPENAI_API_KEY")
    @classmethod
    def validate_required_string(cls, v):
        if not v:
            raise ValueError("Field is required and cannot be empty")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_prefix=""
    )

_settings_instance = None

def get_settings() -> Optional[Settings]:
    """Get the settings instance, creating it if necessary and if not in test environment."""
    global _settings_instance
    if _settings_instance is None and "PYTEST_CURRENT_TEST" not in os.environ:
        try:
            _settings_instance = Settings()
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to load settings: {str(e)}")
    return _settings_instance 

_global_config_instance = None

def get_global_config() -> GlobalConfig:
    """Get the global configuration instance, creating it if necessary."""
    global _global_config_instance
    if _global_config_instance is None:
        try:
            config_path = os.getenv("CONFIG_PATH", "config.yaml")
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
            if "global" in config_data:
                _global_config_instance = GlobalConfig(**config_data["global"])
            else:
                _global_config_instance = GlobalConfig()
        except Exception as e:
            logger = structlog.get_logger()
            logger.warning("Failed to load global configuration, using defaults", error=str(e))
            _global_config_instance = GlobalConfig()
    return _global_config_instance 