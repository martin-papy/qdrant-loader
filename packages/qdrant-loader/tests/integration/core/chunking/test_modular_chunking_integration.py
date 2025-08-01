"""Integration tests for modular chunking architecture.

These tests verify that the complete modular chunking system works correctly
without mocks, testing the full integration of all components.
"""

import pytest
from unittest.mock import Mock
from qdrant_loader.config import Settings, GlobalConfig
from qdrant_loader.core.chunking.strategy.default.text_document_parser import TextDocumentParser

# Import test fixtures
from tests.fixtures.modular_chunking import (
    create_sample_text_document,
    create_formatted_text_document,
    create_simple_text_document,
    create_long_text_document,
    create_edge_case_document
)


class TestModularChunkingIntegration:
    """Integration tests for the complete modular chunking system."""
    
    @pytest.fixture
    def real_settings(self):
        """Create real settings (minimal mocking) for integration tests."""
        # Create a real GlobalConfig with test values
        global_config = GlobalConfig()
        global_config.chunking.chunk_size = 1000
        global_config.chunking.chunk_overlap = 200
        global_config.chunking.max_chunks_per_document = 100
        
        # Configure strategy-specific settings with test values
        global_config.chunking.strategies.default.min_chunk_size = 50
        global_config.chunking.strategies.default.enable_semantic_analysis = False  # Disable for faster tests
        global_config.chunking.strategies.default.enable_entity_extraction = True
        
        # Create settings with the global config
        settings = Mock(spec=Settings)
        settings.global_config = global_config
        
        return settings
    
    @pytest.fixture
    def sample_documents(self):
        """Create a collection of sample documents for testing."""
        return {
            "simple": create_simple_text_document(),
            "formatted": create_formatted_text_document(),
            "sample": create_sample_text_document(),
            "long": create_long_text_document(),
            "edge_cases": create_edge_case_document()
        }
    
    def test_text_document_parser_integration(self, real_settings, sample_documents):
        """Test TextDocumentParser with real documents."""
        parser = TextDocumentParser()
        
        for doc_name, document in sample_documents.items():
            structure = parser.parse_document_structure(document.content)
            
            # Verify basic structure analysis
            assert structure["structure_type"] == "plain_text"
            assert structure["paragraph_count"] >= 0
            assert structure["sentence_count"] >= 0
            assert structure["word_count"] > 0
            assert structure["character_count"] == len(document.content)
            
            # Verify formatting detection works
            assert "formatting_indicators" in structure
            assert isinstance(structure["formatting_indicators"], dict)
            
            # Verify content characteristics
            assert "avg_paragraph_length" in structure
            assert "avg_sentence_length" in structure
            assert "content_density" in structure
            
            # Document-specific validations
            if doc_name == "formatted":
                # Formatted document should detect various features
                assert structure["has_list_items"] is True
                assert structure["has_numbered_sections"] is True
                formatting = structure["formatting_indicators"]
                assert formatting["has_bold_text"] is True
                assert formatting["has_urls"] is True
                assert formatting["has_email_addresses"] is True
            
            if doc_name == "edge_cases":
                # Edge case document should handle Unicode
                formatting = structure["formatting_indicators"]
                assert structure["has_unicode"] is True
    
    def test_base_components_integration(self, real_settings):
        """Test that base components work together correctly."""
        from qdrant_loader.core.chunking.strategy.base.section_splitter import BaseSectionSplitter
        from qdrant_loader.core.chunking.strategy.base.metadata_extractor import BaseMetadataExtractor
        from qdrant_loader.core.chunking.strategy.base.chunk_processor import BaseChunkProcessor
        
        # Create a concrete section splitter for testing
        class TestSectionSplitter(BaseSectionSplitter):
            def split_sections(self, content: str, document=None):
                paragraphs = content.split('\n\n')
                return [
                    self.create_section_metadata(p.strip(), i, "paragraph")
                    for i, p in enumerate(paragraphs)
                    if p.strip()
                ]
        
        # Create a concrete metadata extractor for testing
        class TestMetadataExtractor(BaseMetadataExtractor):
            def extract_hierarchical_metadata(self, content: str, chunk_metadata: dict, document):
                metadata = chunk_metadata.copy()
                metadata.update({
                    "content_analysis": self.analyze_content_type(content),
                    "cross_references": self.extract_cross_references(content),
                    "keyword_density": self.extract_keyword_density(content, top_n=5)
                })
                return metadata
            
            def extract_entities(self, text: str):
                import re
                # Simple entity extraction - find capitalized words
                entities = re.findall(r'\b[A-Z][a-z]+\b', text)
                return list(set(entities))[:10]  # Limit to 10 entities
        
        # Create a concrete chunk processor for testing
        class TestChunkProcessor(BaseChunkProcessor):
            def create_chunk_document(self, original_doc, chunk_content, chunk_index, total_chunks, chunk_metadata, skip_nlp=False):
                from qdrant_loader.core.document import Document
                
                chunk_id = self.generate_chunk_id(original_doc, chunk_index)
                final_metadata = self.create_base_chunk_metadata(original_doc, chunk_index, total_chunks, chunk_metadata)
                
                return Document(
                    id=chunk_id,
                    content=chunk_content,
                    url=original_doc.url,
                    content_type=original_doc.content_type,
                    source_type=original_doc.source_type,
                    source=original_doc.source,
                    title=f"{original_doc.title} - Chunk {chunk_index + 1}",
                    metadata=final_metadata
                )
        
        # Test components working together
        document = create_sample_text_document()
        
        # 1. Split content into sections
        splitter = TestSectionSplitter(real_settings)
        sections = splitter.split_sections(document.content, document)
        
        assert len(sections) > 0
        for section in sections:
            assert "content" in section
            assert "index" in section
            assert "section_type" in section
        
        # 2. Extract metadata for each section
        extractor = TestMetadataExtractor()
        processor = TestChunkProcessor(real_settings)
        
        enriched_sections = []
        for section in sections:
            enriched_metadata = extractor.extract_hierarchical_metadata(
                section["content"], section, document
            )
            enriched_sections.append({
                "content": section["content"],
                "metadata": enriched_metadata
            })
        
        # 3. Create chunk documents
        chunk_documents = []
        for i, section in enumerate(enriched_sections):
            chunk_doc = processor.create_chunk_document(
                original_doc=document,
                chunk_content=section["content"],
                chunk_index=i,
                total_chunks=len(enriched_sections),
                chunk_metadata=section["metadata"],
                skip_nlp=True  # Skip for faster testing
            )
            chunk_documents.append(chunk_doc)
        
        # Verify integration results
        assert len(chunk_documents) == len(sections)
        
        for i, chunk_doc in enumerate(chunk_documents):
            # Verify chunk document structure
            assert chunk_doc.content == sections[i]["content"]
            assert chunk_doc.metadata["chunk_index"] == i
            assert chunk_doc.metadata["total_chunks"] == len(chunk_documents)
            assert chunk_doc.metadata["is_chunk"] is True
            assert chunk_doc.metadata["parent_document_id"] == document.id
            
            # Verify enriched metadata is preserved
            assert "content_analysis" in chunk_doc.metadata
            assert "cross_references" in chunk_doc.metadata
            assert "keyword_density" in chunk_doc.metadata
    
    def test_configuration_driven_behavior(self, sample_documents):
        """Test that configuration settings properly control behavior."""
        from qdrant_loader.core.chunking.strategy.base.section_splitter import BaseSectionSplitter
        
        class ConfigTestSplitter(BaseSectionSplitter):
            def split_sections(self, content: str, document=None):
                # Use configured chunk size for splitting
                return self.split_content_by_size(content, self.chunk_size)
        
        # Test with different chunk sizes
        small_config = GlobalConfig()
        small_config.chunking.chunk_size = 200
        small_config.chunking.chunk_overlap = 50
        
        large_config = GlobalConfig()
        large_config.chunking.chunk_size = 2000
        large_config.chunking.chunk_overlap = 400
        
        # Create settings with different configs
        small_settings = Mock(spec=Settings)
        small_settings.global_config = small_config
        
        large_settings = Mock(spec=Settings)
        large_settings.global_config = large_config
        
        document = sample_documents["long"]
        
        # Test with small chunks
        small_splitter = ConfigTestSplitter(small_settings)
        small_chunks = small_splitter.split_sections(document.content)
        
        # Test with large chunks  
        large_splitter = ConfigTestSplitter(large_settings)
        large_chunks = large_splitter.split_sections(document.content)
        
        # Small chunk size should produce more chunks
        assert len(small_chunks) > len(large_chunks)
        
        # Verify chunk sizes respect configuration
        for chunk in small_chunks:
            assert len(chunk) <= small_config.chunking.chunk_size + small_config.chunking.chunk_overlap
        
        for chunk in large_chunks:
            assert len(chunk) <= large_config.chunking.chunk_size + large_config.chunking.chunk_overlap
    
    def test_strategy_specific_configuration(self):
        """Test that strategy-specific configuration works correctly."""
        config = GlobalConfig()
        
        # Test default strategy configuration
        default_config = config.chunking.strategies.default
        assert default_config.min_chunk_size == 100
        assert default_config.enable_semantic_analysis is True
        assert default_config.enable_entity_extraction is True
        
        # Test HTML strategy configuration
        html_config = config.chunking.strategies.html
        assert html_config.simple_parsing_threshold == 100000
        assert html_config.max_html_size_for_parsing == 500000
        assert html_config.preserve_semantic_structure is True
        
        # Test code strategy configuration
        code_config = config.chunking.strategies.code
        assert code_config.max_file_size_for_ast == 75000
        assert code_config.enable_ast_parsing is True
        assert code_config.enable_dependency_analysis is True
        
        # Test JSON strategy configuration
        json_config = config.chunking.strategies.json_strategy
        assert json_config.max_json_size_for_parsing == 1000000
        assert json_config.enable_schema_inference is True
        assert json_config.max_array_items_per_chunk == 50
        
        # Test Markdown strategy configuration
        markdown_config = config.chunking.strategies.markdown
        assert markdown_config.min_content_length_for_nlp == 100
        assert markdown_config.min_word_count_for_nlp == 20
        assert markdown_config.min_section_size == 500
        assert markdown_config.max_chunks_per_section == 1000
        assert markdown_config.enable_hierarchical_metadata is True
    
    def test_metadata_consistency_across_chunks(self, real_settings, sample_documents):
        """Test that metadata is consistent across all chunks from the same document."""
        from qdrant_loader.core.chunking.strategy.base.metadata_extractor import BaseMetadataExtractor
        from qdrant_loader.core.chunking.strategy.base.chunk_processor import BaseChunkProcessor
        
        class ConsistencyMetadataExtractor(BaseMetadataExtractor):
            def extract_hierarchical_metadata(self, content: str, chunk_metadata: dict, document):
                metadata = chunk_metadata.copy()
                metadata.update({
                    "document_title": document.title,
                    "document_source": document.source,
                    "extraction_timestamp": "2024-01-15T12:00:00"  # Fixed for consistency
                })
                return metadata
            
            def extract_entities(self, text: str):
                return ["Entity1", "Entity2"]  # Fixed entities for consistency
        
        class ConsistencyChunkProcessor(BaseChunkProcessor):
            def create_chunk_document(self, original_doc, chunk_content, chunk_index, total_chunks, chunk_metadata, skip_nlp=False):
                from qdrant_loader.core.document import Document
                
                chunk_id = self.generate_chunk_id(original_doc, chunk_index)
                final_metadata = self.create_base_chunk_metadata(original_doc, chunk_index, total_chunks, chunk_metadata)
                
                return Document(
                    id=chunk_id,
                    content=chunk_content,
                    url=original_doc.url,
                    content_type=original_doc.content_type,
                    source_type=original_doc.source_type,
                    source=original_doc.source,
                    title=f"{original_doc.title} - Chunk {chunk_index + 1}",
                    metadata=final_metadata
                )
        
        document = sample_documents["long"]
        extractor = ConsistencyMetadataExtractor()
        processor = ConsistencyChunkProcessor(real_settings)
        
        # Create multiple chunks
        content_parts = document.content.split('\n\n')[:5]  # Take first 5 paragraphs
        chunk_documents = []
        
        for i, part in enumerate(content_parts):
            chunk_metadata = {"section_type": "paragraph", "part_index": i}
            enriched_metadata = extractor.extract_hierarchical_metadata(part, chunk_metadata, document)
            
            chunk_doc = processor.create_chunk_document(
                original_doc=document,
                chunk_content=part,
                chunk_index=i,
                total_chunks=len(content_parts),
                chunk_metadata=enriched_metadata,
                skip_nlp=True
            )
            chunk_documents.append(chunk_doc)
        
        # Verify consistency across chunks
        for chunk_doc in chunk_documents:
            # Document-level metadata should be consistent
            assert chunk_doc.metadata["document_title"] == document.title
            assert chunk_doc.metadata["document_source"] == document.source
            assert chunk_doc.metadata["extraction_timestamp"] == "2024-01-15T12:00:00"
            assert chunk_doc.metadata["parent_document_id"] == document.id
            assert chunk_doc.metadata["total_chunks"] == len(content_parts)
            
            # Chunk-specific metadata should vary appropriately
            assert "chunk_index" in chunk_doc.metadata
            assert chunk_doc.metadata["is_chunk"] is True
    
    def test_error_handling_and_robustness(self, real_settings):
        """Test that the system handles errors gracefully."""
        parser = TextDocumentParser()
        
        # Test with edge cases
        edge_cases = [
            "",  # Empty content
            "   \n\n   ",  # Only whitespace
            "A",  # Single character
            "Word",  # Single word
            "Word\n" * 1000,  # Repetitive content
        ]
        
        for content in edge_cases:
            try:
                structure = parser.parse_document_structure(content)
                
                # Should handle gracefully
                assert "structure_type" in structure
                assert "paragraph_count" in structure
                assert "sentence_count" in structure
                assert structure["character_count"] == len(content)
                
            except Exception as e:
                pytest.fail(f"Parser failed on edge case '{content[:20]}...': {e}")
    
    def test_performance_with_large_content(self, real_settings):
        """Test performance characteristics with larger content."""
        import time
        
        # Create very large document
        large_content = "This is a performance test sentence. " * 1000
        large_doc = create_simple_text_document()
        large_doc.content = large_content
        
        parser = TextDocumentParser()
        
        # Measure parsing time
        start_time = time.time()
        structure = parser.parse_document_structure(large_doc.content)
        parsing_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 1 second for this size)
        assert parsing_time < 1.0, f"Parsing took too long: {parsing_time:.2f} seconds"
        
        # Should produce valid results
        assert structure["character_count"] == len(large_doc.content)
        assert structure["word_count"] > 0
        assert structure["paragraph_count"] > 0
    
    def test_chunk_boundary_optimization(self, real_settings):
        """Test that chunk boundaries are optimized properly."""
        from qdrant_loader.core.chunking.strategy.base.chunk_processor import BaseChunkProcessor
        
        class BoundaryChunkProcessor(BaseChunkProcessor):
            def create_chunk_document(self, original_doc, chunk_content, chunk_index, total_chunks, chunk_metadata, skip_nlp=False):
                # Not needed for this test
                pass
        
        processor = BoundaryChunkProcessor(real_settings)
        
        # Test with content that has clear boundaries
        chunks_with_broken_sentences = [
            "This is the first sentence. this is a broken",
            "sentence that continues here. This is complete.",
            "Another complete sentence here."
        ]
        
        optimized = processor.optimize_chunk_boundaries(chunks_with_broken_sentences)
        
        # Should handle the optimization gracefully
        assert len(optimized) > 0
        
        # Should remove empty chunks
        chunks_with_empty = ["First chunk", "", "   ", "Second chunk"]
        optimized_empty = processor.optimize_chunk_boundaries(chunks_with_empty)
        
        assert len(optimized_empty) == 2
        assert "First chunk" in optimized_empty
        assert "Second chunk" in optimized_empty 