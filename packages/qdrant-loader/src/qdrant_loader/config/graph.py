"""Graph configuration settings.

This module defines the Graph-specific configuration settings.
"""

from pydantic import BaseModel, Field, PositiveInt, SecretStr


class GraphConnectionConfig(BaseModel):
    host: str = Field(default="localhost", min_length=1, description="Graph DB host")
    port: int = Field(default=6379, ge=1, le=65535, description="Graph DB port")
    password: SecretStr | None = Field(default=None, description="Graph DB password")


class GraphPoolConfig(BaseModel):
    max_connections: PositiveInt = Field(default=10, description="Max connections")

class GraphConfig(BaseModel):
    """Configuration for Graph database."""

    enabled: bool = Field(default=False, description="Enable graph processing")
    backend: str = Field(default="falkordb", min_length=1, description="Graph backend type")

    connection: GraphConnectionConfig = Field(
        default_factory=GraphConnectionConfig,
        description="Connection settings"
    )

    graph_name: str = Field(default="default_graph", min_length=1, description="Graph name / namespace")

    pool: GraphPoolConfig = Field(
        default_factory=GraphPoolConfig,
        description="Connection pool settings"
    )

    def to_dict(self) -> dict:
        """Convert config to dictionary (useful for client init)."""
        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "host": self.connection.host,
            "port": self.connection.port,
            "password": self.connection.password.get_secret_value() if self.connection.password else None,
            "graph_name": self.graph_name,
            "max_connections": self.pool.max_connections,
        }

