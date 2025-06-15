"""Custom exceptions for the search system."""

from typing import Any, Dict, Optional


class SearchEngineError(Exception):
    """Base exception for search engine errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "SEARCH_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
    ):
        """Initialize search engine error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            recoverable: Whether the error is recoverable with retry/fallback
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.recoverable = recoverable

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }


class QdrantConnectionError(SearchEngineError):
    """Error connecting to or communicating with Qdrant."""

    def __init__(
        self,
        message: str = "Failed to connect to Qdrant server",
        qdrant_url: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if qdrant_url:
            details["qdrant_url"] = qdrant_url
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="QDRANT_CONNECTION_ERROR",
            details=details,
            recoverable=True,
        )


class QdrantQueryError(SearchEngineError):
    """Error executing query against Qdrant."""

    def __init__(
        self,
        message: str = "Failed to execute Qdrant query",
        query: Optional[str] = None,
        collection_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if query:
            details["query"] = query
        if collection_name:
            details["collection_name"] = collection_name
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="QDRANT_QUERY_ERROR",
            details=details,
            recoverable=True,
        )


class Neo4jConnectionError(SearchEngineError):
    """Error connecting to or communicating with Neo4j."""

    def __init__(
        self,
        message: str = "Failed to connect to Neo4j database",
        neo4j_uri: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if neo4j_uri:
            details["neo4j_uri"] = neo4j_uri
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="NEO4J_CONNECTION_ERROR",
            details=details,
            recoverable=True,
        )


class Neo4jQueryError(SearchEngineError):
    """Error executing Cypher query against Neo4j."""

    def __init__(
        self,
        message: str = "Failed to execute Neo4j query",
        cypher_query: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if cypher_query:
            details["cypher_query"] = cypher_query
        if parameters:
            details["parameters"] = parameters
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="NEO4J_QUERY_ERROR",
            details=details,
            recoverable=True,
        )


class GraphitiError(SearchEngineError):
    """Error with Graphiti knowledge graph operations."""

    def __init__(
        self,
        message: str = "Graphiti operation failed",
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="GRAPHITI_ERROR",
            details=details,
            recoverable=True,
        )


class OpenAIEmbeddingError(SearchEngineError):
    """Error generating embeddings with OpenAI."""

    def __init__(
        self,
        message: str = "Failed to generate embeddings",
        text: Optional[str] = None,
        model: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if text:
            details["text_length"] = len(text)
            details["text_preview"] = text[:100] + "..." if len(text) > 100 else text
        if model:
            details["model"] = model
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="OPENAI_EMBEDDING_ERROR",
            details=details,
            recoverable=True,
        )


class SearchConfigurationError(SearchEngineError):
    """Error with search configuration or parameters."""

    def __init__(
        self,
        message: str = "Invalid search configuration",
        parameter: Optional[str] = None,
        value: Optional[Any] = None,
        expected: Optional[str] = None,
    ):
        details = {}
        if parameter:
            details["parameter"] = parameter
        if value is not None:
            details["value"] = value
        if expected:
            details["expected"] = expected

        super().__init__(
            message=message,
            error_code="SEARCH_CONFIG_ERROR",
            details=details,
            recoverable=False,  # Configuration errors are not recoverable without fixing the config
        )


class SearchTimeoutError(SearchEngineError):
    """Error when search operation times out."""

    def __init__(
        self,
        message: str = "Search operation timed out",
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
    ):
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            error_code="SEARCH_TIMEOUT_ERROR",
            details=details,
            recoverable=True,
        )


class FusionStrategyError(SearchEngineError):
    """Error with result fusion strategy."""

    def __init__(
        self,
        message: str = "Result fusion failed",
        strategy: Optional[str] = None,
        result_counts: Optional[Dict[str, int]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if strategy:
            details["strategy"] = strategy
        if result_counts:
            details["result_counts"] = result_counts
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="FUSION_STRATEGY_ERROR",
            details=details,
            recoverable=True,
        )


class SearchResultsEmptyError(SearchEngineError):
    """Error when search returns no results but results were expected."""

    def __init__(
        self,
        message: str = "Search returned no results",
        query: Optional[str] = None,
        search_type: Optional[str] = None,
        filters_applied: Optional[Dict[str, Any]] = None,
    ):
        details = {}
        if query:
            details["query"] = query
        if search_type:
            details["search_type"] = search_type
        if filters_applied:
            details["filters_applied"] = filters_applied

        super().__init__(
            message=message,
            error_code="SEARCH_NO_RESULTS",
            details=details,
            recoverable=False,  # No results is not recoverable by retry
        )


class HybridSearchError(SearchEngineError):
    """Error during hybrid search operations."""

    def __init__(
        self,
        message: str = "Hybrid search operation failed",
        failed_components: Optional[list[str]] = None,
        successful_components: Optional[list[str]] = None,
        original_error: Optional[Exception] = None,
    ):
        details = {}
        if failed_components:
            details["failed_components"] = failed_components
        if successful_components:
            details["successful_components"] = successful_components
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="HYBRID_SEARCH_ERROR",
            details=details,
            recoverable=True,
        )
