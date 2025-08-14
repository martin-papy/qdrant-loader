from __future__ import annotations

from ..interfaces import GraphBuilder


class DefaultGraphBuilder(GraphBuilder):
    """Adapter to legacy graph building via CitationNetworkAnalyzer."""

    def build(self, results):  # type: ignore[override]
        from ...cross_document_intelligence import CitationNetworkAnalyzer  # type: ignore

        analyzer = CitationNetworkAnalyzer()
        return analyzer.build_citation_network(results)


