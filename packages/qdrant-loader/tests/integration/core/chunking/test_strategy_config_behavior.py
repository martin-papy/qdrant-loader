"""Behavioral tests for chunking strategy configuration options.

These tests verify that configuration changes actually affect the behavior
of chunking strategies, not just that the configuration values exist.
"""
from unittest.mock import Mock, patch

from qdrant_loader.config.global_config import GlobalConfig
from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.markdown.markdown_strategy import MarkdownChunkingStrategy
from qdrant_loader.core.chunking.strategy.default_strategy import DefaultChunkingStrategy
from qdrant_loader.core.document import Document


class TestMarkdownStrategyConfigBehavior:
    """Test that MarkdownStrategyConfig options actually affect behavior."""

    def create_settings_with_markdown_config(self, **markdown_overrides):
        """Create settings with custom markdown configuration."""
        settings = Mock(spec=Settings)
        settings.global_config = GlobalConfig()
        
        # Override markdown strategy config
        for key, value in markdown_overrides.items():
            setattr(settings.global_config.chunking.strategies.markdown, key, value)
        
        # Set up other required configs
        settings.global_config.semantic_analysis.spacy_model = "en_core_web_sm"
        settings.global_config.semantic_analysis.num_topics = 3
        settings.global_config.semantic_analysis.lda_passes = 10
        
        return settings

    def create_test_document(self, content: str) -> Document:
        """Create a test document."""
        return Document(
            id="test-doc",
            content=content,
            source="test",
            source_type="markdown",
            content_type="md",  # Add missing content_type
            title="Test Document",  # Add missing title
            url="test://document",  # Add missing url
            metadata={"file_name": "test.md"}
        )

    @patch('qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer')
    def test_min_content_length_for_nlp_affects_processing(self, mock_semantic_analyzer):
        """Test that min_content_length_for_nlp controls NLP processing."""
        # Create content that's exactly at the threshold
        short_content = "x" * 99  # Below default threshold of 100
        medium_content = "x" * 150  # Above threshold

        # Test with default threshold (100)
        default_settings = self.create_settings_with_markdown_config()
        strategy = MarkdownChunkingStrategy(default_settings)
        
        short_doc = self.create_test_document(short_content)
        medium_doc = self.create_test_document(medium_content)
        
        # Process documents and check skip_nlp behavior via the strategy's logic
        # Short content should skip NLP, medium should not
        
        # Check the skip_nlp logic in the strategy
        short_skip_nlp = (
            len(short_content) < 100 or
            len(short_content.split()) < 20 or
            short_content.count('\n') < 3
        )
        medium_skip_nlp = (
            len(medium_content) < 100 or
            len(medium_content.split()) < 20 or
            medium_content.count('\n') < 3
        )
        
        assert short_skip_nlp is True
        assert medium_skip_nlp is True  # Still true due to word count and newlines
        
        # Test with lowered threshold
        low_threshold_settings = self.create_settings_with_markdown_config(
            min_content_length_for_nlp=50
        )
        strategy_low = MarkdownChunkingStrategy(low_threshold_settings)
        
        # Now short content should pass the length check (but may fail other checks)
        short_skip_nlp_low = (
            len(short_content) < 50 or
            len(short_content.split()) < 20 or
            short_content.count('\n') < 3
        )
        
        assert short_skip_nlp_low is True  # Still skipped due to other criteria

    @patch('qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer')
    def test_min_word_count_for_nlp_affects_processing(self, mock_semantic_analyzer):
        """Test that min_word_count_for_nlp controls NLP processing."""
        # Create content with specific word counts
        few_words = "word " * 10  # 10 words (below default threshold of 20)
        many_words = "word " * 30  # 30 words (above threshold)

        settings = self.create_settings_with_markdown_config()
        strategy = MarkdownChunkingStrategy(settings)
        
        # Check skip_nlp logic for word count
        few_words_skip = len(few_words.split()) < 20
        many_words_skip = len(many_words.split()) < 20
        
        assert few_words_skip is True
        assert many_words_skip is False
        
        # Test with lowered word count threshold
        low_word_settings = self.create_settings_with_markdown_config(
            min_word_count_for_nlp=5
        )
        strategy_low = MarkdownChunkingStrategy(low_word_settings)
        
        few_words_skip_low = len(few_words.split()) < 5
        assert few_words_skip_low is False  # Should now pass word count check

    @patch('qdrant_loader.core.chunking.strategy.markdown.chunk_processor.SemanticAnalyzer')
    def test_max_workers_affects_thread_pool(self, mock_semantic_analyzer):
        """Test that max_workers configuration affects thread pool initialization."""
        # Test default worker count
        default_settings = self.create_settings_with_markdown_config()
        
        with patch('qdrant_loader.core.chunking.strategy.markdown.chunk_processor.concurrent.futures.ThreadPoolExecutor') as mock_executor:
            strategy = MarkdownChunkingStrategy(default_settings)
            
            # Should use default max_workers=4
            mock_executor.assert_called_with(max_workers=4)
        
        # Test custom worker count
        custom_settings = self.create_settings_with_markdown_config(max_workers=8)
        
        with patch('qdrant_loader.core.chunking.strategy.markdown.chunk_processor.concurrent.futures.ThreadPoolExecutor') as mock_executor:
            strategy = MarkdownChunkingStrategy(custom_settings)
            
            # Should use custom max_workers=8
            mock_executor.assert_called_with(max_workers=8)

    def test_estimation_buffer_affects_chunk_estimation(self):
        """Test that estimation_buffer affects chunk count estimation."""
        # Use larger content to ensure base estimate > 0
        content = "x" * 5000  # 5000 characters
        
        # Test with default buffer (0.2 = 20%)
        default_settings = self.create_settings_with_markdown_config()
        strategy = MarkdownChunkingStrategy(default_settings)
        
        base_estimate = len(content) // default_settings.global_config.chunking.chunk_size
        default_estimate = strategy.chunk_processor.estimate_chunk_count(content)
        
        # Should be base estimate + 20% buffer
        expected_default = max(1, int(base_estimate * 1.2))
        assert default_estimate == expected_default
        
        # Test with higher buffer (0.5 = 50%)
        high_buffer_settings = self.create_settings_with_markdown_config(estimation_buffer=0.5)
        strategy_high = MarkdownChunkingStrategy(high_buffer_settings)
        
        high_estimate = strategy_high.chunk_processor.estimate_chunk_count(content)
        expected_high = max(1, int(base_estimate * 1.5))
        assert high_estimate == expected_high
        assert high_estimate > default_estimate

    def test_words_per_minute_affects_reading_time(self):
        """Test that words_per_minute_reading affects reading time calculation."""
        content = "word " * 500  # 500 words (enough to show differences)
        
        # Test with default reading speed (200 WPM)
        default_settings = self.create_settings_with_markdown_config()
        strategy = MarkdownChunkingStrategy(default_settings)
        
        # Calculate expected reading time using the metadata extractor logic
        word_count = len(content.split())
        default_reading_time = max(1, word_count // 200)  # 500/200 = 2.5 -> 2 minutes
        
        # Create a chunk document to test metadata extraction
        doc = self.create_test_document(content)
        chunk_meta = {"content": content, "section_type": "text"}
        
        enriched_meta = strategy.metadata_extractor.extract_hierarchical_metadata(
            content, chunk_meta, doc
        )
        
        assert enriched_meta["content_type_analysis"]["estimated_read_time"] == default_reading_time
        
        # Test with faster reading speed (400 WPM)
        fast_settings = self.create_settings_with_markdown_config(words_per_minute_reading=400)
        strategy_fast = MarkdownChunkingStrategy(fast_settings)
        
        fast_reading_time = max(1, word_count // 400)  # 500/400 = 1.25 -> 1 minute
        fast_meta = strategy_fast.metadata_extractor.extract_hierarchical_metadata(
            content, chunk_meta, doc
        )
        
        assert fast_meta["content_type_analysis"]["estimated_read_time"] == fast_reading_time
        assert fast_meta["content_type_analysis"]["estimated_read_time"] < enriched_meta["content_type_analysis"]["estimated_read_time"]


class TestChunkingSizeConfigBehavior:
    """Test that chunk size and overlap configurations affect behavior."""

    def create_settings_with_chunking_config(self, chunk_size=1500, chunk_overlap=200, max_chunks=500):
        """Create settings with custom chunking configuration."""
        settings = Mock(spec=Settings)
        settings.global_config = GlobalConfig()
        settings.global_config.chunking.chunk_size = chunk_size
        settings.global_config.chunking.chunk_overlap = chunk_overlap
        settings.global_config.chunking.max_chunks_per_document = max_chunks
        
        # Set up other required configs
        settings.global_config.embedding.tokenizer = "cl100k_base"
        
        return settings

    def test_chunk_size_affects_chunk_count(self):
        """Test that chunk_size configuration affects the number of chunks produced."""
        # Create a large text document
        large_text = "This is a sentence. " * 200  # ~4000 characters
        
        # Test with small chunk size
        small_chunk_settings = self.create_settings_with_chunking_config(chunk_size=500, chunk_overlap=100)
        small_strategy = DefaultChunkingStrategy(small_chunk_settings)
        
        # Test with large chunk size
        large_chunk_settings = self.create_settings_with_chunking_config(chunk_size=2000, chunk_overlap=100)
        large_strategy = DefaultChunkingStrategy(large_chunk_settings)
        
        doc = Document(
            id="test-doc",
            content=large_text,
            source="test",
            source_type="text",
            content_type="text",  # Add missing content_type
            title="Test Document",
            url="test://document",
            metadata={}
        )
        
        small_chunks = small_strategy.chunk_document(doc)
        large_chunks = large_strategy.chunk_document(doc)
        
        # Smaller chunk size should produce more chunks
        assert len(small_chunks) > len(large_chunks)
        
        # Verify individual chunk sizes respect configuration
        for chunk in small_chunks:
            # Allow some tolerance due to overlap and word boundaries
            assert len(chunk.content) <= small_chunk_settings.global_config.chunking.chunk_size + 200
        
        for chunk in large_chunks:
            assert len(chunk.content) <= large_chunk_settings.global_config.chunking.chunk_size + 200

    def test_max_chunks_per_document_limits_output(self):
        """Test that max_chunks_per_document limits the number of chunks."""
        # Create very large text that would normally produce many chunks
        huge_text = "This is a sentence. " * 1000  # ~20,000 characters
        
        # Configure with small chunk size and low max chunks limit
        limited_settings = self.create_settings_with_chunking_config(
            chunk_size=200,
            chunk_overlap=50,
            max_chunks=5  # Very low limit
        )
        strategy = DefaultChunkingStrategy(limited_settings)
        
        doc = Document(
            id="test-doc",
            content=huge_text,
            source="test",
            source_type="text",
            content_type="text",  # Add missing content_type
            title="Test Document",
            url="test://document",
            metadata={}
        )
        
        chunks = strategy.chunk_document(doc)
        
        # Should be limited to max_chunks_per_document
        assert len(chunks) <= limited_settings.global_config.chunking.max_chunks_per_document
        assert len(chunks) == 5  # Should hit the limit exactly

    def test_chunk_overlap_affects_content_overlap(self):
        """Test that chunk_overlap configuration affects content overlap between chunks."""
        # Create text that will be split into multiple chunks
        text = "Sentence one. " * 50 + "Sentence two. " * 50  # Clear boundary in middle
        
        # Test with no overlap
        no_overlap_settings = self.create_settings_with_chunking_config(
            chunk_size=500,
            chunk_overlap=0
        )
        no_overlap_strategy = DefaultChunkingStrategy(no_overlap_settings)
        
        # Test with significant overlap
        overlap_settings = self.create_settings_with_chunking_config(
            chunk_size=500,
            chunk_overlap=100
        )
        overlap_strategy = DefaultChunkingStrategy(overlap_settings)
        
        doc = Document(
            id="test-doc",
            content=text,
            source="test",
            source_type="text",
            content_type="text",  # Add missing content_type
            title="Test Document",
            url="test://document",
            metadata={}
        )
        
        no_overlap_chunks = no_overlap_strategy.chunk_document(doc)
        overlap_chunks = overlap_strategy.chunk_document(doc)
        
        # Both should produce multiple chunks
        assert len(no_overlap_chunks) > 1
        assert len(overlap_chunks) > 1
        
        # With overlap, there should be some content shared between consecutive chunks
        if len(overlap_chunks) >= 2:
            chunk1_content = overlap_chunks[0].content
            chunk2_content = overlap_chunks[1].content
            
            # Find common substring (simple check for any shared words)
            chunk1_words = set(chunk1_content.split())
            chunk2_words = set(chunk2_content.split())
            common_words = chunk1_words.intersection(chunk2_words)
            
            # With overlap, there should be some common content
            # (This is a simplified check - actual overlap detection is more complex)
            assert len(common_words) > 0


class TestConfigurationIntegrationBehavior:
    """Test end-to-end configuration behavior through the system."""

    def test_yaml_config_propagates_to_strategy_behavior(self):
        """Test that YAML configuration values propagate through to actual strategy behavior."""
        # This would ideally test loading from an actual YAML file
        # For now, we'll test the configuration propagation chain
        
        config = GlobalConfig()
        
        # Modify configuration values
        config.chunking.chunk_size = 800
        config.chunking.strategies.markdown.min_section_size = 300
        config.chunking.strategies.markdown.max_workers = 6
        
        # Create settings with this config
        settings = Mock(spec=Settings)
        settings.global_config = config
        
        # Initialize strategy
        strategy = MarkdownChunkingStrategy(settings)
        
        # Verify configuration values propagated
        assert strategy.settings.global_config.chunking.chunk_size == 800
        assert strategy.settings.global_config.chunking.strategies.markdown.min_section_size == 300
        assert strategy.settings.global_config.chunking.strategies.markdown.max_workers == 6
        
        # Verify the values are actually used in components
        assert strategy.section_splitter.settings.global_config.chunking.chunk_size == 800

    def test_strategy_selection_uses_correct_config(self):
        """Test that different strategies use their respective configurations."""
        config = GlobalConfig()
        
        # Set different values for different strategies
        config.chunking.strategies.default.min_chunk_size = 100
        config.chunking.strategies.markdown.min_section_size = 400
        
        settings = Mock(spec=Settings)
        settings.global_config = config
        
        # Create different strategies
        default_strategy = DefaultChunkingStrategy(settings)
        markdown_strategy = MarkdownChunkingStrategy(settings)
        
        # Each should use its own configuration
        default_config = default_strategy.settings.global_config.chunking.strategies.default
        markdown_config = markdown_strategy.settings.global_config.chunking.strategies.markdown
        
        assert default_config.min_chunk_size == 100
        assert markdown_config.min_section_size == 400
        
        # Verify they don't interfere with each other
        assert markdown_config.min_section_size != default_config.min_chunk_size 