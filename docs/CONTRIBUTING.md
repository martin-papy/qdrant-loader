# Contributing to QDrant Loader

We welcome contributions to both the QDrant Loader and MCP Server packages! This guide will help you get started.

## 🏗️ Project Structure

This is a repository containing two main packages:

```text
qdrant-loader/
├── packages/
│   ├── qdrant-loader/           # Core loader functionality
│   └── qdrant-loader-mcp-server/ # MCP server functionality
├── docs/                        # Shared documentation
├── .github/workflows/           # CI/CD pipelines
└── pyproject.toml              # Workspace configuration
```

## 🚀 Getting Started

### Prerequisites

- Python 3.12 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/martin-papy/qdrant-loader.git
   cd qdrant-loader
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**

   ```bash
   make install-dev
   # Or manually:
   pip install -e packages/qdrant-loader[dev]
   pip install -e packages/qdrant-loader-mcp-server[dev]
   ```

4. **Set up configuration**

   ```bash
   cp config.template.yaml config.yaml
   cp env.template .env
   # Edit these files with your configuration
   ```

## 🔧 Development Workflow

### Making Changes

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - For loader functionality: work in `packages/qdrant-loader/`
   - For MCP server functionality: work in `packages/qdrant-loader-mcp-server/`
   - For shared documentation: work in `docs/`

3. **Follow coding standards**

   ```bash
   make format  # Format code
   make lint    # Check code quality
   ```

4. **Add tests**
   - Add tests for new functionality
   - Ensure existing tests still pass

   ```bash
   make test           # Run all tests
   make test-loader    # Test only loader package
   make test-mcp       # Test only MCP server package
   ```

5. **Update documentation**
   - Update relevant README files
   - Add docstrings to new functions/classes
   - Update CHANGELOG.md in the appropriate package

### Code Quality Standards

We maintain high code quality standards:

- **Formatting**: Use Black with 88 character line length
- **Import sorting**: Use isort with Black profile
- **Linting**: Use Ruff for fast Python linting
- **Type checking**: Use mypy for static type checking
- **Testing**: Maintain >80% test coverage

### Running Tests

```bash
# Run all tests
make test

# Run tests for specific package
make test-loader
make test-mcp

# Run tests with coverage
make test-coverage

# Run specific test file
pytest packages/qdrant-loader/tests/test_specific.py
```

### Code Formatting

```bash
# Format all code
make format

# Or run tools individually
black packages/
isort packages/
ruff check --fix packages/
```

## 📝 Commit Guidelines

We follow conventional commit format:

```text
type(scope): description

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Scopes

- `loader`: Changes to qdrant-loader package
- `mcp`: Changes to mcp-server package
- `docs`: Documentation changes
- `ci`: CI/CD changes
- `deps`: Dependency updates

### Examples

```text
feat(loader): add support for PDF document processing
fix(mcp): resolve connection timeout issues
docs: update installation instructions
test(loader): add tests for git connector
```

## 🔍 Pull Request Process

1. **Ensure your branch is up to date**

   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run all checks**

   ```bash
   make check  # Runs lint + test
   ```

3. **Create a pull request**
   - Use a clear, descriptive title
   - Reference any related issues
   - Describe what changes you made and why
   - Include screenshots for UI changes

4. **Address review feedback**
   - Make requested changes
   - Push updates to your branch
   - Respond to reviewer comments

## 🐛 Reporting Issues

When reporting issues:

1. **Check existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Provide clear reproduction steps**
4. **Include environment details**:
   - Python version
   - Package versions
   - Operating system
   - Relevant configuration

## 📦 Package-Specific Guidelines

### QDrant Loader Package

- Focus on data ingestion and processing
- Maintain connector interfaces
- Ensure proper error handling and logging
- Test with various data sources

### MCP Server Package

- Follow MCP protocol specifications
- Maintain API compatibility
- Ensure proper async/await usage
- Test integration with Cursor IDE

## 🏷️ Release Process

This project uses **unified versioning** - both packages always have the same version number. Releases are managed using the `release.py` script with comprehensive safety checks.

### Prerequisites

1. **Environment Setup**:

   ```bash
   # Ensure you have a GitHub token in .env
   echo "GITHUB_TOKEN=your_token_here" >> .env
   ```

2. **Clean Working Directory**:
   - All changes must be committed
   - No unpushed commits
   - Local main branch up to date with remote
   - All GitHub Actions workflows passing

### Release Steps

1. **Check Release Readiness**:

   ```bash
   # Dry run to see what would happen
   python release.py --dry-run
   ```

2. **Sync Package Versions** (if needed):

   ```bash
   # Sync all packages to the same version
   python release.py --sync-versions
   ```

3. **Create the Release**:

   ```bash
   # Interactive release process
   python release.py
   ```

### Release Script Features

The `release.py` script provides:

- **Safety Checks**: Git status, branch, workflows, and more
- **Unified Versioning**: Ensures both packages have the same version
- **Dry Run Mode**: Preview changes without making them
- **Version Sync**: Automatically sync package versions
- **GitHub Integration**: Creates releases and tags automatically
- **User-Friendly Output**: Clear, actionable feedback

### Version Bump Options

When creating a release, you can choose:

1. **Major** (e.g., 1.0.0) - Breaking changes
2. **Minor** (e.g., 0.2.0) - New features
3. **Patch** (e.g., 0.1.4) - Bug fixes
4. **Beta** (e.g., 0.1.3b2) - Pre-release versions
5. **Custom** - Specify exact version

### Automated Actions

The script automatically:

1. **Creates Git tags** for both packages
2. **Pushes tags** to GitHub
3. **Creates GitHub releases** with release notes
4. **Updates package versions** in pyproject.toml files
5. **Commits version changes** to the repository

### GitHub Actions Integration

After the release script completes, GitHub Actions will:

- Run all tests
- Build the packages
- Publish to PyPI

## 🤝 Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Share knowledge and best practices
- Follow our [Code of Conduct](CODE_OF_CONDUCT.md)

## 📚 Additional Resources

- [Release Management Guide](./RELEASE.md) - Comprehensive release documentation
- [QDrant Loader Documentation](../packages/qdrant-loader/README.md)
- [MCP Server Documentation](../packages/qdrant-loader-mcp-server/README.md)
- [Project Issues](https://github.com/martin-papy/qdrant-loader/issues)
- [Discussions](https://github.com/martin-papy/qdrant-loader/discussions)

## ❓ Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check package-specific README files

Thank you for contributing to QDrant Loader! 🎉
