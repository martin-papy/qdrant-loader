from __future__ import annotations

from pathlib import Path

import click


def create_database_directory(path: Path) -> bool:
    """Prompt to create a directory for the database; return True if created.

    Caller is responsible for logging around this utility.
    """
    abs_path = path.resolve()
    if click.confirm("Would you like to create this directory?", default=True):
        abs_path.mkdir(parents=True, mode=0o755, exist_ok=True)
        return True
    return False


