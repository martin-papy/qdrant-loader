# 🧑‍💻 Coding Standards

This document outlines the coding standards and best practices for the QDrant Loader project. The standards are designed to be both human-readable and easily parseable by AI agents.

## 📋 Table of Contents

1. [Code Style](#code-style)
2. [Project Structure](#project-structure)
3. [Documentation](#documentation)
4. [Testing](#testing)
5. [Error Handling](#error-handling)
6. [Logging](#logging)
7. [Type Hints](#type-hints)
8. [Dependencies](#dependencies)

## 🎨 Code Style {#code-style}

### Python Code Formatting

- Use [Black](https://github.com/psf/black) for code formatting
- Maximum line length: 88 characters
- Use double quotes for strings
- Use trailing commas in multi-line lists/dictionaries
- Use type hints for all function parameters and return values

### Naming Conventions

- Class names: `PascalCase`
- Function names: `snake_case`
- Variable names: `snake_case`
- Constant names: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`
- Module names: `snake_case`

### Imports

- Use [isort](https://github.com/PyCQA/isort) for import sorting
- Group imports in this order:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Use absolute imports for local modules

## 📁 Project Structure

```text
qdrant-loader/
├── src/                    # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── embedding.py       # Embedding service
│   ├── qdrant_manager.py  # QDrant database operations
│   └── utils/             # Utility functions
├── tests/                 # Test files
├── docs/                  # Documentation
└── scripts/              # Utility scripts
```

## 📝 Documentation

### Docstrings

- Use Google-style docstrings
- Include type hints in docstrings
- Document all public functions, classes, and methods
- Include examples for complex functions

Example:

```python
def process_document(content: str, chunk_size: int = 500) -> List[str]:
    """Process a document into chunks of specified size.

    Args:
        content: The document content to process
        chunk_size: Maximum size of each chunk in tokens

    Returns:
        List of document chunks

    Example:
        >>> process_document("This is a test document", chunk_size=5)
        ["This is a", "test document"]
    """
```

### README and Documentation

- Keep README.md up to date
- Document all environment variables
- Include setup and usage instructions
- Document API endpoints and parameters

## 🧪 Testing

### Test Structure

- Use pytest for testing
- Follow the same directory structure as src/
- Test files should be named `test_*.py`
- Test functions should be named `test_*`

### Test Coverage

- Maintain minimum 80% test coverage
- Use pytest-cov for coverage reporting
- Document test cases in docstrings

### Testing Best Practices

- Use fixtures for common setup
- Mock external dependencies
- Test both success and failure cases
- Include integration tests for critical paths

## ⚠️ Error Handling

### Exception Handling

- Use specific exceptions rather than generic ones
- Include meaningful error messages
- Log exceptions with context
- Use custom exceptions for domain-specific errors

Example:

```python
class DocumentProcessingError(Exception):
    """Raised when document processing fails."""
    pass

try:
    process_document(content)
except ValueError as e:
    raise DocumentProcessingError(f"Invalid document format: {str(e)}")
```

## 📊 Logging

### Logging Standards

- Use structlog for structured logging
- Include context in log messages
- Use appropriate log levels:
  - DEBUG: Detailed information for debugging
  - INFO: General operational information
  - WARNING: Warning messages
  - ERROR: Error conditions
  - CRITICAL: Critical conditions

Example:

```python
import structlog

logger = structlog.get_logger()

def process_document(content: str):
    logger.info("processing_document", content_length=len(content))
    try:
        # Processing logic
        logger.info("document_processed_successfully")
    except Exception as e:
        logger.error("document_processing_failed", error=str(e))
        raise
```

## 🏷️ Type Hints

### Type Hinting Standards

- Use Python 3.8+ type hints
- Use typing module for complex types
- Use Optional for nullable values
- Use Union for multiple possible types
- Use TypeVar for generic types

Example:

```python
from typing import List, Optional, TypeVar, Union

T = TypeVar('T')

def process_items(items: List[T], max_items: Optional[int] = None) -> Union[List[T], None]:
    """Process a list of items with optional maximum count."""
    pass
```

## 📦 Dependencies

### Dependency Management

- Use requirements.txt for dependencies
- Pin all dependency versions
- Document all dependencies in README.md
- Use virtual environments for development
- Keep dependencies up to date

### Adding New Dependencies

1. Add to requirements.txt
2. Document in README.md
3. Update setup.py if needed
4. Test with clean environment

## 🔄 Version Control

### Git Standards

- Use meaningful commit messages
- Follow conventional commits
- Keep commits atomic and focused
- Use feature branches for development
- Submit PRs for review

### Branch Naming

- feature/: New features
- bugfix/: Bug fixes
- hotfix/: Urgent fixes
- docs/: Documentation updates
- test/: Test-related changes

Example:

```text
feature/add-document-processing
bugfix/fix-chunking-logic
docs/update-api-documentation
```
