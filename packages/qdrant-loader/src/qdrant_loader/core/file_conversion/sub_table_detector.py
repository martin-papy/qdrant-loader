"""Connected-components sub-table detector for spreadsheet sheets.

Algorithm reference: https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/xlsx.py
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pandas as pd


@dataclass(frozen=True)
class _BoundingBox:
    row_min: int
    row_max: int
    col_min: int
    col_max: int

    def overlaps_row_wise(self, other: _BoundingBox) -> bool:
        return not (self.row_max < other.row_min or other.row_max < self.row_min)


def _box_width(box: _BoundingBox) -> int:
    return box.col_max - box.col_min + 1


class SubTableDetector:
    """Detect logical sub-tables within a single header-less sheet DataFrame."""

    def detect(self, sheet: pd.DataFrame) -> list[pd.DataFrame]:
        """Return one DataFrame per detected sub-table, with NaN padding stripped."""
        if sheet.empty or sheet.isna().all().all():
            return []

        graph = self._build_cell_graph(sheet)
        components = [c for c in nx.connected_components(graph) if c]
        boxes = [self._bounding_box(c) for c in components]
        merged = self._merge_row_overlapping(boxes)

        tables: list[pd.DataFrame] = []
        for box in merged:
            sub = sheet.iloc[
                box.row_min : box.row_max + 1, box.col_min : box.col_max + 1
            ]
            sub = sub.dropna(axis=0, how="all").dropna(axis=1, how="all")
            sub = sub.reset_index(drop=True)
            sub.columns = range(sub.shape[1])
            if not sub.empty:
                tables.append(sub)
        return tables

    @staticmethod
    def _build_cell_graph(sheet: pd.DataFrame) -> nx.Graph:
        graph = nx.Graph()
        nrows, ncols = sheet.shape
        non_empty = ~sheet.isna()
        for r in range(nrows):
            for c in range(ncols):
                if not non_empty.iat[r, c]:
                    continue
                graph.add_node((r, c))
                for dr, dc in (
                    (-1, 0),
                    (0, -1),
                ):  # 4-connected: only up and left needed
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < nrows and 0 <= cc < ncols and non_empty.iat[rr, cc]:
                        graph.add_edge((r, c), (rr, cc))
        return graph

    @staticmethod
    def _bounding_box(component: set[tuple[int, int]]) -> _BoundingBox:
        rows = [r for r, _ in component]
        cols = [c for _, c in component]
        return _BoundingBox(
            row_min=min(rows),
            row_max=max(rows),
            col_min=min(cols),
            col_max=max(cols),
        )

    @staticmethod
    def _merge_row_overlapping(boxes: list[_BoundingBox]) -> list[_BoundingBox]:
        """Merge boxes that share row range when one is a narrow annotation column.

        Two equal-width tables side-by-side (e.g. ``[A,B] | blank | [C,D]``) are
        intentionally NOT merged — those are independent logical tables. We only
        merge when one component is a single column wide, which matches the
        "main table + adjacent notes column" pattern.
        """
        if not boxes:
            return []
        boxes = sorted(boxes, key=lambda b: (b.row_min, b.col_min))
        merged: list[_BoundingBox] = [boxes[0]]
        for box in boxes[1:]:
            last = merged[-1]
            if box.overlaps_row_wise(last) and (
                _box_width(box) == 1 or _box_width(last) == 1
            ):
                merged[-1] = _BoundingBox(
                    row_min=min(last.row_min, box.row_min),
                    row_max=max(last.row_max, box.row_max),
                    col_min=min(last.col_min, box.col_min),
                    col_max=max(last.col_max, box.col_max),
                )
            else:
                merged.append(box)
        return merged
