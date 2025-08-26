"""
Citation Network Analysis for Cross-Document Intelligence.

This module implements citation and reference network analysis between documents,
building networks from cross-references, hierarchical relationships, and calculating
centrality scores to identify authoritative and well-connected documents.
"""

from __future__ import annotations

import time

from ....utils.logging import LoggingConfig
from ...models import SearchResult
from .models import CitationNetwork


class CitationNetworkAnalyzer:
    """Analyzes citation and reference networks between documents."""

    def __init__(self):
        """Initialize the citation network analyzer."""
        self.logger = LoggingConfig.get_logger(__name__)

    def build_citation_network(self, documents: list[SearchResult]) -> CitationNetwork:
        """Build citation network from document cross-references and hierarchical relationships."""
        start_time = time.time()

        network = CitationNetwork()
        doc_lookup = {f"{doc.source_type}:{doc.source_title}": doc for doc in documents}

        # Add nodes to the network
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            network.nodes[doc_id] = {
                "title": doc.source_title,
                "source_type": doc.source_type,
                "project_id": doc.project_id,
                "word_count": doc.word_count or 0,
                "has_code": doc.has_code_blocks,
                "has_tables": doc.has_tables,
                "depth": doc.depth or 0,
                "creation_date": getattr(doc, "created_at", None),
            }

        # Add edges based on cross-references
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"

            # Process cross-references
            if doc.cross_references:
                for ref in doc.cross_references:
                    target_url = ref.get("url", "") if isinstance(ref, dict) else ""
                    ref_text = (
                        ref.get("text", "") if isinstance(ref, dict) else str(ref)
                    )

                    # Try to find referenced document
                    target_doc_id = self._find_referenced_document(
                        target_url, doc_lookup
                    )
                    if target_doc_id and target_doc_id != doc_id:
                        network.edges.append(
                            (
                                doc_id,
                                target_doc_id,
                                {
                                    "relation_type": "cross_reference",
                                    "reference_text": ref_text,
                                    "reference_url": target_url,
                                    "weight": 1.0,
                                },
                            )
                        )

            # Add hierarchical relationships
            if doc.parent_id is not None:
                if doc.parent_id in doc_lookup:
                    network.edges.append(
                        (
                            doc.parent_id,
                            doc_id,
                            {
                                "relation_type": "hierarchical_child",
                                "weight": 2.0,  # Higher weight for hierarchical relationships
                            },
                        )
                    )
                else:
                    # Parent declared but not found; log for visibility and skip
                    self.logger.debug(
                        "Parent ID not found in documents for hierarchical edge",
                        child_id=doc_id,
                        parent_id=doc.parent_id,
                    )

            # Add sibling relationships
            if doc.sibling_sections:
                for sibling in doc.sibling_sections:
                    sibling_doc_id = self._find_sibling_document(
                        sibling, doc_lookup, doc
                    )
                    if sibling_doc_id and sibling_doc_id != doc_id:
                        network.edges.append(
                            (
                                doc_id,
                                sibling_doc_id,
                                {"relation_type": "sibling", "weight": 0.5},
                            )
                        )

        # Build NetworkX graph and calculate centrality scores
        network.build_graph()
        network.calculate_centrality_scores()

        processing_time = (time.time() - start_time) * 1000
        self.logger.info(
            f"Built citation network with {len(network.nodes)} nodes and {len(network.edges)} edges in {processing_time:.2f}ms"
        )

        return network

    def _find_referenced_document(
        self, reference_url: str, doc_lookup: dict[str, SearchResult]
    ) -> str | None:
        """Find document that matches a reference URL."""
        if not reference_url:
            return None

        # Try exact URL match first
        for doc_id, doc in doc_lookup.items():
            if doc.source_url and reference_url in doc.source_url:
                return doc_id

        # Try title-based matching for internal references
        for doc_id, doc in doc_lookup.items():
            if reference_url.lower() in doc.source_title.lower():
                return doc_id

        return None

    def _find_sibling_document(
        self,
        sibling_reference: str,
        doc_lookup: dict[str, SearchResult],
        current_doc: SearchResult | None = None,
    ) -> str | None:
        """Find document that matches a sibling reference.

        Uses normalized whole-phrase matching and, when available, validates
        via explicit hierarchy metadata (matching parent identifiers) to avoid
        false positives from broad substring checks.
        """
        import re

        if not sibling_reference:
            return None

        def normalize_title(value: str) -> str:
            # Lowercase and keep word characters joined by single spaces
            tokens = re.findall(r"\w+", (value or "").lower())
            return " ".join(tokens)

        target_norm = normalize_title(sibling_reference)

        for doc_id, candidate in doc_lookup.items():
            # Prefer siblings within the same source type when known
            if current_doc is not None:
                if getattr(current_doc, "source_type", None) and (
                    candidate.source_type != current_doc.source_type
                ):
                    continue

                # Skip self
                if candidate is current_doc:
                    continue

            cand_title_norm = normalize_title(getattr(candidate, "source_title", ""))
            if not cand_title_norm:
                continue

            # Exact normalized title match or whole-phrase match using word boundaries
            if target_norm == cand_title_norm or re.search(
                r"\b" + re.escape(target_norm) + r"\b", cand_title_norm
            ):
                # Validate using parent metadata if both sides provide it
                parent_ok = True
                if current_doc is not None:
                    cur_parent_id = getattr(current_doc, "parent_id", None)
                    cand_parent_id = getattr(candidate, "parent_id", None)
                    if cur_parent_id is not None and cand_parent_id is not None:
                        parent_ok = cur_parent_id == cand_parent_id

                    if parent_ok:
                        cur_parent_doc_id = getattr(
                            current_doc, "parent_document_id", None
                        )
                        cand_parent_doc_id = getattr(
                            candidate, "parent_document_id", None
                        )
                        if (
                            cur_parent_doc_id is not None
                            and cand_parent_doc_id is not None
                        ):
                            parent_ok = cur_parent_doc_id == cand_parent_doc_id

                if parent_ok:
                    return doc_id

        return None

    def get_most_authoritative_documents(
        self, network: CitationNetwork, limit: int = 10
    ) -> list[tuple[str, float]]:
        """Get the most authoritative documents based on citation analysis."""
        if not network.authority_scores:
            return []

        # Sort by authority score
        sorted_docs = sorted(
            network.authority_scores.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_docs[:limit]

    def get_most_connected_documents(
        self, network: CitationNetwork, limit: int = 10
    ) -> list[tuple[str, int]]:
        """Get the most connected documents based on degree centrality."""
        if not network.graph:
            return []

        # Calculate degree centrality
        degree_centrality = dict(network.graph.degree())
        sorted_docs = sorted(
            degree_centrality.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_docs[:limit]
