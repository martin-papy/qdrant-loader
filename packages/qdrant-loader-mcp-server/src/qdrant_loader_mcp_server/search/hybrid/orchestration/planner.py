from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class HybridPlan:
    use_pipeline: bool
    expanded_query: Optional[str]


class QueryPlanner:
    """Decide how to execute a hybrid search request.

    Current behavior mirrors legacy: prefer pipeline when available.
    """

    def make_plan(self, has_pipeline: bool, expanded_query: Optional[str]) -> HybridPlan:
        return HybridPlan(use_pipeline=bool(has_pipeline), expanded_query=expanded_query)


