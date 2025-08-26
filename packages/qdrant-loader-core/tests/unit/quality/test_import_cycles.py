from __future__ import annotations

import ast
from pathlib import Path

SCOPE_PREFIX = "qdrant_loader_core.llm"


def _iter_python_files(base: Path) -> list[Path]:
    return [p for p in base.rglob("*.py") if "__pycache__" not in p.parts]


def _module_name_from_path(src_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(src_root).with_suffix("")
    # Build module name from relative parts only to avoid duplicating the package segment
    # e.g. "qdrant_loader_core/llm/x.py" -> "qdrant_loader_core.llm.x"
    return ".".join(rel.parts)


def _resolve_relative_import(
    current_module: str, module: str | None, level: int
) -> str | None:
    if level == 0:
        return module
    parts = current_module.split(".")
    if len(parts) < level:
        return None
    base = parts[: len(parts) - level]
    if module:
        base.extend(module.split("."))
    return ".".join(base) if base else None


def _collect_edges(
    src_root: Path, scope_prefix: str
) -> tuple[dict[str, set[str]], list[str]]:
    graph: dict[str, set[str]] = {}
    modules: list[str] = []

    for py_file in _iter_python_files(src_root):
        # Resolve module name relative to src_root (not its parent) to avoid "src." prefix
        mod = _module_name_from_path(src_root, py_file)
        # Normalize package __init__ modules to the package name
        if mod.endswith(".__init__"):
            mod = mod.rsplit(".", 1)[0]
        # Optionally reduce noise by seeding only in-scope modules
        if not mod.startswith(scope_prefix):
            continue
        modules.append(mod)
        graph.setdefault(mod, set())
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(scope_prefix):
                        nbr = alias.name
                        if nbr.endswith(".__init__"):
                            nbr = nbr.rsplit(".", 1)[0]
                        graph[mod].add(nbr)
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_relative_import(mod, node.module, node.level)
                if target and target.startswith(scope_prefix):
                    nbr = target
                    if nbr.endswith(".__init__"):
                        nbr = nbr.rsplit(".", 1)[0]
                    graph[mod].add(nbr)
    return graph, modules


def _has_cycles(
    graph: dict[str, set[str]], scope_prefix: str
) -> tuple[bool, list[list[str]]]:
    visited: set[str] = set()
    stack: set[str] = set()
    path: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        if node in stack:
            if node in path:
                idx = path.index(node)
                cycles.append(path[idx:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        path.append(node)
        for nbr in graph.get(node, ()):  # only traverse within prefix scope
            if nbr.startswith(scope_prefix):
                dfs(nbr)
        path.pop()
        stack.remove(node)

    for n in list(graph.keys()):
        if n.startswith(scope_prefix) and n not in visited:
            dfs(n)

    return (len(cycles) > 0), cycles


def test_no_import_cycles_in_core_llm():
    pkg_root = Path(__file__).resolve().parents[3]
    # Prefer repository-style "src" layout; fall back to package root if not present
    src_root = pkg_root / "src"
    if not src_root.exists():
        src_root = pkg_root
    graph, _ = _collect_edges(src_root, SCOPE_PREFIX)
    has_cycles, cycles = _has_cycles(graph, SCOPE_PREFIX)
    assert not has_cycles, f"Import cycles detected in core LLM modules: {cycles}"
