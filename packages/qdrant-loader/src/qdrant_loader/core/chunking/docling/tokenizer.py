"""Builds the docling tokenizer that bounds chunk size.

:class:`TokenizerFactory` is the single place that turns our engine-neutral
:class:`~.config.TokenizerConfig` into a docling ``BaseTokenizer`` — the chunking
analogue of the conversion option builder. It is a small pure class holding the
injected config and imports docling lazily, so importing this package costs nothing
until a chunk is actually sized.

Aligning the chunk budget to the *embedding* model's tokenizer is the whole point of
this layer; a mismatched tokenizer is the character-budget mistake it exists to fix.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qdrant_loader.utils.logging import LoggingConfig

from .config import TokenizerConfig, TokenizerKind
from .exceptions import TokenizerUnavailableError

if TYPE_CHECKING:
    from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer

logger = LoggingConfig.get_logger(__name__)


class TokenizerFactory:
    """Config -> docling ``BaseTokenizer``. The only place tokenizers are built."""

    def __init__(self, config: TokenizerConfig) -> None:
        self._config = config

    def build(self) -> BaseTokenizer:
        """Construct the tokenizer for the configured kind.

        Raises :class:`TokenizerUnavailableError` (loud, not a silent char-count
        fallback) when the backing library or model cannot be loaded. When the config
        is an approximate counting proxy (``embedding.tokenizer="none"``), warns once
        here so the choice is observable rather than silent.
        """
        if self._config.approximate:
            logger.warning(
                "Chunk token counts are approximate: the embedding model exposes no "
                "tokenizer, so this proxy is used only for counting. Set a chunking "
                "tokenizer matching your embedding model for exact token budgeting.",
                proxy_tokenizer=self._config.model,
            )
        match self._config.kind:
            case TokenizerKind.OPENAI:
                return self._build_openai()
            case TokenizerKind.HUGGINGFACE:
                return self._build_huggingface()
        raise TokenizerUnavailableError(
            str(self._config.kind), "unknown tokenizer kind"
        )

    def _build_openai(self) -> BaseTokenizer:
        try:
            import tiktoken
            from docling_core.transforms.chunker.tokenizer.openai import (
                OpenAITokenizer,
            )

            encoding = tiktoken.get_encoding(self._config.model)
        except Exception as error:  # missing dep / unknown encoding / no cached BPE
            raise TokenizerUnavailableError("openai", str(error)) from error
        return OpenAITokenizer(tokenizer=encoding, max_tokens=self._config.max_tokens)

    def _build_huggingface(self) -> BaseTokenizer:
        try:
            from docling_core.transforms.chunker.tokenizer.huggingface import (
                HuggingFaceTokenizer,
            )

            return HuggingFaceTokenizer.from_pretrained(
                model_name=self._config.model,
                max_tokens=self._config.max_tokens,
            )
        except Exception as error:  # missing dep / model not present / offline hub
            raise TokenizerUnavailableError("huggingface", str(error)) from error
