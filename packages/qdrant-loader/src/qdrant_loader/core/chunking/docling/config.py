"""Engine-agnostic chunking configuration.

Frozen dataclasses describing *our* chunking knobs — never docling types. The
tokenizer factory in :mod:`.tokenizer` is the single place that turns this into a
docling tokenizer, which keeps the chunker behind the seam in :mod:`.chunker`.

The rationale for each default lives in
``docling/chunking/03-best-practices-and-contract-redesign.md``: §3.3/§5.4 (token
budget + the embedding model's own tokenizer), §3.3 (the HybridChunker merge pass),
§5.1 (embed the heading-path-prefixed text), §5.3 (``chunk_schema_version``).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TokenizerKind(StrEnum):
    """Which docling tokenizer wrapper backs the token budget.

    The string values double as the type-safe parse target for a YAML config
    field, mirroring :class:`~..conversion.config.ConversionProfile`.
    """

    OPENAI = "openai"  # tiktoken — pairs with an OpenAI-style embedding model
    HUGGINGFACE = "huggingface"  # transformers AutoTokenizer for a HF model id


class TableSerialization(StrEnum):
    """How table items are rendered into chunk text.

    The string values double as the type-safe parse target for the YAML field
    ``chunking.strategies.docling.table_serialization``.
    """

    # docling's chunking default: "row, column = value" triplets — more
    # semantically meaningful embeddings than grid layouts (per docling's docs)
    TRIPLETS = "triplets"
    # GitHub-flavored markdown rows — better LLM/display readability; very wide
    # tables may overflow the token budget (docling#3428)
    MARKDOWN = "markdown"


@dataclass(frozen=True, slots=True)
class TokenizerConfig:
    """How to count tokens, aligned to the *embedding* model (doc 03 §5.4).

    ``HybridChunker`` requires a real tokenizer to size chunks; counting against a
    tokenizer unrelated to the embedder is the §2.2 char-budget mistake. ``model``
    is a tiktoken encoding name for ``OPENAI`` or a HF model id for ``HUGGINGFACE``.
    """

    kind: TokenizerKind = TokenizerKind.OPENAI
    model: str = "cl100k_base"
    max_tokens: int = 512  # the embedding model's per-chunk budget (a hard ceiling)
    # True when this is a *counting proxy*, not the embedding model's own tokenizer
    # (the model exposes none — e.g. Ollama). Counts are approximate; the factory
    # warns once so the choice is observable, never silent.
    approximate: bool = False


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """The complete, immutable chunking configuration for one chunker instance."""

    tokenizer: TokenizerConfig = field(default_factory=TokenizerConfig)

    # ── HybridChunker behaviour ──
    merge_peers: bool = True  # recombine undersized adjacent chunks sharing headings
    delim: str = "\n"  # serialization delimiter between merged doc items
    # how table items become chunk text; YAML-exposed via
    # ``chunking.strategies.docling.table_serialization``
    table_serialization: TableSerialization = TableSerialization.TRIPLETS

    # ── contract shaping ──
    # §5.1 contextual embedding: when on, the chunk's contextualized text (heading_path
    # + body) becomes the embedded text AND the stored content. Opt-in (default off) via
    # ``chunking.strategies.docling.include_context_in_embed``; the seam is wired through
    # the chunker (contextualize) and the mapper (content = embed_text).
    include_context_in_embed: bool = False
    # §3.3 caveat: contextualize() can push a chunk past max_tokens (HybridChunker only
    # guarantees the budget for the bare body). When True, the chunker logs a warning on
    # overflow rather than failing — the embedder may truncate oversized input.
    enforce_token_budget: bool = True
    chunk_schema_version: str = "1"  # §5.3: lets a future re-index be detected

    @classmethod
    def from_embedding(
        cls, *, tokenizer: str, max_tokens: int, **overrides: Any
    ) -> ChunkingConfig:
        """Derive a config from the loader's embedding settings (doc 03 §5.4).

        ``tokenizer`` is the ``embedding.tokenizer`` string the loader already
        carries; ``max_tokens`` is its ``max_tokens_per_chunk``. Top-level overrides
        replace whole fields (pass a built :class:`TokenizerConfig`, not its parts).
        """
        baseline = cls(tokenizer=cls._resolve_tokenizer(tokenizer, max_tokens))
        return dataclasses.replace(baseline, **overrides) if overrides else baseline

    @staticmethod
    def _resolve_tokenizer(tokenizer: str, max_tokens: int) -> TokenizerConfig:
        """Map an ``embedding.tokenizer`` string onto a :class:`TokenizerConfig`.

        ``"none"`` (the Ollama-local default, which exposes no tokenizer) falls back
        to tiktoken ``cl100k_base`` as an *approximate counting proxy* — flagged so
        the factory warns once, never a silent guess. A slashed value (``org/model``)
        is a HF model id; anything else is a tiktoken encoding name, and is treated as
        the embedding model's real tokenizer (not approximate).
        """
        if not tokenizer or tokenizer == "none":
            return TokenizerConfig(
                kind=TokenizerKind.OPENAI,
                model="cl100k_base",
                max_tokens=max_tokens,
                approximate=True,
            )
        if "/" in tokenizer:
            return TokenizerConfig(
                kind=TokenizerKind.HUGGINGFACE, model=tokenizer, max_tokens=max_tokens
            )
        return TokenizerConfig(
            kind=TokenizerKind.OPENAI, model=tokenizer, max_tokens=max_tokens
        )
