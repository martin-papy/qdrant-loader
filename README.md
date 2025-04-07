# QDrant Loader

A tool for collecting and vectorizing technical content from multiple sources and storing it in a QDrant vector database. The ultimate goal is to use the qdrant database for coding more effectively using AI Tooling like: Cursor, Windsurf (using mcp-qdrant-server) or GitHub Copilot.

## Features

- Ingestion of technical content from various sources
- Smart chunking and preprocessing of documents
- Vectorization using OpenAI embeddings
- Storage in QDrant vector database
- Configurable through environment variables
- Command-line interface for easy operation

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

## Configuration

### Environment Variables

Create a `.env` file in your project root with the following variables:

```bash
# QDrant Configuration
QDRANT_URL=https://your-qdrant-instance:6333
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION_NAME=your-collection-name

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

```

### Configuration File

Create a `config.yaml` file in your project root for source-specific settings:

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
qdrant-loader ingest

# Run ingestion with specific configuration
qdrant-loader ingest --config custom-config.yaml

# Run ingestion for specific source types
qdrant-loader ingest --source-type confluence  # Ingest only Confluence sources
qdrant-loader ingest --source-type git        # Ingest only Git repositories
qdrant-loader ingest --source-type public-docs # Ingest only public documentation

# Run ingestion for a specific source
qdrant-loader ingest --source-type confluence --source my-space  # Specific Confluence space
qdrant-loader ingest --source-type git --source my-repo         # Specific Git repository
qdrant-loader ingest --source-type public-docs --source my-docs # Specific public docs

# Show current configuration
qdrant-loader config

# Show version information
qdrant-loader version
```

### Common Options

All commands support the following options:

```bash
# Enable verbose output
qdrant-loader [command] --verbose

# Set logging level
qdrant-loader [command] --log-level DEBUG
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

- Python 3.8 or higher
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
