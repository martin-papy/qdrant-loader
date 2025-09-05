from __future__ import annotations

from pathlib import Path

DEFAULT_LIMIT = 400
STRICT_LIMIT = 300

STRICT_SCOPES = [
    "llm/",
]

EXEMPTIONS = {
    # add exemptions if needed later
}


def _count_lines(path: Path) -> int:
    # Ensure file is closed promptly to avoid ResourceWarning in tests
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f)


def _normalize_scope(scope: str) -> str:
    """Normalize a scope string to POSIX style and strip leading './'."""
    return scope.replace("\\", "/").lstrip("./")


def _is_in_scopes(path: Path, scopes: list[str]) -> bool:
    """Return True if the relative POSIX path starts with any normalized scope."""
    rel_posix = path.as_posix().lstrip("./")
    return any(rel_posix.startswith(_normalize_scope(scope)) for scope in scopes)


def test_module_sizes_within_thresholds_core():
    pkg_root = Path(__file__).resolve().parents[3]
    src_root = pkg_root / "src" / "qdrant_loader_core"

    offenders: list[tuple[str, int, int]] = []

    for path in src_root.rglob("*.py"):
        rel = path.relative_to(src_root)
        rel_str = str(rel)
        line_count = _count_lines(path)

        if rel_str in EXEMPTIONS:
            limit = EXEMPTIONS[rel_str]
        elif _is_in_scopes(rel, STRICT_SCOPES):
            limit = STRICT_LIMIT
        else:
            limit = DEFAULT_LIMIT

        if line_count > limit:
            offenders.append((rel_str, line_count, limit))

    assert not offenders, "Core modules exceeding size limits:\n" + "\n".join(
        f" - {p} : {n} > {lim}" for p, n, lim in offenders
    )
