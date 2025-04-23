#!/usr/bin/env python
"""
Run all tests without import conflicts.

This script runs the tests separately to avoid module import conflicts.
"""

import subprocess
import sys


def main():
    """Run all tests."""
    test_commands = [
        # Core, config, and utils tests
        ["python", "-m", "pytest", "tests/unit/core", "tests/unit/config", "tests/unit/utils"],
        # Connector tests - run each directory separately
        ["python", "-m", "pytest", "tests/unit/connectors/git"],
        ["python", "-m", "pytest", "tests/unit/connectors/jira"],
        ["python", "-m", "pytest", "tests/unit/connectors/confluence"],
        ["python", "-m", "pytest", "tests/unit/connectors/publicdocs"],
        ["python", "-m", "pytest", "tests/unit/connectors/test_base_connector.py"],
        # Integration tests
        ["python", "-m", "pytest", "tests/integration"],
    ]

    failed = False

    for cmd in test_commands:
        print(f"\n\n{'=' * 80}")
        print(f"Running: {' '.join(cmd)}")
        print(f"{'=' * 80}\n")

        result = subprocess.run(cmd)

        if result.returncode != 0:
            failed = True
            print(f"\n\nTests failed: {' '.join(cmd)}")

    if failed:
        print("\n\nSome tests failed!")
        sys.exit(1)
    else:
        print("\n\nAll tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
