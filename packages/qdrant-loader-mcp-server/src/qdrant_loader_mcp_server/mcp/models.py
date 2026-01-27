"""MCP request and response models."""

from typing import Any

from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    """MCP request model."""

    jsonrpc: str = Field(..., description="JSON-RPC version")
    method: str = Field(..., description="Method to call")
    params: dict[str, Any] = Field(..., description="Method parameters")
    id: int = Field(..., description="Request ID")


class MCPResponse(BaseModel):
    """MCP response model."""

    jsonrpc: str = Field(..., description="JSON-RPC version")
    id: int = Field(..., description="Request ID")
    result: Any | None = Field(None, description="Result of the request")
    error: dict[str, Any] | None = Field(None, description="Error information")

class MCPReranking(BaseModel):
    """Reranking model."""

    enabled: bool = Field(default=False, description="Enable or disable reranking")
    model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-12-v2",
        description="Reranking model to use",
    )
    device: str = Field(default="cpu", description="Device to run the reranking model")
    batch_size: int = Field(
        default=32, description="Batch size for reranking model inference"
    )