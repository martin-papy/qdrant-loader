# QDrant Loader

A tool for collecting and vectorizing technical content from multiple sources and storing it in a QDrant vector database.

## Features

- Ingestion of technical content from various sources
- Smart chunking and preprocessing of documents
- Vectorization using OpenAI embeddings
- Storage in QDrant vector database
- Configurable through environment variables

## Setup

1. Clone the repository:

    ```bash
    git clone <repository-url>
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
