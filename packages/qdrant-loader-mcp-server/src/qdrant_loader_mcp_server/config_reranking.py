from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class MCPReranking(BaseModel):

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable or disable reranking")
    model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-12-v2",
        description="Reranking model to use",
    )
    device: str | None = Field(
        default=None,
        description="Device to run the reranking model (auto-detects if not specified)",
    )
    batch_size: PositiveInt = Field(
        default=32,
        description="Batch size for reranking model inference (must be >= 1)",
    )
