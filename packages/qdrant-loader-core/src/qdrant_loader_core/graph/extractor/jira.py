from typing import Any

from qdrant_loader_core.graph.extractor.base_extractor import BaseEntityExtractor


class JiraEntityExtractor(BaseEntityExtractor):
    SOURCE_TYPE = "jira"

    def _extract_impl(self, raw: dict[str, Any]) -> None:
        issue_key = raw.get("key")
        fields = raw.get("fields", {})
        if not issue_key:
            return

        doc = self.build_document(
            source_type=self.SOURCE_TYPE,
            native_id=issue_key,
            title=fields.get("summary", ""),
            url=raw.get("self", ""),
            created_at=fields.get("created"),
            updated_at=fields.get("updated"),
            qdrant_point_ids=[],
            properties={
                "status": self._safe(fields, "status"),
                "priority": self._safe(fields, "priority"),
                "issue_type": self._safe(fields, "issuetype"),
            },
        )

        self._person(fields.get("assignee"), doc, "BELONGS_TO")
        self._person(fields.get("reporter"), doc, "REPORTED_BY")

        if proj := fields.get("project"):
            container = self.get_or_create_container(
                kind="jira_project",
                native_id=proj.get("key"),
                name=proj.get("name"),
            )
            self.emit_edge(source=doc, target=container, edge_type="BELONGS_TO")

        for label in fields.get("labels", []):
            label = self.get_or_create_label(name=label)
            self.emit_edge(source=doc, target=label, edge_type="HAS_LABEL")

    def _person(self, user, doc, edge):
        if not user:
            return
        p = self.get_or_create_person(
            email=user.get("emailAddress"),
            username=user.get("accountId"),
            display_name=user.get("displayName"),
        )
        self.emit_edge(source=doc, target=p, edge_type=edge)

    def _safe(self, obj, key):
        return (obj.get(key) or {}).get("name")
