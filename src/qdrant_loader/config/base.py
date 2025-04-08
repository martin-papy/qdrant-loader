"""Base configuration interfaces and protocols.

This module defines the base interfaces and protocols for all configuration types
in the application. These serve as contracts that concrete configuration classes
must implement.
"""

from typing import Protocol, Any, Dict, Optional
from pydantic import BaseModel


class ConfigProtocol(Protocol):
    """Protocol for configuration objects.
    
    This protocol defines the minimum interface that all configuration classes
    must implement. It serves as a contract for configuration objects.
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: The configuration as a dictionary.
        """
        ...


class SourceConfigProtocol(Protocol):
    """Protocol for source-specific configurations.
    
    This protocol defines the interface for configurations specific to data sources
    like Git, Confluence, or Jira.
    """
    
    def validate(self) -> None:
        """Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid.
        """
        ...


class BaseConfig(BaseModel):
    """Base class for all configuration types.
    
    This class serves as the base for all configuration classes in the application.
    It provides common functionality and implements the ConfigProtocol.
    """
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        extra = "forbid"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: The configuration as a dictionary.
        """
        return self.dict()


class BaseSourceConfig(BaseConfig):
    """Base class for source-specific configurations.
    
    This class serves as the base for all source-specific configuration classes.
    It provides common functionality and implements the SourceConfigProtocol.
    """
    
    def validate(self) -> None:
        """Validate the configuration.
        
        This method should be overridden by subclasses to implement
        source-specific validation logic.
        """
        pass 