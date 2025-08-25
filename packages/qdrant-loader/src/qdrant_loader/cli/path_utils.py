from __future__ import annotations

from pathlib import Path

import click


def create_database_directory(path: Path) -> bool:
    """Prompt to create a directory for the database; return True if created.

    Caller is responsible for logging around this utility.
    """
    abs_path = path.resolve()
    # If directory already exists, no need to prompt; treat as success
    # Use is_dir() in addition to exists() to avoid false positives in tests that patch exists
    if abs_path.exists() and abs_path.is_dir():
        return True
    # If a filesystem entry exists at the path but it's not a directory, fail early
    if abs_path.exists() and not abs_path.is_dir():
        raise click.ClickException(f"Path exists and is not a directory: {abs_path}")
    # Prompt user with explicit path information
    if click.confirm(f"Directory does not exist: {abs_path}. Create it?", default=True):
        try:
            # Use OS defaults for mode; create parents as needed
            abs_path.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            # Raise ClickException with clear message and original error
            raise click.ClickException(
                f"Failed to create directory '{abs_path}': {e}"
            ) from e
    return False


