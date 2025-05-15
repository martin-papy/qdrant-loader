from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from openai import AsyncOpenAI
import asyncio
import os
import logging
from pathlib import Path
import math
from qdrant_loader.config import initialize_config, get_settings
from qdrant_loader.core.embedding.embedding_service import EmbeddingService
from qdrant_loader.core.search.hybrid_search import HybridSearchService
from qdrant_loader.core.search.faiss_search import FAISSSearchService
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_search():
    logger.info("Starting test search process")

    # Load environment variables
    logger.info("Loading environment variables")
    load_dotenv()

    # Initialize config from test config file
    config_path = Path("config.yaml")
    try:
        initialize_config(config_path)
        settings = get_settings()
    except Exception as e:
        logger.error(f"Failed to initialize config: {str(e)}")
        return

    # Validate environment variables
    required_vars = [
        "QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY", "QDRANT_COLLECTION_NAME"
    ]
    missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return

    # Initialize Qdrant client and embedding service
    logger.info("Initializing Qdrant client and embedding service")
    qdrant = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )
    embedding_service = EmbeddingService(settings)

    # Adapter for FAISSSearchService protocol compliance
    class EmbeddingServiceAdapter:
        def __init__(self, service):
            self._service = service
        async def generate_embedding(self, text: str):
            return await self._service.get_embedding(text)

    embedding_service_adapter = EmbeddingServiceAdapter(embedding_service)

    # Query to test
    query = "What is the PRD of our application?"
    logger.info(f"Running search for query: {query}")

    # Hybrid Search
    logger.info("Running HybridSearchService...")
    hybrid_search = HybridSearchService(
        qdrant_client=qdrant,
        embedding_service=embedding_service,
        collection_name=settings.QDRANT_COLLECTION_NAME,
    )
    try:
        hybrid_results = await hybrid_search.search(query, limit=5)
        print("\nHybrid Search Results:")
        for i, result in enumerate(hybrid_results, 1):
            if i <= 3:
                print(f"\nResult {i} (score={result.score:.4f}, vector={result.vector_score:.4f}, keyword={result.keyword_score:.4f}):")
                content = result.content
                if content:
                    print(f"Full Content (up to 1000 chars): {content[:1000]}")
                else:
                    print("Content is empty.")
                    print(f"Metadata: {result.metadata}")
            else:
                print(f"\nResult {i} (score={result.score:.4f}, vector={result.vector_score:.4f}, keyword={result.keyword_score:.4f}):")
                print(f"Content: {result.content[:200]}...")
                print(f"Metadata: {result.metadata}")
    except Exception as e:
        logger.error(f"Hybrid search failed: {str(e)}")

    # FAISS Search
    logger.info("Running FAISSSearchService...")
    try:
        # Debug: Print collection configuration
        collection_info = qdrant.get_collection(settings.QDRANT_COLLECTION_NAME)
        logger.info(f"Collection info: {collection_info}")
        if collection_info and collection_info.config and collection_info.config.params:
            vector_params = collection_info.config.params.vectors
            logger.info(f"Vector params: {vector_params}")
            logger.info(f"Vector params type: {type(vector_params)}")
            logger.info(f"Vector params keys: {vector_params.keys() if isinstance(vector_params, dict) else 'Not a dict'}")
            if isinstance(vector_params, dict):
                for name, params in vector_params.items():
                    logger.info(f"Vector config for {name}:")
                    logger.info(f"  Size: {params.size}")
                    logger.info(f"  Distance: {params.distance}")
        # Dynamically compute nlist
        num_vectors = getattr(collection_info, 'points_count', None)
        if num_vectors is None:
            # fallback: count points via scroll (slow for large collections)
            num_vectors = 0
            offset = None
            while True:
                scroll_response = qdrant.scroll(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    limit=100,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False
                )
                points = scroll_response[0]
                num_vectors += len(points)
                offset = scroll_response[1]
                if not offset:
                    break
        nlist = max(1, min(100, int(math.sqrt(num_vectors)), num_vectors))
        logger.info(f"Using nlist={nlist} for FAISS IVFFlat (num_vectors={num_vectors})")
        faiss_search = FAISSSearchService(
            qdrant_client=qdrant,
            embedding_service=embedding_service_adapter,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            index_type="IVFFlat",
            nlist=nlist,
            min_score=0.5,
        )
        faiss_results = await faiss_search.search(query, limit=5)
        print("\nFAISS Search Results:")
        for i, result in enumerate(faiss_results, 1):
            print(f"\nResult {i} (score={result['score']:.4f}):")
            print(f"Content: {result['content'][:200]}...")
            print(f"Metadata: {result['metadata']}")
        if not faiss_results:
            print("No FAISS results returned. Debugging info:")
            # Debug: Log distances and indices from FAISS search
            if faiss_search.index is not None:
                query_embedding = await embedding_service_adapter.generate_embedding(query)
                query_vector = np.array([query_embedding], dtype=np.float32)
                distances, indices = faiss_search.index.search(query_vector, 5) # type: ignore
                print(f"FAISS distances: {distances[0]}")
                print(f"FAISS indices: {indices[0]}")
                # Debug: Check if any points are retrieved from Qdrant
                for idx in indices[0]:
                    point_id = int(idx)
                    points = qdrant.retrieve(collection_name=settings.QDRANT_COLLECTION_NAME, ids=[point_id], with_payload=True)
                    if points:
                        print(f"Point {point_id} retrieved: {points[0].payload}")
                    else:
                        print(f"No point found for index {point_id}")
            else:
                print("FAISS index is not initialized.")
    except Exception as e:
        logger.error(f"FAISS search failed: {str(e)}")

    logger.info("Test search process completed")


if __name__ == "__main__":
    logger.info("Starting script execution")
    asyncio.run(test_search())
    logger.info("Script execution completed")
