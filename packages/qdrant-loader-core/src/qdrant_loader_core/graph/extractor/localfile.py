from __future__ import annotations

from pathlib import PurePath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qdrant_loader.core.document import Document

from ..models import (
    CoreNodeLabel,
    GraphNode,
    PersonInfo,
)
from .base_extractor import BaseEntityExtractor


class LocalFileEntityExtractor(BaseEntityExtractor):
    """
    Extract graph entities from local filesystem documents.
    """

    source_type = "localfile"

    def _project(self, doc: Document) -> str | None:
        """
        Local files are not associated with a project.
        """
        return None

    def _extract_people(
        self,
        doc: Document,
    ) -> list[tuple[PersonInfo, str]]:
        """
        Local files do not expose author information by default.
        """
        return []

    def _extract_container(
        self,
        doc: Document,
    ) -> GraphNode | None:

        if not doc.url:
            return None

        pure_path = PurePath(doc.url)

        parent_path = str(pure_path.parent)
        directory = "root" if parent_path == "." else parent_path
        directory_name = PurePath(directory).name if directory != "root" else "root"

        return GraphNode(
            id=f"dir:{directory}",
            label=CoreNodeLabel.CONTAINER.value,
            project=None,
            properties={
                "kind": "filesystem_dir",
                "name": directory_name,
                "path": directory,
            },
        )

    def _build_document_node(
        self,
        doc: Document,
        project: str | None,
    ) -> GraphNode:
        """
        Build a document node enriched with filesystem metadata.
        """

        file_name = doc.metadata.get("file_name")

        return GraphNode(
            id=doc.id,
            label=CoreNodeLabel.DOCUMENT.value,
            project=project,
            properties={
                "title": file_name,
                "url": doc.url,
                "created_at": doc.metadata.get("created_at"),
                "updated_at": doc.metadata.get("updated_at"),
                "source_type": self.source_type,
            },
        )
