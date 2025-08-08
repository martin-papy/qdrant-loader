"""Comprehensive tests for Prometheus Metrics to achieve 80%+ coverage."""

import threading
import time
from unittest.mock import Mock, patch

from prometheus_client import REGISTRY

from qdrant_loader.core.monitoring import prometheus_metrics


class TestPrometheusMetrics:
    """Comprehensive tests for Prometheus metrics functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset module state before each test
        prometheus_metrics._metrics_server_started = False
        prometheus_metrics._metrics_server_thread = None
        
        # Clear any existing metric values
        prometheus_metrics.INGESTED_DOCUMENTS._value._value = 0
        prometheus_metrics.CHUNK_QUEUE_SIZE.set(0)
        prometheus_metrics.EMBED_QUEUE_SIZE.set(0)
        prometheus_metrics.CPU_USAGE.set(0)
        prometheus_metrics.MEMORY_USAGE.set(0)
        
        # Clear histogram values by manually resetting internal state
        try:
            # Reset histograms by clearing their buckets and sum
            for hist in [prometheus_metrics.CHUNKING_DURATION, 
                        prometheus_metrics.EMBEDDING_DURATION, 
                        prometheus_metrics.UPSERT_DURATION]:
                hist._sum._value = 0
                for bucket in hist._buckets:
                    bucket._value = 0
        except Exception:
            # If histogram clearing fails, skip it
            pass

    def teardown_method(self):
        """Clean up after each test."""
        # Reset module state after each test
        prometheus_metrics._metrics_server_started = False
        prometheus_metrics._metrics_server_thread = None
    
    def get_histogram_count(self, histogram):
        """Helper to get count value from histogram using collect()."""
        for metric_family in histogram.collect():
            for sample in metric_family.samples:
                if sample.name.endswith('_count'):
                    return sample.value
        return 0

    def test_metrics_definitions(self):
        """Test that all metrics are properly defined."""
        # Test Counter metrics
        assert prometheus_metrics.INGESTED_DOCUMENTS._name == "qdrant_ingested_documents"
        assert "Total number of documents ingested" in prometheus_metrics.INGESTED_DOCUMENTS._documentation
        
        # Test Histogram metrics
        assert prometheus_metrics.CHUNKING_DURATION._name == "qdrant_chunking_duration_seconds"
        assert "Time spent chunking documents" in prometheus_metrics.CHUNKING_DURATION._documentation
        
        assert prometheus_metrics.EMBEDDING_DURATION._name == "qdrant_embedding_duration_seconds"
        assert "Time spent embedding chunks" in prometheus_metrics.EMBEDDING_DURATION._documentation
        
        assert prometheus_metrics.UPSERT_DURATION._name == "qdrant_upsert_duration_seconds"
        assert "Time spent upserting to Qdrant" in prometheus_metrics.UPSERT_DURATION._documentation
        
        # Test Gauge metrics
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._name == "qdrant_chunk_queue_size"
        assert "Current size of the chunk queue" in prometheus_metrics.CHUNK_QUEUE_SIZE._documentation
        
        assert prometheus_metrics.EMBED_QUEUE_SIZE._name == "qdrant_embed_queue_size"
        assert "Current size of the embedding queue" in prometheus_metrics.EMBED_QUEUE_SIZE._documentation
        
        assert prometheus_metrics.CPU_USAGE._name == "qdrant_cpu_usage_percent"
        assert "CPU usage percent" in prometheus_metrics.CPU_USAGE._documentation
        
        assert prometheus_metrics.MEMORY_USAGE._name == "qdrant_memory_usage_percent"
        assert "Memory usage percent" in prometheus_metrics.MEMORY_USAGE._documentation

    def test_counter_metrics_functionality(self):
        """Test Counter metrics functionality."""
        # Test INGESTED_DOCUMENTS counter
        initial_value = prometheus_metrics.INGESTED_DOCUMENTS._value._value
        
        # Increment counter
        prometheus_metrics.INGESTED_DOCUMENTS.inc()
        assert prometheus_metrics.INGESTED_DOCUMENTS._value._value == initial_value + 1
        
        # Increment by specific amount
        prometheus_metrics.INGESTED_DOCUMENTS.inc(5)
        assert prometheus_metrics.INGESTED_DOCUMENTS._value._value == initial_value + 6

    def test_gauge_metrics_functionality(self):
        """Test Gauge metrics functionality."""
        # Test CHUNK_QUEUE_SIZE gauge
        prometheus_metrics.CHUNK_QUEUE_SIZE.set(10)
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._value._value == 10
        
        # Test increment/decrement
        prometheus_metrics.CHUNK_QUEUE_SIZE.inc()
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._value._value == 11
        
        prometheus_metrics.CHUNK_QUEUE_SIZE.dec(3)
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._value._value == 8
        
        # Test EMBED_QUEUE_SIZE gauge
        prometheus_metrics.EMBED_QUEUE_SIZE.set(25)
        assert prometheus_metrics.EMBED_QUEUE_SIZE._value._value == 25
        
        # Test CPU and Memory usage
        prometheus_metrics.CPU_USAGE.set(75.5)
        assert prometheus_metrics.CPU_USAGE._value._value == 75.5
        
        prometheus_metrics.MEMORY_USAGE.set(62.3)
        assert prometheus_metrics.MEMORY_USAGE._value._value == 62.3

    def test_histogram_metrics_functionality(self):
        """Test Histogram metrics functionality."""
        # Test CHUNKING_DURATION histogram
        prometheus_metrics.CHUNKING_DURATION.observe(1.5)
        assert prometheus_metrics.CHUNKING_DURATION._sum._value > 0
        assert self.get_histogram_count(prometheus_metrics.CHUNKING_DURATION) == 1
        
        # Test EMBEDDING_DURATION histogram
        prometheus_metrics.EMBEDDING_DURATION.observe(2.3)
        assert prometheus_metrics.EMBEDDING_DURATION._sum._value > 0
        assert self.get_histogram_count(prometheus_metrics.EMBEDDING_DURATION) == 1
        
        # Test UPSERT_DURATION histogram
        prometheus_metrics.UPSERT_DURATION.observe(0.8)
        assert prometheus_metrics.UPSERT_DURATION._sum._value > 0
        assert self.get_histogram_count(prometheus_metrics.UPSERT_DURATION) == 1

    def test_histogram_timer_context_manager(self):
        """Test histogram timer context manager functionality."""
        # Test chunking duration timer
        with prometheus_metrics.CHUNKING_DURATION.time():
            time.sleep(0.01)  # Small sleep to ensure measurable time
        
        assert self.get_histogram_count(prometheus_metrics.CHUNKING_DURATION) == 1
        assert prometheus_metrics.CHUNKING_DURATION._sum._value > 0
        
        # Test embedding duration timer
        with prometheus_metrics.EMBEDDING_DURATION.time():
            time.sleep(0.01)
        
        assert self.get_histogram_count(prometheus_metrics.EMBEDDING_DURATION) == 1
        assert prometheus_metrics.EMBEDDING_DURATION._sum._value > 0

    @patch('qdrant_loader.core.monitoring.prometheus_metrics.start_http_server')
    def test_start_metrics_server_success(self, mock_start_server):
        """Test successful metrics server startup."""
        # Test starting server on default port
        prometheus_metrics.start_metrics_server()
        
        mock_start_server.assert_called_once_with(8001)
        assert prometheus_metrics._metrics_server_started is True
        
        # Test starting server on custom port
        prometheus_metrics._metrics_server_started = False
        prometheus_metrics.start_metrics_server(port=9090)
        
        # Should be called twice now (once for default, once for custom port)
        assert mock_start_server.call_count == 2
        mock_start_server.assert_called_with(9090)

    @patch('qdrant_loader.core.monitoring.prometheus_metrics.start_http_server')
    def test_start_metrics_server_already_started(self, mock_start_server):
        """Test metrics server startup when already started."""
        # Set server as already started
        prometheus_metrics._metrics_server_started = True
        
        # Try to start again
        prometheus_metrics.start_metrics_server()
        
        # Should not call start_http_server
        mock_start_server.assert_not_called()

    @patch('qdrant_loader.core.monitoring.prometheus_metrics.start_http_server')
    def test_start_metrics_server_exception_handling(self, mock_start_server):
        """Test metrics server startup exception handling."""
        # Mock server to raise exception
        mock_start_server.side_effect = Exception("Port already in use")
        
        # Should not raise exception, just log error
        prometheus_metrics.start_metrics_server()
        
        mock_start_server.assert_called_once_with(8001)
        # Server should not be marked as started if exception occurred
        assert prometheus_metrics._metrics_server_started is False

    def test_stop_metrics_server(self):
        """Test metrics server stopping functionality."""
        # Set server as started
        prometheus_metrics._metrics_server_started = True
        mock_thread = Mock(spec=threading.Thread)
        prometheus_metrics._metrics_server_thread = mock_thread
        
        # Stop the server
        prometheus_metrics.stop_metrics_server()
        
        # Should reset state
        assert prometheus_metrics._metrics_server_started is False
        assert prometheus_metrics._metrics_server_thread is None

    def test_stop_metrics_server_not_started(self):
        """Test stopping metrics server when not started."""
        # Ensure server is not marked as started
        prometheus_metrics._metrics_server_started = False
        prometheus_metrics._metrics_server_thread = None
        
        # Should not raise exception
        prometheus_metrics.stop_metrics_server()
        
        # State should remain the same
        assert prometheus_metrics._metrics_server_started is False
        assert prometheus_metrics._metrics_server_thread is None

    def test_stop_metrics_server_no_thread(self):
        """Test stopping metrics server when started but no thread reference."""
        # Set server as started but no thread reference
        prometheus_metrics._metrics_server_started = True
        prometheus_metrics._metrics_server_thread = None
        
        # Should still reset state
        prometheus_metrics.stop_metrics_server()
        
        assert prometheus_metrics._metrics_server_started is False
        assert prometheus_metrics._metrics_server_thread is None

    def test_module_state_variables(self):
        """Test module-level state variables."""
        # Test initial state
        assert prometheus_metrics._metrics_server_thread is None
        assert prometheus_metrics._metrics_server_started is False
        
        # Test setting state
        mock_thread = Mock(spec=threading.Thread)
        prometheus_metrics._metrics_server_thread = mock_thread
        prometheus_metrics._metrics_server_started = True
        
        assert prometheus_metrics._metrics_server_thread is mock_thread
        assert prometheus_metrics._metrics_server_started is True

    @patch('atexit.register')
    @patch('qdrant_loader.core.monitoring.prometheus_metrics.start_http_server')
    def test_atexit_registration(self, mock_start_server, mock_atexit_register):
        """Test that cleanup function is registered with atexit."""
        prometheus_metrics.start_metrics_server()
        
        # Verify atexit.register was called with stop_metrics_server
        mock_atexit_register.assert_called_once_with(prometheus_metrics.stop_metrics_server)

    def test_metrics_thread_safety(self):
        """Test metrics thread safety with concurrent access."""
        def increment_counter():
            for _ in range(100):
                prometheus_metrics.INGESTED_DOCUMENTS.inc()
        
        def update_gauge():
            for i in range(100):
                prometheus_metrics.CHUNK_QUEUE_SIZE.set(i)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            t1 = threading.Thread(target=increment_counter)
            t2 = threading.Thread(target=update_gauge)
            threads.extend([t1, t2])
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify counter was incremented correctly
        assert prometheus_metrics.INGESTED_DOCUMENTS._value._value == 500  # 5 threads * 100 increments
        
        # Gauge should have some value (exact value depends on thread execution order)
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._value._value >= 0

    def test_metrics_reset_functionality(self):
        """Test resetting metrics values."""
        # Set some values
        prometheus_metrics.INGESTED_DOCUMENTS.inc(10)
        prometheus_metrics.CHUNK_QUEUE_SIZE.set(50)
        prometheus_metrics.CHUNKING_DURATION.observe(2.5)
        
        # Verify values are set
        assert prometheus_metrics.INGESTED_DOCUMENTS._value._value == 10
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._value._value == 50
        assert self.get_histogram_count(prometheus_metrics.CHUNKING_DURATION) == 1
        
        # Reset counter (note: Prometheus counters don't have reset, but we can simulate)
        prometheus_metrics.INGESTED_DOCUMENTS._value._value = 0
        assert prometheus_metrics.INGESTED_DOCUMENTS._value._value == 0
        
        # Reset gauge
        prometheus_metrics.CHUNK_QUEUE_SIZE.set(0)
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._value._value == 0

    def test_all_metrics_are_registered(self):
        """Test that all metrics are registered with the default registry."""
        # Get all metric names from the registry
        metric_names = [metric.describe()[0].name for metric in REGISTRY._collector_to_names.keys() 
                       if hasattr(metric, 'describe') and metric.describe()]
        
        # Check that our metrics are registered
        expected_metrics = [
            "qdrant_ingested_documents",
            "qdrant_chunking_duration_seconds",
            "qdrant_embedding_duration_seconds", 
            "qdrant_upsert_duration_seconds",
            "qdrant_chunk_queue_size",
            "qdrant_embed_queue_size",
            "qdrant_cpu_usage_percent",
            "qdrant_memory_usage_percent"
        ]
        
        for expected_metric in expected_metrics:
            assert any(expected_metric in name for name in metric_names), f"Metric {expected_metric} not found in registry"

    def test_metrics_edge_cases(self):
        """Test edge cases for metrics."""
        # Test very large counter increment
        prometheus_metrics.INGESTED_DOCUMENTS.inc(1000000)
        assert prometheus_metrics.INGESTED_DOCUMENTS._value._value >= 1000000
        
        # Test negative gauge values
        prometheus_metrics.CHUNK_QUEUE_SIZE.set(-1)
        assert prometheus_metrics.CHUNK_QUEUE_SIZE._value._value == -1
        
        # Test zero duration observation
        prometheus_metrics.CHUNKING_DURATION.observe(0)
        assert self.get_histogram_count(prometheus_metrics.CHUNKING_DURATION) >= 1
        
        # Test very small duration observation
        prometheus_metrics.EMBEDDING_DURATION.observe(0.000001)
        assert self.get_histogram_count(prometheus_metrics.EMBEDDING_DURATION) >= 1
        
        # Test very large duration observation
        prometheus_metrics.UPSERT_DURATION.observe(999999.999)
        assert self.get_histogram_count(prometheus_metrics.UPSERT_DURATION) >= 1

    def test_logging_integration(self):
        """Test that logging is properly configured."""
        # Test that logger is created
        assert prometheus_metrics.logger is not None
        assert prometheus_metrics.logger.name == "qdrant_loader.core.monitoring.prometheus_metrics"