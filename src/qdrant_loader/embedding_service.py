import time
from openai import OpenAI
import tiktoken
import structlog
from typing import List, Optional
from qdrant_loader.config import Settings

logger = structlog.get_logger()

class EmbeddingService:
    """Service for generating embeddings using OpenAI's API."""
    
    def __init__(self, settings: Settings):
        """Initialize the embedding service.
        
        Args:
            settings: The application settings containing OpenAI API key.
        """
        self.settings = settings
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.global_config.embedding.model
        self.encoding = tiktoken.encoding_for_model(self.model)
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

    def _apply_rate_limit(self):
        """Apply rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        try:
            self._apply_rate_limit()
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]  # OpenAI API expects a list
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to get embedding", error=str(e))
            raise

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        try:
            self._apply_rate_limit()
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error("Failed to get embeddings", error=str(e))
            raise

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self.encoding.encode(text))

    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """Count the number of tokens in a list of text strings."""
        return [self.count_tokens(text) for text in texts]

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        # For OpenAI's text-embedding-3-small model, the dimension is 1536
        return 1536 