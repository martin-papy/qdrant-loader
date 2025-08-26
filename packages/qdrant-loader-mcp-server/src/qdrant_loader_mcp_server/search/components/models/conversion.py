from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConversionInfo:
    original_file_type: str | None = None
    conversion_method: str | None = None
    is_excel_sheet: bool = False
    is_converted: bool = False
