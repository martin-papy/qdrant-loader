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
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager (replaces pip + venv)
- **QDrant instance** (local or cloud) for testing

Install uv if you don't have it:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Development Setup

1. **Fork and Clone**

   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/qdrant-loader.git
   cd qdrant-loader
   ```

2. **Install Dependencies**

   ```bash
   # Install all workspace packages with development dependencies
   # uv automatically creates and manages the virtual environment
   uv sync --all-packages --all-extras
   ```

3. **Verify Installation**

   ```bash
   # Test that everything is working
   uv run qdrant-loader --help
   uv run mcp-qdrant-loader --help
   uv run pytest --version
   ```

### Project Structure

```text
qdrant-loader/
├── packages/
│   ├── qdrant-loader-core/      # Shared core library
│   │   ├── src/qdrant_loader_core/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── qdrant-loader/           # Data ingestion package
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
├── pyproject.toml              # uv workspace configuration
├── uv.lock                     # Deterministic lockfile (committed to git)
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
make test

# Run tests for specific package
make test-loader
make test-mcp
make test-core

# Run with coverage
make test-coverage

# Run linting and formatting
make lint
make format
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

> **📖 For comprehensive guidelines** including Pythonic patterns, AI/RAG best practices, and PR review checklists, see the [Best Practices Guide](./docs/developers/contributing/README.md).

### Code Style

We use the following tools to maintain code quality:

- **[Black](https://black.readthedocs.io/)**: Code formatting
- **[isort](https://pycqa.github.io/isort/)**: Import sorting
- **[Ruff](https://docs.astral.sh/ruff/)**: Fast Python linter
- **[MyPy](https://mypy.readthedocs.io/)**: Static type checking

### Formatting Commands

```bash
# Format code (black + isort + ruff fix)
make format

# Lint only
make lint

# Or run tools directly via uv
uv run black .
uv run isort .
uv run ruff check --fix .
```

### Code Guidelines

Detailed implementation standards are maintained in one place:

- **[Best Practices Guide](./docs/developers/contributing/README.md)** for Pythonic patterns, DI, architecture constraints, AI/RAG quality gates, and PR review checklist

Minimum expectations for all contributions:

- Keep code readable and typed
- Add/maintain docstrings for public interfaces
- Prefer explicit dependencies over implicit behavior
- Handle errors with actionable messages and structured logs

## 🧪 Testing Guidelines

Testing standards and strategy are documented here:

- **[Developer Testing Guide](./docs/developers/testing/README.md)** for test design, scope, fixtures, and integration patterns
- **[Best Practices Guide](./docs/developers/contributing/README.md)** for AI/RAG-specific evaluation and review gates

### Test Commands

```bash
# Run all tests
make test

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest packages/qdrant-loader/tests/test_processors.py

# Run tests matching a pattern
uv run pytest -k "test_document"

# Run with coverage
make test-coverage

# Run only fast tests (skip slow integration tests)
uv run pytest -m "not slow"
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

````markdown
# Use clear headings

## Structure content logically

### Include code examples

```bash
# Command examples should be copy-pastable
qdrant-loader --workspace . init
```
````

**Use formatting** for emphasis and `code` for technical terms.

- Create clear lists
- With actionable items
- That users can follow

### Building Documentation Website

```bash
# Build the documentation website
make docs

# Or run directly
uv run python website/build.py --output site --templates website/templates --base-url "http://127.0.0.1:3000/site/"

# Serve locally for testing
cd site
uv run python -m http.server 8000
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
3. **Create GitHub release** with changelog
4. **Publish to PyPI** using the release script

```bash
# Check release readiness
uv run python release.py --dry-run

# Create a new release
uv run python release.py
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
