from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CoreNodeLabel(StrEnum):
    DOCUMENT = "Document"
    PERSON = "Person"
    CONTAINER = "Container"
    LABEL = "Label"
    CONCEPT = "Concept"
    CHUNK = "Chunk"


class CoreEdgeType(StrEnum):
    AUTHORED_BY = "AUTHORED_BY"
    BELONGS_TO = "BELONGS_TO"
    HAS_LABEL = "HAS_LABEL"
    LINKS_TO = "LINKS_TO"
    PART_OF = "PART_OF"
    HAS_CHUNK = "HAS_CHUNK"
    HAS_CHILD = "HAS_CHILD"
    HAS_ATTACHMENT = "HAS_ATTACHMENT"




@dataclass(slots=True, frozen=True)
class PersonInfo:
    id: str
    display_name: str

    email: str | None = None
    username: str | None = None

    source_type: str | None = None
    source_id: str | None = None


@dataclass
class GraphNode:
    id: str
    label: CoreNodeLabel
    project: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: CoreEdgeType
    project: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
