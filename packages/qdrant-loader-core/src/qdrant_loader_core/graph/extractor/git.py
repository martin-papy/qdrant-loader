from typing import Any

from qdrant_loader_core.graph.extractor.base_extractor import BaseEntityExtractor


class GitEntityExtractor(BaseEntityExtractor):
    SOURCE_TYPE = "git"

    def _extract_impl(self, raw: dict[str, Any]) -> None:
        sha = raw.get("sha")
        if not sha:
            return

        doc = self.build_document(
            source_type=self.SOURCE_TYPE,
            native_id=sha,
            title=raw.get("commit", {}).get("message", "")[:80],
            url=raw.get("html_url", ""),
            created_at=raw.get("commit", {}).get("author", {}).get("date"),
            updated_at=raw.get("commit", {}).get("author", {}).get("date"),
            qdrant_point_ids=[],
            properties={},
        )

        # Author
        if author := raw.get("commit", {}).get("author"):
            person = self.get_or_create_person(
                email=author.get("email"),
                display_name=author.get("name"),
            )
            self.emit_edge(source=doc, target=person, edge_type="AUTHORED_BY")

        # Repo
        if repo := raw.get("repository"):
            container = self.get_or_create_container(
                kind="git_repo",
                native_id=repo.get("full_name"),
                name=repo.get("name"),
            )
            self.emit_edge(source=doc, target=container, edge_type="BELONGS_TO")
