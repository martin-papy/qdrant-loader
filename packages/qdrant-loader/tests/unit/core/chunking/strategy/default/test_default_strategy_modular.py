"""Tests for the modernized DefaultChunkingStrategy using modular architecture."""

import pytest
from unittest.mock import Mock, patch

from qdrant_loader.core.chunking.strategy.default_strategy import DefaultChunkingStrategy
from qdrant_loader.core.document import Document
from qdrant_loader.config import Settings


class TestDefaultChunkingStrategyModular:
    """Test the modernized DefaultChunkingStrategy class."""

    @pytest.fixture
    def settings(self):
        """Create comprehensive mock settings for testing."""
        settings = Mock(spec=Settings)
        
        # Global config
        settings.global_config = Mock()
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 1500
        settings.global_config.chunking.chunk_overlap = 200
        settings.global_config.chunking.max_chunks_per_document = 500
        settings.global_config.chunking.strategies = Mock()
        settings.global_config.chunking.strategies.default = Mock()
        settings.global_config.chunking.strategies.default.min_chunk_size = 100
        settings.global_config.chunking.strategies.default.enable_semantic_analysis = True
        settings.global_config.chunking.strategies.default.enable_entity_extraction = True
        
        # Semantic analysis config
        settings.global_config.semantic_analysis = Mock()
        settings.global_config.semantic_analysis.enabled = True
        settings.global_config.semantic_analysis.spacy_model = "en_core_web_sm"
        settings.global_config.semantic_analysis.topic_modeling = Mock()
        settings.global_config.semantic_analysis.topic_modeling.enabled = True
        settings.global_config.semantic_analysis.topic_modeling.algorithm = "lda"
        settings.global_config.semantic_analysis.topic_modeling.n_topics = 5
        
        # Embedding config  
        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = "cl100k_base"
        
        return settings

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            title="Test Document",
            content_type="text",
            content="This is a sample document for testing. It has multiple sentences and paragraphs.\n\nThis is the second paragraph with more content for chunking.",
            metadata={"file_name": "test.txt"},
            source="test.txt",
            source_type="file",
            url="file:///test.txt"
        )

    @pytest.fixture
    def strategy(self, settings):
        """Create a DefaultChunkingStrategy instance with mocked dependencies."""
        with patch('qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor'):
            return DefaultChunkingStrategy(settings)

    def test_initialization_with_modular_components(self, settings):
        """Test that the strategy initializes with all modular components."""
        with patch('qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor'):
            strategy = DefaultChunkingStrategy(settings)
        
        # Check that all modular components are initialized
        assert hasattr(strategy, 'document_parser')
        assert hasattr(strategy, 'section_splitter')
        assert hasattr(strategy, 'metadata_extractor')
        assert hasattr(strategy, 'chunk_processor')
        assert hasattr(strategy, 'progress_tracker')
        
        # Check component types
        from qdrant_loader.core.chunking.strategy.default import (
            TextDocumentParser,
            TextSectionSplitter,
            TextMetadataExtractor,
            TextChunkProcessor
        )
        
        assert isinstance(strategy.document_parser, TextDocumentParser)
        assert isinstance(strategy.section_splitter, TextSectionSplitter)
        assert isinstance(strategy.metadata_extractor, TextMetadataExtractor)
        assert isinstance(strategy.chunk_processor, TextChunkProcessor)

    def test_initialization_logging(self, settings):
        """Test that initialization logs correctly."""
        with patch('qdrant_loader.core.chunking.strategy.default_strategy.logger') as mock_logger, \
             patch('qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor'):
            strategy = DefaultChunkingStrategy(settings)
            
            # Verify that info log was called with modular architecture message
            mock_logger.info.assert_called()
            args, kwargs = mock_logger.info.call_args
            assert "modular architecture" in args[0]

    def test_chunk_document_basic_functionality(self, strategy, sample_document):
        """Test basic chunk_document functionality."""
        # Mock the modular components
        strategy.document_parser.parse_document_structure = Mock(return_value={
            "paragraph_count": 2,
            "sentence_count": 3,
            "structure_type": "plain_text"
        })
        
        strategy.section_splitter.split_sections = Mock(return_value=[
            {
                "content": "This is a sample document for testing. It has multiple sentences and paragraphs.",
                "section_type": "paragraph",
                "word_count": 12
            },
            {
                "content": "This is the second paragraph with more content for chunking.",
                "section_type": "paragraph", 
                "word_count": 10
            }
        ])
        
        strategy.metadata_extractor.extract_hierarchical_metadata = Mock(side_effect=lambda content, meta, doc: {
            **meta,
            "enhanced_metadata": True,
            "word_count": len(content.split()),
            "content_type": "text"
        })
        
        strategy.chunk_processor.estimate_chunk_count = Mock(return_value=2)
        strategy.chunk_processor.should_skip_semantic_analysis = Mock(return_value=False)
        strategy.chunk_processor.create_chunk_document = Mock(side_effect=lambda **kwargs: Document(
            title=f"Chunk {kwargs['chunk_index']}",
            content_type="text_chunk",
            content=kwargs['chunk_content'],
            metadata=kwargs['chunk_metadata'],
            source=kwargs['original_doc'].source,
            source_type="chunk",
            url=f"chunk://{kwargs['chunk_index']}"
        ))
        
        # Test chunking
        result = strategy.chunk_document(sample_document)
        
        # Verify results
        assert len(result) == 2
        assert all(isinstance(doc, Document) for doc in result)
        
        # Verify component calls
        strategy.document_parser.parse_document_structure.assert_called_once()
        strategy.section_splitter.split_sections.assert_called_once()
        assert strategy.metadata_extractor.extract_hierarchical_metadata.call_count == 2
        assert strategy.chunk_processor.create_chunk_document.call_count == 2

    def test_chunk_document_empty_content(self, strategy):
        """Test chunking with empty content."""
        empty_doc = Document(
            title="Empty Document",
            content_type="text",
            content="",
            metadata={},
            source="empty.txt",
            source_type="file",
            url="file:///empty.txt"
        )
        
        # Mock section splitter to return empty chunks
        strategy.section_splitter.split_sections = Mock(return_value=[])
        
        result = strategy.chunk_document(empty_doc)
        
        assert result == []


        
        # Should have called section splitter
        strategy.section_splitter.split_sections.assert_called_once()

    def test_shutdown_method(self, strategy):
        """Test the shutdown method."""
        # Mock chunk processor with shutdown method
        strategy.chunk_processor.shutdown = Mock()
        
        strategy.shutdown()
        
        # Verify chunk processor shutdown was called
        strategy.chunk_processor.shutdown.assert_called_once()

    def test_shutdown_method_handles_missing_components(self, settings):
        """Test shutdown method handles missing components gracefully."""
        with patch('qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor'):
            strategy = DefaultChunkingStrategy(settings)
            
            # Remove chunk_processor to simulate initialization failure
            delattr(strategy, 'chunk_processor')
            
            # Should not raise exception and should handle missing components gracefully
            try:
                strategy.shutdown()
                success = True
            except Exception:
                success = False
            
            assert success, "shutdown() should handle missing components gracefully" 