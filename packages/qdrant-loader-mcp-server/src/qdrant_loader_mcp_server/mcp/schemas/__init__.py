from typing import Any

from .analyze_relationships import get_analyze_relationships_tool_schema
from .attachment import get_attachment_search_tool_schema
from .cluster_documents import get_cluster_documents_tool_schema
from .detect_conflicts import get_detect_conflicts_tool_schema
from .expand_cluster import get_expand_cluster_tool_schema
from .expand_document import get_expand_document_tool_schema
from .find_complementary import get_find_complementary_tool_schema
from .find_similar import get_find_similar_tool_schema
from .hierarchy import get_hierarchy_search_tool_schema
from .search import get_search_tool_schema


def get_all_tool_schemas() -> list[dict[str, Any]]:
    # Backward-compatibility alias: expose detect_conflicts under legacy name
    # 'detect_document_conflicts' in the tools list while the underlying schema
    # function uses the canonical 'detect_conflicts' name.
    conflicts_schema = get_detect_conflicts_tool_schema()
    conflicts_schema_legacy = {**conflicts_schema, "name": "detect_document_conflicts"}

    return [
        get_search_tool_schema(),
        get_hierarchy_search_tool_schema(),
        get_attachment_search_tool_schema(),
        get_analyze_relationships_tool_schema(),
        get_find_similar_tool_schema(),
        conflicts_schema_legacy,
        get_find_complementary_tool_schema(),
        get_cluster_documents_tool_schema(),
        get_expand_document_tool_schema(),
        get_expand_cluster_tool_schema(),
    ]


class MCPSchemas:
    """Backward-compatible wrapper exposing static methods for tests/importers."""

    get_search_tool_schema = staticmethod(get_search_tool_schema)
    get_hierarchy_search_tool_schema = staticmethod(get_hierarchy_search_tool_schema)
    get_attachment_search_tool_schema = staticmethod(get_attachment_search_tool_schema)
    get_analyze_relationships_tool_schema = staticmethod(
        get_analyze_relationships_tool_schema
    )
    get_find_similar_tool_schema = staticmethod(get_find_similar_tool_schema)
    get_detect_conflicts_tool_schema = staticmethod(get_detect_conflicts_tool_schema)
    get_find_complementary_tool_schema = staticmethod(
        get_find_complementary_tool_schema
    )
    get_cluster_documents_tool_schema = staticmethod(get_cluster_documents_tool_schema)
    get_expand_document_tool_schema = staticmethod(get_expand_document_tool_schema)
    get_expand_cluster_tool_schema = staticmethod(get_expand_cluster_tool_schema)

    @classmethod
    def get_all_tool_schemas(cls) -> list[dict[str, Any]]:
        return get_all_tool_schemas()


__all__ = [
    "get_search_tool_schema",
    "get_hierarchy_search_tool_schema",
    "get_attachment_search_tool_schema",
    "get_analyze_relationships_tool_schema",
    "get_find_similar_tool_schema",
    "get_detect_conflicts_tool_schema",
    "get_find_complementary_tool_schema",
    "get_cluster_documents_tool_schema",
    "get_expand_document_tool_schema",
    "get_expand_cluster_tool_schema",
    "get_all_tool_schemas",
    "MCPSchemas",
]
