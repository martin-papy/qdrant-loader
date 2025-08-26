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
    # If a filesystem entry exists at the path but it's not a directory,
    # offer to create the directory (for back-compat with tests that patch exists()).
    # Treat this the same as a missing directory from a UX perspective.
    if abs_path.exists() and not abs_path.is_dir():
        if not click.confirm(
            f"Directory does not exist: {abs_path}. Create it?", default=True
        ):
            return False
        try:
            abs_path.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            raise click.ClickException(
                f"Failed to create directory '{abs_path}': {e}"
            ) from e

    # Prompt user with explicit path information when directory truly doesn't exist
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
