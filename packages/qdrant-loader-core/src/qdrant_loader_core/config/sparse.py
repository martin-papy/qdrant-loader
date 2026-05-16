"""Shared sparse/hybrid runtime configuration.

The contract for sparse/hybrid retrieval lives here: a Pydantic ``BaseModel``
with field validators that explicitly reject anything outside ``bool`` /
``"true"`` / ``"false"`` for bool fields and non-empty strings for string
fields. YAML is the sole source of truth — callers pass the parsed global
config to :meth:`SparseRuntimeConfig.from_global_config`; layering and
missing-value handling live in this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SparseRuntimeConfig(BaseModel):
    """Sparse/hybrid retrieval configuration.

    Immutable (``frozen=True``) and closed (``extra="forbid"``) — unknown
    fields at construction raise ``ValidationError``, and accepted fields can
    only be replaced via :meth:`model_copy`. ``use_qdrant_hybrid`` only
    affects retrieval (the MCP server); the loader package ignores it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True, description="Enable sparse vectors for ingest and retrieval."
    )
    model: str = Field(
        default="bm25",
        min_length=1,
        description="Sparse encoder model identifier (e.g. 'bm25').",
    )
    dense_vector_name: str = Field(
        default="dense",
        min_length=1,
        description="Named-vector key for the dense embedding in Qdrant.",
    )
    sparse_vector_name: str = Field(
        default="sparse",
        min_length=1,
        description="Named-vector key for the sparse embedding in Qdrant.",
    )
    auto_fallback: bool = Field(
        default=True,
        description="Fall back to dense-only behaviour when sparse is unavailable.",
    )
    use_qdrant_hybrid: bool = Field(
        default=True,
        description="Use Qdrant server-side fusion for retrieval (MCP server only).",
    )

    @field_validator("enabled", "auto_fallback", "use_qdrant_hybrid", mode="before")
    @classmethod
    def _strict_bool(cls, v: Any) -> bool:
        """Accept only ``bool`` or the strings ``"true"`` / ``"false"`` (case-insensitive).

        This is intentionally stricter than Pydantic's default bool coercion —
        we don't want ``1``, ``"yes"``, or ``"on"`` to silently mean True in a
        config file.
        """
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized == "true":
                return True
            if normalized == "false":
                return False
        raise ValueError(f"expected bool or 'true'/'false', got {v!r}")

    @field_validator("model", "dense_vector_name", "sparse_vector_name", mode="before")
    @classmethod
    def _strict_str(cls, v: Any) -> str:
        """Accept only non-empty strings; reject ``None``, numbers, etc."""
        if isinstance(v, str) and v.strip():
            return v
        raise ValueError(f"expected non-empty string, got {v!r}")

    @classmethod
    def from_global_config(
        cls, global_config: Mapping[str, Any] | None = None
    ) -> SparseRuntimeConfig:
        """Build a config from the parsed global YAML section.

        Reads from ``global_config['llm']['sparse']`` and
        ``global_config['llm']['retrieval']['sparse']`` (the retrieval block
        wins where it overlaps), plus
        ``global_config['llm']['retrieval']['use_qdrant_hybrid']``.

        Missing or wrongly-shaped sections produce defaults; invalid values
        raise ``pydantic.ValidationError``.
        """
        if not isinstance(global_config, Mapping):
            return cls()
        llm = global_config.get("llm")
        if not isinstance(llm, Mapping):
            return cls()

        # The retrieval block wins where it overlaps with the top-level sparse block.
        overrides: dict[str, Any] = {}
        if isinstance(llm.get("sparse"), Mapping):
            overrides.update(llm["sparse"])

        retrieval = llm.get("retrieval")
        if isinstance(retrieval, Mapping):
            if isinstance(retrieval.get("sparse"), Mapping):
                overrides.update(retrieval["sparse"])
            if "use_qdrant_hybrid" in retrieval:
                overrides["use_qdrant_hybrid"] = retrieval["use_qdrant_hybrid"]

        # Drop unknown keys here so the contract surface is the model's fields,
        # not whatever the YAML happens to contain.
        recognised = {k: v for k, v in overrides.items() if k in cls.model_fields}
        return cls(**recognised)
