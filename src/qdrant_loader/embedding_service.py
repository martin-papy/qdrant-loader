from openai import OpenAI
import tiktoken
import structlog
from typing import List, Optional
from .config import Settings, get_settings

logger = structlog.get_logger()

class EmbeddingService:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        if not self.settings:
            raise ValueError("Settings must be provided either through environment or constructor")
        
        # Set model first
        self.model = self.settings.OPENAI_MODEL
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
        except Exception as e:
            logger.error("Failed to initialize OpenAI client", error=str(e))
            raise
        
        # Initialize tokenizer after OpenAI client
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except Exception as e:
            logger.error("Failed to initialize tokenizer", error=str(e))
            raise

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text string."""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to get embedding", error=str(e))
            raise

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of text strings."""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
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