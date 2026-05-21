from typing import Any

from qdrant_loader_core.graph.extractor.base_extractor import BaseEntityExtractor


class ConfluenceEntityExtractor(BaseEntityExtractor):
    SOURCE_TYPE = "confluence"

    def _extract_impl(self, raw: dict[str, Any]) -> None:
        page_id = raw.get("id")
        if not page_id:
            return

        doc = self.build_document(
            source_type=self.SOURCE_TYPE,
            native_id=page_id,
            title=raw.get("title", ""),
            url=raw.get("_links", {}).get("webui", ""),
            created_at=raw.get("history", {}).get("createdDate"),
            updated_at=raw.get("version", {}).get("when"),
            qdrant_point_ids=[],
            properties={},
        )

        # Author
        if creator := raw.get("history", {}).get("createdBy"):
            person = self.get_or_create_person(
                username=creator.get("accountId"),
                display_name=creator.get("displayName"),
            )
            self.emit_edge(source=doc, target=person, edge_type="AUTHORED_BY")

        # Space
        if space := raw.get("space"):
            space_node = self.get_or_create_container(
                kind="confluence_space",
                native_id=space.get("key"),
                name=space.get("name"),
            )
            self.emit_edge(source=doc, target=space_node, edge_type="BELONGS_TO")

        # Labels
        for label in raw.get("metadata", {}).get("labels", {}).get("results", []):
            label = self.get_or_create_label(name=label.get("name"))
            self.emit_edge(source=doc, target=label, edge_type="HAS_LABEL")
