import uuid

import pytest
from qdrant_client import models
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager


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

    async def test_simple_ingestion_and_retrieval(self):
        """
        Tests a simple document ingestion and verifies its existence in both
        Qdrant and Neo4j.
        """
        doc_id = str(uuid.uuid4())
        content = "This is a test document."
        vector = [0.1] * 1536  # Matching the dimension in conftest

        # 1. Ingest into Qdrant
        await self.qdrant_manager.upsert_points(
            points=[
                models.PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={"content": content, "doc_id": doc_id},
                )
            ]
        )

        # 2. Ingest into Neo4j
        self.neo4j_manager.execute_query(
            "CREATE (d:Document {doc_id: $doc_id, content: $content})",
            parameters={"doc_id": doc_id, "content": content},
        )

        # 3. Verify in Qdrant
        retrieved_points = self.qdrant_client.retrieve(
            collection_name=self.settings.global_config.qdrant.collection_name,
            ids=[doc_id],
            with_payload=True,
        )
        assert len(retrieved_points) == 1
        assert retrieved_points[0].payload["content"] == content

        # 4. Verify in Neo4j
        records = self.neo4j_manager.execute_query(
            "MATCH (d:Document {doc_id: $doc_id}) RETURN d.content AS content",
            parameters={"doc_id": doc_id},
        )
        assert len(records) == 1
        assert records[0]["content"] == content
