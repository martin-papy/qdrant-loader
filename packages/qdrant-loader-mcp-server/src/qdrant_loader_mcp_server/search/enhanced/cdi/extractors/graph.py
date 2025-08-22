from __future__ import annotations

from ..interfaces import GraphBuilder


class DefaultGraphBuilder(GraphBuilder):
    """Adapter to legacy graph building via CitationNetworkAnalyzer."""

    def build(self, results):  # type: ignore[override]
        # Prefer local CDI citations analyzer; fall back to legacy path. Raise clear error if both fail.
        try:
            from ..citations import CitationNetworkAnalyzer  # type: ignore[misc]
        except Exception:
            try:
                from ...cross_document_intelligence import CitationNetworkAnalyzer  # type: ignore
            except Exception as e:
                raise ImportError(
                    "Unable to import CitationNetworkAnalyzer from CDI citations or legacy cross_document_intelligence. "
                    "Attempted imports: 'from ..citations' and legacy 'from ...cross_document_intelligence'."
                ) from e

        analyzer = CitationNetworkAnalyzer()
        return analyzer.build_citation_network(results)


