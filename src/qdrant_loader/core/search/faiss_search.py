"""FAISS-based vector search implementation."""

import logging
from typing import List, Dict, Any, Optional, Tuple, cast, Protocol, Union
import numpy as np
import faiss
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_loader.core.embedding import EmbeddingService

logger = logging.getLogger(__name__)

class EmbeddingServiceProtocol(Protocol):
    """Protocol for embedding service."""
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        ...

class FAISSSearchService:
    """Service for performing vector search using FAISS."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_service: EmbeddingServiceProtocol,
        collection_name: str,
        index_type: str = "IVFFlat",
        nlist: int = 100,
        nprobe: int = 10,
        min_score: float = 0.7
    ):
        """Initialize the FAISS search service.

        Args:
            qdrant_client: Qdrant client instance
            embedding_service: Embedding service instance
            collection_name: Name of the Qdrant collection
            index_type: Type of FAISS index to use (IVFFlat, Flat, HNSW)
            nlist: Number of clusters for IVFFlat index
            nprobe: Number of clusters to probe during search
            min_score: Minimum similarity score threshold
        """
        self.qdrant_client = qdrant_client
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.index_type = index_type
        self.nlist = nlist
        self.nprobe = nprobe
        self.min_score = min_score
        self.index: Optional[faiss.Index] = None
        self.vector_dim: Optional[int] = None
        self.id_map: list = []  # Mapping from FAISS index to Qdrant point ID
        self._initialize_index()

    def _initialize_index(self) -> None:
        """Initialize the FAISS index."""
        try:
            # Get collection info to determine vector dimension
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            if not collection_info or not collection_info.config or not collection_info.config.params:
                raise ValueError("Invalid collection configuration")
            
            vector_params = collection_info.config.params.vectors
            # Support both single-vector and multi-vector collections
            if isinstance(vector_params, dict):
                # Multi-vector: get the first config
                first_vector_config = next(iter(vector_params.values()), None)
            elif hasattr(vector_params, 'size'):
                # Single-vector: use directly
                first_vector_config = vector_params
            else:
                raise ValueError("Invalid vector parameters")
            
            if first_vector_config is None or not hasattr(first_vector_config, 'size'):
                raise ValueError("Vector configuration must have a size attribute")
            self.vector_dim = first_vector_config.size
            if not isinstance(self.vector_dim, int):
                raise ValueError("Vector size must be an integer")

            # Create appropriate index based on type
            if self.index_type == "IVFFlat":
                quantizer = faiss.IndexFlatL2(self.vector_dim)
                self.index = faiss.IndexIVFFlat(quantizer, self.vector_dim, self.nlist)
                if self.index is not None:
                    self.index.nprobe = self.nprobe
            elif self.index_type == "Flat":
                self.index = faiss.IndexFlatL2(self.vector_dim)
            elif self.index_type == "HNSW":
                self.index = faiss.IndexHNSWFlat(self.vector_dim, 32)  # 32 is the number of neighbors
            else:
                raise ValueError(f"Unsupported index type: {self.index_type}")

            if self.index is None:
                raise ValueError("Failed to create FAISS index")

            # Load vectors from Qdrant into FAISS
            self._load_vectors()

        except Exception as e:
            logger.error(f"Error initializing FAISS index: {str(e)}")
            raise

    def _load_vectors(self) -> None:
        """Load vectors from Qdrant into FAISS index."""
        try:
            if self.index is None:
                raise ValueError("FAISS index not initialized")

            self.id_map = []  # Reset mapping
            # Scroll through all points in the collection
            offset = None
            while True:
                scroll_response = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=False,
                    with_vectors=True
                )
                
                points = scroll_response[0]
                if not points:
                    break

                # Extract vectors and add to index
                vectors = np.array([point.vector for point in points], dtype=np.float32)
                # Store the mapping from FAISS index to Qdrant point ID
                for point in points:
                    self.id_map.append(point.id)
                if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
                    self.index.train(vectors)  # type: ignore
                self.index.add(vectors)  # type: ignore

                offset = scroll_response[1]
                if not offset:
                    break

        except Exception as e:
            logger.error(f"Error loading vectors into FAISS: {str(e)}")
            raise

    async def search(
        self,
        query: str,
        limit: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector search using FAISS.

        Args:
            query: Search query
            limit: Maximum number of results to return
            filter_conditions: Optional filter conditions

        Returns:
            List of search results with scores
        """
        try:
            if self.index is None:
                raise ValueError("FAISS index not initialized")

            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            query_vector = np.array([query_embedding], dtype=np.float32)

            # Search in FAISS index
            distances, indices = self.index.search(query_vector, limit)  # type: ignore

            # Get corresponding points from Qdrant
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if distance < self.min_score:
                    continue
                # Map FAISS index to Qdrant point ID
                if idx < 0 or idx >= len(self.id_map):
                    continue
                point_id = self.id_map[idx]
                # Get point from Qdrant
                points = self.qdrant_client.retrieve(
                    collection_name=self.collection_name,
                    ids=[point_id],
                    with_payload=True
                )
                
                if not points:
                    continue
                    
                point = points[0]
                if not point or not point.payload:
                    continue

                # Apply filters if specified
                if filter_conditions and not self._check_filters(cast(Dict[str, Any], point.payload), filter_conditions):
                    continue

                results.append({
                    "id": point.id,
                    "score": float(distance),
                    "content": point.payload.get("content", ""),
                    "metadata": point.payload.get("metadata", {})
                })

            return results

        except Exception as e:
            logger.error(f"Error performing FAISS search: {str(e)}")
            raise

    def _check_filters(self, payload: Dict[str, Any], filter_conditions: Dict[str, Any]) -> bool:
        """Check if a point's payload matches filter conditions.

        Args:
            payload: Point payload
            filter_conditions: Filter conditions to check

        Returns:
            Boolean indicating if point matches filters
        """
        for key, value in filter_conditions.items():
            if key not in payload:
                return False
            if payload[key] != value:
                return False
        return True

    def update_index(self) -> None:
        """Update the FAISS index with new vectors from Qdrant."""
        try:
            if self.index is None:
                raise ValueError("FAISS index not initialized")

            # Clear existing index
            self.index.reset()
            
            # Reload vectors
            self._load_vectors()
            
            logger.info("FAISS index updated successfully")
        except Exception as e:
            logger.error(f"Error updating FAISS index: {str(e)}")
            raise 