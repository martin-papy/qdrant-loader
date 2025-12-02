"""
Asset Management - Static File Handling and Asset Operations.

This module handles asset copying, static file management,
and asset-related operations for the website builder.
"""

import shutil
from pathlib import Path


class AssetManager:
    """Handles asset management and static file operations."""

    def __init__(self, output_dir: str = "site"):
        """Initialize asset manager."""
        self.output_dir = Path(output_dir)

    def copy_assets(self) -> None:
        """Copy all website assets to output directory."""
        assets_source = Path("website/assets")
        assets_dest = self.output_dir / "assets"

        if assets_source.exists():
            if assets_dest.exists():
                shutil.rmtree(assets_dest)

            # Define ignore patterns for files we don't want to copy
            def ignore_patterns(dir, files):
                ignored = []
                for file in files:
                    # Ignore Python files and other development files
                    if file.endswith((".py", ".pyc", "__pycache__")):
                        ignored.append(file)
                return ignored

            shutil.copytree(assets_source, assets_dest, ignore=ignore_patterns)
            print(f"📁 Assets copied to {assets_dest}")
        else:
            print(f"⚠️  Assets directory not found: {assets_source}")

    def copy_static_file(self, source_path: str, dest_path: str) -> None:
        """Copy a single static file."""
        source = Path(source_path)
        dest = self.output_dir / dest_path

        if source.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            print(f"📄 Copied {source} -> {dest}")
        else:
            print(f"⚠️  Static file not found: {source}")

    def ensure_output_directory(self) -> None:
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def copy_static_files(self, static_files: list[str]) -> None:
        """Copy multiple static files."""
        for file_path in static_files:
            # Check for colon syntax (source:dest)
            # Need to handle Windows paths like C:\\path\\file.txt:dest/path
            # Strategy: find the last colon that isn't preceded by exactly one character (drive letter)
            source_path = None
            dest_path = None
            
            # Find all colon positions
            colon_indices = [i for i, c in enumerate(file_path) if c == ":"]
            
            # Check if we have a source:dest pattern
            # Windows drive letter pattern: position 1 is colon and position 0 is alpha
            has_dest = False
            if len(colon_indices) > 0:
                # Check from the end for a colon that represents source:dest delimiter
                for colon_idx in reversed(colon_indices):
                    # If this colon is not at position 1 (not a drive letter)
                    # or if there are chars before it (not start of path)
                    if colon_idx != 1:
                        # This could be a source:dest delimiter
                        source = file_path[:colon_idx]
                        dest = file_path[colon_idx+1:]
                        # Verify source looks like a valid path (has path separators or is just a filename)
                        if "\\" in source or "/" in source or "." in source:
                            source_path = Path(source)
                            dest_path = self.output_dir / dest
                            has_dest = True
                            break
            
            if not has_dest:
                source_path = Path(file_path)
                dest_path = self.output_dir / source_path.name

            # Handle directories and files differently
            if source_path.exists():
                if source_path.is_dir():
                    # Copy directory
                    dest_path.mkdir(parents=True, exist_ok=True)
                    for item in source_path.rglob("*"):
                        if item.is_file():
                            rel_path = item.relative_to(source_path)
                            target = dest_path / rel_path
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, target)
                    print(f"📁 Directory copied: {source_path} -> {dest_path}")
                else:
                    # Copy file
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    print(f"📄 File copied: {source_path} -> {dest_path}")
            else:
                print(f"⚠️  Static file/directory not found: {source_path}")
