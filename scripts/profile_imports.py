#!/usr/bin/env python3
"""Profile import chain for qdrant-loader CLI.

Uses Python's -X importtime to capture the full import tree, then parses
and displays the top imports by cumulative time.

Usage:
    python scripts/profile_imports.py
    python scripts/profile_imports.py --top 30
    python scripts/profile_imports.py --save import_profile.txt
    python scripts/profile_imports.py --tree
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportEntry:
    """A single import entry from -X importtime output."""

    module: str
    self_us: int  # self time in microseconds
    cumulative_us: int  # cumulative time in microseconds
    depth: int
    children: list["ImportEntry"] = field(default_factory=list)

    @property
    def self_ms(self) -> float:
        return self.self_us / 1000

    @property
    def cumulative_ms(self) -> float:
        return self.cumulative_us / 1000


def run_importtime(module: str = "qdrant_loader.main") -> str:
    """Run python -X importtime and capture stderr output."""
    result = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", f"import {module}"],
        capture_output=True,
        text=True,
    )
    return result.stderr


def parse_importtime(output: str) -> list[ImportEntry]:
    """Parse -X importtime output into ImportEntry objects.

    Format: import time: self [us] | cumulative | name
    Depth is indicated by leading spaces/pipes in the name.
    """
    entries = []
    # Pattern: "import time:   <self_us> |   <cumul_us> |   <depth_indicators><name>"
    pattern = re.compile(
        r"import time:\s+(\d+)\s+\|\s+(\d+)\s+\|\s+([\s|]*)([\w.]+)"
    )

    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            self_us = int(match.group(1))
            cumul_us = int(match.group(2))
            indent = match.group(3)
            name = match.group(4)
            # Depth is determined by the number of leading spaces (2 per level)
            depth = len(indent.replace("|", " ")) // 2
            entries.append(
                ImportEntry(
                    module=name,
                    self_us=self_us,
                    cumulative_us=cumul_us,
                    depth=depth,
                )
            )

    return entries


def group_by_package(entries: list[ImportEntry], top_n: int = 10) -> dict[str, float]:
    """Group imports by top-level package and sum self times."""
    packages: dict[str, float] = {}
    for entry in entries:
        pkg = entry.module.split(".")[0]
        packages[pkg] = packages.get(pkg, 0) + entry.self_ms
    # Sort by total self time descending
    sorted_pkgs = dict(sorted(packages.items(), key=lambda x: x[1], reverse=True)[:top_n])
    return sorted_pkgs


def print_top_imports(entries: list[ImportEntry], top_n: int = 20) -> None:
    """Print top imports sorted by cumulative time."""
    sorted_entries = sorted(entries, key=lambda e: e.cumulative_us, reverse=True)

    print(f"\n--- Top {top_n} Imports by Cumulative Time ---\n")
    print(f"{'Module':<55} {'Self (ms)':>10} {'Cumul (ms)':>12}")
    print("-" * 80)

    for entry in sorted_entries[:top_n]:
        print(f"{entry.module:<55} {entry.self_ms:>9.1f} {entry.cumulative_ms:>11.1f}")


def print_package_summary(entries: list[ImportEntry]) -> None:
    """Print summary grouped by top-level package."""
    packages = group_by_package(entries, top_n=15)

    print("\n--- Import Time by Package (self time) ---\n")
    print(f"{'Package':<30} {'Self Time (ms)':>15}")
    print("-" * 48)

    total = sum(packages.values())
    for pkg, ms in packages.items():
        pct = (ms / total * 100) if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"{pkg:<30} {ms:>13.1f}ms  {bar} ({pct:.0f}%)")

    print(f"\n{'Total':<30} {total:>13.1f}ms")


def print_import_tree(entries: list[ImportEntry], min_ms: float = 5.0) -> None:
    """Print import tree showing hierarchy (filtered by min time)."""
    print(f"\n--- Import Tree (>={min_ms:.0f}ms) ---\n")

    for entry in entries:
        if entry.cumulative_ms < min_ms:
            continue
        indent = "  " * entry.depth
        marker = "+" if entry.depth == 0 else "|--"
        print(
            f"{indent}{marker} {entry.module} "
            f"(self={entry.self_ms:.1f}ms, cumul={entry.cumulative_ms:.1f}ms)"
        )


def main():
    parser = argparse.ArgumentParser(description="Profile qdrant-loader import chain")
    parser.add_argument(
        "--module",
        type=str,
        default="qdrant_loader.main",
        help="Module to profile (default: qdrant_loader.main)",
    )
    parser.add_argument("--top", type=int, default=20, help="Number of top imports to show (default: 20)")
    parser.add_argument("--tree", action="store_true", help="Show import tree")
    parser.add_argument("--tree-min-ms", type=float, default=5.0, help="Min ms to show in tree (default: 5)")
    parser.add_argument("--save", type=str, help="Save raw importtime output to file")
    parser.add_argument("--load", type=str, help="Load previously saved importtime output")
    parser.add_argument("--packages", action="store_true", help="Show package-level summary")
    args = parser.parse_args()

    if args.load:
        print(f"Loading import profile from {args.load}...")
        raw_output = Path(args.load).read_text()
    else:
        print(f"Profiling imports for: {args.module}")
        print(f"Running: {sys.executable} -X importtime -c 'import {args.module}'")
        raw_output = run_importtime(args.module)

    if args.save:
        Path(args.save).write_text(raw_output)
        print(f"Raw output saved to {args.save}")

    entries = parse_importtime(raw_output)

    if not entries:
        print("No import entries found. Is the module installed?", file=sys.stderr)
        sys.exit(1)

    print(f"\nTotal imports traced: {len(entries)}")

    print_top_imports(entries, top_n=args.top)

    if args.packages:
        print_package_summary(entries)

    if args.tree:
        print_import_tree(entries, min_ms=args.tree_min_ms)

    # Always show package summary as it's quick and useful
    if not args.packages:
        print_package_summary(entries)


if __name__ == "__main__":
    main()
