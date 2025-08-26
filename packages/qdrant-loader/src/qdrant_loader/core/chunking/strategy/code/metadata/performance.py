from __future__ import annotations

import re


def analyze_performance_patterns(content: str) -> dict[str, list[str]]:
    performance_indicators = {
        "optimization_patterns": [],
        "potential_bottlenecks": [],
        "resource_usage": [],
    }

    content_lower = content.lower()

    if any(k in content_lower for k in ["cache", "memoize", "lazy"]):
        performance_indicators["optimization_patterns"].append("caching")
    if "async" in content_lower or "await" in content_lower:
        performance_indicators["optimization_patterns"].append("async_programming")
    if any(k in content_lower for k in ["parallel", "concurrent", "threading"]):
        performance_indicators["optimization_patterns"].append("concurrency")

    total_loops = content.count("for ") + content.count("while ")
    if total_loops >= 3:
        performance_indicators["potential_bottlenecks"].append("nested_loops")

    lines = content.split("\n")
    def_pattern = re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
    for idx, line in enumerate(lines):
        match = def_pattern.match(line)
        if not match:
            continue
        func_name = match.group(1)
        bare_call_regex = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
        method_call_regex = re.compile(r"\." + re.escape(func_name) + r"\s*\(")
        call_count = 0
        for j, other_line in enumerate(lines):
            if j == idx:
                continue
            if bare_call_regex.search(other_line) or method_call_regex.search(
                other_line
            ):
                call_count += 1
        if call_count > 0:
            performance_indicators["potential_bottlenecks"].append("recursion")
            break

    if content.count("database") > 5 or content.count("query") > 5:
        performance_indicators["potential_bottlenecks"].append("database_heavy")
    if content.count("file") > 10 or content.count("read") > 10:
        performance_indicators["potential_bottlenecks"].append("io_heavy")

    if any(k in content_lower for k in ["memory", "buffer", "allocation"]):
        performance_indicators["resource_usage"].append("memory_allocation")
    if any(k in content_lower for k in ["connection", "pool", "socket"]):
        performance_indicators["resource_usage"].append("connection_management")

    return performance_indicators
