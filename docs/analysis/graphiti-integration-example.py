"""
Example integration of Graphiti with QDrant Loader
This demonstrates how to enhance document processing with knowledge graph capabilities

NOTE: This is a CONCEPTUAL EXAMPLE showing how the integration would work.
      It assumes both graphiti-core and qdrant-loader packages are installed.
      Some imports and methods are simplified for clarity.
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime

# These imports would be available after installing graphiti-core
from graphiti_core import Graphiti  # type: ignore
from graphiti_core.llm_client import OpenAIClient, LLMConfig  # type: ignore
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig  # type: ignore
from qdrant_client import QdrantClient

# These are from the qdrant-loader package
from qdrant_loader.core.document import Document
from qdrant_loader.core.embedding_service import EmbeddingService


class GraphitiEnhancedLoader:
    """Enhanced document loader that combines vector search with knowledge graphs."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        openai_api_key: str,
    ):
        # Initialize QDrant components
        self.qdrant_client = qdrant_client
        self.embedding_service = EmbeddingService(
            client=openai_api_key,
            model_name="text-embedding-3-small",
        )

        # Initialize Graphiti
        self.graphiti = Graphiti(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            llm_client=OpenAIClient(
                llm_config=LLMConfig(
                    api_key=openai_api_key, model="gpt-4", small_model="gpt-3.5-turbo"
                )
            ),
            embedder=OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key=openai_api_key, embedding_model="text-embedding-3-small"
                )
            ),
        )

    async def process_document(self, document: Document) -> Dict[str, Any]:
        """Process a document through both vector and graph pipelines."""

        # 1. Extract entities and relationships using Graphiti
        episode_data = {
            "content": document.content,
            "metadata": {
                "source": document.source,
                "source_type": document.source_type,
                "title": document.title,
                "url": document.url,
                "timestamp": document.created_at.isoformat(),
                **document.metadata,
            },
        }

        # Add to knowledge graph
        await self.graphiti.add_episode(
            name=document.title,
            episode_body=document.content,
            source_description=f"{document.source_type}: {document.source}",
            reference_time=document.created_at,
        )

        # 2. Process for vector search (existing functionality)
        chunks = self._chunk_document(document)
        embeddings = await self.embedding_service.embed_batch(  # type: ignore
            [chunk.content for chunk in chunks]
        )

        # Store in QDrant
        await self._store_in_qdrant(chunks, embeddings)

        # 3. Extract additional insights from the graph
        entities = await self._extract_entities_from_graph(document.id)

        return {
            "document_id": document.id,
            "chunks_created": len(chunks),
            "entities_extracted": len(entities),
            "entities": entities,
        }

    async def enhanced_search(
        self,
        query: str,
        limit: int = 10,
        use_graph: bool = True,
        use_vector: bool = True,
    ) -> List[Dict[str, Any]]:
        """Perform enhanced search combining vector and graph results."""

        results = []

        # 1. Vector search in QDrant
        if use_vector:
            vector_results = await self._vector_search(query, limit)
            results.extend(vector_results)

        # 2. Graph search in Graphiti
        if use_graph:
            # Search for relevant edges (relationships)
            graph_results = await self.graphiti.search(query=query, num_results=limit)

            # Convert graph results to standard format
            for edge in graph_results:
                results.append(
                    {
                        "type": "relationship",
                        "score": edge.score,
                        "source_entity": edge.source_node_name,
                        "target_entity": edge.target_node_name,
                        "relationship": edge.fact,
                        "metadata": edge.metadata,
                    }
                )

        # 3. Rerank combined results using graph distance
        if use_graph and use_vector and results:
            results = await self.graphiti.rerank(results)

        return results[:limit]

    async def find_relationships(
        self, entity: str, relationship_type: str = None, depth: int = 2  # type: ignore
    ) -> Dict[str, Any]:
        """Find all relationships for a given entity."""

        # Search for the entity in the graph
        entity_results = await self.graphiti.search(query=entity, num_results=50)

        relationships = {
            "entity": entity,
            "direct_relationships": [],
            "indirect_relationships": [],
        }

        # Process direct relationships
        for edge in entity_results:
            if edge.source_node_name == entity or edge.target_node_name == entity:
                if not relationship_type or relationship_type in edge.fact:
                    relationships["direct_relationships"].append(
                        {
                            "type": edge.fact,
                            "related_entity": (
                                edge.target_node_name
                                if edge.source_node_name == entity
                                else edge.source_node_name
                            ),
                            "confidence": edge.score,
                            "valid_from": edge.valid_from,
                            "valid_to": edge.valid_to,
                        }
                    )

        # TODO: Implement graph traversal for indirect relationships

        return relationships

    async def analyze_impact(self, entity: str) -> Dict[str, Any]:
        """Analyze the impact of changes to an entity."""

        # Find all entities that depend on this one
        dependencies = await self.find_relationships(
            entity, relationship_type="depends_on"
        )

        # Find all documents mentioning this entity
        document_results = await self.enhanced_search(
            query=entity, use_graph=True, use_vector=True
        )

        return {
            "entity": entity,
            "direct_dependencies": len(dependencies["direct_relationships"]),
            "affected_documents": len(document_results),
            "impact_summary": self._generate_impact_summary(
                dependencies, document_results
            ),
        }

    async def get_temporal_context(
        self, entity: str, start_date: datetime = None, end_date: datetime = None  # type: ignore
    ) -> List[Dict[str, Any]]:
        """Get temporal context for an entity."""

        # Search for all edges related to the entity
        all_edges = await self.graphiti.search(query=entity, num_results=100)

        # Filter by time range
        temporal_edges = []
        for edge in all_edges:
            if start_date and edge.valid_from < start_date:
                continue
            if end_date and edge.valid_to and edge.valid_to > end_date:
                continue

            temporal_edges.append(
                {
                    "timestamp": edge.created_at,
                    "fact": edge.fact,
                    "entities": [edge.source_node_name, edge.target_node_name],
                    "valid_from": edge.valid_from,
                    "valid_to": edge.valid_to,
                    "metadata": edge.metadata,
                }
            )

        # Sort by timestamp
        temporal_edges.sort(key=lambda x: x["timestamp"])

        return temporal_edges

    def _chunk_document(self, document: Document) -> List[Document]:
        """Chunk document for vector storage (simplified)."""
        # This would use the actual chunking logic from qdrant-loader
        chunks = []
        # ... chunking implementation ...
        return chunks

    async def _store_in_qdrant(
        self, chunks: List[Document], embeddings: List[List[float]]
    ):
        """Store chunks and embeddings in QDrant."""
        # This would use the actual QDrant storage logic
        pass

    async def _vector_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform vector search in QDrant."""
        # This would use the actual QDrant search logic
        return []

    async def _extract_entities_from_graph(
        self, document_id: str
    ) -> List[Dict[str, Any]]:
        """Extract entities related to a document from the graph."""
        # Search for edges mentioning the document
        edges = await self.graphiti.search(query=document_id, num_results=50)

        entities = []
        seen = set()

        for edge in edges:
            # Add source entity
            if edge.source_node_name not in seen:
                seen.add(edge.source_node_name)
                entities.append(
                    {"name": edge.source_node_name, "type": edge.source_node_type}
                )

            # Add target entity
            if edge.target_node_name not in seen:
                seen.add(edge.target_node_name)
                entities.append(
                    {"name": edge.target_node_name, "type": edge.target_node_type}
                )

        return entities

    def _generate_impact_summary(
        self, dependencies: Dict[str, Any], documents: List[Dict[str, Any]]
    ) -> str:
        """Generate a summary of impact analysis."""
        summary = (
            f"Found {len(dependencies['direct_relationships'])} direct dependencies "
        )
        summary += f"and {len(documents)} related documents. "

        if dependencies["direct_relationships"]:
            summary += "Key dependencies: "
            deps = [
                rel["related_entity"]
                for rel in dependencies["direct_relationships"][:3]
            ]
            summary += ", ".join(deps)
            if len(dependencies["direct_relationships"]) > 3:
                summary += f", and {len(dependencies['direct_relationships']) - 3} more"

        return summary


# Example usage for MCP Server integration
class GraphitiMCPTools:
    """MCP tools enhanced with Graphiti capabilities."""

    def __init__(self, loader: GraphitiEnhancedLoader):
        self.loader = loader

    async def search_with_relationships(
        self, query: str, include_graph: bool = True, limit: int = 10
    ) -> Dict[str, Any]:
        """Enhanced search that includes relationship context."""

        results = await self.loader.enhanced_search(
            query=query, limit=limit, use_graph=include_graph, use_vector=True
        )

        # Enrich results with relationship context
        enriched_results = []
        for result in results:
            if result["type"] == "relationship":
                # This is a graph result
                enriched_results.append(
                    {
                        "type": "relationship",
                        "description": f"{result['source_entity']} {result['relationship']} {result['target_entity']}",
                        "score": result["score"],
                        "context": result["metadata"],
                    }
                )
            else:
                # This is a vector result - enrich with graph data
                entities = await self.loader._extract_entities_from_graph(
                    result.get("document_id", "")
                )
                enriched_results.append(
                    {
                        "type": "document",
                        "content": result["content"],
                        "score": result["score"],
                        "entities": entities,
                        "metadata": result["metadata"],
                    }
                )

        return {
            "query": query,
            "results": enriched_results,
            "total_results": len(enriched_results),
        }

    async def trace_dependencies(
        self, component: str, max_depth: int = 3
    ) -> Dict[str, Any]:
        """Trace all dependencies of a component."""

        dependencies = await self.loader.find_relationships(
            entity=component, relationship_type="depends_on", depth=max_depth
        )

        return {
            "component": component,
            "dependency_tree": self._build_dependency_tree(dependencies),
            "total_dependencies": len(dependencies["direct_relationships"])
            + len(dependencies["indirect_relationships"]),
        }

    async def explain_architecture(self, system: str) -> Dict[str, Any]:
        """Explain the architecture of a system using the knowledge graph."""

        # Find all components of the system
        components = await self.loader.find_relationships(
            entity=system, relationship_type="contains"
        )

        # Find interactions between components
        interactions = []
        for comp in components["direct_relationships"]:
            comp_interactions = await self.loader.find_relationships(
                entity=comp["related_entity"], relationship_type="interacts_with"
            )
            interactions.extend(comp_interactions["direct_relationships"])

        return {
            "system": system,
            "components": components["direct_relationships"],
            "interactions": interactions,
            "summary": self._generate_architecture_summary(components, interactions),
        }

    def _build_dependency_tree(self, dependencies: Dict[str, Any]) -> Dict[str, Any]:
        """Build a tree structure from flat dependency list."""
        # Simplified implementation
        return {
            "root": dependencies["entity"],
            "children": [
                {
                    "name": dep["related_entity"],
                    "type": dep["type"],
                    "confidence": dep["confidence"],
                }
                for dep in dependencies["direct_relationships"]
            ],
        }

    def _generate_architecture_summary(
        self, components: Dict[str, Any], interactions: List[Dict[str, Any]]
    ) -> str:
        """Generate a summary of system architecture."""
        summary = f"The system consists of {len(components['direct_relationships'])} main components. "
        summary += f"There are {len(interactions)} interactions between components. "

        # Add key components
        if components["direct_relationships"]:
            key_components = [
                c["related_entity"] for c in components["direct_relationships"][:3]
            ]
            summary += f"Key components include: {', '.join(key_components)}."

        return summary


# Example of how this would be used in practice
async def main():
    # Initialize the enhanced loader
    loader = GraphitiEnhancedLoader(
        qdrant_client=QdrantClient("localhost:6333"),
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        openai_api_key="your-api-key",
    )

    # Process a document
    document = Document(
        title="Authentication Service Documentation",
        content="The authentication service handles user login...",
        source_type="confluence",
        source="internal-docs",
        url="https://confluence.example.com/auth-service",
        metadata={"author": "John Doe", "version": "2.0"},
    )

    result = await loader.process_document(document)
    print(f"Processed document: {result}")

    # Perform enhanced search
    search_results = await loader.enhanced_search(
        query="How does authentication work?", use_graph=True, use_vector=True
    )
    print(f"Search results: {search_results}")

    # Find relationships
    auth_relationships = await loader.find_relationships(
        entity="authentication_service", relationship_type="depends_on"
    )
    print(f"Authentication service dependencies: {auth_relationships}")

    # Analyze impact
    impact = await loader.analyze_impact("user_api")
    print(f"Impact of changing user_api: {impact}")


if __name__ == "__main__":
    asyncio.run(main())
