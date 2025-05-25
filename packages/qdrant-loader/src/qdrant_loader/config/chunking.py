"""Configuration for text chunking."""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""

    chunk_size: int = Field(
        default=1000,
        description="Size of text chunks in characters",
        gt=0,
        title="Chunk Size",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks in characters",
        ge=0,
        title="Chunk Overlap",
    )

    @field_validator("chunk_overlap")
    def validate_chunk_overlap(cls, v: int, info: ValidationInfo) -> int:
        """Validate that chunk overlap is less than chunk size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v
