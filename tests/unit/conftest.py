import pytest
from pathlib import Path

# Add any unit test specific fixtures or configuration here

def pytest_configure(config):
    """Configure pytest for unit tests."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    ) 