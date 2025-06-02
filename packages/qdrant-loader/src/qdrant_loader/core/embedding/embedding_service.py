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
            self.client = OpenAI(
                api_key=settings.global_config.embedding.api_key, base_url=self.endpoint
            )
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

        # Retry configuration for network resilience
        self.max_retries = 3
        self.base_retry_delay = 1.0  # Start with 1 second
        self.max_retry_delay = 30.0  # Cap at 30 seconds

    async def _apply_rate_limit(self):
        """Apply rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    async def _retry_with_backoff(self, operation, operation_name: str, **kwargs):
        """Execute an operation with exponential backoff retry logic.

        Args:
            operation: The async operation to retry
            operation_name: Name of the operation for logging
            **kwargs: Additional arguments passed to the operation

        Returns:
            The result of the successful operation

        Raises:
            The last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                if attempt > 0:
                    # Calculate exponential backoff delay
                    delay = min(
                        self.base_retry_delay * (2 ** (attempt - 1)),
                        self.max_retry_delay,
                    )
                    logger.warning(
                        f"Retrying {operation_name} after network error",
                        attempt=attempt,
                        max_retries=self.max_retries,
                        delay_seconds=delay,
                        last_error=str(last_exception) if last_exception else None,
                    )
                    await asyncio.sleep(delay)

                # Execute the operation
                result = await operation(**kwargs)

                if attempt > 0:
                    logger.info(
                        f"Successfully recovered {operation_name} after retries",
                        successful_attempt=attempt + 1,
                        total_attempts=attempt + 1,
                    )

                return result

            except (
                asyncio.TimeoutError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                ConnectionError,
                OSError,
            ) as e:
                last_exception = e

                if attempt == self.max_retries:
                    logger.error(
                        f"All retry attempts failed for {operation_name}",
                        total_attempts=attempt + 1,
                        final_error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

                logger.warning(
                    f"Network error in {operation_name}, will retry",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                    error_type=type(e).__name__,
                )

            except Exception as e:
                # For non-network errors, don't retry
                logger.error(
                    f"Non-retryable error in {operation_name}",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Unexpected error in retry logic for {operation_name}")

    async def get_embeddings(
        self, texts: Sequence[str | Document]
    ) -> list[list[float]]:
        """Get embeddings for a list of texts."""
        if not texts:
            return []

        # Extract content if texts are Document objects
        contents = [
            text.content if isinstance(text, Document) else text for text in texts
        ]

        # Filter out empty, None, or invalid content
        valid_contents = []
        valid_indices = []
        for i, content in enumerate(contents):
            if content and isinstance(content, str) and content.strip():
                valid_contents.append(content.strip())
                valid_indices.append(i)
            else:
                logger.warning(
                    f"Skipping invalid content at index {i}: {repr(content)}"
                )

        if not valid_contents:
            logger.warning(
                "No valid content found in batch, returning empty embeddings"
            )
            return []

        logger.debug(
            "Starting batch embedding process",
            total_texts=len(contents),
            valid_texts=len(valid_contents),
            filtered_out=len(contents) - len(valid_contents),
        )

        # Validate and split content based on token limits
        # Use configurable token limits from settings
        MAX_TOKENS_PER_REQUEST = (
            self.settings.global_config.embedding.max_tokens_per_request
        )
        MAX_TOKENS_PER_CHUNK = (
            self.settings.global_config.embedding.max_tokens_per_chunk
        )

        validated_contents = []
        truncated_count = 0
        for content in valid_contents:
            token_count = self.count_tokens(content)
            if token_count > MAX_TOKENS_PER_CHUNK:
                truncated_count += 1
                logger.warning(
                    "Content exceeds maximum token limit, truncating",
                    content_length=len(content),
                    token_count=token_count,
                    max_tokens=MAX_TOKENS_PER_CHUNK,
                )
                # Truncate content to fit within token limit
                if self.encoding is not None:
                    # Use tokenizer to truncate precisely
                    tokens = self.encoding.encode(content)
                    truncated_tokens = tokens[:MAX_TOKENS_PER_CHUNK]
                    truncated_content = self.encoding.decode(truncated_tokens)
                    validated_contents.append(truncated_content)
                else:
                    # Fallback to character-based truncation (rough estimate)
                    # Assume ~4 characters per token on average
                    max_chars = MAX_TOKENS_PER_CHUNK * 4
                    validated_contents.append(content[:max_chars])
            else:
                validated_contents.append(content)

        if truncated_count > 0:
            logger.info(
                f"⚠️ Truncated {truncated_count} content items due to token limits. You might want to adjust chunk size and/or max tokens settings in config.yaml"
            )

        # Create smart batches that respect token limits
        embeddings = []
        current_batch = []
        current_batch_tokens = 0
        batch_count = 0

        for content in validated_contents:
            content_tokens = self.count_tokens(content)

            # Check if adding this content would exceed the token limit
            if current_batch and (
                current_batch_tokens + content_tokens > MAX_TOKENS_PER_REQUEST
            ):
                # Process current batch
                batch_count += 1
                batch_embeddings = await self._process_batch(current_batch)
                embeddings.extend(batch_embeddings)

                # Start new batch
                current_batch = [content]
                current_batch_tokens = content_tokens
            else:
                # Add to current batch
                current_batch.append(content)
                current_batch_tokens += content_tokens

        # Process final batch if it exists
        if current_batch:
            batch_count += 1
            batch_embeddings = await self._process_batch(current_batch)
            embeddings.extend(batch_embeddings)

        logger.info(
            f"🔗 Generated embeddings: {len(embeddings)} items in {batch_count} batches"
        )
        return embeddings

    async def _process_batch(self, batch: list[str]) -> list[list[float]]:
        """Process a single batch of content for embeddings.

        Args:
            batch: List of content strings to embed

        Returns:
            List of embedding vectors
        """
        if not batch:
            return []

        batch_num = getattr(self, "_batch_counter", 0) + 1
        setattr(self, "_batch_counter", batch_num)

        logger.debug(
            "Processing embedding batch",
            batch_num=batch_num,
            batch_size=len(batch),
            total_tokens=sum(self.count_tokens(content) for content in batch),
        )

        await self._apply_rate_limit()

        # Use retry logic for network resilience
        return await self._retry_with_backoff(
            self._execute_embedding_request,
            f"embedding batch {batch_num}",
            batch=batch,
            batch_num=batch_num,
        )

    async def _execute_embedding_request(
        self, batch: list[str], batch_num: int
    ) -> list[list[float]]:
        """Execute the actual embedding request (used by retry logic).

        Args:
            batch: List of content strings to embed
            batch_num: Batch number for logging

        Returns:
            List of embedding vectors
        """
        try:
            if self.use_openai and self.client is not None:
                logger.debug(
                    "Getting batch embeddings from OpenAI",
                    model=self.model,
                    batch_num=batch_num,
                )

                # Use shorter timeout for initial attempts, let retry logic handle failures
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.embeddings.create, model=self.model, input=batch
                    ),
                    timeout=45.0,  # Reduced from 90s for faster failure detection
                )
                batch_embeddings = [embedding.embedding for embedding in response.data]

            else:
                # Local service request
                logger.debug(
                    "Getting batch embeddings from local service",
                    model=self.model,
                    endpoint=self.endpoint,
                    batch_num=batch_num,
                )

                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        requests.post,
                        f"{self.endpoint}/embeddings",
                        json={"input": batch, "model": self.model},
                        headers={"Content-Type": "application/json"},
                        timeout=30,  # Reduced timeout for faster failure detection
                    ),
                    timeout=45.0,  # Reduced from 90s
                )
                response.raise_for_status()
                data = response.json()
                if "data" not in data or not data["data"]:
                    raise ValueError(
                        "Invalid response format from local embedding service"
                    )
                batch_embeddings = [item["embedding"] for item in data["data"]]

            logger.debug(
                "Completed batch processing",
                batch_num=batch_num,
                processed_embeddings=len(batch_embeddings),
            )

            return batch_embeddings

        except Exception as e:
            logger.debug(
                "Embedding request failed",
                batch_num=batch_num,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise  # Let the retry logic handle it

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for a single text."""
        # Validate input
        if not text or not isinstance(text, str) or not text.strip():
            logger.warning(f"Invalid text for embedding: {repr(text)}")
            raise ValueError(
                "Invalid text for embedding: text must be a non-empty string"
            )

        clean_text = text.strip()

        # Use retry logic for network resilience
        return await self._retry_with_backoff(
            self._execute_single_embedding_request, "single embedding", text=clean_text
        )

    async def _execute_single_embedding_request(self, text: str) -> list[float]:
        """Execute a single embedding request (used by retry logic).

        Args:
            text: The text to embed

        Returns:
            The embedding vector
        """
        try:
            await self._apply_rate_limit()
            if self.use_openai and self.client is not None:
                logger.debug("Getting embedding from OpenAI", model=self.model)
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.embeddings.create,
                        model=self.model,
                        input=[text],  # OpenAI API expects a list
                    ),
                    timeout=30.0,  # Reduced timeout for faster failure detection
                )
                return response.data[0].embedding
            else:
                # Local service request
                logger.debug(
                    "Getting embedding from local service",
                    model=self.model,
                    endpoint=self.endpoint,
                )
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        requests.post,
                        f"{self.endpoint}/embeddings",
                        json={"input": text, "model": self.model},
                        headers={"Content-Type": "application/json"},
                        timeout=15,  # Reduced timeout
                    ),
                    timeout=30.0,  # Reduced timeout
                )
                response.raise_for_status()
                data = response.json()
                if "data" not in data or not data["data"]:
                    raise ValueError(
                        "Invalid response format from local embedding service"
                    )
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.debug(
                "Single embedding request failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise  # Let the retry logic handle it

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
