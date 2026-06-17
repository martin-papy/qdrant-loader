"""Shared fixtures for the conversion engine tests.

Real sample files are lifted from docling's own corpus (see
``tests/fixtures/unit/conversion/README.md``). We deliberately convert real
documents rather than mocking, so the tests prove *our* engine wires docling up
correctly — not that docling itself works.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parents[3] / "fixtures" / "unit" / "conversion"


def _fixture(name: str) -> Path:
    path = FIXTURE_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"missing conversion fixture: {path}")
    return path


@pytest.fixture
def xlsx_path() -> Path:
    """A small workbook with one titled table."""
    return _fixture("xlsx_05_table_with_title.xlsx")


@pytest.fixture
def csv_path() -> Path:
    return _fixture("csv-comma.csv")


@pytest.fixture
def docx_path() -> Path:
    return _fixture("lorem_ipsum.docx")


@pytest.fixture
def corrupt_xlsx_path(tmp_path: Path) -> Path:
    """A real file with an .xlsx name whose bytes are not a valid workbook.

    Drives the failure path: docling should fail to open it and our engine must
    surface that as a typed FAILED outcome, never a fake document.
    """
    path = tmp_path / "corrupt.xlsx"
    path.write_bytes(b"PK\x03\x04 not a real workbook " + b"\x00" * 64)
    return path
