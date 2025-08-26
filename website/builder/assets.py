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
                    if file.endswith(('.py', '.pyc', '__pycache__')):
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
            source_path = Path(file_path)

            if ":" in file_path:
                source, dest = file_path.split(":", 1)
                source_path = Path(source)
                dest_path = self.output_dir / dest
            else:
                # Copy to same relative path
                dest_path = self.output_dir / source_path.name

            # Handle directories and files differently
            if source_path.exists():
                if source_path.is_dir():
                    # Copy directory
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"📁 Directory copied: {source_path} -> {dest_path}")
                else:
                    # Copy file
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    print(f"📄 File copied: {source_path} -> {dest_path}")
            else:
                print(f"⚠️  Static file/directory not found: {source_path}")
