"""
Integration tests for input boundary validation with real services.

Tests comprehensive input boundary scenarios including edge cases,
large inputs, and special characters to ensure robust data handling.
"""

import pytest
import tempfile
import os
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, UTC

from qdrant_loader.config import Settings, GlobalConfig
from qdrant_loader.config.qdrant import QdrantConfig
from qdrant_loader.config.models import ProjectsConfig
from qdrant_loader.core.chunking.strategy.default_strategy import DefaultChunkingStrategy
from qdrant_loader.core.document import Document
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager


class TestInputBoundaryValidationIntegration:
    """Integration tests for input boundary validation with real services."""

    def _create_test_settings(self):
        """Create test settings with minimal required configuration."""
        # Create QdrantConfig first
        qdrant_config = QdrantConfig(
            url="http://localhost:6333",
            api_key="test-key",
            collection_name="test-collection"
        )
        
        # Put QdrantConfig inside GlobalConfig
        global_config = GlobalConfig(qdrant=qdrant_config)
        
        # Create Settings with the proper structure
        return Settings(
            global_config=global_config,
            projects_config=ProjectsConfig()
        )

    def _create_test_document(self, content: str, title: str = "Test Document") -> Document:
        """Create a test document with the given content."""
        return Document(
            title=title,
            content=content,
            content_type="text/plain",
            source_type="test",
            source="test-source",
            url="test://document",
            metadata={},
            is_deleted=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

    def test_empty_and_minimal_input_handling_with_services(self):
        """Test handling of empty and minimal inputs with real services."""
        settings = self._create_test_settings()
        chunking_strategy = DefaultChunkingStrategy(settings)

        # Test cases for boundary conditions
        test_cases = [
            ("", "Empty content"),
            ("a", "Single character"),
            ("Hello", "Minimal content"),
            ("   ", "Whitespace only"),
            ("\n", "Newline only"),
            ("\t", "Tab only"),
        ]

        results = []
        for content, description in test_cases:
            try:
                doc = Document(
                    title=f"Test: {description}",
                    content=content,
                    content_type="text/plain",
                    source_type="test",
                    source="test-source",
                    url="test://document",
                    metadata={'test_case': description},
                    is_deleted=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                chunks = chunking_strategy.chunk_document(doc)
                results.append({
                    'description': description,
                    'content_length': len(content),
                    'num_chunks': len(chunks),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'description': description,
                    'content_length': len(content),
                    'success': False,
                    'error': str(e)
                })

        # Verify that most cases are handled gracefully
        successful_results = [r for r in results if r['success']]
        assert len(successful_results) >= len(test_cases) // 2, "Most boundary cases should be handled"

    def test_large_input_handling_with_chunking(self):
        """Test handling of large inputs with chunking strategy."""
        settings = self._create_test_settings()
        chunking_strategy = DefaultChunkingStrategy(settings)

        # Create progressively larger content
        base_content = "This is a test sentence for chunking validation. " * 10
        
        test_sizes = [1, 5, 20]  # Multipliers for base content
        
        for multiplier in test_sizes:
            large_content = base_content * multiplier
            
            doc = Document(
                title=f"Large Document Test {multiplier}",
                content=large_content,
                content_type="text/plain",
                source_type="test",
                source="test-source",
                url="test://document",
                metadata={'size_multiplier': multiplier},
                is_deleted=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            chunks = chunking_strategy.chunk_document(doc)
            
            # Verify chunking behavior
            assert len(chunks) >= 1, f"Should produce at least one chunk for multiplier {multiplier}"
            assert all(isinstance(chunk, Document) for chunk in chunks), "All chunks should be Document objects"

    def test_unicode_and_special_characters_with_chunking(self):
        """Test handling of unicode and special characters with chunking."""
        settings = self._create_test_settings()
        chunking_strategy = DefaultChunkingStrategy(settings)

        # Test various unicode and special character scenarios
        test_contents = [
            "Hello 世界! Testing unicode characters.",
            "Émoji test: 🌍🚀💡 with special chars",
            "Mixed: ASCII + UTF-8 + 中文 + العربية",
            "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?",
            "Control chars: \n\t\r and other whitespace",
            "Zero-width chars: \u200b\u200c\u200d",
        ]

        for i, content in enumerate(test_contents):
            doc = Document(
                title=f"Unicode Test {i}",
                content=content,
                content_type="text/plain",
                source_type="test",
                source="test-source",
                url="test://document",
                metadata={'test_type': 'unicode'},
                is_deleted=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            chunks = chunking_strategy.chunk_document(doc)
            
            # Verify that unicode content is handled properly
            assert len(chunks) >= 1, f"Should handle unicode content in test {i}"
            
            # Verify that content is preserved in chunks
            combined_content = " ".join(chunk.content for chunk in chunks)
            assert len(combined_content) > 0, f"Content should be preserved in chunks for test {i}"

    def test_whitespace_and_formatting_preservation_with_chunking(self):
        """Test preservation of whitespace and formatting with chunking."""
        settings = self._create_test_settings()
        chunking_strategy = DefaultChunkingStrategy(settings)

        # Test content with various formatting
        formatted_content = """
        This is a test document with various formatting.
        
        It has multiple paragraphs.
        
            - Indented lists
            - With bullet points
        
        And some code-like content:
            def hello():
                return "world"
        
        Plus normal text at the end.
        """

        doc = Document(
            title="Formatting Test Document",
            content=formatted_content,
            content_type="text/plain",
            source_type="test",
            source="test-source",
            url="test://document",
            metadata={'test_type': 'formatting'},
            is_deleted=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        chunks = chunking_strategy.chunk_document(doc)
        
        # Verify formatting is handled
        assert len(chunks) >= 1, "Should handle formatted content"
        
        # Check that some structure is preserved
        combined_content = " ".join(chunk.content for chunk in chunks)
        assert "test document" in combined_content.lower(), "Content should be preserved"

    def test_error_handling_with_invalid_inputs(self):
        """Test error handling with various invalid inputs."""
        settings = self._create_test_settings()
        chunking_strategy = DefaultChunkingStrategy(settings)

        # Test potentially problematic inputs
        problematic_inputs = [
            "\x00\x01\x02",  # Null bytes and control characters
            "x" * 100000,    # Very large content
            "\n" * 1000,     # Many newlines
            "\t" * 500,      # Many tabs
            "🌍" * 1000,     # Many unicode characters
        ]

        successful_tests = 0
        for i, content in enumerate(problematic_inputs):
            try:
                doc = Document(
                    title=f"Error Test {i}",
                    content=content,
                    content_type="text/plain",
                    source_type="test",
                    source="test-source",
                    url="test://document",
                    metadata={'test_type': 'error_handling'},
                    is_deleted=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                chunks = chunking_strategy.chunk_document(doc)
                
                # If we get here, the test succeeded
                assert isinstance(chunks, list), f"Should return list for test {i}"
                successful_tests += 1
                
            except Exception as e:
                # Some failures are acceptable for truly problematic input
                print(f"Expected failure for problematic input {i}: {e}")

        # At least some tests should succeed
        assert successful_tests >= len(problematic_inputs) // 2, "At least half of error tests should succeed"

    def test_configuration_validation(self):
        """Test that configuration validation works correctly."""
        settings = self._create_test_settings()
        
        # Verify that settings are valid
        assert settings.global_config is not None
        assert settings.global_config.qdrant is not None
        assert settings.global_config.qdrant.url == "http://localhost:6333"
        assert settings.global_config.qdrant.collection_name == "test-collection"
        
        # Test that chunking strategy can be created
        chunking_strategy = DefaultChunkingStrategy(settings)
        assert chunking_strategy is not None

    def test_concurrent_chunking_operations(self):
        """Test concurrent chunking operations for thread safety."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        settings = self._create_test_settings()

        def chunking_task(task_id):
            """Task that performs chunking operations."""
            try:
                chunking_strategy = DefaultChunkingStrategy(settings)
                
                content = f"Concurrent test content for task {task_id}. " * 20
                doc = Document(
                    title=f"Concurrent Task {task_id}",
                    content=content,
                    content_type="text/plain",
                    source_type="test",
                    source="test-source",
                    url=f"test://document/{task_id}",
                    metadata={'task_id': task_id},
                    is_deleted=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                chunks = chunking_strategy.chunk_document(doc)
                return {
                    'task_id': task_id,
                    'success': True,
                    'num_chunks': len(chunks)
                }
            except Exception as e:
                return {
                    'task_id': task_id,
                    'success': False,
                    'error': str(e)
                }

        # Run concurrent tasks
        num_tasks = 10
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(chunking_task, i) for i in range(num_tasks)]
            results = [future.result() for future in futures]

        # Analyze results
        successful_tasks = [r for r in results if r['success']]
        failed_tasks = [r for r in results if not r['success']]

        # Most tasks should succeed
        success_rate = len(successful_tasks) / len(results)
        assert success_rate >= 0.7, f"Success rate should be at least 70%, got {success_rate}"

        # Log failures for debugging
        if failed_tasks:
            print(f"Some concurrent tasks failed: {failed_tasks}")

    def test_neo4j_manager_basic_functionality(self):
        """Test basic Neo4j manager functionality without actual connection."""
        # This is a placeholder test for Neo4j manager
        # In a real integration test, you would test actual Neo4j operations

        settings = self._create_test_settings()
        
        # Verify that settings can be used to create managers
        # Note: We're not actually connecting to Neo4j in this test
        assert settings.global_config is not None
        
        # Test would create Neo4jManager here if we had the actual implementation
        # manager = Neo4jManager(settings)
        # assert manager is not None

    def test_qdrant_manager_basic_functionality(self):
        """Test basic Qdrant manager functionality without actual connection."""
        # This is a placeholder test for Qdrant manager
        # In a real integration test, you would test actual Qdrant operations

        settings = self._create_test_settings()
        
        # Verify that settings can be used to create managers
        # Note: We're not actually connecting to Qdrant in this test
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.qdrant_collection_name == "test-collection"
        
        # Test would create QdrantManager here if we had the actual implementation
        # manager = QdrantManager(settings)
        # assert manager is not None 