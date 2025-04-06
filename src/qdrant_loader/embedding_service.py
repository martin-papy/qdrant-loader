from openai import OpenAI
import tiktoken
import structlog
from typing import List, Optional
from qdrant_loader.config import Settings, get_global_config

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
        self.model = get_global_config().embedding.model
        self.encoding = tiktoken.encoding_for_model(self.model)

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text string."""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]  # Wrap single text in a list
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to get embedding", error=str(e))
            raise

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of text strings."""
        try:
            # Clean and format the input texts
            formatted_texts = []
            for text in texts:
                # Convert to string and clean
                cleaned_text = str(text).strip()
                # Skip empty strings
                if cleaned_text:
                    formatted_texts.append(cleaned_text)
                
            if not formatted_texts:
                logger.warning("No valid texts to embed after cleaning")
                return []
            
            # Split into batches to avoid token limits
            batch_size = get_global_config().embedding.batch_size
            batches = [formatted_texts[i:i + batch_size] for i in range(0, len(formatted_texts), batch_size)]
            
            all_embeddings = []
            for batch in batches:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch  # Pass the batch directly as a list
                )
                all_embeddings.extend([item.embedding for item in response.data])
            
            return all_embeddings
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