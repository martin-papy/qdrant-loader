from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from qdrant_loader.core.document import Document

from qdrant_loader_core.graph.extractor.base_extractor import (
    BaseEntityExtractor,
)
from qdrant_loader_core.graph.models import (
    CoreEdgeType,
    CoreNodeLabel,
    GraphEdge,
    GraphNode,
    PersonInfo,
)


class JiraEntityExtractor(BaseEntityExtractor):
    """
    Jira graph extractor.

    Extracts:
    - Document node (status, priority, issue_type)
    - Person nodes (reporter, assignee)
    - Container node (jira project)
    - Label nodes
    - Linked issue relationships
    - Parent/subtask relationships
    - Cross-source links from URLs found in description
    """

    # NOTE:
    # Jira API currently provides `linked_issues` as list[str] without relationship types
    # (e.g., "blocks", "duplicates", etc.), so we default to "kind=related".
    # This can be enhanced when richer link metadata becomes available.

    # Additionally, epic relationships are not implemented because the current data model
    # does not include an `epic_key` or equivalent field. Support for epic-child relationships
    # can be added once such metadata is available.

    source_type = "jira"

    CONFLUENCE_URL_RE = re.compile(
        r"https?://[^\s]*confluence[^\s]+",
        re.IGNORECASE,
    )

    GIT_URL_RE = re.compile(
        r"https?://(?:github|gitlab|bitbucket)[^\s]+",
        re.IGNORECASE,
    )

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    def _project(
        self,
        doc: Document,
    ) -> str | None:
        return doc.metadata.get("project_key")

    # ------------------------------------------------------------------
    # Document
    # ------------------------------------------------------------------

    def _build_document_node(
        self,
        doc: Document,
        project: str | None,
    ) -> GraphNode:
        metadata = doc.metadata

        return GraphNode(
            id=doc.id,
            label=CoreNodeLabel.DOCUMENT,
            project=project,
            properties={
                "title": doc.title,
                "source_type": self.source_type,
                "status": metadata.get("status"),
                "priority": metadata.get("priority"),
                "issue_type": metadata.get("issue_type"),
            },
        )

    # ------------------------------------------------------------------
    # People
    # ------------------------------------------------------------------

    def _extract_people(
        self,
        doc: Document,
    ) -> list[tuple[PersonInfo, str]]:
        people = []

        reporter = doc.metadata.get("reporter")

        if reporter:
            if isinstance(reporter, dict):
                person_id = (
                    reporter.get("email_address")
                    or reporter.get("account_id")
                    or reporter.get("display_name")
                )
                display_name = reporter.get("display_name", person_id)
            else:
                person_id = str(reporter)
                display_name = person_id

            if person_id:
                people.append(
                    (PersonInfo(id=person_id, display_name=display_name), "reporter")
                )

        assignee = doc.metadata.get("assignee")

        if assignee:
            if isinstance(assignee, dict):
                person_id = (
                    assignee.get("email_address")
                    or assignee.get("account_id")
                    or assignee.get("display_name")
                )
                display_name = assignee.get("display_name", person_id)
            else:
                person_id = str(assignee)
                display_name = person_id

            if person_id:
                people.append(
                    (PersonInfo(id=person_id, display_name=display_name), "assignee")
                )

        return people

    # ------------------------------------------------------------------
    # Container
    # ------------------------------------------------------------------

    def _extract_container(
        self,
        doc: Document,
    ) -> GraphNode | None:
        project_key = doc.metadata.get("project_key")

        if not project_key:
            return None

        return GraphNode(
            id=f"jira:{project_key}",
            label=CoreNodeLabel.CONTAINER,
            project=project_key,
            properties={
                "kind": "jira_project",
                "project_key": project_key,
            },
        )

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    def _extract_labels(
        self,
        doc: Document,
    ) -> list[GraphNode]:
        project = self._project(doc)

        nodes: list[GraphNode] = []

        for label in doc.metadata.get("labels", []):
            nodes.append(
                GraphNode(
                    id=f"label:{label}",
                    label=CoreNodeLabel.LABEL,
                    project=project,
                    properties={
                        "name": label,
                    },
                )
            )

        return nodes

    # ------------------------------------------------------------------
    # Cross-source URL links
    # ------------------------------------------------------------------
    def _extract_links(
        self,
        doc: Document,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        project = self._project(doc)

        text = doc.metadata.get("description") or getattr(doc, "content", "") or ""

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        def _is_url(value: str) -> bool:
            try:
                parsed = urlparse(value)
                return bool(parsed.scheme and parsed.netloc)
            except Exception:
                return False

        def _handle_url(url: str, kind: str) -> None:
            target = url.strip()

            if not _is_url(target):
                return

            nodes.append(
                GraphNode(
                    id=target,
                    label=CoreNodeLabel.URL,
                    project=project,
                    properties={"url": target},
                )
            )

            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=target,
                    edge_type=CoreEdgeType.LINKS_TO,
                    project=project,
                    properties={"kind": kind},
                )
            )

        for url in self.CONFLUENCE_URL_RE.findall(text):
            _handle_url(url, "confluence")

        for url in self.GIT_URL_RE.findall(text):
            _handle_url(url, "git")

        return nodes, edges

    # ------------------------------------------------------------------
    # Jira-specific relationships
    # ------------------------------------------------------------------

    def _extract_source_specific(
        self,
        doc: Document,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        project = self._project(doc)

        edges: list[GraphEdge] = []

        metadata = doc.metadata

        # --------------------------------------------------------------
        # Linked Issues
        # --------------------------------------------------------------

        for issue_key in metadata.get("linked_issues", []):
            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=issue_key,
                    edge_type=CoreEdgeType.LINKS_TO,
                    project=project,
                    properties={
                        "kind": "related",
                    },
                )
            )
        # --------------------------------------------------------------
        # Parent Issue
        # --------------------------------------------------------------

        parent_issue = metadata.get("parent_key")

        if parent_issue:
            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=parent_issue,
                    edge_type=CoreEdgeType.PART_OF,
                    project=project,
                    properties={
                        "kind": "subtask",
                    },
                )
            )

        return [], edges
