#!/usr/bin/env python3
"""
Main entry point for the QDrant Loader CLI.
"""
from qdrant_loader.cli import main


# For backward compatibility, also expose the cli function
def cli():
    """CLI entry point for backward compatibility."""
    main()


if __name__ == "__main__":
    main()
