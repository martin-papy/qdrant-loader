from __future__ import annotations

from pathlib import Path

DEFAULT_LIMIT = 1200
STRICT_LIMIT = 1000

STRICT_SCOPES = [
    "mcp/",
    "search/",
]

EXEMPTIONS = {
    # Add exemptions if needed for large orchestrators
}


def _count_lines(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))


def _is_in_scopes(rel_posix: str, scopes: list[str]) -> bool:
    return any(rel_posix.startswith(scope) for scope in scopes)


def test_module_sizes_within_thresholds_mcp():
    pkg_root = Path(__file__).resolve().parents[3]
    src_root = pkg_root / "src" / "qdrant_loader_mcp_server"

    offenders: list[tuple[str, int, int]] = []

    for path in src_root.rglob("*.py"):
        rel = path.relative_to(src_root)
        rel_str = rel.as_posix()
        line_count = _count_lines(path)

        if rel_str in EXEMPTIONS:
            limit = EXEMPTIONS[rel_str]
        elif _is_in_scopes(rel_str, STRICT_SCOPES):
            limit = STRICT_LIMIT
        else:
            limit = DEFAULT_LIMIT

        if line_count > limit:
            offenders.append((rel_str, line_count, limit))

    assert not offenders, "MCP modules exceeding size limits:\n" + "\n".join(
        f" - {p} : {n} > {lim}" for p, n, lim in offenders
    )
