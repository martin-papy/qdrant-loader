"""Main application entry point for RAG MCP Server."""

from .cli import cli


def main():
    """Main entry point that delegates to the CLI."""
    cli()


if __name__ == "__main__":
    main()
