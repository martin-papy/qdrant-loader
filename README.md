# QDrant Loader

A tool for collecting and vectorizing technical content from multiple sources and storing it in a QDrant vector database. The ultime goal is to use the qdrant database for coding more effectively using AI Tooling like : Cursor, Windsufr ( using mcp-qdrant-server ) or GitHub Copilot.

## Features

- Ingestion of technical content from various sources
- Smart chunking and preprocessing of documents
- Vectorization using OpenAI embeddings
- Storage in QDrant vector database
- Configurable through environment variables

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

5. Initialize the QDrant collection:

    ```bash
    python -m src.init_collection
    ```

    This will create a collection with:
    - 1536 dimensions (matching OpenAI's text-embedding-3-small model)
    - Cosine similarity distance metric
    - Collection name as specified in your .env file

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
```

## Usage

[Usage instructions will be added as the project develops]

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

The GNU GPLv3 is a copyleft license that requires anyone who distributes your code or a derivative work to make the source available under the same terms. This license also provides patent protection and protection against tivoization.
