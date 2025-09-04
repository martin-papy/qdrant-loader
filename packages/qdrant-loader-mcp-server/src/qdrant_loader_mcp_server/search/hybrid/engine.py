"""
Hybrid Search Engine Implementation.

This module implements the main HybridSearchEngine class that orchestrates
vector search, keyword search, intent classification, knowledge graph integration,
cross-document intelligence, and faceted search capabilities.
"""

from __future__ import annotations

from typing import Any

from ...config import SearchConfig
from ...utils.logging import LoggingConfig
from .api import HybridEngineAPI
from .models import (
    DEFAULT_KEYWORD_WEIGHT,
    DEFAULT_METADATA_WEIGHT,
    DEFAULT_MIN_SCORE,
    DEFAULT_VECTOR_WEIGHT,
    HybridProcessingConfig,
)

logger = LoggingConfig.get_logger(__name__)


class HybridSearchEngine(HybridEngineAPI):
    """Refactored hybrid search service using modular components."""

    def __init__(
        self,
        qdrant_client: Any,
        openai_client: Any,
        collection_name: str,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
        metadata_weight: float = DEFAULT_METADATA_WEIGHT,
        min_score: float = DEFAULT_MIN_SCORE,
        # Enhanced search parameters
        knowledge_graph: Any = None,
        enable_intent_adaptation: bool = True,
        search_config: SearchConfig | None = None,
        processing_config: HybridProcessingConfig | None = None,
    ):
        """Initialize the hybrid search service.

        Args:
            qdrant_client: Qdrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            vector_weight: Weight for vector search scores (0-1)
            keyword_weight: Weight for keyword search scores (0-1)
            metadata_weight: Weight for metadata-based scoring (0-1)
            min_score: Minimum combined score threshold
            knowledge_graph: Optional knowledge graph for integration
            enable_intent_adaptation: Enable intent-aware adaptive search
            search_config: Optional search configuration for performance optimization
            processing_config: Optional processing configuration controlling hybrid processing behaviors
        """
        self.qdrant_client = qdrant_client
        # Use a property-backed attribute so test fixtures can inject a client after init
        self._openai_client = None
        # Assign via setter to allow future propagation when pipeline is ready
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.metadata_weight = metadata_weight
        self.min_score = min_score
        self.logger = LoggingConfig.get_logger(__name__)

        # Centralized initialization via builder
        from .components.builder import initialize_engine_components
        from .models import HybridProcessingConfig as _HPC

        effective_processing_config = processing_config or _HPC()
        initialize_engine_components(
            self,
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name=collection_name,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            metadata_weight=metadata_weight,
            min_score=min_score,
            knowledge_graph=knowledge_graph,
            enable_intent_adaptation=enable_intent_adaptation,
            search_config=search_config,
            processing_config=effective_processing_config,
        )

    @property
    def openai_client(self) -> Any:
        return self._openai_client

    @openai_client.setter
    def openai_client(self, client: Any) -> None:
        # Store locally
        self._openai_client = client
        # Best-effort propagate to vector search service and prefer explicit client over provider
        try:
            vss = getattr(self, "vector_search_service", None)
            if vss is not None:
                try:
                    vss.openai_client = client
                    if client is not None:
                        # Prefer explicit OpenAI client; disable provider to avoid NotImplemented stubs
                        vss.embeddings_provider = None
                except Exception:
                    pass
        except Exception:
            pass

    async def search(self, *args, **kwargs):  # type: ignore[override]
        try:
            return await super().search(*args, **kwargs)
        except Exception as e:
            self.logger.error(
                "Error in hybrid search", error=str(e), query=kwargs.get("query")
            )
            raise

    # All other public and internal methods are provided by HybridEngineAPI
