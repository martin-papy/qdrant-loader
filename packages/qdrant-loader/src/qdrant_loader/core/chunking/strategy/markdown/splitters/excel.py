"""Excel splitter implementation extracted from `section_splitter`."""

import re

from qdrant_loader.core.chunking.strategy.markdown.splitters.base import BaseSplitter


class ExcelSplitter(BaseSplitter):
    """Excel-specific splitter that preserves table structure."""

    def split_content(self, content: str, max_size: int) -> list[str]:
        """Split Excel sheet content into chunks, preserving table structure where possible.

        Args:
            content: Excel sheet content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        chunks: list[str] = []

        max_chunks_per_section = min(
            self.settings.global_config.chunking.strategies.markdown.max_chunks_per_section,
            self.settings.global_config.chunking.max_chunks_per_document // 2,
        )

        logical_units: list[str] = []
        lines = content.split("\n")
        current_unit: list[str] = []
        in_table = False

        for line in lines:
            line = line.strip()

            is_table_line = bool(re.match(r"^\|.*\|$", line)) or bool(
                re.match(r"^[|\-\s:]+$", line)
            )

            if is_table_line and not in_table:
                if current_unit:
                    logical_units.append("\n".join(current_unit))
                    current_unit = []
                in_table = True
                current_unit.append(line)
            elif not is_table_line and in_table:
                if current_unit:
                    logical_units.append("\n".join(current_unit))
                    current_unit = []
                in_table = False
                if line:
                    current_unit.append(line)
            else:
                if line or current_unit:
                    current_unit.append(line)

        if current_unit:
            logical_units.append("\n".join(current_unit))

        split_logical_units: list[str] = []
        for unit in logical_units:
            if len(unit) > max_size:
                lines = unit.split("\n")
                current_sub_unit: list[str] = []

                for line in lines:
                    test_unit = "\n".join(current_sub_unit + [line])
                    if current_sub_unit and len(test_unit) > max_size:
                        split_logical_units.append("\n".join(current_sub_unit))
                        current_sub_unit = [line]
                    else:
                        current_sub_unit.append(line)

                if current_sub_unit:
                    split_logical_units.append("\n".join(current_sub_unit))
            else:
                split_logical_units.append(unit)

        logical_units = split_logical_units

        i = 0
        while i < len(logical_units) and len(chunks) < max_chunks_per_section:
            current_chunk = ""
            units_in_chunk = 0

            j = i
            while j < len(logical_units):
                unit = logical_units[j]

                if current_chunk and len(current_chunk) + len(unit) + 2 > max_size:
                    break

                if current_chunk:
                    current_chunk += "\n\n" + unit
                else:
                    current_chunk = unit

                units_in_chunk += 1
                j += 1

            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            if units_in_chunk > 0:
                if self.chunk_overlap == 0:
                    advance = units_in_chunk
                else:
                    overlap_units = min(1, units_in_chunk // 2)
                    advance = max(1, units_in_chunk - overlap_units)

                i += advance
            else:
                i += 1

        if i < len(logical_units) and len(chunks) >= max_chunks_per_section:
            from qdrant_loader.core.chunking.strategy.markdown import (
                section_splitter as _section_module,
            )

            _section_module.logger.warning(
                f"Excel sheet reached maximum chunks limit ({max_chunks_per_section}), truncating remaining content",
                extra={
                    "remaining_units": len(logical_units) - i,
                    "max_chunks_per_section": max_chunks_per_section,
                },
            )

        return chunks


__all__ = ["ExcelSplitter"]
