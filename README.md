# QDrant Loader

A tool for collecting and vectorizing technical content from multiple sources and storing it in a QDrant vector database. The ultimate goal is to use the qdrant database for coding more effectively using AI Tooling like: Cursor, Windsurf (using mcp-qdrant-server) or GitHub Copilot.

## Features

- Ingestion of technical content from various sources
- Smart chunking and preprocessing of documents
- Vectorization using OpenAI embeddings or any OpenAI-compatible endpoint
- Support for different embedding models (OpenAI, BAAI/bge-small-en-v1.5, etc.)
- Storage in QDrant vector database
- Configurable through environment variables and YAML configuration
- Command-line interface for easy operation
- Comprehensive logging and debugging capabilities

## Supported Connectors

- **Git**: Ingest code and documentation from Git repositories
- **Confluence**: Extract technical documentation from Confluence spaces
- **JIRA**: Collect technical specifications and documentation from JIRA issues
- **Public Documentation**: Ingest public technical documentation from websites
- **Custom Sources**: Extensible architecture for adding new data sources

## Quick Start

1. Install the package:

    ```bash
    pip install qdrant-loader
    ```

2. Configure your environment:

    ```bash
    # Download and configure environment variables
    curl -o .env https://raw.githubusercontent.com/kheldar666/qdrant-loader/main/.env.template
    # Edit .env with your configuration

    # Download and configure the main configuration file
    curl -o config.yaml https://raw.githubusercontent.com/kheldar666/qdrant-loader/main/config.template.yaml
    # Edit config.yaml with your source configurations
    ```

3. Initialize the QDrant collection:

    ```bash
    qdrant-loader init
    ```

4. Run the ingestion pipeline:

    ```bash
    qdrant-loader ingest
    ```

## Basic Commands

```bash
# Show help and available commands
qdrant-loader --help

# Initialize the QDrant collection
qdrant-loader init

# Run ingestion for all sources
qdrant-loader ingest

# Run ingestion for specific source types
qdrant-loader ingest --source-type confluence  # Ingest only Confluence
qdrant-loader ingest --source-type git        # Ingest only Git
qdrant-loader ingest --source-type jira       # Ingest only JIRA

# Show current configuration
qdrant-loader config

# Show version information
qdrant-loader version
```

## Documentation

For detailed documentation about the client usage, configuration options, and advanced features, please refer to the [Client Usage Guide](docs/ClientUsage.md).

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/kheldar666/qdrant-loader.git
cd qdrant-loader

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
.\venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install in development mode
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest --cov=src tests/
```

> **Note on Environment Files**: During tests, both `.env` and `.env.test` files are loaded, with `.env.test` taking precedence and overriding any common variables. This allows tests to use specific test configurations while maintaining default values for non-test-specific settings.

## Technical Requirements

- Python 3.12 or higher
- QDrant server (local or cloud instance)
- OpenAI API key
- Sufficient disk space for the vector database
- Internet connection for API access

## Contributing

We welcome contributions! Please:

1. Check existing issues to avoid duplicates
2. Create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Relevant error messages

For code contributions:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description
4. Ensure all tests pass

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
