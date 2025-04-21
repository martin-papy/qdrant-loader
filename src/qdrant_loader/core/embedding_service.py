import asyncio
import time
from collections.abc import Sequence

import requests
import tiktoken
from openai import OpenAI

from qdrant_loader.config import Settings
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI's API or local service."""

    def __init__(self, settings: Settings):
        """Initialize the embedding service.

        Args:
            settings: The application settings containing API key and endpoint.
        """
        self.settings = settings
        self.endpoint = settings.global_config.embedding.endpoint.rstrip("/")
        self.model = settings.global_config.embedding.model
        self.tokenizer = settings.global_config.embedding.tokenizer
        self.batch_size = settings.global_config.embedding.batch_size

        # Initialize client based on endpoint
        if "https://api.openai.com/v1" == self.endpoint:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=self.endpoint)
            self.use_openai = True
        else:
            self.client = None
            self.use_openai = False

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

    async def get_embeddings(self, texts: Sequence[str | Document]) -> list[list[float]]:
        """Get embeddings for a list of texts."""
        if not texts:
            return []

        # Extract content if texts are Document objects
        contents = [text.content if isinstance(text, Document) else text for text in texts]
        logger.debug("Starting batch embedding process", total_texts=len(contents))

        # Process in larger batches to improve performance
        batch_size = min(self.batch_size * 4, 100)  # Increased batch size but capped at 100
        embeddings = []

        for i in range(0, len(contents), batch_size):
            batch = contents[i : i + batch_size]
            batch_num = i // batch_size + 1
            logger.debug(
                "Processing batch",
                batch_num=batch_num,
                batch_size=len(batch),
            )
            await self._apply_rate_limit()

            try:
                if self.use_openai and self.client is not None:
                    logger.debug("Getting batch embeddings from OpenAI", model=self.model)
                    response = await asyncio.to_thread(
                        self.client.embeddings.create, model=self.model, input=batch
                    )
                    embeddings.extend([embedding.embedding for embedding in response.data])
                else:
                    # Local service request
                    logger.debug(
                        "Getting batch embeddings from local service",
                        model=self.model,
                        endpoint=self.endpoint,
                    )
                    response = await asyncio.to_thread(
                        requests.post,
                        f"{self.endpoint}/embeddings",
                        json={"input": batch, "model": self.model},
                        headers={"Content-Type": "application/json"},
                        timeout=60,  # Increased timeout for larger batches
                    )
                    response.raise_for_status()
                    data = response.json()
                    if "data" not in data or not data["data"]:
                        raise ValueError("Invalid response format from local embedding service")
                    embeddings.extend([item["embedding"] for item in data["data"]])

                logger.debug(
                    "Completed batch processing",
                    batch_num=batch_num,
                    processed_embeddings=len(embeddings),
                )

            except Exception as e:
                logger.error(
                    "Failed to process batch",
                    batch_num=batch_num,
                    error=str(e),
                )
                raise

        return embeddings

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for a single text."""
        try:
            await self._apply_rate_limit()
            if self.use_openai and self.client is not None:
                logger.debug("Getting embedding from OpenAI", model=self.model)
                response = await asyncio.to_thread(
                    self.client.embeddings.create,
                    model=self.model,
                    input=[text],  # OpenAI API expects a list
                )
                return response.data[0].embedding
            else:
                # Local service request
                logger.debug(
                    "Getting embedding from local service", model=self.model, endpoint=self.endpoint
                )
                response = await asyncio.to_thread(
                    requests.post,
                    f"{self.endpoint}/embeddings",
                    json={"input": text, "model": self.model},
                    headers={"Content-Type": "application/json"},
                    timeout=30,  # 30 second timeout
                )
                response.raise_for_status()
                data = response.json()
                if "data" not in data or not data["data"]:
                    raise ValueError("Invalid response format from local embedding service")
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error("Failed to get embedding", error=str(e))
            raise

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
        return self.settings.global_config.embedding.vector_size or 1536
