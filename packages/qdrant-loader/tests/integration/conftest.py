"""Integration test configuration.

This conftest.py ensures that test environment variables are loaded
before any module-level configuration checks are performed.
"""

from pathlib import Path

from dotenv import load_dotenv


def pytest_configure(config):
    """Configure pytest before test collection.

    This runs before module imports, ensuring environment variables
    are available for module-level configuration checks.
    """
    # Load test environment variables early
    tests_dir = Path(__file__).parent.parent
    env_path = tests_dir / ".env.test"

    if env_path.exists():
        load_dotenv(env_path, override=True)
        print(f"Loaded test environment from {env_path}")
    else:
        print(f"Warning: Test environment file not found at {env_path}")


# Also load environment variables at import time as a fallback
tests_dir = Path(__file__).parent.parent
env_path = tests_dir / ".env.test"
if env_path.exists():
    load_dotenv(env_path, override=True)
