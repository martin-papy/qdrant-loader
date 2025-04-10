# QDrant Loader

A tool for collecting and vectorizing technical content from multiple sources and storing it in a QDrant vector database. The ultimate goal is to use the qdrant database for coding more effectively using AI Tooling like: Cursor, Windsurf (using mcp-qdrant-server) or GitHub Copilot.

## Features

- Ingestion of technical content from various sources
- Smart chunking and preprocessing of documents
- Vectorization using OpenAI embeddings
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
    cp .env.template .env
    # Edit .env with your configuration
    ```

3. Create your configuration file:

    ```bash
    cp config.template.yaml config.yaml
    # Edit config.yaml with your source configurations
    ```

4. Initialize the QDrant collection:

    ```bash
    qdrant-loader init
    ```

5. Run the ingestion pipeline:

    ```bash
    qdrant-loader ingest
    ```

## Configuration

### Environment Variables

Required variables:

- `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME`
- `OPENAI_API_KEY`

Optional variables (required only for specific sources):

- Git: `REPO_TOKEN`, `REPO_URL`
- Confluence: `CONFLUENCE_URL`, `CONFLUENCE_SPACE_KEY`, `CONFLUENCE_TOKEN`, `CONFLUENCE_EMAIL`
- JIRA: `JIRA_URL`, `JIRA_PROJECT_KEY`, `JIRA_TOKEN`, `JIRA_EMAIL`

See [.env.template](.env.template) for all available environment variables and their descriptions.

### Configuration File

The `config.yaml` file controls the ingestion pipeline behavior. Key settings include:

```yaml
global:
  chunking:
    size: 500
    overlap: 50
  embedding:
    model: text-embedding-3-small
    batch_size: 100
  logging:
    level: INFO
    format: json
    file: qdrant-loader.log

sources:
  jira:
    my_project:
      base_url: "https://your-domain.atlassian.net"
      project_key: "PROJ"
      issue_types:
        - "Documentation"
        - "Technical Spec"
      include_statuses:
        - "Done"
        - "Approved"
```

See [config.template.yaml](config.template.yaml) for complete configuration options.

## Usage

### Command Line Interface

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
qdrant-loader ingest --source-type public-docs # Ingest only public docs
qdrant-loader ingest --source-type jira       # Ingest only JIRA

# Run ingestion for specific sources
qdrant-loader ingest --source-type confluence --source my-space
qdrant-loader ingest --source-type git --source my-repo
qdrant-loader ingest --source-type jira --source my-project

# Show current configuration
qdrant-loader config

# Show version information
qdrant-loader version
```

### Common Options

All commands support:

- `--verbose`: Enable verbose output
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--config FILE`: Specify custom config file (defaults to config.yaml)

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

# Install in development mode with additional dev dependencies
pip install -e
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest --cov=src tests/

# Run specific test files
pytest tests/test_config.py
pytest tests/test_qdrant_manager.py
pytest tests/test_embedding_service.py
pytest tests/test_cli.py
```

### Release Management

The project includes a release management script (`release.py`) to automate version bumping and GitHub releases.

```bash
# Run release script
python release.py

# Test release process (dry run)
python release.py --dry-run
```

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
