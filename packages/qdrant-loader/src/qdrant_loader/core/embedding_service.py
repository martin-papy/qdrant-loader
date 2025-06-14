import logging


class EmbeddingService:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for a single text.

        Args:
            text: The text to get embedding for

        Returns:
            List of floats representing the embedding vector
        """
        self.logger.debug(
            "Getting embedding for text",
            extra={"text_length": len(text), "model": self.model_name},
        )

        try:
            # Get embedding from OpenAI
            response = await self.client.embeddings.create(
                model=self.model_name, input=text
            )

            embedding = response.data[0].embedding
            self.logger.debug(
                "Successfully generated embedding",
                extra={"text_length": len(text), "embedding_size": len(embedding)},
            )
            return embedding
        except Exception as e:
            self.logger.error(
                f"Error generating embedding: {str(e)}",
                extra={
                    "text_length": len(text),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts.

        Args:
            texts: List of texts to get embeddings for

        Returns:
            List of embedding vectors
        """
        self.logger.debug(
            "Getting embeddings for texts",
            extra={"text_count": len(texts), "model": self.model_name},
        )

        try:
            # Get embeddings from OpenAI
            response = await self.client.embeddings.create(
                model=self.model_name, input=texts
            )

            embeddings = [data.embedding for data in response.data]
            self.logger.debug(
                "Successfully generated embeddings",
                extra={
                    "text_count": len(texts),
                    "embedding_count": len(embeddings),
                    "embedding_size": len(embeddings[0]) if embeddings else 0,
                },
            )
            return embeddings
        except Exception as e:
            self.logger.error(
                f"Error generating embeddings: {str(e)}",
                extra={
                    "text_count": len(texts),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
