import numpy as np
import pandas as pd
from qdrant_loader.core.file_conversion.sub_table_detector import (
    SubTableDetector,
)


def _grid(*rows: list) -> pd.DataFrame:
    """Build a header-less DataFrame from a literal grid of cell values."""
    return pd.DataFrame(rows)


def test_detects_single_table():
    sheet = _grid(
        ["A", "B"],
        [1, 2],
        [3, 4],
    )
    tables = SubTableDetector().detect(sheet)
    assert len(tables) == 1
    assert tables[0].shape == (3, 2)


def test_detects_two_tables_separated_by_blank_row():
    sheet = _grid(
        ["A", "B"],
        [1, 2],
        [np.nan, np.nan],
        ["C", "D"],
        [5, 6],
    )
    tables = SubTableDetector().detect(sheet)
    assert len(tables) == 2
    assert tables[0].iloc[0].tolist() == ["A", "B"]
    assert tables[1].iloc[0].tolist() == ["C", "D"]


def test_detects_two_tables_separated_by_blank_column():
    sheet = _grid(
        ["A", "B", np.nan, "C", "D"],
        [1, 2, np.nan, 5, 6],
        [3, 4, np.nan, 7, 8],
    )
    tables = SubTableDetector().detect(sheet)
    assert len(tables) == 2
    assert tables[0].shape == (3, 2)
    assert tables[1].shape == (3, 2)


def test_merges_tables_overlapping_row_wise():
    """If two components share row range, treat as one logical table.

    This handles the common case of an annotation column to the right of the
    main table — splitting it would lose the row-level association.
    """
    sheet = _grid(
        ["A", "B", np.nan, "Notes"],
        [1, 2, np.nan, "ok"],
        [3, 4, np.nan, "review"],
    )
    tables = SubTableDetector().detect(sheet)
    assert len(tables) == 1


def test_returns_empty_list_for_empty_sheet():
    sheet = _grid([np.nan, np.nan], [np.nan, np.nan])
    assert SubTableDetector().detect(sheet) == []


def test_detector_drops_nan_padding_around_each_subtable():
    sheet = _grid(
        [np.nan, np.nan, np.nan],
        [np.nan, "A", "B"],
        [np.nan, 1, 2],
        [np.nan, np.nan, np.nan],
    )
    tables = SubTableDetector().detect(sheet)
    assert len(tables) == 1
    assert tables[0].iloc[0].tolist() == ["A", "B"]
