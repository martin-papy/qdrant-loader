import atexit
import logging
import threading

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# Metrics definitions
INGESTED_DOCUMENTS = Counter(
    "qdrant_ingested_documents_total", "Total number of documents ingested"
)
CHUNKING_DURATION = Histogram(
    "qdrant_chunking_duration_seconds", "Time spent chunking documents"
)
EMBEDDING_DURATION = Histogram(
    "qdrant_embedding_duration_seconds", "Time spent embedding chunks"
)
UPSERT_DURATION = Histogram(
    "qdrant_upsert_duration_seconds", "Time spent upserting to Qdrant"
)
CHUNK_QUEUE_SIZE = Gauge("qdrant_chunk_queue_size", "Current size of the chunk queue")
EMBED_QUEUE_SIZE = Gauge(
    "qdrant_embed_queue_size", "Current size of the embedding queue"
)
CPU_USAGE = Gauge("qdrant_cpu_usage_percent", "CPU usage percent")
MEMORY_USAGE = Gauge("qdrant_memory_usage_percent", "Memory usage percent")

_metrics_server_thread: threading.Thread | None = None
_metrics_server_started = False


def start_metrics_server(port: int = 8001):
    """Start Prometheus metrics HTTP server in a daemon thread."""
    global _metrics_server_thread, _metrics_server_started

    if _metrics_server_started:
        logger.debug("Metrics server already started, skipping")
        return

    try:
        # Start the HTTP server - this creates non-daemon threads internally
        start_http_server(port)
        _metrics_server_started = True
        logger.info(f"Prometheus metrics server started on port {port}")

        # Register cleanup function to be called on exit
        atexit.register(stop_metrics_server)

    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise


def stop_metrics_server():
    """Stop the metrics server and cleanup resources."""
    global _metrics_server_started

    if _metrics_server_started:
        logger.info("Stopping metrics server...")
        _metrics_server_started = False

        # Note: prometheus_client doesn't provide a clean way to stop the server
        # The HTTP server threads will be cleaned up when the process exits
        # This is a known limitation of the prometheus_client library


# Example usage in pipeline:
# with CHUNKING_DURATION.time():
#     ...
# CHUNK_QUEUE_SIZE.set(len(chunk_queue))
# CPU_USAGE.set(psutil.cpu_percent())
# MEMORY_USAGE.set(psutil.virtual_memory().percent)
