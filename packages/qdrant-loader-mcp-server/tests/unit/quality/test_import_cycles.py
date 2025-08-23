from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple


SCOPE_PREFIXES = [
    "qdrant_loader_mcp_server.mcp",
    "qdrant_loader_mcp_server.search",
]


def _iter_python_files(base: Path) -> List[Path]:
    return [p for p in base.rglob("*.py") if "__pycache__" not in p.parts]


def _module_name_from_path(src_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(src_root).with_suffix("")
    return ".".join((src_root.name, *rel.parts))


def _resolve_relative_import(current_module: str, module: str | None, level: int) -> str | None:
    if level == 0:
        return module
    parts = current_module.split(".")
    if len(parts) < level:
        return None
    base = parts[: len(parts) - level]
    if module:
        base.extend(module.split("."))
    return ".".join(base) if base else None


def _collect_edges(src_root: Path, scope_prefixes: List[str]) -> Tuple[Dict[str, Set[str]], List[str]]:
    graph: Dict[str, Set[str]] = {}
    modules: List[str] = []
    for py_file in _iter_python_files(src_root):
        mod = _module_name_from_path(src_root.parent, py_file)
        modules.append(mod)
        graph.setdefault(mod, set())
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in scope_prefixes):
                        graph[mod].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_relative_import(mod, node.module, node.level)
                if target and any(target.startswith(p) for p in scope_prefixes):
                    graph[mod].add(target)
    return graph, modules


def _has_cycles(graph: Dict[str, Set[str]], scope_prefixes: List[str]) -> Tuple[bool, List[List[str]]]:
    visited: Set[str] = set()
    stack: Set[str] = set()
    path: List[str] = []
    cycles: List[List[str]] = []

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
            if any(nbr.startswith(p) for p in scope_prefixes):
                dfs(nbr)
        path.pop()
        stack.remove(node)

    for n in list(graph.keys()):
        if any(n.startswith(p) for p in scope_prefixes) and n not in visited:
            dfs(n)

    return (len(cycles) > 0), cycles


def test_no_import_cycles_in_mcp():
    pkg_root = Path(__file__).resolve().parents[3]
    src_root = pkg_root / "src" / "qdrant_loader_mcp_server"
    graph, _ = _collect_edges(src_root, SCOPE_PREFIXES)
    has_cycles, cycles = _has_cycles(graph, SCOPE_PREFIXES)
    assert not has_cycles, f"Import cycles detected in MCP modules: {cycles}"






