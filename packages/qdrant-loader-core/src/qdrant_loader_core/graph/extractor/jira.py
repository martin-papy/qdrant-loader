import re

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
    - Epic relationships
    - Cross-source links from URLs found in description
    """

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
            person_id = reporter.get("email_address") or reporter.get("account_id")

            if person_id:
                people.append(
                    (
                        PersonInfo(
                            id=person_id,
                            display_name=reporter.get(
                                "display_name",
                                person_id,
                            ),
                        ),
                        "reporter",
                    )
                )

        assignee = doc.metadata.get("assignee")

        if assignee:
            person_id = assignee.get("email_address") or assignee.get("account_id")

            if person_id:
                people.append(
                    (
                        PersonInfo(
                            id=person_id,
                            display_name=assignee.get(
                                "display_name",
                                person_id,
                            ),
                        ),
                        "assignee",
                    )
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
    ) -> list[GraphEdge]:
        project = self._project(doc)

        text = doc.metadata.get("description") or getattr(doc, "content", "") or ""

        edges: list[GraphEdge] = []

        for url in self.CONFLUENCE_URL_RE.findall(text):
            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=url,
                    edge_type=CoreEdgeType.LINKS_TO,
                    project=project,
                    properties={
                        "kind": "confluence",
                    },
                )
            )

        for url in self.GIT_URL_RE.findall(text):
            edges.append(
                GraphEdge(
                    source=doc.id,
                    target=url,
                    edge_type=CoreEdgeType.LINKS_TO,
                    project=project,
                    properties={
                        "kind": "git",
                    },
                )
            )

        return edges

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
