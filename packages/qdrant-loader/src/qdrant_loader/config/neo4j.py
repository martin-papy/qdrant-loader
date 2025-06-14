"""Neo4j configuration settings.

This module defines the Neo4j-specific configuration settings.
"""

from pydantic import Field

from qdrant_loader.config.base import BaseConfig


class Neo4jConfig(BaseConfig):
    """Configuration for Neo4j graph database."""

    uri: str = Field(..., description="Neo4j server URI (bolt://host:port)")
    user: str = Field(..., description="Neo4j username")
    password: str = Field(..., description="Neo4j password")
    database: str = Field(default="neo4j", description="Neo4j database name")
    encrypted: bool = Field(default=True, description="Use encrypted connection")
    trusted_certificates: str = Field(
        default="TRUST_SYSTEM_CA_SIGNED_CERTIFICATES",
        description="Trust strategy (replaces deprecated 'trust')",
    )
    max_connection_lifetime: int = Field(
        default=3600, description="Max connection lifetime in seconds"
    )
    max_connection_pool_size: int = Field(
        default=100, description="Max connection pool size"
    )
    connection_acquisition_timeout: int = Field(
        default=60, description="Connection acquisition timeout in seconds"
    )

    # Enterprise-specific settings
    routing: bool = Field(
        default=False,
        description="Enable routing for cluster environments (Enterprise)",
    )
    read_preference: str = Field(
        default="write", description="Read preference: 'write' or 'read' (Enterprise)"
    )
    bookmarks: bool = Field(
        default=True, description="Enable bookmarks for causal consistency (Enterprise)"
    )
    fetch_size: int = Field(
        default=1000, description="Default fetch size for result streaming"
    )

    # Connection retry settings
    max_retry_time: int = Field(default=30, description="Maximum retry time in seconds")
    initial_retry_delay: float = Field(
        default=1.0, description="Initial retry delay in seconds"
    )
    retry_delay_multiplier: float = Field(
        default=2.0, description="Retry delay multiplier"
    )
    retry_delay_jitter_factor: float = Field(
        default=0.2, description="Retry delay jitter factor"
    )

    def to_dict(self) -> dict[str, str | int | bool | float]:
        """Convert the configuration to a dictionary."""
        return {
            "uri": self.uri,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "encrypted": self.encrypted,
            "trusted_certificates": self.trusted_certificates,
            "max_connection_lifetime": self.max_connection_lifetime,
            "max_connection_pool_size": self.max_connection_pool_size,
            "connection_acquisition_timeout": self.connection_acquisition_timeout,
            "routing": self.routing,
            "read_preference": self.read_preference,
            "bookmarks": self.bookmarks,
            "fetch_size": self.fetch_size,
            "max_retry_time": self.max_retry_time,
            "initial_retry_delay": self.initial_retry_delay,
            "retry_delay_multiplier": self.retry_delay_multiplier,
            "retry_delay_jitter_factor": self.retry_delay_jitter_factor,
        }

    def get_driver_config(self) -> dict:
        """Get configuration dictionary for Neo4j driver initialization."""
        config = {
            "max_connection_lifetime": self.max_connection_lifetime,
            "max_connection_pool_size": self.max_connection_pool_size,
            "connection_acquisition_timeout": self.connection_acquisition_timeout,
            "max_transaction_retry_time": self.max_retry_time,  # Driver expects max_transaction_retry_time
            "initial_retry_delay": self.initial_retry_delay,
            "retry_delay_multiplier": self.retry_delay_multiplier,
            "retry_delay_jitter_factor": self.retry_delay_jitter_factor,
        }

        # Only add encryption settings for bolt:// and neo4j:// schemes
        # For neo4j+s://, neo4j+ssc://, bolt+s://, bolt+ssc:// schemes,
        # encryption is handled by the URI scheme itself
        if self.uri.startswith(("bolt://", "neo4j://")):
            config["encrypted"] = self.encrypted
            config["trusted_certificates"] = self.trusted_certificates

        # Add Enterprise-specific routing configuration
        if self.routing:
            config["routing_context"] = {}

        return config
