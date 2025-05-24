#!/usr/bin/env python3
"""Test timeout calculation for different file sizes."""


def calculate_timeout(doc_size):
    """Calculate adaptive timeout based on document size."""
    if doc_size < 10_000:  # Small files (< 10KB)
        base_timeout = 30.0
    elif doc_size < 50_000:  # Medium files (10-50KB)
        base_timeout = 60.0
    elif doc_size < 100_000:  # Large files (50-100KB)
        base_timeout = 120.0
    else:  # Very large files (> 100KB)
        base_timeout = 180.0

    size_factor = min(doc_size / 50000, 4.0)
    pressure_factor = 0.5  # Assume some queue pressure
    adaptive_timeout = base_timeout * (1 + size_factor + pressure_factor)
    adaptive_timeout = min(adaptive_timeout, 300.0)
    return adaptive_timeout


# Test different file sizes
test_files = [
    ("Small enum (8 lines)", 200),
    ("Small interface (9 lines)", 250),
    ("Small exception (14 lines)", 350),
    ("Medium Java file", 5000),
    ("Large Java file (244 lines)", 10000),
    ("Very large Java file", 50000),
]

print("File Size vs Timeout Analysis:")
print("=" * 50)
for name, size in test_files:
    timeout = calculate_timeout(size)
    print(f"{name:25} | {size:6} bytes | {timeout:5.1f}s timeout")

print("\nConclusion:")
print("Small files get 45s timeout, which should be MORE than enough")
print("for simple enum/interface parsing that takes 0.05ms")
