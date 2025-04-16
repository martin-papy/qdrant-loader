import asyncio
import time
from collections.abc import Sequence

import structlog
import tiktoken
from openai import OpenAI

from qdrant_loader.config import Settings
from qdrant_loader.core.document import Document

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating embeddings using OpenAI's API."""

    def __init__(self, settings: Settings):
        """Initialize the embedding service.

        Args:
            settings: The application settings containing OpenAI API key and endpoint.
        """
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY, base_url=settings.global_config.embedding.endpoint
        )
        self.model = settings.global_config.embedding.model
        self.tokenizer = settings.global_config.embedding.tokenizer
        self.batch_size = settings.global_config.embedding.batch_size

        # Initialize tokenizer based on configuration
        if self.tokenizer == "none":
            self.encoding = None
        else:
            try:
                self.encoding = tiktoken.get_encoding(self.tokenizer)
            except Exception as e:
                logger.warning(
                    "Failed to initialize tokenizer, falling back to simple character counting",
                    error=str(e),
                    tokenizer=self.tokenizer,
                )
                self.encoding = None

        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests

    async def _apply_rate_limit(self):
        """Apply rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for a single text."""
        try:
            await self._apply_rate_limit()
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model,
                input=[text],  # OpenAI API expects a list
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to get embedding", error=str(e))
            raise

    async def get_embeddings(self, texts: Sequence[str | Document]) -> list[list[float]]:
        """Get embeddings for a list of texts."""
        if not texts:
            return []

        # Extract content if texts are Document objects
        contents = [text.content if isinstance(text, Document) else text for text in texts]

        # Process in smaller batches to respect rate limits
        batch_size = 100
        embeddings = []
        for i in range(0, len(contents), batch_size):
            batch = contents[i : i + batch_size]
            await self._apply_rate_limit()
            batch_embeddings = await asyncio.to_thread(
                self.client.embeddings.create, model=self.model, input=batch
            )
            embeddings.extend([embedding.embedding for embedding in batch_embeddings.data])

        return embeddings

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        if self.encoding is None:
            # Fallback to character count if no tokenizer is available
            return len(text)
        return len(self.encoding.encode(text))

    def count_tokens_batch(self, texts: list[str]) -> list[int]:
        """Count the number of tokens in a list of text strings."""
        return [self.count_tokens(text) for text in texts]

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        # For OpenAI's text-embedding-3-small model, the dimension is 1536
        return 1536
