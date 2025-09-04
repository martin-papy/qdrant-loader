from __future__ import annotations

from ..interfaces import GraphBuilder


class DefaultGraphBuilder(GraphBuilder):
    """Adapter to legacy graph building via CitationNetworkAnalyzer."""

    def build(self, results):  # type: ignore[override]
        # Prefer local CDI citations analyzer; fall back to legacy path. Raise clear error if both fail.
        try:
            from ..citations import CitationNetworkAnalyzer  # type: ignore[misc]
        except (ImportError, ModuleNotFoundError) as first_import_exc:
            try:
                from ..cross_document_intelligence import (
                    CitationNetworkAnalyzer,  # type: ignore[misc]
                )
            except (ImportError, ModuleNotFoundError) as fallback_import_exc:
                # Raise a clear error with both original exceptions chained for debugging context
                message = (
                    "Unable to import CitationNetworkAnalyzer from CDI citations or fallback cross_document_intelligence. "
                    "Attempted imports: 'from ..citations' and 'from ..cross_document_intelligence'."
                )
                raise ImportError(message) from ExceptionGroup(
                    "CitationNetworkAnalyzer import failures",
                    [first_import_exc, fallback_import_exc],
                )

        analyzer = CitationNetworkAnalyzer()
        return analyzer.build_citation_network(results)
