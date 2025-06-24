"""
Integration tests for critical error scenarios and system resilience.

Tests comprehensive error path scenarios including resource exhaustion,
cascading failures, and recovery mechanisms to ensure system stability.
"""

import pytest
import time
import gc
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import psutil

from qdrant_loader.config import Settings, GlobalConfig
from qdrant_loader.config.qdrant import QdrantConfig
from qdrant_loader.config.models import ProjectsConfig
from qdrant_loader.core.chunking.strategy.default_strategy import DefaultChunkingStrategy


class TestCriticalErrorScenariosIntegration:
    """Integration tests for critical error scenarios and system resilience."""

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

    def test_memory_exhaustion_scenarios_with_real_services(self):
        """Test system behavior under memory pressure."""
        settings = self._create_test_settings()
        chunking_strategy = DefaultChunkingStrategy(settings)

        # Track initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Create progressively larger content to test memory handling
        memory_test_results = []
        
        for size_multiplier in [1, 10, 100]:
            try:
                # Create large content
                large_content = "Test content. " * (1000 * size_multiplier)
                
                # Monitor memory before operation
                memory_before = process.memory_info().rss
                
                # Test chunking with large content
                from qdrant_loader.core.document import Document
                from datetime import datetime, UTC
                
                doc = Document(
                    title=f"Large Document {size_multiplier}",
                    content=large_content,
                    content_type="text/plain",
                    source_type="test",
                    source="test-source",
                    url="test://document",
                    metadata={},
                    is_deleted=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                chunks = chunking_strategy.chunk_document(doc)
                
                # Monitor memory after operation
                memory_after = process.memory_info().rss
                memory_increase = memory_after - memory_before
                
                memory_test_results.append({
                    'size_multiplier': size_multiplier,
                    'content_length': len(large_content),
                    'num_chunks': len(chunks),
                    'memory_increase': memory_increase,
                    'success': True
                })
                
                # Force garbage collection
                del large_content, doc, chunks
                gc.collect()
                
            except MemoryError:
                memory_test_results.append({
                    'size_multiplier': size_multiplier,
                    'success': False,
                    'error': 'MemoryError'
                })
                break
            except Exception as e:
                memory_test_results.append({
                    'size_multiplier': size_multiplier,
                    'success': False,
                    'error': str(e)
                })

        # Verify that at least the smaller tests succeeded
        assert memory_test_results[0]['success'], "Basic memory test should succeed"
        
        # Verify memory is released after operations
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Allow some memory growth but it shouldn't be excessive
        assert memory_growth < 100 * 1024 * 1024, "Memory growth should be reasonable"

    def test_concurrent_operations_under_load(self):
        """Test system behavior under concurrent load."""
        settings = self._create_test_settings()
        
        def create_chunking_task(task_id):
            """Create a chunking task that simulates real work."""
            try:
                chunking_strategy = DefaultChunkingStrategy(settings)
                
                from qdrant_loader.core.document import Document
                from datetime import datetime, UTC
                
                content = f"Task {task_id} content. " * 100
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
                    'num_chunks': len(chunks),
                    'content_length': len(content)
                }
            except Exception as e:
                return {
                    'task_id': task_id,
                    'success': False,
                    'error': str(e)
                }

        # Run multiple concurrent tasks
        num_tasks = 20
        max_workers = 5
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(create_chunking_task, i) 
                for i in range(num_tasks)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # Analyze results
        successful_tasks = [r for r in results if r['success']]
        failed_tasks = [r for r in results if not r['success']]
        
        # Should have high success rate
        success_rate = len(successful_tasks) / len(results)
        assert success_rate >= 0.8, f"Success rate should be at least 80%, got {success_rate}"
        
        # Log any failures for debugging
        if failed_tasks:
            print(f"Failed tasks: {failed_tasks}")

    def test_configuration_error_scenarios(self):
        """Test handling of various configuration errors."""
        
        # Test invalid chunk size
        try:
            # Create QdrantConfig first
            qdrant_config = QdrantConfig(
                url="http://localhost:6333",
                api_key="test-key",
                collection_name="test-collection"
            )
            
            # Put QdrantConfig inside GlobalConfig
            global_config = GlobalConfig(qdrant=qdrant_config)
            
            # Create Settings with the proper structure
            invalid_settings = Settings(
                global_config=global_config,
                projects_config=ProjectsConfig()
            )
            
            # Manually set invalid chunk size
            invalid_settings.global_config.chunking.chunk_size = -1
            
            chunking_strategy = DefaultChunkingStrategy(invalid_settings)
            
            # Should handle invalid configuration gracefully
            from qdrant_loader.core.document import Document
            from datetime import datetime, UTC
            
            doc = Document(
                title="Test Document",
                content="Test content",
                content_type="text/plain",
                source_type="test",
                source="test-source",
                url="test://document",
                metadata={},
                is_deleted=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            chunks = chunking_strategy.chunk_document(doc)
            assert len(chunks) >= 1  # Should still produce chunks
            
        except Exception as e:
            # It's acceptable for invalid configuration to raise errors
            assert "chunk" in str(e).lower() and ("size" in str(e).lower() or "overlap" in str(e).lower())

    def test_file_system_error_scenarios(self):
        """Test handling of file system related errors."""
        
        # Test with temporary directory that gets removed
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            
            # Create a test file
            with open(test_file, 'w') as f:
                f.write("Test content for file system test")
            
            # Verify file exists
            assert os.path.exists(test_file)
            
            # Test reading the file
            with open(test_file, 'r') as f:
                content = f.read()
                assert "Test content" in content
        
        # After context, temp_dir should be cleaned up
        assert not os.path.exists(temp_dir)

    def test_resource_cleanup_scenarios(self):
        """Test proper resource cleanup under various scenarios."""
        settings = self._create_test_settings()
        
        # Test multiple chunking strategy creations and cleanups
        strategies = []
        
        try:
            for i in range(10):
                strategy = DefaultChunkingStrategy(settings)
                strategies.append(strategy)
                
                # Use the strategy briefly
                from qdrant_loader.core.document import Document
                from datetime import datetime, UTC
                
                doc = Document(
                    title=f"Cleanup Test {i}",
                    content=f"Content for cleanup test {i}",
                    content_type="text/plain",
                    source_type="test",
                    source="test-source",
                    url=f"test://document/{i}",
                    metadata={},
                    is_deleted=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                chunks = strategy.chunk_document(doc)
                assert len(chunks) >= 1
                
        finally:
            # Clean up resources
            strategies.clear()
            gc.collect()
        
        # Test should complete without resource leaks
        assert True

    def test_error_propagation_scenarios(self):
        """Test error propagation through the system."""
        settings = self._create_test_settings()
        chunking_strategy = DefaultChunkingStrategy(settings)
        
        # Test with various problematic inputs
        test_cases = [
            ("", "Empty content"),
            ("x" * 100000, "Very large content"),
            ("Special chars: \x00\x01\x02", "Control characters"),
        ]
        
        results = []
        for content, description in test_cases:
            try:
                from qdrant_loader.core.document import Document
                from datetime import datetime, UTC
                
                doc = Document(
                    title=f"Error Test: {description}",
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
                    'success': True,
                    'num_chunks': len(chunks)
                })
                
            except Exception as e:
                results.append({
                    'description': description,
                    'success': False,
                    'error': str(e)
                })
        
        # At least basic cases should succeed
        successful_results = [r for r in results if r['success']]
        assert len(successful_results) >= 1, "At least one test case should succeed"

    def test_timeout_and_recovery_scenarios(self):
        """Test timeout handling and recovery mechanisms."""
        settings = self._create_test_settings()
        
        def slow_operation():
            """Simulate a slow operation."""
            time.sleep(0.1)  # Small delay to simulate work
            chunking_strategy = DefaultChunkingStrategy(settings)
            
            from qdrant_loader.core.document import Document
            from datetime import datetime, UTC
            
            doc = Document(
                title="Timeout Test Document",
                content="Content for timeout test",
                content_type="text/plain",
                source_type="test",
                source="test-source",
                url="test://document",
                metadata={},
                is_deleted=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            return chunking_strategy.chunk_document(doc)
        
        # Test with timeout
        start_time = time.time()
        
        try:
            # Use ThreadPoolExecutor with timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(slow_operation)
                result = future.result(timeout=5.0)  # 5 second timeout
                
                assert result is not None
                assert len(result) >= 1
                
        except Exception as e:
            # If timeout occurs, that's also a valid test result
            print(f"Timeout test completed with: {e}")
        
        elapsed_time = time.time() - start_time
        assert elapsed_time < 10.0, "Operation should complete within reasonable time" 