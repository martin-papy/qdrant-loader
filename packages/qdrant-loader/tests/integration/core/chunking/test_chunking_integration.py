"""Tests for chunking service integration with file conversion."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import GlobalConfig, Settings
from qdrant_loader.core.chunking.chunking_service import ChunkingService
from qdrant_loader.core.chunking.strategy import MarkdownChunkingStrategy
from qdrant_loader.core.document import Document


class TestChunkingIntegration:
    """Test chunking service integration with file conversion."""

    @pytest.fixture
    def mock_global_config(self):
        """Create mock global configuration."""
        config = Mock(spec=GlobalConfig)
        config.chunking = Mock()
        config.chunking.chunk_size = 1000
        config.chunking.chunk_overlap = 100
        config.chunking.max_chunks_per_document = 500
        return config

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = None
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 1000
        settings.global_config.chunking.chunk_overlap = 100
        settings.global_config.chunking.max_chunks_per_document = 500
        
        # Add strategy-specific configurations
        settings.global_config.chunking.strategies = Mock()
        settings.global_config.chunking.strategies.markdown = Mock()
        settings.global_config.chunking.strategies.markdown.min_content_length_for_nlp = 100
        settings.global_config.chunking.strategies.markdown.min_word_count_for_nlp = 20
        settings.global_config.chunking.strategies.markdown.min_line_count_for_nlp = 3
        settings.global_config.chunking.strategies.markdown.min_section_size = 500
        settings.global_config.chunking.strategies.markdown.max_chunks_per_section = 1000
        settings.global_config.chunking.strategies.markdown.max_overlap_percentage = 0.25
        settings.global_config.chunking.strategies.markdown.max_workers = 4
        settings.global_config.chunking.strategies.markdown.estimation_buffer = 0.2
        settings.global_config.chunking.strategies.markdown.words_per_minute_reading = 200
        settings.global_config.chunking.strategies.markdown.header_analysis_threshold_h1 = 3
        settings.global_config.chunking.strategies.markdown.header_analysis_threshold_h3 = 8
        settings.global_config.chunking.strategies.markdown.enable_hierarchical_metadata = True
        
        settings.global_config.semantic_analysis = Mock()
        settings.global_config.semantic_analysis.spacy_model = "en_core_web_sm"
        settings.global_config.semantic_analysis.num_topics = 3
        settings.global_config.semantic_analysis.lda_passes = 10
        return settings

    @pytest.fixture
    def chunking_service(self, mock_global_config, mock_settings):
        """Create a chunking service instance."""
        with (
            patch("qdrant_loader.core.chunking.chunking_service.Path") as mock_path,
            patch("qdrant_loader.core.chunking.chunking_service.IngestionMonitor"),
            patch("qdrant_loader.core.chunking.chunking_service.LoggingConfig"),
            patch("spacy.load") as mock_spacy_load,
        ):
            # Setup Path mocks
            mock_cwd_path = Mock()
            mock_metrics_dir = Mock()
            mock_cwd_path.__truediv__ = Mock(return_value=mock_metrics_dir)
            mock_path.cwd.return_value = mock_cwd_path
            mock_metrics_dir.absolute.return_value = "/test/metrics"
            
            # Setup spacy mock
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            mock_spacy_load.return_value = mock_nlp
            
            return ChunkingService(mock_global_config, mock_settings)

    def test_converted_file_uses_markdown_strategy(self, chunking_service):
        """Test that converted files use markdown chunking strategy."""
        # Create a document that was converted with MarkItDown
        document = Document(
            title="Converted PDF Document",
            content="# Document Title\n\nThis is converted content from a PDF file.",
            content_type="md",  # Converted files have markdown content type
            metadata={
                "conversion_method": "markitdown",
                "original_file_type": "pdf",
                "original_filename": "document.pdf",
                "file_size": 1024,
            },
            source_type="git",
            source="test-repo",
            url="https://example.com/document.pdf",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Get the strategy for this document
        strategy = chunking_service._get_strategy(document)

        # Should use markdown strategy for converted files
        assert isinstance(strategy, MarkdownChunkingStrategy)

    def test_fallback_converted_file_uses_markdown_strategy(self, chunking_service):
        """Test that fallback converted files use markdown chunking strategy."""
        # Create a document that failed conversion but has fallback content
        document = Document(
            title="Failed Conversion Document",
            content="# document.xlsx\n\nFile type: xlsx\nSize: 2048 bytes\nConversion failed: Unsupported format",
            content_type="md",  # Fallback documents are also markdown
            metadata={
                "conversion_method": "markitdown_fallback",
                "original_file_type": "xlsx",
                "original_filename": "document.xlsx",
                "file_size": 2048,
                "conversion_failed": True,
                "conversion_error": "Unsupported format",
            },
            source_type="localfile",
            source="test-files",
            url="file:///path/to/document.xlsx",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Get the strategy for this document
        strategy = chunking_service._get_strategy(document)

        # Should use markdown strategy for fallback documents
        assert isinstance(strategy, MarkdownChunkingStrategy)

    def test_attachment_document_uses_markdown_strategy(self, chunking_service):
        """Test that attachment documents use markdown chunking strategy."""
        # Create an attachment document that was converted
        document = Document(
            title="Attachment: presentation.pptx",
            content="# Presentation Title\n\n## Slide 1\n\nContent from PowerPoint slide.",
            content_type="md",  # Converted attachments have markdown content type
            metadata={
                "conversion_method": "markitdown",
                "original_file_type": "pptx",
                "original_filename": "presentation.pptx",
                "file_size": 5120,
                "is_attachment": True,
                "parent_document_id": "parent-doc-123",
                "attachment_id": "att-456",
            },
            source_type="confluence",
            source="test-space",
            url="https://confluence.example.com/pages/123#attachment-456",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Get the strategy for this document
        strategy = chunking_service._get_strategy(document)

        # Should use markdown strategy for converted attachments
        assert isinstance(strategy, MarkdownChunkingStrategy)

    def test_regular_markdown_file_uses_markdown_strategy(self, chunking_service):
        """Test that regular markdown files still use markdown strategy."""
        # Create a regular markdown document (not converted)
        document = Document(
            title="Regular Markdown File",
            content="# Regular Markdown\n\nThis is a regular markdown file.",
            content_type="md",
            metadata={
                # No conversion metadata
            },
            source_type="git",
            source="test-repo",
            url="https://example.com/README.md",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Get the strategy for this document
        strategy = chunking_service._get_strategy(document)

        # Should still use markdown strategy for regular markdown files
        assert isinstance(strategy, MarkdownChunkingStrategy)

    def test_chunk_converted_document(self, chunking_service):
        """Test that converted documents are chunked correctly."""
        # Create a larger converted document with enough content for multiple chunks
        content = """# Converted Document

## Section 1
This is the first section of a converted document. It contains multiple paragraphs and should be chunked appropriately. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

## Section 2
This is the second section with more content that will help test the chunking behavior. Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.

## Section 3
Final section to ensure we have enough content for multiple chunks. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur.

## Section 4
Additional content to ensure we definitely exceed the chunk size limit. At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga.

## Section 5
Even more content to guarantee multiple chunks. Et harum quidem rerum facilis est et expedita distinctio. Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil impedit quo minus id quod maxime placeat facere possimus, omnis voluptas assumenda est, omnis dolor repellendus. Temporibus autem quibusdam et aut officiis debitis aut rerum necessitatibus saepe eveniet ut et voluptates repudiandae sint et molestiae non recusandae.
"""

        document = Document(
            title="Large Converted Document",
            content=content,
            content_type="md",
            metadata={
                "conversion_method": "markitdown",
                "original_file_type": "docx",
                "original_filename": "large_document.docx",
                "file_size": 10240,
            },
            source_type="confluence",
            source="test-space",
            url="https://confluence.example.com/attachment/large_document.docx",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Chunk the document
        chunks = chunking_service.chunk_document(document)

        # Should have at least one chunk (may be multiple depending on content size)
        assert len(chunks) >= 1

        # All chunks should preserve conversion metadata
        for chunk in chunks:
            assert chunk.metadata.get("conversion_method") == "markitdown"
            assert chunk.metadata.get("original_file_type") == "docx"
            assert chunk.metadata.get("original_filename") == "large_document.docx"
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata

        # First chunk should contain the title
        assert "# Converted Document" in chunks[0].content

        # Log the actual chunk count for debugging
        print(f"Document content length: {len(content)} characters")
        print(f"Number of chunks created: {len(chunks)}")
        if len(chunks) > 1:
            print("✅ Multiple chunks created as expected")
        else:
            print("ℹ️ Single chunk created (content may be smaller than chunk size)")
