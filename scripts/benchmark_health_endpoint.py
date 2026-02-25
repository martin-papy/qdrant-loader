#!/usr/bin/env python3
"""Benchmark time until /health endpoint is available.

Measures the actual time from server start until /health endpoint responds.
This is the metric that matters for AI Agents checking MCP readiness.

Usage:
    python scripts/benchmark_health_endpoint.py
    python scripts/benchmark_health_endpoint.py --runs 3
    python scripts/benchmark_health_endpoint.py --port 8081
"""

import argparse
import asyncio
import json
import os
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx


async def wait_for_health(url: str, timeout: float = 120.0, poll_interval: float = 0.1) -> tuple[float, dict | None]:
    """Wait for health endpoint to respond.

    Returns:
        Tuple of (time_to_ready_ms, health_response)
    """
    start = time.perf_counter()
    deadline = start + timeout

    async with httpx.AsyncClient(timeout=2.0) as client:
        while time.perf_counter() < deadline:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    elapsed = (time.perf_counter() - start) * 1000
                    try:
                        data = response.json()
                    except Exception:
                        data = {"raw": response.text}
                    return elapsed, data
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                pass
            except Exception as e:
                print(f"  Unexpected error: {e}", file=sys.stderr)

            await asyncio.sleep(poll_interval)

    return -1, None  # Timeout


async def measure_health_startup(
    python_exe: str,
    host: str = "127.0.0.1",
    port: int = 8080,
    timeout: float = 120.0
) -> dict:
    """Start MCP server and measure time until /health responds.

    Returns:
        Dict with timing results
    """
    health_url = f"http://{host}:{port}/health"

    # Start the server process
    env = os.environ.copy()
    # Set dummy values for required env vars if not set
    if "QDRANT_URL" not in env:
        env["QDRANT_URL"] = "http://localhost:6333"
    if "OPENAI_API_KEY" not in env:
        env["OPENAI_API_KEY"] = "sk-dummy-key-for-benchmark"

    cmd = [
        python_exe, "-m", "qdrant_loader_mcp_server.main",
        "--transport", "http",
        "--host", host,
        "--port", str(port),
        "--log-level", "WARNING"
    ]

    process = None
    try:
        start_time = time.perf_counter()

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Wait for health endpoint
        elapsed_ms, health_response = await wait_for_health(
            health_url,
            timeout=timeout,
            poll_interval=0.05  # Poll every 50ms
        )

        if elapsed_ms < 0:
            return {
                "success": False,
                "error": f"Timeout after {timeout}s waiting for {health_url}",
                "time_ms": -1
            }

        return {
            "success": True,
            "time_ms": round(elapsed_ms, 1),
            "health_response": health_response
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "time_ms": -1
        }
    finally:
        if process:
            try:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            except Exception:
                pass


def run_benchmark(python_exe: str, runs: int = 3, port: int = 8080) -> dict:
    """Run multiple benchmark iterations."""
    results = []

    print(f"Benchmarking /health endpoint startup ({runs} runs)...")
    print(f"Using Python: {python_exe}")
    print()

    for i in range(runs):
        # Use different port for each run to avoid conflicts
        run_port = port + i
        print(f"  Run {i+1}/{runs} (port {run_port})... ", end="", flush=True)

        result = asyncio.run(measure_health_startup(
            python_exe,
            port=run_port,
            timeout=120.0
        ))

        if result["success"]:
            print(f"{result['time_ms']:.0f}ms")
            results.append(result["time_ms"])
        else:
            print(f"FAILED: {result.get('error', 'Unknown error')}")

        # Small delay between runs
        time.sleep(1)

    if not results:
        return {"error": "All runs failed", "runs": runs}

    return {
        "runs": len(results),
        "mean_ms": round(statistics.mean(results), 1),
        "min_ms": round(min(results), 1),
        "max_ms": round(max(results), 1),
        "stdev_ms": round(statistics.stdev(results), 1) if len(results) > 1 else 0,
        "median_ms": round(statistics.median(results), 1),
        "all_ms": [round(t, 1) for t in results]
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark MCP server /health endpoint startup time")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs (default: 3)")
    parser.add_argument("--port", type=int, default=8080, help="Starting port (default: 8080)")
    parser.add_argument("--save", type=str, help="Save results to JSON file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Use the same Python that's running this script
    python_exe = sys.executable

    results = run_benchmark(python_exe, runs=args.runs, port=args.port)

    print()
    if "error" in results:
        print(f"ERROR: {results['error']}")
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("--- /health Endpoint Startup Time ---")
        print(f"  Mean:   {results['mean_ms']:.0f}ms")
        print(f"  Min:    {results['min_ms']:.0f}ms")
        print(f"  Max:    {results['max_ms']:.0f}ms")
        print(f"  Stdev:  {results['stdev_ms']:.0f}ms")
        print(f"  Median: {results['median_ms']:.0f}ms")

    if args.save:
        save_path = Path(args.save)
        save_path.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to {save_path}")


if __name__ == "__main__":
    main()
