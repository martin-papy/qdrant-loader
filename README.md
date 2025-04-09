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

## Setup

1. Clone the repository:

    ```bash
    git clone https://github.com/kheldar666/qdrant-loader.git
    cd qdrant-loader
    ```

2. Create and activate a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On macOS/Linux
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Configure environment variables:

    ```bash
    cp .env.template .env
    # Edit .env with your configuration
    ```

    See [.env.template](.env.template) for all available environment variables and their descriptions.

5. Create your configuration file:

    ```bash
    cp config.template.yaml config.yaml
    # Edit config.yaml with your source configurations
    ```

    See [config.template.yaml](config.template.yaml) for detailed configuration options and examples.

## Configuration

### Environment Variables

Create a `.env` file in your project root with the following variables (not all are mandatory):

```bash
# QDrant Configuration
QDRANT_URL=https://your-qdrant-instance:6333
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION_NAME=your-collection-name

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Git Configuration
REPO_TOKEN=your-repo-token               # Github PAT
REPO_URL=your-repo-url

# Confluence Configuration
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=your-space-key
CONFLUENCE_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=your-confluence-email

# JIRA Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_PROJECT_KEY=your-project-key
JIRA_TOKEN=your-jira-token
JIRA_EMAIL=your-jira-email

# Logging Configuration (Optional)
LOG_LEVEL=INFO                           # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                          # Options: json, plain
```

Environment variables can be set in three ways:

1. In the `.env` file (recommended for development)
2. As system environment variables
3. Through the shell before running commands

Required variables:

- `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME`
- `OPENAI_API_KEY`

Optional variables:

- Source-specific variables are only required if you're using that source
- Logging variables have sensible defaults

Note: API keys and tokens are automatically masked in logs and output.

### Configuration File

The configuration file (`config.yaml`) is required for running the ingestion pipeline. It contains source-specific settings and global configurations. See [config.template.yaml](config.template.yaml) for a complete template with detailed comments:

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

## Usage

### Installation

You can use QDrant Loader in two ways:

1. **Install from PyPI (Recommended for end users)**:

   ```bash
   pip install qdrant-loader
   ```

2. **Install from source (Recommended for development)**:

   ```bash
   # Clone the repository
   git clone https://github.com/kheldar666/qdrant-loader.git
   cd qdrant-loader

   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   .\venv\Scripts\activate  # On Windows

   # Install in development mode
   pip install -e .
   ```

### Command Line Interface

The QDrant Loader provides a command-line interface for all operations. After installation, you can use the `qdrant-loader` command:

```bash
# Show help and available commands
qdrant-loader --help

# Initialize the QDrant collection
qdrant-loader init

# Force reinitialize the collection
qdrant-loader init --force

# Run the ingestion pipeline
# Will use config.yaml in current directory if --config is not specified
qdrant-loader ingest
# Or specify a custom config file
qdrant-loader ingest --config custom-config.yaml

# Run ingestion for specific source types
qdrant-loader ingest --source-type confluence  # Ingest only Confluence sources
qdrant-loader ingest --source-type git        # Ingest only Git repositories
qdrant-loader ingest --source-type public-docs # Ingest only public documentation
qdrant-loader ingest --source-type jira       # Ingest only JIRA sources

# Run ingestion for a specific source
qdrant-loader ingest --source-type confluence --source my-space  # Specific Confluence space
qdrant-loader ingest --source-type git --source my-repo         # Specific Git repository
qdrant-loader ingest --source-type public-docs --source my-docs # Specific public docs
qdrant-loader ingest --source-type jira --source my-project     # Specific JIRA project

# Show current configuration
qdrant-loader config

# Show version information
qdrant-loader version
```

### Logging and Debugging

The CLI provides comprehensive logging capabilities:

```bash
# Enable verbose output
qdrant-loader [command] --verbose

# Set logging level
qdrant-loader [command] --log-level DEBUG

# View logs in real-time
tail -f qdrant-loader.log
```

Logs are written to both:

1. Console (stdout)
2. Log file (default: `qdrant-loader.log`)

Log levels available:

- `DEBUG`: Detailed information for debugging
- `INFO`: General operational information
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failed operations
- `CRITICAL`: Critical errors that prevent operation

Log formats:

- `json`: Structured JSON format (default)
- `plain`: Human-readable text format

### Common Options

All commands support the following options:

```bash
# Enable verbose output
qdrant-loader [command] --verbose

# Set logging level
qdrant-loader [command] --log-level DEBUG

# Specify config file (optional, defaults to config.yaml)
qdrant-loader [command] --config custom-config.yaml
```

### Python Module Usage

You can also use the CLI directly through Python:

```bash
# When installed from PyPI
python -m qdrant_loader.cli [command] [options]

# When running from source
python -m src.qdrant_loader.cli [command] [options]
```

### Development Usage

When working with the source code:

1. **Running Tests**:

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

2. **Building the Package**:

   ```bash
   # Build the package
   python -m build

   # Install the built package
   pip install dist/qdrant_loader-*.whl
   ```

3. **Running from Source**:

   ```bash
   # Run the CLI directly from source
   python -m src.qdrant_loader.cli [command] [options]

   # Run with development logging
   LOG_LEVEL=DEBUG python -m src.qdrant_loader.cli [command] [options]
   ```

## Technical Requirements

- Python 3.12 or higher
- QDrant server (local or cloud instance)
- OpenAI API key
- Sufficient disk space for the vector database
- Internet connection for API access

## Contributing and Support

We welcome contributions and feedback! Here's how you can get involved:

### Reporting Issues

If you encounter any bugs or have feature requests, please:

1. Check the [existing issues](https://github.com/kheldar666/qdrant-loader/issues) to avoid duplicates
2. Create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the problem
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)
   - Relevant error messages or logs

### Providing Feedback

- For general feedback or suggestions, create a [Discussion](https://github.com/kheldar666/qdrant-loader/discussions)
- For code contributions, please:
  1. Fork the repository
  2. Create a feature branch
  3. Submit a pull request with a clear description of changes
  4. Ensure all tests pass and new code is covered by tests

## Development

### Running Tests

Run the full test suite:

```bash
pytest tests/
```

Run tests with coverage report:

```bash
pytest --cov=src tests/
```

Run specific test files:

```bash
pytest tests/test_config.py
pytest tests/test_qdrant_manager.py
pytest tests/test_embedding_service.py
pytest tests/test_cli.py
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

The GNU GPLv3 is a copyleft license that requires anyone who distributes your code or a derivative work to make the source available under the same terms. This license also provides patent protection and protection against tivoization.
