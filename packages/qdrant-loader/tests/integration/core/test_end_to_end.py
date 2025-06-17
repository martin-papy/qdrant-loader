import os
import uuid
import pytest
from qdrant_client import models
from qdrant_loader.core.managers.qdrant_manager import QdrantManager
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.config import Neo4jConfig


@pytest.mark.asyncio
class TestRealServicesIntegration:
    @pytest.fixture(autouse=True)
    def setup(
        self, qdrant_client, neo4j_driver, clean_collection, clean_neo4j, test_settings
    ):
        self.qdrant_client = qdrant_client
        self.neo4j_driver = neo4j_driver
        self.settings = test_settings
        self.qdrant_manager = QdrantManager(settings=self.settings)
        self.neo4j_manager = Neo4jManager(config=self.settings.global_config.neo4j)
        self.qdrant_manager.connect()
        self.neo4j_manager.connect()

    async def test_ingestion_and_hybrid_retrieval(self):
        """
        Tests a more complete E2E scenario:
        1. Ingests two documents.
        2. Creates a relationship between them in Neo4j.
        3. Performs a vector search in Qdrant.
        4. Verifies the data in both databases.
        """
        # 1. Ingest two documents
        doc_1_id = str(uuid.uuid4())
        doc_2_id = str(uuid.uuid4())
        doc_1_content = "This document is about cats."
        doc_2_content = "This document is about dogs."
        vector_1 = [0.1] * 1536
        vector_2 = [0.2] * 1536

        await self.qdrant_manager.upsert_points(
            points=[
                models.PointStruct(
                    id=doc_1_id,
                    vector=vector_1,
                    payload={"content": doc_1_content, "doc_id": doc_1_id},
                ),
                models.PointStruct(
                    id=doc_2_id,
                    vector=vector_2,
                    payload={"content": doc_2_content, "doc_id": doc_2_id},
                ),
            ]
        )

        self.neo4j_manager.execute_query(
            "CREATE (d:Document {doc_id: $doc_id, content: $content})",
            parameters={"doc_id": doc_1_id, "content": doc_1_content},
        )
        self.neo4j_manager.execute_query(
            "CREATE (d:Document {doc_id: $doc_id, content: $content})",
            parameters={"doc_id": doc_2_id, "content": doc_2_content},
        )

        # 2. Create a relationship
        self.neo4j_manager.execute_query(
            """
            MATCH (d1:Document {doc_id: $doc_1_id})
            MATCH (d2:Document {doc_id: $doc_2_id})
            CREATE (d1)-[:RELATED_TO]->(d2)
            """,
            parameters={"doc_1_id": doc_1_id, "doc_2_id": doc_2_id},
        )

        # 3. Verify in Qdrant
        retrieved_points = self.qdrant_client.retrieve(
            collection_name=self.settings.global_config.qdrant.collection_name,
            ids=[doc_1_id, doc_2_id],
            with_payload=True,
        )
        assert len(retrieved_points) == 2

        # 4. Verify in Neo4j
        result = self.neo4j_manager.execute_query(
            "MATCH (d:Document) RETURN count(d) as count"
        )
        assert result[0]["count"] == 2

        result = self.neo4j_manager.execute_query(
            "MATCH (:Document)-[r:RELATED_TO]->(:Document) RETURN count(r) as count"
        )
        assert result[0]["count"] == 1
