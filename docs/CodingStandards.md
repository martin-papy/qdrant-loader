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
9. [Connector Development](#connector-development)
10. [State Management](#state-management)

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
├── src/
│   ├── qdrant_loader/
│   │   ├── core/                    # Core functionality
│   │   │   ├── state/              # State management
│   │   │   ├── performance/        # Performance optimization
│   │   │   └── ingestion_pipeline.py
│   │   │
│   │   ├── connectors/             # Source connectors
│   │   │   ├── git/               # Git connector
│   │   │   ├── confluence/        # Confluence connector
│   │   │   ├── jira/             # Jira connector
│   │   │   ├── publicdocs/      # Public docs connector
│   │   │   └── base.py           # Base connector classes
│   │   │
│   │   ├── config/               # Configuration management
│   │   ├── cli/                 # Command line interface
│   │   └── utils/              # Utility functions
│   │
├── tests/                      # Test files
│   ├── unit/                  # Unit tests
│   ├── integration/          # Integration tests
│   └── fixtures/            # Test fixtures
│
├── docs/                    # Documentation
└── scripts/               # Utility scripts
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
- Include tests for both connector and change detection functionality
- Test state management operations
- Test incremental ingestion scenarios

### Test Coverage

- Maintain minimum 80% test coverage
- Use pytest-cov for coverage reporting
- Document test cases in docstrings
- Include tests for:
  - Connector functionality
  - Change detection
  - State management
  - Incremental ingestion
  - Error handling
  - Performance optimization

### Testing Best Practices

- Use fixtures for common setup
- Mock external dependencies
- Test both success and failure cases
- Include integration tests for critical paths
- Test state persistence and recovery
- Test concurrent operations

## ⚠️ Error Handling

### Exception Handling

- Use specific exceptions rather than generic ones
- Include meaningful error messages
- Log exceptions with context
- Use custom exceptions for domain-specific errors
- Handle state management errors appropriately
- Implement proper error recovery for incremental ingestion

Example:

```python
class StateManagementError(Exception):
    """Raised when state management operations fail."""
    pass

class ChangeDetectionError(Exception):
    """Raised when change detection fails."""
    pass

class IncrementalIngestionError(Exception):
    """Raised when incremental ingestion fails."""
    pass
```

## 📊 Logging

### Logging Standards

- Use structlog for structured logging
- Include context in log messages
- Use appropriate log levels
- Log state management operations
- Log change detection events
- Log incremental ingestion progress

Example:

```python
import structlog

logger = structlog.get_logger()

def process_incremental_changes(source_type: str, source: str):
    logger.info("processing_incremental_changes", 
                source_type=source_type,
                source=source)
    try:
        # Processing logic
        logger.info("changes_processed_successfully",
                   change_count=len(changes))
    except Exception as e:
        logger.error("change_processing_failed",
                    error=str(e),
                    source_type=source_type,
                    source=source)
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

## 🔌 Connector Development

### Connector Structure

- Each connector should be in its own directory
- Include both connector and change detection logic
- Follow the base connector interface
- Implement proper error handling
- Include comprehensive testing

Example:

```python
from qdrant_loader.connectors.base import BaseConnector, BaseChangeDetector

class GitConnector(BaseConnector):
    """Git connector implementation."""
    pass

class GitChangeDetector(BaseChangeDetector):
    """Git change detection implementation."""
    pass
```

### Change Detection

- Implement source-specific change detection
- Track document modifications
- Handle document deletions
- Support incremental updates
- Include proper error handling

### Testing Connectors

- Test connector functionality
- Test change detection
- Test error handling
- Test state management integration
- Test incremental ingestion

## 💾 State Management

### Database Operations

- Use SQLAlchemy for database operations
- Implement proper migrations
- Handle concurrent access
- Include error recovery
- Support both user and package paths

### State Tracking

- Track document states
- Track ingestion history
- Handle state updates
- Support state recovery
- Implement proper cleanup

### Testing State Management

- Test database operations
- Test state tracking
- Test concurrent access
- Test error recovery
- Test state persistence
