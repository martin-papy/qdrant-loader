"""Reranking models."""

from pydantic import BaseModel, Field

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