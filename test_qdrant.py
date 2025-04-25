from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from openai import AsyncOpenAI
import asyncio
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_search():
    logger.info("Starting test search process")

    # Load environment variables
    logger.info("Loading environment variables")
    load_dotenv()

    # Validate environment variables
    required_vars = ["QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY", "QDRANT_COLLECTION_NAME"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return

    # Initialize clients
    logger.info("Initializing Qdrant client")
    qdrant = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )

    logger.info("Initializing OpenAI client")
    openai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Get embedding for query
    query = "What is the PRD of our application?"
    logger.info(f"Generating embedding for query: {query}")
    try:
        embedding_response = await openai.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        embedding = embedding_response.data[0].embedding
        logger.info(f"Successfully generated embedding of size: {len(embedding)}")
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        return

    # Search with debug info
    logger.info("Preparing search parameters")
    print("\nSearching with parameters:")
    print(f"Collection: {os.environ['QDRANT_COLLECTION_NAME']}")
    print(f"Query: {query}")
    print(f"Embedding size: {len(embedding)}")

    try:
        logger.info("Executing Qdrant search query")
        results = qdrant.query_points(
            collection_name=os.environ["QDRANT_COLLECTION_NAME"],
            query=embedding,
            limit=5,
            score_threshold=0.3,
            search_params=models.SearchParams(hnsw_ef=512, exact=False),
        )
        logger.info(f"Search completed successfully. Found {len(results.points)} results")
    except Exception as e:
        logger.error(f"Failed to execute search query: {str(e)}")
        return

    print("\nSearch results:")
    for i, hit in enumerate(results.points, 1):
        logger.info(f"Processing result {i} with score {hit.score}")
        print(f"\nScore: {hit.score}")
        print(f"Payload: {hit.payload}")

    logger.info("Test search process completed")


if __name__ == "__main__":
    logger.info("Starting script execution")
    asyncio.run(test_search())
    logger.info("Script execution completed")
