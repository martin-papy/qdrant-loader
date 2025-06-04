"""Tests for the embedding_service module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from qdrant_loader.core.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Test the EmbeddingService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.model_name = "text-embedding-ada-002"
        self.service = EmbeddingService(self.mock_client, self.model_name)

    def test_init(self):
        """Test EmbeddingService initialization."""
        assert self.service.client == self.mock_client
        assert self.service.model_name == self.model_name
        assert self.service.logger is not None

    @pytest.mark.asyncio
    async def test_get_embedding_success(self):
        """Test successful single embedding generation."""
        # Mock response
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = mock_embedding

        self.mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        text = "Test text for embedding"
        result = await self.service.get_embedding(text)

        # Verify client was called correctly
        self.mock_client.embeddings.create.assert_called_once_with(
            model=self.model_name, input=text
        )

        # Verify result
        assert result == mock_embedding
        assert isinstance(result, list)
        assert all(isinstance(x, (int, float)) for x in result)

    @pytest.mark.asyncio
    async def test_get_embedding_error(self):
        """Test error handling in single embedding generation."""
        # Mock client to raise exception
        self.mock_client.embeddings.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        text = "Test text for embedding"

        with pytest.raises(Exception, match="API Error"):
            await self.service.get_embedding(text)

        # Verify client was called
        self.mock_client.embeddings.create.assert_called_once_with(
            model=self.model_name, input=text
        )

    @pytest.mark.asyncio
    async def test_get_embedding_logging(self):
        """Test logging in single embedding generation."""
        # Mock response
        mock_embedding = [0.1, 0.2, 0.3]
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = mock_embedding

        self.mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch.object(self.service, "logger") as mock_logger:
            text = "Test text"
            await self.service.get_embedding(text)

            # Verify debug logging was called
            assert mock_logger.debug.call_count == 2

            # Check first debug call (getting embedding)
            first_call = mock_logger.debug.call_args_list[0]
            assert "Getting embedding for text" in first_call[0][0]
            assert first_call[1]["extra"]["text_length"] == len(text)
            assert first_call[1]["extra"]["model"] == self.model_name

            # Check second debug call (success)
            second_call = mock_logger.debug.call_args_list[1]
            assert "Successfully generated embedding" in second_call[0][0]
            assert second_call[1]["extra"]["embedding_size"] == len(mock_embedding)

    @pytest.mark.asyncio
    async def test_get_embedding_error_logging(self):
        """Test error logging in single embedding generation."""
        # Mock client to raise exception
        error_message = "API Rate Limit"
        self.mock_client.embeddings.create = AsyncMock(
            side_effect=ValueError(error_message)
        )

        with patch.object(self.service, "logger") as mock_logger:
            text = "Test text"

            with pytest.raises(ValueError):
                await self.service.get_embedding(text)

            # Verify error logging was called
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args

            assert error_message in error_call[0][0]
            assert error_call[1]["extra"]["text_length"] == len(text)
            assert error_call[1]["extra"]["error"] == error_message
            assert error_call[1]["extra"]["error_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_get_embeddings_success(self):
        """Test successful multiple embeddings generation."""
        # Mock response
        mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        mock_response = Mock()
        mock_response.data = []
        for embedding in mock_embeddings:
            mock_data = Mock()
            mock_data.embedding = embedding
            mock_response.data.append(mock_data)

        self.mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["Text 1", "Text 2", "Text 3"]
        result = await self.service.get_embeddings(texts)

        # Verify client was called correctly
        self.mock_client.embeddings.create.assert_called_once_with(
            model=self.model_name, input=texts
        )

        # Verify result
        assert result == mock_embeddings
        assert len(result) == len(texts)
        assert all(isinstance(embedding, list) for embedding in result)

    @pytest.mark.asyncio
    async def test_get_embeddings_empty_list(self):
        """Test multiple embeddings generation with empty input."""
        # Mock response for empty input
        mock_response = Mock()
        mock_response.data = []

        self.mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = []
        result = await self.service.get_embeddings(texts)

        # Verify client was called correctly
        self.mock_client.embeddings.create.assert_called_once_with(
            model=self.model_name, input=texts
        )

        # Verify result
        assert result == []

    @pytest.mark.asyncio
    async def test_get_embeddings_error(self):
        """Test error handling in multiple embeddings generation."""
        # Mock client to raise exception
        self.mock_client.embeddings.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        texts = ["Text 1", "Text 2"]

        with pytest.raises(Exception, match="API Error"):
            await self.service.get_embeddings(texts)

        # Verify client was called
        self.mock_client.embeddings.create.assert_called_once_with(
            model=self.model_name, input=texts
        )

    @pytest.mark.asyncio
    async def test_get_embeddings_logging(self):
        """Test logging in multiple embeddings generation."""
        # Mock response
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        mock_response = Mock()
        mock_response.data = []
        for embedding in mock_embeddings:
            mock_data = Mock()
            mock_data.embedding = embedding
            mock_response.data.append(mock_data)

        self.mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch.object(self.service, "logger") as mock_logger:
            texts = ["Text 1", "Text 2"]
            await self.service.get_embeddings(texts)

            # Verify debug logging was called
            assert mock_logger.debug.call_count == 2

            # Check first debug call (getting embeddings)
            first_call = mock_logger.debug.call_args_list[0]
            assert "Getting embeddings for texts" in first_call[0][0]
            assert first_call[1]["extra"]["text_count"] == len(texts)
            assert first_call[1]["extra"]["model"] == self.model_name

            # Check second debug call (success)
            second_call = mock_logger.debug.call_args_list[1]
            assert "Successfully generated embeddings" in second_call[0][0]
            assert second_call[1]["extra"]["embedding_count"] == len(mock_embeddings)
            assert second_call[1]["extra"]["embedding_size"] == len(mock_embeddings[0])

    @pytest.mark.asyncio
    async def test_get_embeddings_error_logging(self):
        """Test error logging in multiple embeddings generation."""
        # Mock client to raise exception
        error_message = "Connection timeout"
        self.mock_client.embeddings.create = AsyncMock(
            side_effect=ConnectionError(error_message)
        )

        with patch.object(self.service, "logger") as mock_logger:
            texts = ["Text 1", "Text 2"]

            with pytest.raises(ConnectionError):
                await self.service.get_embeddings(texts)

            # Verify error logging was called
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args

            assert error_message in error_call[0][0]
            assert error_call[1]["extra"]["text_count"] == len(texts)
            assert error_call[1]["extra"]["error"] == error_message
            assert error_call[1]["extra"]["error_type"] == "ConnectionError"

    @pytest.mark.asyncio
    async def test_get_embeddings_single_text(self):
        """Test multiple embeddings generation with single text."""
        # Mock response
        mock_embedding = [0.1, 0.2, 0.3]
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = mock_embedding

        self.mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["Single text"]
        result = await self.service.get_embeddings(texts)

        # Verify result
        assert result == [mock_embedding]
        assert len(result) == 1

    def test_logger_initialization(self):
        """Test that logger is properly initialized."""
        service = EmbeddingService(Mock(), "test-model")
        assert service.logger is not None
        assert service.logger.name == "qdrant_loader.core.embedding_service"

    @pytest.mark.asyncio
    async def test_different_model_names(self):
        """Test service with different model names."""
        models = ["text-embedding-ada-002", "text-embedding-3-small", "custom-model"]

        for model in models:
            service = EmbeddingService(Mock(), model)
            assert service.model_name == model

            # Mock successful response
            mock_response = Mock()
            mock_response.data = [Mock()]
            mock_response.data[0].embedding = [0.1, 0.2]
            service.client.embeddings.create = AsyncMock(return_value=mock_response)

            await service.get_embedding("test")

            # Verify correct model was used
            service.client.embeddings.create.assert_called_with(
                model=model, input="test"
            )
