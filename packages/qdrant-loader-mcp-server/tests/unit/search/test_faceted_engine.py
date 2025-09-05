import asyncio
from types import SimpleNamespace


class FakeHybridSearch:
    async def search_with_facets(
        self,
        query,
        limit,
        source_types,
        project_ids,
        facet_filters,
        generate_facets,
    ):
        class FacetType:
            def __init__(self, value):
                self.value = value

            def __hash__(self):
                return hash(self.value)

        facet = SimpleNamespace(
            facet_type=FacetType("source"),
            name="source",
            display_name="Source",
            description="Source type",
            values=[SimpleNamespace(value="confluence", count=2, display_name="Confluence", description="")],
            get_top_values=lambda n: [SimpleNamespace(value="confluence", count=2, display_name="Confluence", description="")],
        )
        return SimpleNamespace(
            results=[SimpleNamespace()],
            facets=[facet],
            total_results=2,
            filtered_count=2,
            applied_filters=facet_filters or [],
            generation_time_ms=1.23,
        )


class FakeEngine:
    def __init__(self):
        self.hybrid_search = FakeHybridSearch()


def test_search_with_facets_basic():
    from qdrant_loader_mcp_server.search.engine.faceted import FacetedSearchOperations

    ops = FacetedSearchOperations(engine=FakeEngine())

    async def run():
        resp = await ops.search_with_facets("q", limit=5, facet_filters=[{"facet_type": "source", "values": ["confluence"], "operator": "OR"}])
        assert resp["total_results"] == 2
        assert resp["filtered_count"] == 2
        assert resp["facets"][0]["type"] == "source"

    asyncio.get_event_loop().run_until_complete(run())


def test_get_facet_suggestions_basic(monkeypatch):
    from qdrant_loader_mcp_server.search.engine.faceted import FacetedSearchOperations

    class FacetType:
        def __init__(self, value):
            self.value = value

        def __hash__(self):
            return hash(self.value)

    class FakeSuggestion:
        def __init__(self):
            self.facets = [
                SimpleNamespace(
                    facet_type=FacetType("source"),
                    name="source",
                    display_name="Source",
                    description="",
                    values=["confluence"],
                    get_top_values=lambda n: [SimpleNamespace(value="confluence", count=2, display_name="Confluence")],
                )
            ]
            self.generation_time_ms = 1.0

    class FakeFacetGen:
        async def generate_facets_from_documents(self, documents, max_facets_per_type, enable_ai_generation):
            return FakeSuggestion()

    # Patch DynamicFacetGenerator used inside the function
    monkeypatch.setattr(
        "qdrant_loader_mcp_server.search.enhanced.faceted_search.DynamicFacetGenerator",
        lambda: FakeFacetGen(),
        raising=True,
    )

    # Build sample docs with minimal attributes used by coverage paths
    docs = [SimpleNamespace(source_type="confluence", project_id="p1", created_at="2024-01-01", topics=["t"], entities=["e"]) ]

    ops = FacetedSearchOperations(engine=FakeEngine())

    async def run():
        out = await ops.get_facet_suggestions(docs, max_facets_per_type=3)
        assert out["suggested_facets"][0]["type"] == "source"
        assert out["generation_metadata"]["total_documents_analyzed"] == 1

    asyncio.get_event_loop().run_until_complete(run())


