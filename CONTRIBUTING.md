# Contributing to QDrant Loader

Thank you for your interest in contributing to QDrant Loader! This guide will help you get started with contributing to our monorepo ecosystem.

## 🎯 Ways to Contribute

- **🐛 Bug Reports**: Help us identify and fix issues
- **✨ Feature Requests**: Suggest new features or improvements
- **📝 Documentation**: Improve our guides and references
- **🔧 Code Contributions**: Fix bugs, add features, or improve performance
- **🧪 Testing**: Add tests or improve test coverage
- **💬 Community Support**: Help other users in discussions

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** (latest stable version recommended)
- **Git** for version control
- **Virtual environment** (venv, conda, or similar)
- **QDrant instance** (local or cloud) for testing

### Development Setup

1. **Fork and Clone**

   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/qdrant-loader.git
   cd qdrant-loader
   ```

2. **Create Virtual Environment**

   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in Development Mode**

   ```bash
   # Install both packages with development dependencies
   pip install -e packages/qdrant-loader[dev]
   pip install -e packages/qdrant-loader-mcp-server[dev]
   ```

4. **Verify Installation**

   ```bash
   # Test that everything is working
   qdrant-loader --help
   mcp-qdrant-loader --help
   pytest --version
   ```

### Project Structure

```text
qdrant-loader/
├── packages/
│   ├── qdrant-loader/           # Core data ingestion package
│   │   ├── src/qdrant_loader/   # Source code
│   │   ├── tests/               # Package tests
│   │   ├── pyproject.toml       # Package configuration
│   │   └── README.md            # Package documentation
│   └── qdrant-loader-mcp-server/ # MCP server package
│       ├── src/qdrant_loader_mcp_server/
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
├── docs/                        # Documentation
├── website/                     # Documentation website generator
├── .github/workflows/           # CI/CD pipelines
├── pyproject.toml              # Workspace configuration
├── README.md                   # Main project README
└── CONTRIBUTING.md             # This file
```

## 🔧 Development Workflow

### 1. Create a Feature Branch

```bash
# Create and switch to a new branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- **Follow our coding standards** (see below)
- **Add tests** for new functionality
- **Update documentation** as needed
- **Keep commits focused** and atomic

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run tests for specific package
pytest packages/qdrant-loader/tests/
pytest packages/qdrant-loader-mcp-server/tests/

# Run with coverage
pytest --cov=packages --cov-report=html

# Run linting and formatting
black packages/
isort packages/
ruff check packages/
mypy packages/
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add support for new data source connector"

# Or for bug fixes
git commit -m "fix: resolve issue with file conversion timeout"
```

### 5. Push and Create Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create a pull request on GitHub
# Include a clear description of your changes
```

## 📝 Coding Standards

### Code Style

We use the following tools to maintain code quality:

- **[Black](https://black.readthedocs.io/)**: Code formatting
- **[isort](https://pycqa.github.io/isort/)**: Import sorting
- **[Ruff](https://docs.astral.sh/ruff/)**: Fast Python linter
- **[MyPy](https://mypy.readthedocs.io/)**: Static type checking

### Formatting Commands

```bash
# Format code
black packages/

# Sort imports
isort packages/

# Lint code
ruff check packages/

# Type checking
mypy packages/

# Fix auto-fixable issues
ruff check --fix packages/
```

### Code Guidelines

#### General Principles

- **Write clear, readable code** with descriptive variable and function names
- **Add type hints** for all function parameters and return values
- **Include docstrings** for all public functions, classes, and modules
- **Keep functions focused** and single-purpose
- **Handle errors gracefully** with appropriate exception handling

#### Docstring Format

Use Google-style docstrings:

```python
def process_document(content: str, metadata: Dict[str, Any]) -> ProcessedDocument:
    """Process a document with the given content and metadata.
    
    Args:
        content: The raw document content to process.
        metadata: Additional metadata about the document.
        
    Returns:
        A ProcessedDocument instance with chunked content and enriched metadata.
        
    Raises:
        ProcessingError: If the document cannot be processed.
    """
    # Implementation here
```

#### Type Hints

```python
from typing import Dict, List, Optional, Union
from pathlib import Path

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from a file."""
    pass

def process_files(files: List[Path], max_size: Optional[int] = None) -> List[str]:
    """Process a list of files."""
    pass
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit tests**: Test individual functions and classes in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch
from qdrant_loader.processors import DocumentProcessor

class TestDocumentProcessor:
    """Test cases for DocumentProcessor."""
    
    def test_process_simple_document(self):
        """Test processing a simple text document."""
        processor = DocumentProcessor()
        content = "This is a test document."
        
        result = processor.process(content)
        
        assert result.chunks
        assert len(result.chunks) == 1
        assert result.chunks[0].content == content
    
    @patch('qdrant_loader.processors.external_service')
    def test_process_with_external_service(self, mock_service):
        """Test processing with mocked external service."""
        mock_service.return_value = "processed content"
        processor = DocumentProcessor()
        
        result = processor.process("input")
        
        mock_service.assert_called_once_with("input")
        assert result.content == "processed content"
```

### Test Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest packages/qdrant-loader/tests/test_processors.py

# Run tests matching a pattern
pytest -k "test_document"

# Run with coverage
pytest --cov=packages --cov-report=html

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

## 📚 Documentation Guidelines

### Documentation Types

- **Code documentation**: Docstrings and inline comments
- **User guides**: How-to guides for end users
- **Developer documentation**: Architecture and API references
- **README files**: Package and project overviews

### Writing Documentation

#### Principles

- **Write for your audience**: Users vs. developers have different needs
- **Be clear and concise**: Avoid jargon and unnecessary complexity
- **Include examples**: Show, don't just tell
- **Keep it current**: Update docs when code changes

#### Markdown Guidelines

```markdown
# Use clear headings

## Structure content logically

### Include code examples

```bash
# Command examples should be copy-pastable
qdrant-loader --workspace . init
```

**Use formatting** for emphasis and `code` for technical terms.

- Create clear lists
- With actionable items
- That users can follow

### Building Documentation Website

```bash
# Build the documentation website
cd website
python build.py --output ../dist

# Serve locally for testing
cd ../dist
python -m http.server 8000
```

## 🚀 Pull Request Process

### Before Submitting

- [ ] **Tests pass**: All existing and new tests pass
- [ ] **Code is formatted**: Black, isort, and ruff checks pass
- [ ] **Type checking passes**: MyPy reports no errors
- [ ] **Documentation updated**: Relevant docs are updated

### Pull Request Template

When creating a pull request, include:

```markdown
## Description
Brief description of the changes and why they're needed.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Code is commented, particularly in hard-to-understand areas
- [ ] Corresponding changes to documentation made
- [ ] Tests added that prove the fix is effective or feature works
- [ ] New and existing unit tests pass locally
```

### Review Process

1. **Automated checks**: CI/CD pipeline runs tests and quality checks
2. **Code review**: Maintainers review code for quality and design
3. **Feedback incorporation**: Address review comments
4. **Approval and merge**: Once approved, changes are merged

## 🐛 Bug Reports

### Before Reporting

- **Search existing issues** to avoid duplicates
- **Try the latest version** to see if the issue is already fixed
- **Gather information** about your environment and the issue

### Bug Report Template

```markdown
## Bug Description
A clear and concise description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
A clear and concise description of what you expected to happen.

## Environment
- OS: [e.g. macOS 12.0, Ubuntu 20.04, Windows 10]
- Python version: [e.g. 3.12.2]
- QDrant Loader version: [e.g. 0.4.0b1]
- QDrant version: [e.g. 1.7.0]

## Additional Context
Add any other context about the problem here.
```

## ✨ Feature Requests

### Before Requesting

- **Check existing issues** for similar requests
- **Consider the scope**: Does it fit the project's goals?
- **Think about implementation**: How might it work?

### Feature Request Template

```markdown
## Feature Description
A clear and concise description of what you want to happen.

## Problem Statement
What problem does this feature solve? What's the current limitation?

## Proposed Solution
Describe the solution you'd like to see implemented.

## Alternatives Considered
Describe any alternative solutions or features you've considered.

## Additional Context
Add any other context, mockups, or examples about the feature request here.
```

## 🏷️ Release Process

### Version Management

We use **unified versioning** - both packages always have the same version number.

### Release Steps (for maintainers)

1. **Update version numbers** in both packages
2. **Create release branch** and test thoroughly
3. **Create GitHub release** with release notes
4. **Publish to PyPI** using the release script

```bash
# Check release readiness
python release.py --dry-run

# Create a new release
python release.py
```

## 🤝 Community Guidelines

### Code of Conduct

- **Be respectful** and inclusive in all interactions
- **Be constructive** in feedback and discussions
- **Be patient** with new contributors and users
- **Be collaborative** and help others succeed

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community discussions
- **Pull Requests**: Code review and collaboration

### Getting Help

- **Documentation**: Check our comprehensive docs first
- **Search Issues**: Look for existing solutions
- **Ask Questions**: Use GitHub Discussions for help
- **Be Specific**: Provide context and details when asking for help

## 📄 License

By contributing to QDrant Loader, you agree that your contributions will be licensed under the GNU GPLv3 license.

---

**Thank you for contributing to QDrant Loader!** Your contributions help make this project better for everyone. If you have questions about contributing, feel free to ask in [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions).
