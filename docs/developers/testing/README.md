# Testing Guide

This section provides comprehensive testing documentation for QDrant Loader, covering unit testing, integration testing, and quality assurance practices.

## 🎯 Testing Overview

QDrant Loader follows a comprehensive testing strategy to ensure reliability, performance, and maintainability:

### 🧪 Testing Philosophy

1. **Test-Driven Development** - Write tests before implementing features
2. **Comprehensive Coverage** - Aim for 85%+ test coverage
3. **Fast Feedback** - Quick unit tests for rapid development
4. **Real-World Testing** - Integration tests with actual services
5. **Performance Validation** - Regular performance benchmarking

### 📚 Testing Categories

- **Unit Testing** - Testing individual components in isolation
- **Integration Testing** - Testing component interactions and end-to-end workflows
- **Quality Assurance** - Code quality, review processes, and standards

## 🚀 Quick Start

### Test Environment Setup

```bash
# Clone the repository
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader

# Install all workspace packages with development dependencies
# uv automatically creates and manages the virtual environment
# All test tools (pytest, pytest-asyncio, pytest-cov, pytest-mock, etc.)
# are declared as dev dependencies and installed automatically
uv sync --all-packages --all-extras

# Run all tests (verbose)
uv run pytest -v

# Run with coverage per package
make test-loader    # qdrant-loader package
make test-mcp       # qdrant-loader-mcp-server package
make test-core      # qdrant-loader-core package
make test-coverage  # all packages with HTML coverage report
```

### Running Specific Test Categories

```bash
# Unit tests only
uv run pytest packages/qdrant-loader/tests/unit/
# Integration tests only
uv run pytest packages/qdrant-loader/tests/integration/
# Specific test file
uv run pytest packages/qdrant-loader/tests/unit/core/test_qdrant_manager.py
# Specific test function
uv run pytest packages/qdrant-loader/tests/unit/core/test_qdrant_manager.py::TestQdrantManager::test_initialization_default_settings
```

## 🧪 Testing Framework

### Core Testing Tools

| Tool               | Purpose                   | Usage                      |
| ------------------ | ------------------------- | -------------------------- |
| **pytest**         | Test runner and framework | Main testing framework     |
| **pytest-asyncio** | Async test support        | Testing async functions    |
| **pytest-cov**     | Coverage reporting        | Code coverage analysis     |
| **pytest-mock**    | Mocking utilities         | Mock external dependencies |
| **requests-mock**  | HTTP mocking              | Mock external HTTP calls   |
| **pytest-timeout** | Test timeouts             | Prevent hanging tests      |

### Test Configuration

- Key settings live in [pyproject.toml](../../../pyproject.toml) under `[tool.pytest.ini_options]` and coverage settings under `[tool.coverage.*]`:

### Test Structure

```text
packages/qdrant-loader/tests/
├── conftest.py
├── fixtures/
├── unit/
│   ├── cli/
│   ├── config/
│   ├── connectors/
│   ├── core/
│   ├── quality/
│   └── utils/
└── integration/
```

## 🔧 Test Fixtures and Mock Utilities

- Shared fixtures: [packages/qdrant-loader/tests/conftest.py](../../../packages/qdrant-loader/tests/conftest.py)
- Loader test helpers: [packages/qdrant-loader/tests/utils.py](../../../packages/qdrant-loader/tests/utils.py)
- Core package fixtures: [packages/qdrant-loader-core/tests/conftest.py](../../../packages/qdrant-loader-core/tests/conftest.py)
- MCP server fixtures: [packages/qdrant-loader-mcp-server/tests/conftest.py](../../../packages/qdrant-loader-mcp-server/tests/conftest.py)

## 🧪 Unit Testing Patterns

Keep tests focused on behavior and run them by scope.

```bash
# All loader unit tests
uv run pytest packages/qdrant-loader/tests/unit/ -v

# Focused areas
uv run pytest packages/qdrant-loader/tests/unit/cli/ -v
uv run pytest packages/qdrant-loader/tests/unit/core/ -v
uv run pytest packages/qdrant-loader/tests/unit/quality/ -v
```

Examples:

- CLI unit tests: [packages/qdrant-loader/tests/unit/cli/](../../../packages/qdrant-loader/tests/unit/cli/)
- Core unit tests: [packages/qdrant-loader/tests/unit/core/](../../../packages/qdrant-loader/tests/unit/core/)
- Quality unit tests: [packages/qdrant-loader/tests/unit/quality/](../../../packages/qdrant-loader/tests/unit/quality/)

## 🔗 Integration Testing

Run integration tests separately because they may require external services or secrets.

```bash
uv run pytest packages/qdrant-loader/tests/integration/ -v
```

Examples:

- Loader integration tests: [packages/qdrant-loader/tests/integration/](../../../packages/qdrant-loader/tests/integration/)
- MCP integration tests: [packages/qdrant-loader-mcp-server/tests/integration/](../../../packages/qdrant-loader-mcp-server/tests/integration/)

## 🧪 Performance Testing

Performance tests are optional for most PRs and should be run for performance-sensitive changes.

- Start from: [packages/qdrant-loader/tests/](../../../packages/qdrant-loader/tests/)
- Use profiling targets and commands in: [Makefile](../../../Makefile)

## 🔍 Quality Assurance

### Code Quality Checks

```bash
# Run all quality checks
make test
make lint
make format
# Individual checks via uv
uv run ruff check .          # Linting
uv run ruff format --check . # Code formatting check
# Per-package test coverage
make test-loader   # packages/qdrant-loader
make test-mcp      # packages/qdrant-loader-mcp-server
make test-core     # packages/qdrant-loader-core
make test-coverage # all packages combined
```

### Package-specific quality gates

- Import cycle and module size guards are under `packages/qdrant-loader/tests/unit/quality/` or `packages/qdrant-loader-mcp-server/tests/unit/quality/`.
- Keep refactored modules within target sizes (<300–400 lines) unless explicitly exempted in tests.
- Prefer thin entrypoints and shared helpers to avoid duplication.

### Continuous Integration

- CI workflows:
  - Test workflow: [.github/workflows/test.yml](../../../.github/workflows/test.yml)
  - Quality workflow: [.github/workflows/quality-gates.yml](../../../.github/workflows/quality-gates.yml)

Notes:

- CI uses uv for dependency management.
- Integration tests in CI are conditionally executed based on branch/event and secret availability.

## 📚 Testing Best Practices

### Guidelines

1. **Write tests first** - Follow TDD principles
2. **Test behavior, not implementation** - Focus on what, not how
3. **Use descriptive test names** - Make test purpose clear
4. **Keep tests independent** - No test should depend on another
5. **Mock external dependencies** - Isolate units under test
6. **Test edge cases** - Include error conditions and boundary values

### Testing Checklist

- [ ] Unit tests for all new functionality
- [ ] Integration tests for user workflows
- [ ] Error handling and edge cases covered
- [ ] Mocks for external dependencies
- [ ] Test data cleanup
- [ ] Documentation updated

### Common Patterns

```python
# Async testing
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None

# Exception testing
def test_exception_handling():
    with pytest.raises(ValueError, match="Expected error message"):
        function_that_should_raise()

# Parametrized testing
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
])
def test_multiple_inputs(input, expected):
    assert process_input(input) == expected

# Mocking with patch
@patch("module.external_function")
def test_with_mock(mock_function):
    mock_function.return_value = "mocked_result"
    result = function_under_test()
    assert result == "expected_result"
```

## 🆘 Getting Help

### Testing Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report testing issues
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask testing questions
- **[Test Examples](https://github.com/martin-papy/qdrant-loader/tree/main/packages/qdrant-loader/tests)** - Reference implementations

### Contributing Tests

- **[Contributing Guide](/docs/CONTRIBUTING.md)** - How to contribute tests
- **[Development Setup](../)** - Development environment setup

---

**Ready to write tests?** Start with unit tests for individual components or check out the existing test suite for patterns and examples.
