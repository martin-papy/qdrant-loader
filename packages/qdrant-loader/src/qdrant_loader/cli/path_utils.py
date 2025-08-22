from __future__ import annotations

from pathlib import Path

import click


def create_database_directory(path: Path) -> bool:
    """Prompt to create a directory for the database; return True if created.

    Caller is responsible for logging around this utility.
    """
    abs_path = path.resolve()
    # If directory already exists, no need to prompt; treat as success
    if abs_path.exists():
        return True
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


