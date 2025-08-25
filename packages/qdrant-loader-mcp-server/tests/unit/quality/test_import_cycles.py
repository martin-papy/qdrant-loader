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
    """Collect import edges, ignoring TYPE_CHECKING-only and self-import edges."""
    graph: Dict[str, Set[str]] = {}
    modules: List[str] = []

    class ImportCollector(ast.NodeVisitor):
        def __init__(self, current_module: str):
            self.current_module = current_module
            self.in_type_checking_block = 0

        def visit_If(self, node: ast.If) -> None:  # type: ignore[override]
            # Detect `if TYPE_CHECKING:` blocks
            is_type_checking = isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"
            if is_type_checking:
                self.in_type_checking_block += 1
                for n in node.body:
                    self.visit(n)
                self.in_type_checking_block -= 1
                # Visit orelse without the flag (not type-checking guarded)
                for n in node.orelse:
                    self.visit(n)
                return
            # Fallback to generic traversal
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:  # type: ignore[override]
            if self.in_type_checking_block:
                return
            for alias in node.names:
                name = alias.name
                if any(name.startswith(p) for p in scope_prefixes):
                    if name != self.current_module:  # ignore self-import edges
                        graph[self.current_module].add(name)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # type: ignore[override]
            if self.in_type_checking_block:
                return
            target = _resolve_relative_import(self.current_module, node.module, node.level)
            if target and any(target.startswith(p) for p in scope_prefixes):
                if target != self.current_module:  # ignore self-import edges
                    graph[self.current_module].add(target)

    for py_file in _iter_python_files(src_root):
        # Use the package src root to avoid 'src.' prefix in module names
        mod = _module_name_from_path(src_root, py_file)
        modules.append(mod)
        graph.setdefault(mod, set())
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        ImportCollector(mod).visit(tree)

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






