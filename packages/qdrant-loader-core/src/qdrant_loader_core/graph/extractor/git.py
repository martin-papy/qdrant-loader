from qdrant_loader.core.document import Document
from qdrant_loader_core.graph.extractor.base_extractor import (
    BaseEntityExtractor,
)
from qdrant_loader_core.graph.models import (
    CoreNodeLabel,
    GraphNode,
    PersonInfo,
)


class GitEntityExtractor(BaseEntityExtractor):
    """
    Git repository graph extractor.

    Extracts:
    - Document node (file)
    - Person node from last_commit_author
    - Container node from repository
    """

    source_type = "git"

    def _project(
        self,
        doc: Document,
    ) -> str | None:
        return doc.metadata.get("repository_name")

    def _extract_people(
        self,
        doc: Document,
    ) -> list[tuple[PersonInfo, str]]:
        author = doc.metadata.get("last_commit_author")

        if not author:
            return []

        return [
            (
                PersonInfo(
                    id=f"git_user:{author}",
                    display_name=author,
                ),
                "last_committer",
            )
        ]

    def _extract_container(
        self,
        doc: Document,
    ) -> GraphNode | None:
        repo_name = doc.metadata.get("repository_name")

        if not repo_name:
            return None

        return GraphNode(
            id=f"git:{repo_name}",
            label=CoreNodeLabel.CONTAINER,
            project=repo_name,
            properties={
                "kind": "repository",
                "repository_name": repo_name,
                "repository_owner": doc.metadata.get("repository_owner"),
                "repository_url": doc.metadata.get("repository_url"),
            },
        )
