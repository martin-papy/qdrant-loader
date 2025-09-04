from __future__ import annotations

from pathlib import Path

# Thresholds
DEFAULT_LIMIT = 400  # global default for strategy modules
STRICT_LIMIT = 300  # preferred for refactored areas

# Scopes to enforce
STRICT_SCOPES = [
    "qdrant_loader/core/chunking/strategy/code/",
    "qdrant_loader/core/chunking/strategy/markdown/splitters/",
    "qdrant_loader/connectors/shared/",
]

# Known exemptions (path suffixes) with allowed higher limits
EXEMPTIONS = {
    "qdrant_loader/core/chunking/strategy/markdown/section_splitter.py": 600,
    "qdrant_loader/core/chunking/strategy/base_strategy.py": 500,
    "qdrant_loader/core/chunking/strategy/json/json_metadata_extractor.py": 900,
    "qdrant_loader/core/chunking/strategy/html/html_metadata_extractor.py": 500,
}


def _count_lines(path: Path) -> int:
    # Ensure file handle is properly closed to avoid ResourceWarning on some platforms
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f)


def _is_in_scopes(path: Path, scopes: list[str]) -> bool:
    s = str(path)
    return any(scope in s for scope in scopes)


def test_module_sizes_within_thresholds():
    pkg_root = Path(__file__).resolve().parents[3]
    src_root = pkg_root / "src" / "qdrant_loader"

    offenders: list[tuple[str, int, int]] = []

    for path in src_root.rglob("*.py"):
        rel = path.relative_to(src_root)
        rel_str = str(rel)
        line_count = _count_lines(path)

        # Determine limit
        if rel_str in EXEMPTIONS:
            limit = EXEMPTIONS[rel_str]
        elif _is_in_scopes(rel, STRICT_SCOPES):
            limit = STRICT_LIMIT
        elif "qdrant_loader/core/chunking/strategy/" in str(rel):
            limit = DEFAULT_LIMIT
        else:
            # not in our guard
            continue

        if line_count > limit:
            offenders.append((rel_str, line_count, limit))

    assert not offenders, "Modules exceeding size limits:\n" + "\n".join(
        f" - {p} : {n} > {lim}" for p, n, lim in offenders
    )
