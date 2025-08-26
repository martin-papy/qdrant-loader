from __future__ import annotations


def calculate_maintainability_metrics(content: str) -> dict[str, float | int]:
    lines = content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]

    avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
    max_line_length = max(len(line) for line in lines) if lines else 0
    long_lines = len([line for line in lines if len(line) > 120])
    code_density = len(non_empty_lines) / len(lines) if lines else 0

    readability_score = 100
    if avg_line_length > 100:
        readability_score -= 20
    if max_line_length > 200:
        readability_score -= 15
    if long_lines > len(lines) * 0.3:
        readability_score -= 25
    if code_density < 0.5:
        readability_score -= 10

    return {
        "avg_line_length": avg_line_length,
        "max_line_length": max_line_length,
        "long_lines_count": long_lines,
        "code_density": code_density,
        "readability_score": max(0, readability_score),
        "estimated_read_time_minutes": (
            len(non_empty_lines) / 50 if non_empty_lines else 0
        ),
    }
