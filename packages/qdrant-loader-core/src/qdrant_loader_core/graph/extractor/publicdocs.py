from urllib.parse import urlparse

from qdrant_loader.core.document import Document
from qdrant_loader_core.graph.extractor.base_extractor import (
    BaseEntityExtractor,
)
from qdrant_loader_core.graph.models import (
    CoreEdgeType,
    CoreNodeLabel,
    GraphEdge,
    GraphNode,
)


class PublicDocsEntityExtractor(BaseEntityExtractor):
    """
    Public documentation graph extractor.

    Extracts:
    - Document node from page
    - Container node from website/domain
    - LINKS_TO edges between pages
    - Attachment nodes
    """

    source_type = "publicdocs"

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    def _project(
        self,
        doc: Document,
    ) -> str | None:
        url = doc.metadata.get("url")

        if not url:
            return None

        parsed = urlparse(url)

        return parsed.netloc

    # ------------------------------------------------------------------
    # People
    # ------------------------------------------------------------------

    def _extract_people(
        self,
        doc: Document,
    ) -> list:
        return []

    # ------------------------------------------------------------------
    # Container
    # ------------------------------------------------------------------

    def _extract_container(
        self,
        doc: Document,
    ) -> GraphNode | None:
        url = doc.metadata.get("url")

        if not url:
            return None

        parsed = urlparse(url)

        domain = parsed.netloc

        if not domain:
            return None

        return GraphNode(
            id=f"site:{domain}",
            label=CoreNodeLabel.CONTAINER,
            project=domain,
            properties={
                "kind": "website",
                "domain": domain,
            },
        )

    def _extract_labels(
        self,
        doc: Document,
    ) -> list[GraphNode]:
        project = self._project(doc)

        return [
            GraphNode(
                id=f"label:{tag}",
                label=CoreNodeLabel.LABEL,
                project=project,
                properties={"name": tag},
            )
            for tag in doc.metadata.get("tags", [])
        ]

    # ------------------------------------------------------------------
    # Links + Attachments
    # ------------------------------------------------------------------

    def _extract_source_specific(
        self,
        doc: Document,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        project = self._project(doc)

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # --------------------------------------------------------------
        # Internal links
        # --------------------------------------------------------------

        for link in doc.metadata.get("links", []):
            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=link,
                    edge_type=CoreEdgeType.LINKS_TO,
                    project=project,
                )
            )

        # --------------------------------------------------------------
        # Attachments
        # --------------------------------------------------------------

        for attachment in doc.metadata.get("attachments", []):
            attachment_id = attachment.get("id")

            if not attachment_id:
                continue

            nodes.append(
                GraphNode(
                    id=f"attachment:{attachment_id}",
                    label="Attachment",
                    project=project,
                    properties={
                        "filename": attachment.get("filename"),
                        "mime_type": attachment.get("mime_type"),
                        "download_url": attachment.get("download_url"),
                    },
                )
            )

            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=f"attachment:{attachment_id}",
                    edge_type=CoreEdgeType.HAS_ATTACHMENT,
                    project=project,
                )
            )

        return nodes, edges
