"""Unit tests for the provider-based embedding service."""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.document import Document
from qdrant_loader.core.embedding.embedding_service import EmbeddingService


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    # Create mock for global config
    global_config = MagicMock()

    # Create mock for embedding config
    embedding_config = MagicMock()
    embedding_config.endpoint = "https://api.openai.com/v1"
    embedding_config.model = "text-embedding-3-small"
    embedding_config.tokenizer = "cl100k_base"
    embedding_config.batch_size = 10
    embedding_config.vector_size = 1536
    embedding_config.max_tokens_per_request = 8000
    embedding_config.max_tokens_per_chunk = 8000
    embedding_config.api_key = "test-key"

    # Attach embedding config to global config
    global_config.embedding = embedding_config

    # Create main settings mock
    settings = MagicMock(spec=Settings)
    settings.global_config = global_config

    # Provide unified llm settings for provider (preferred path)
    settings.llm_settings = SimpleNamespace(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        models={"embeddings": "text-embedding-3-small"},
        tokenizer="cl100k_base",
        embeddings=SimpleNamespace(vector_size=1536),
    )

    return settings


def _fake_provider(vector_dim: int = 1536):
    class _Emb:
        async def embed(self, inputs):  # type: ignore[no-untyped-def]
            return [[0.1] * vector_dim for _ in inputs]

    class _Prov:
        def embeddings(self):
            return _Emb()

    return _Prov()


def test_init_provider(mock_settings):
    """Service initializes with core provider."""
    fake_provider = _fake_provider()

    def _fake_import(name):
        if name == "qdrant_loader_core.llm.factory":
            return SimpleNamespace(create_provider=lambda _: fake_provider)
        raise ImportError(name)

    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        side_effect=_fake_import,
    ) as imp:
        service = EmbeddingService(mock_settings)
        assert service.provider is fake_provider
        imp.assert_called()


def test_init_tokenizer_none():
    """Tokenizer 'none' disables encoding."""
    # settings with tokenizer none
    global_config = MagicMock()
    embedding_config = MagicMock()
    embedding_config.tokenizer = "none"
    global_config.embedding = embedding_config
    settings = MagicMock(spec=Settings)
    settings.global_config = global_config
    settings.llm_settings = SimpleNamespace(
        provider="openai_compat",
        base_url="http://localhost:11434/v1",
        api_key=None,
        models={"embeddings": "nomic-embed-text"},
        tokenizer="none",
        embeddings=SimpleNamespace(vector_size=768),
    )
    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        return_value=SimpleNamespace(create_provider=lambda _: _fake_provider(768)),
    ):
        service = EmbeddingService(settings)
        assert service.encoding is None


def test_init_tokenizer():
    """Test tokenizer initialization."""
    with patch("tiktoken.get_encoding") as mock_get_encoding:
        # Create proper mock settings structure
        global_config = MagicMock()
        embedding_config = MagicMock()
        embedding_config.tokenizer = "cl100k_base"
        global_config.embedding = embedding_config

        settings = MagicMock(spec=Settings)
        settings.global_config = global_config
        # Ensure llm_settings does not override tokenizer
        settings.llm_settings = SimpleNamespace(
            provider="openai_compat",
            base_url=None,
            api_key=None,
            models={},
            tokenizer=None,
            embeddings=SimpleNamespace(vector_size=None),
        )

        with patch(
            "qdrant_loader.core.embedding.embedding_service.import_module",
            return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
        ):
            EmbeddingService(settings)

        mock_get_encoding.assert_called_once_with("cl100k_base")


def test_init_tokenizer_fallback():
    """Test tokenizer initialization fallback on error."""
    with patch("tiktoken.get_encoding", side_effect=Exception("Test error")):
        # Create proper mock settings structure
        global_config = MagicMock()
        embedding_config = MagicMock()
        embedding_config.tokenizer = "invalid_tokenizer"
        global_config.embedding = embedding_config

        settings = MagicMock(spec=Settings)
        settings.global_config = global_config

        with patch(
            "qdrant_loader.core.embedding.embedding_service.import_module",
            return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
        ):
            service = EmbeddingService(settings)

        assert service.encoding is None


@pytest.mark.asyncio
async def test_get_embedding_provider(mock_settings):
    """Test getting single embedding via provider."""
    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
    ):
        service = EmbeddingService(mock_settings)
        embedding = await service.get_embedding("test text")
        assert len(embedding) == 1536


@pytest.mark.asyncio
async def test_get_embeddings_batch_provider(mock_settings):
    """Test batch embedding generation via provider."""
    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
    ):
        service = EmbeddingService(mock_settings)
        documents = [
            Document(
                title="Test 1",
                content="Test content 1",
                content_type="text/plain",
                source_type="test",
                source="test_source",
                url="http://test.com/1",
                metadata={},
            ),
            Document(
                title="Test 2",
                content="Test content 2",
                content_type="text/plain",
                source_type="test",
                source="test_source",
                url="http://test.com/2",
                metadata={},
            ),
        ]
        embeddings = await service.get_embeddings(documents)
        assert len(embeddings) == 2
        assert all(len(emb) == 1536 for emb in embeddings)


@pytest.mark.asyncio
async def test_get_embeddings_batch_provider(mock_settings):
    """Test batch embedding via provider returns expected shapes."""
    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
    ):
        service = EmbeddingService(mock_settings)
        documents = [
            Document(
                title="T1",
                content="A",
                content_type="text/plain",
                source_type="t",
                source="s",
                url="u1",
                metadata={},
            ),
            Document(
                title="T2",
                content="B",
                content_type="text/plain",
                source_type="t",
                source="s",
                url="u2",
                metadata={},
            ),
        ]
        res = await service.get_embeddings(documents)
        assert len(res) == 2
        assert all(len(v) == 1536 for v in res)


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting between requests."""
    # Create proper mock settings structure
    global_config = MagicMock()
    embedding_config = MagicMock()
    embedding_config.endpoint = "http://localhost:8000"
    global_config.embedding = embedding_config

    settings = MagicMock(spec=Settings)
    settings.global_config = global_config

    service = EmbeddingService(settings)

    start_time = asyncio.get_event_loop().time()
    await service._apply_rate_limit()
    await service._apply_rate_limit()
    end_time = asyncio.get_event_loop().time()

    assert end_time - start_time >= 0.5  # Minimum interval is 500ms


def test_count_tokens_with_tokenizer(mock_settings):
    """Test token counting with tiktoken."""
    with (
        patch("tiktoken.get_encoding") as mock_get_encoding,
        patch(
            "qdrant_loader.core.embedding.embedding_service.import_module",
            return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
        ),
    ):
        mock_encoding = MagicMock()
        mock_encoding.encode.return_value = [1, 2, 3]  # 3 tokens
        mock_get_encoding.return_value = mock_encoding

        service = EmbeddingService(mock_settings)
        count = service.count_tokens("test text")

        # Our mock encode returns [1,2,3]; but service wraps tiktoken.encode length directly
        assert count == 3
        mock_encoding.encode.assert_called_once()


def test_count_tokens_fallback():
    """Test token counting fallback to character count."""
    # Tokenizer none was already tested above
    global_config = MagicMock()
    embedding_config = MagicMock()
    embedding_config.tokenizer = "none"
    global_config.embedding = embedding_config
    settings = MagicMock(spec=Settings)
    settings.global_config = global_config
    settings.llm_settings = SimpleNamespace(
        provider="openai_compat",
        base_url="http://localhost:11434/v1",
        api_key=None,
        models={"embeddings": "nomic-embed-text"},
        tokenizer="none",
        embeddings=SimpleNamespace(vector_size=768),
    )
    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        return_value=SimpleNamespace(create_provider=lambda _: _fake_provider(768)),
    ):
        service = EmbeddingService(settings)
    count = service.count_tokens("test")

    assert count == 4  # Length of "test"


def test_count_tokens_batch(mock_settings):
    """Test batch token counting."""
    with (
        patch("tiktoken.get_encoding") as mock_get_encoding,
        patch(
            "qdrant_loader.core.embedding.embedding_service.import_module",
            return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
        ),
    ):
        mock_encoding = MagicMock()
        mock_encoding.encode.side_effect = lambda x: [1] * len(x)
        mock_get_encoding.return_value = mock_encoding

        service = EmbeddingService(mock_settings)
        counts = service.count_tokens_batch(["test", "longer text"])

        # With mock encode returning [1]*len(text), lengths equal string lengths
        assert counts == [4, 11]


def test_get_embedding_dimension(mock_settings):
    """Test getting embedding dimension."""
    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        return_value=SimpleNamespace(create_provider=lambda _: _fake_provider()),
    ):
        service = EmbeddingService(mock_settings)
    dimension = service.get_embedding_dimension()

    assert dimension == 1536


@pytest.mark.asyncio
async def test_provider_error_propagates(mock_settings):
    """Provider exceptions bubble up through retry logic."""

    class _BadEmb:
        async def embed(self, inputs):  # type: ignore[no-untyped-def]
            raise RuntimeError("provider failure")

    class _BadProv:
        def embeddings(self):
            return _BadEmb()

    with patch(
        "qdrant_loader.core.embedding.embedding_service.import_module",
        return_value=SimpleNamespace(create_provider=lambda _: _BadProv()),
    ):
        service = EmbeddingService(mock_settings)
        with pytest.raises(RuntimeError, match="provider failure"):
            await service.get_embedding("test text")
