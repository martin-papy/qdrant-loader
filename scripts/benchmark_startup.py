#!/usr/bin/env python3
"""Benchmark startup time for qdrant-loader CLI commands.

Measures wall-clock time for various CLI commands to establish baseline
metrics before optimization. Results include mean, min, max, and stdev.

Usage:
    python scripts/benchmark_startup.py
    python scripts/benchmark_startup.py --runs 10
    python scripts/benchmark_startup.py --json
    python scripts/benchmark_startup.py --compare baseline.json
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path


COMMANDS = {
    "qdrant-loader --help": [sys.executable, "-m", "qdrant_loader.main", "--help"],
    "qdrant-loader config --help": [sys.executable, "-m", "qdrant_loader.main", "config", "--help"],
    "qdrant-loader ingest --help": [sys.executable, "-m", "qdrant_loader.main", "ingest", "--help"],
    "qdrant-loader init --help": [sys.executable, "-m", "qdrant_loader.main", "init", "--help"],
}

MCP_COMMANDS = {
    "qdrant-loader-mcp --help": [
        sys.executable,
        "-m",
        "qdrant_loader_mcp_server.main",
        "--help",
    ],
}


def measure_command(cmd: list[str], runs: int = 5) -> dict:
    """Measure startup time for a command over multiple runs."""
    times = []
    errors = []

    for i in range(runs):
        start = time.perf_counter()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        elapsed = time.perf_counter() - start

        if result.returncode != 0:
            errors.append(f"Run {i+1}: exit code {result.returncode}")
            # Still record the time even on non-zero exit (e.g., missing config)
            # as we're measuring startup time, not successful execution
        times.append(elapsed * 1000)  # Convert to ms

    if not times:
        return {"error": "All runs failed", "errors": errors}

    return {
        "runs": len(times),
        "mean_ms": round(statistics.mean(times), 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "stdev_ms": round(statistics.stdev(times), 1) if len(times) > 1 else 0,
        "median_ms": round(statistics.median(times), 1),
        "all_ms": [round(t, 1) for t in times],
        "errors": errors,
    }


def run_benchmarks(runs: int = 5, include_mcp: bool = True) -> dict:
    """Run all benchmarks and return results."""
    results = {}

    print(f"Running benchmarks ({runs} runs each)...\n")

    all_commands = dict(COMMANDS)
    if include_mcp:
        all_commands.update(MCP_COMMANDS)

    for name, cmd in all_commands.items():
        print(f"  Benchmarking: {name} ", end="", flush=True)
        result = measure_command(cmd, runs)
        results[name] = result

        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(
                f"  mean={result['mean_ms']:.0f}ms "
                f"min={result['min_ms']:.0f}ms "
                f"max={result['max_ms']:.0f}ms "
                f"stdev={result['stdev_ms']:.0f}ms"
            )

    return results


def compare_results(current: dict, baseline: dict) -> None:
    """Compare current results against baseline and print diff."""
    print("\n--- Comparison vs Baseline ---\n")
    print(f"{'Command':<35} {'Baseline':>10} {'Current':>10} {'Delta':>10} {'%':>8}")
    print("-" * 78)

    for name in current:
        if name not in baseline:
            print(f"{name:<35} {'N/A':>10} {current[name]['mean_ms']:>9.0f}ms {'N/A':>10}")
            continue

        base_ms = baseline[name]["mean_ms"]
        curr_ms = current[name]["mean_ms"]
        delta = curr_ms - base_ms
        pct = (delta / base_ms * 100) if base_ms > 0 else 0
        sign = "+" if delta > 0 else ""
        indicator = "SLOWER" if delta > 10 else ("FASTER" if delta < -10 else "~same")

        print(
            f"{name:<35} {base_ms:>9.0f}ms {curr_ms:>9.0f}ms "
            f"{sign}{delta:>8.0f}ms {sign}{pct:>6.1f}% {indicator}"
        )


def print_summary(results: dict) -> None:
    """Print a formatted summary table."""
    print("\n--- Startup Time Benchmark Results ---\n")
    print(f"{'Command':<35} {'Mean':>8} {'Min':>8} {'Max':>8} {'Stdev':>8} {'Median':>8}")
    print("-" * 83)

    for name, result in results.items():
        if "error" in result:
            print(f"{name:<35} {'ERROR':>8}")
            continue
        print(
            f"{name:<35} "
            f"{result['mean_ms']:>7.0f}ms "
            f"{result['min_ms']:>7.0f}ms "
            f"{result['max_ms']:>7.0f}ms "
            f"{result['stdev_ms']:>7.0f}ms "
            f"{result['median_ms']:>7.0f}ms"
        )

    print()


def main():
    parser = argparse.ArgumentParser(description="Benchmark qdrant-loader startup time")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs per command (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--save", type=str, help="Save results to JSON file")
    parser.add_argument("--compare", type=str, help="Compare against baseline JSON file")
    parser.add_argument("--no-mcp", action="store_true", help="Skip MCP server benchmark")
    args = parser.parse_args()

    results = run_benchmarks(runs=args.runs, include_mcp=not args.no_mcp)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_summary(results)

    if args.save:
        save_path = Path(args.save)
        save_path.write_text(json.dumps(results, indent=2))
        print(f"Results saved to {save_path}")

    if args.compare:
        compare_path = Path(args.compare)
        if not compare_path.exists():
            print(f"Baseline file not found: {compare_path}", file=sys.stderr)
            sys.exit(1)
        baseline = json.loads(compare_path.read_text())
        compare_results(results, baseline)


if __name__ == "__main__":
    main()
