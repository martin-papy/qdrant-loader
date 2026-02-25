#!/usr/bin/env python3
"""Benchmark MCP server readiness time.

Measures the actual time from server start until MCP `initialize` request succeeds.
This is the metric that matters for MCP clients (Claude Desktop, Cursor, etc.).

Supports both stdio and HTTP transports.

Usage:
    python scripts/benchmark_mcp_readiness.py
    python scripts/benchmark_mcp_readiness.py --transport stdio
    python scripts/benchmark_mcp_readiness.py --transport http --runs 3
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


# MCP initialize request
INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "benchmark-client",
            "version": "1.0.0"
        }
    }
}


async def measure_http_mcp_readiness(
    python_exe: str,
    host: str = "127.0.0.1",
    port: int = 8080,
    timeout: float = 120.0
) -> dict:
    """Measure time until HTTP MCP endpoint responds to initialize request.

    Returns:
        Dict with timing results
    """
    mcp_url = f"http://{host}:{port}/mcp"

    # Set dummy env vars if not set
    env = os.environ.copy()
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

        # Poll until MCP endpoint responds to initialize
        deadline = start_time + timeout
        async with httpx.AsyncClient(timeout=5.0) as client:
            while time.perf_counter() < deadline:
                try:
                    response = await client.post(
                        mcp_url,
                        json=INITIALIZE_REQUEST,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 200:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        try:
                            data = response.json()
                            # Check if it's a valid MCP response
                            if "result" in data or "error" in data:
                                return {
                                    "success": True,
                                    "time_ms": round(elapsed, 1),
                                    "response": data
                                }
                        except Exception:
                            pass
                except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                    pass
                except Exception as e:
                    print(f"  Unexpected error: {e}", file=sys.stderr)

                await asyncio.sleep(0.1)

        return {
            "success": False,
            "error": f"Timeout after {timeout}s waiting for MCP initialize response",
            "time_ms": -1
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


async def measure_stdio_mcp_readiness(
    python_exe: str,
    timeout: float = 120.0
) -> dict:
    """Measure time until stdio MCP server responds to initialize request.

    Returns:
        Dict with timing results
    """
    env = os.environ.copy()
    if "QDRANT_URL" not in env:
        env["QDRANT_URL"] = "http://localhost:6333"
    if "OPENAI_API_KEY" not in env:
        env["OPENAI_API_KEY"] = "sk-dummy-key-for-benchmark"

    cmd = [
        python_exe, "-m", "qdrant_loader_mcp_server.main",
        "--transport", "stdio",
        "--log-level", "WARNING"
    ]

    process = None
    try:
        start_time = time.perf_counter()

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Send initialize request
        request_line = json.dumps(INITIALIZE_REQUEST) + "\n"
        process.stdin.write(request_line.encode())
        await process.stdin.drain()

        # Wait for response with timeout
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout
            )
            elapsed = (time.perf_counter() - start_time) * 1000

            if response_line:
                try:
                    data = json.loads(response_line.decode().strip())
                    if "result" in data or "error" in data:
                        return {
                            "success": True,
                            "time_ms": round(elapsed, 1),
                            "response": data
                        }
                except json.JSONDecodeError:
                    pass

            return {
                "success": False,
                "error": "Invalid response from server",
                "time_ms": round(elapsed, 1)
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Timeout after {timeout}s waiting for MCP initialize response",
                "time_ms": -1
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
                await asyncio.wait_for(process.wait(), timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass


def run_benchmark(python_exe: str, transport: str = "http", runs: int = 3, port: int = 8080) -> dict:
    """Run multiple benchmark iterations."""
    results = []

    print(f"Benchmarking MCP {transport} readiness ({runs} runs)...")
    print(f"Using Python: {python_exe}")
    print(f"Measuring: Time until 'initialize' request succeeds")
    print()

    for i in range(runs):
        run_port = port + i if transport == "http" else 0
        port_info = f" (port {run_port})" if transport == "http" else ""
        print(f"  Run {i+1}/{runs}{port_info}... ", end="", flush=True)

        if transport == "http":
            result = asyncio.run(measure_http_mcp_readiness(
                python_exe,
                port=run_port,
                timeout=120.0
            ))
        else:
            result = asyncio.run(measure_stdio_mcp_readiness(
                python_exe,
                timeout=120.0
            ))

        if result["success"]:
            print(f"{result['time_ms']:.0f}ms")
            results.append(result["time_ms"])
        else:
            print(f"FAILED: {result.get('error', 'Unknown error')}")

        # Delay between runs
        time.sleep(2)

    if not results:
        return {"error": "All runs failed", "runs": runs, "transport": transport}

    return {
        "transport": transport,
        "metric": "time_to_initialize_response",
        "runs": len(results),
        "mean_ms": round(statistics.mean(results), 1),
        "min_ms": round(min(results), 1),
        "max_ms": round(max(results), 1),
        "stdev_ms": round(statistics.stdev(results), 1) if len(results) > 1 else 0,
        "median_ms": round(statistics.median(results), 1),
        "all_ms": [round(t, 1) for t in results]
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark MCP server readiness (time until initialize succeeds)"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="http",
        help="Transport to test (default: http)"
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of runs (default: 3)")
    parser.add_argument("--port", type=int, default=8080, help="Starting port for HTTP (default: 8080)")
    parser.add_argument("--save", type=str, help="Save results to JSON file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    python_exe = sys.executable

    results = run_benchmark(
        python_exe,
        transport=args.transport,
        runs=args.runs,
        port=args.port
    )

    print()
    if "error" in results:
        print(f"ERROR: {results['error']}")
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"--- MCP {args.transport.upper()} Readiness Time ---")
        print(f"  Metric: Time until 'initialize' request succeeds")
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
