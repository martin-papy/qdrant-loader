# Testing Strategy

## Overview

This document outlines the testing strategy for the Qdrant Loader application. The strategy encompasses both unit tests and integration tests, ensuring comprehensive coverage while maintaining efficiency and reliability.

## Test Organization

### Directory Structure

```test
tests/
├── fixtures/                    # Test data and fixtures
│   ├── unit/                   # Unit test fixtures
│   └── integration/            # Integration test fixtures
├── unit/                       # Unit tests
│   ├── core/                  # Core functionality tests
│   │   ├── config/           # Configuration tests
│   │   ├── embedding/        # Embedding service tests
│   │   └── state/           # State management tests
│   ├── sources/              # Source-specific tests
│   │   ├── publicdocs/      # Public docs source tests
│   │   ├── git/            # Git source tests
│   │   ├── confluence/     # Confluence source tests
│   │   └── jira/          # Jira source tests
│   └── utils/              # Utility function tests
└── integration/            # Integration tests
    ├── core/              # Core integration tests
    ├── sources/          # Source integration tests
    │   ├── publicdocs/  # Public docs integration
    │   ├── git/        # Git integration
    │   ├── confluence/ # Confluence integration
    │   └── jira/      # Jira integration
    └── end_to_end/    # End-to-end workflow tests
├── .env.test          # Test environment configuration
└── config.test.yaml   # Test application configuration
```

### Naming Conventions

- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*`
- Test classes: `Test*`
- Fixtures: `*_fixture` or descriptive names

## Test Types

### Unit Tests

- Isolated testing of individual components
- Heavy use of mocking for external services
- Focus on business logic and edge cases
- Quick execution for rapid feedback

### Integration Tests

- End-to-end testing with real services
- Uses configured test collection in Qdrant
- Minimal mocking, if any
- Tests complete workflows and interactions

## Test Infrastructure

### Configuration

- Uses `.env.test` for environment variables
- Uses `config.test.yaml` for application configuration
- Configuration follows same loading logic as main application

### Fixtures

- Uses pytest fixtures for common setup/teardown
- Fixtures are scoped appropriately (function, class, module, session)
- Promotes code reuse and maintainability

### Coverage

- Uses pytest-cov for coverage reporting
- Minimum coverage threshold: 80%
- Coverage reports generated in:
  - Local development
  - CI pipeline
  - Uploaded to Codacy

## CI Pipeline

### GitHub Actions

- Single job approach for simplicity
- Python 3.13.2
- Environment variables handled via secrets
- Coverage reports generation and upload
- Automatic deployment of coverage reports to GitHub Pages

## Best Practices

1. **Test Isolation**
   - Each test should be independent
   - Clean up resources after tests
   - Use appropriate fixture scoping

2. **Test Data Management**
   - Store test data in fixtures directory
   - Use meaningful test data
   - Keep test data up to date

3. **Mocking Strategy**
   - Mock external services in unit tests
   - Use real services in integration tests
   - Document mock behaviors

4. **Error Handling**
   - Test both success and failure cases
   - Verify error messages and codes
   - Test edge cases and boundary conditions

## Getting Started

1. Install development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run tests locally:

   ```bash
   pytest tests/ --cov=qdrant_loader --cov-report=html
   ```

3. View coverage reports:
   - HTML report in `htmlcov/` directory
   - Console output during test execution

## Maintenance

- Regularly review and update test coverage
- Keep test data current with application changes
- Update mocks when external services change
- Review and refactor tests for efficiency
