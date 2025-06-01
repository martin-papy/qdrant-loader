# Developer Documentation

Welcome to the QDrant Loader developer documentation! This comprehensive guide provides everything you need to understand, extend, test, and deploy QDrant Loader. Whether you're contributing to the core project or building custom extensions, you'll find detailed technical information and practical examples here.

## 🎯 Quick Navigation

### Core Development

- **[Architecture Guide](./architecture.md)** - System design, components, and data flow
- **[API Reference](./api-reference.md)** - Complete API documentation with examples
- **[Extending QDrant Loader](./extending.md)** - Custom connectors, processors, and plugins

### Quality & Deployment

- **[Testing Guide](./testing.md)** - Testing strategies, frameworks, and best practices
- **[Deployment Guide](./deployment.md)** - Production deployment, containerization, and CI/CD

### Documentation

- **[Documentation Maintenance](./documentation/)** - Maintaining and updating documentation

## 🏗️ Architecture Overview

QDrant Loader follows a modular, plugin-based architecture designed for extensibility and scalability:

```
┌─────────────────────────────────────────────────────────────┐
│                    QDrant Loader Core                       │
├─────────────────────────────────────────────────────────────┤
│  Data Sources    │  Processing      │  Vector Storage       │
│  ┌─────────────┐ │  ┌─────────────┐ │  ┌─────────────────┐  │
│  │ Connectors  │ │  │ Processors  │ │  │ QDrant Client   │  │
│  │ - Local     │ │  │ - Text      │ │  │ - Collections   │  │
│  │ - Git       │ │  │ - PDF       │ │  │ - Vectors       │  │
│  │ - Confluence│ │  │ - Markdown  │ │  │ - Search        │  │
│  │ - Jira      │ │  │ - Code      │ │  │ - Metadata      │  │
│  └─────────────┘ │  └─────────────┘ │  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  MCP Server      │  CLI Interface   │  Configuration       │
│  ┌─────────────┐ │  ┌─────────────┐ │  ┌─────────────────┐  │
│  │ Search APIs │ │  │ Commands    │ │  │ YAML/JSON       │  │
│  │ - Semantic  │ │  │ - Load      │ │  │ - Environment   │  │
│  │ - Hierarchy │ │  │ - Search    │ │  │ - Validation    │  │
│  │ - Attachment│ │  │ - Status    │ │  │ - Schemas       │  │
│  └─────────────┘ │  └─────────────┘ │  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Getting Started for Developers

### 1. Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/qdrant-loader.git
cd qdrant-loader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Start QDrant for development
docker run -p 6333:6333 qdrant/qdrant:latest
```

### 2. Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/          # End-to-end tests

# Run with coverage
pytest --cov=qdrant_loader --cov-report=html
```

### 3. Code Quality Checks

```bash
# Format code
black qdrant_loader/
isort qdrant_loader/

# Lint code
flake8 qdrant_loader/
mypy qdrant_loader/

# Security checks
bandit -r qdrant_loader/
safety check
```

## 📚 Core Concepts for Developers

### Data Flow Architecture

Understanding the data flow is crucial for development:

1. **Ingestion Phase**
   - Connectors fetch documents from data sources
   - Processors extract and clean content
   - Chunking strategies split large documents
   - Metadata extraction enriches documents

2. **Embedding Phase**
   - Text content is converted to embeddings
   - Multiple embedding providers supported
   - Batch processing for efficiency
   - Error handling and retries

3. **Storage Phase**
   - Vectors stored in QDrant collections
   - Metadata indexed for filtering
   - Collection management and optimization
   - Backup and recovery strategies

4. **Search Phase**
   - Multiple search algorithms available
   - Semantic similarity search
   - Hierarchy-aware search
   - Attachment-specific search

### Plugin System

QDrant Loader uses a plugin-based architecture for extensibility:

```python
# Example custom connector
from qdrant_loader.connectors.base import BaseConnector

class CustomConnector(BaseConnector):
    def fetch_documents(self):
        # Your custom logic here
        pass
```

Entry points in `setup.py`:

```python
entry_points={
    "qdrant_loader.connectors": [
        "custom = my_plugin.connectors:CustomConnector",
    ],
}
```

## 🔧 Development Workflows

### Contributing to Core

1. **Fork and Clone**

   ```bash
   git clone https://github.com/your-username/qdrant-loader.git
   cd qdrant-loader
   git remote add upstream https://github.com/original-org/qdrant-loader.git
   ```

2. **Create Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Development Cycle**

   ```bash
   # Make changes
   # Run tests
   pytest tests/
   
   # Check code quality
   pre-commit run --all-files
   
   # Commit changes
   git commit -m "feat: add new feature"
   ```

4. **Submit Pull Request**
   - Ensure all tests pass
   - Update documentation
   - Add changelog entry
   - Request review

### Custom Extension Development

1. **Create Plugin Structure**

   ```
   my-qdrant-plugin/
   ├── setup.py
   ├── my_plugin/
   │   ├── __init__.py
   │   ├── connectors/
   │   ├── processors/
   │   └── search/
   └── tests/
   ```

2. **Implement Interfaces**
   - Extend base classes
   - Follow naming conventions
   - Add comprehensive tests
   - Document your extension

3. **Package and Distribute**

   ```bash
   python setup.py sdist bdist_wheel
   pip install my-qdrant-plugin
   ```

## 📖 Detailed Guides

### [Architecture Guide](./architecture.md)

Deep dive into system design, component interactions, and architectural decisions. Essential reading for understanding how QDrant Loader works internally.

**Key Topics:**

- System architecture and design patterns
- Component responsibilities and interfaces
- Data flow and processing pipelines
- Scalability and performance considerations
- Security architecture and threat model

### [API Reference](./api-reference.md)

Complete API documentation with detailed examples and usage patterns. Your go-to reference for programmatic integration.

**Key Topics:**

- Core classes and methods
- Data models and schemas
- Configuration APIs
- Search and retrieval APIs
- Error handling and exceptions
- Authentication and authorization

### [Extending Guide](./extending.md)

Comprehensive guide for building custom functionality and plugins. Learn how to extend QDrant Loader for your specific needs.

**Key Topics:**

- Plugin development framework
- Custom data source connectors
- File processors and content extractors
- Search providers and algorithms
- Authentication providers
- Packaging and distribution

### [Testing Guide](./testing.md)

Testing strategies, frameworks, and best practices for ensuring code quality and reliability.

**Key Topics:**

- Unit testing with pytest
- Integration testing strategies
- End-to-end testing scenarios
- Performance and load testing
- Security testing approaches
- CI/CD integration

### [Deployment Guide](./deployment.md)

Production deployment strategies, containerization, and operational best practices.

**Key Topics:**

- Docker containerization
- Kubernetes deployment
- Cloud platform integration (AWS, Azure, GCP)
- CI/CD pipelines
- Monitoring and observability
- Security configuration

## 🛠️ Development Tools and Utilities

### Code Generation

```bash
# Generate API documentation
sphinx-build -b html docs/ docs/_build/

# Generate type stubs
stubgen -p qdrant_loader -o stubs/

# Generate configuration schema
python scripts/generate_config_schema.py
```

### Debugging and Profiling

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Profile performance
import cProfile
cProfile.run('your_function()')

# Memory profiling
from memory_profiler import profile
@profile
def your_function():
    pass
```

### Development Scripts

```bash
# scripts/dev-setup.sh - Development environment setup
# scripts/run-tests.sh - Comprehensive test runner
# scripts/build-docs.sh - Documentation builder
# scripts/release.sh - Release automation
```

## 🔗 Integration Examples

### Programmatic Usage

```python
from qdrant_loader import QDrantLoader
from qdrant_loader.config import Config

# Load configuration
config = Config.from_file("config.yaml")

# Initialize loader
loader = QDrantLoader(config)

# Load documents
result = loader.load_source("my_documents")

# Search documents
results = loader.search("query", limit=10)
```

### Custom Connector Example

```python
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.models import Document

class DatabaseConnector(BaseConnector):
    def fetch_documents(self):
        # Connect to database
        # Fetch records
        # Convert to Document objects
        for record in self.fetch_records():
            yield Document(
                content=record.content,
                metadata=record.metadata,
                source_type="database"
            )
```

### MCP Server Integration

```python
from qdrant_loader.mcp_server import MCPServer

# Start MCP server
server = MCPServer(config)
server.start()

# Use with AI tools
# The server provides search capabilities to AI development tools
```

## 📋 Development Checklist

### Before Submitting Code

- [ ] All tests pass (`pytest`)
- [ ] Code coverage meets requirements (>80%)
- [ ] Code style checks pass (`black`, `isort`, `flake8`)
- [ ] Type checking passes (`mypy`)
- [ ] Security checks pass (`bandit`, `safety`)
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] Performance impact assessed

### For New Features

- [ ] Design document created
- [ ] API design reviewed
- [ ] Tests cover all code paths
- [ ] Documentation includes examples
- [ ] Backward compatibility maintained
- [ ] Migration guide provided (if needed)
- [ ] Performance benchmarks included

### For Bug Fixes

- [ ] Root cause identified
- [ ] Regression test added
- [ ] Fix verified in multiple environments
- [ ] Documentation updated (if needed)
- [ ] Related issues linked

## 🤝 Community and Support

### Getting Help

- **GitHub Issues** - Bug reports and feature requests
- **Discussions** - Questions and community support
- **Documentation** - Comprehensive guides and references
- **Code Examples** - Real-world usage patterns

### Contributing Guidelines

1. **Code of Conduct** - Be respectful and inclusive
2. **Issue Templates** - Use provided templates for consistency
3. **Pull Request Process** - Follow the established workflow
4. **Review Process** - Participate in code reviews
5. **Documentation** - Keep documentation up to date

### Development Roadmap

- **Core Features** - Enhanced search capabilities
- **Performance** - Optimization and scaling improvements
- **Integrations** - Additional data source connectors
- **Developer Experience** - Better tooling and documentation
- **Enterprise Features** - Advanced security and compliance

---

**Ready to start developing?** Choose your path:

- **New to QDrant Loader?** Start with the [Architecture Guide](./architecture.md)
- **Building integrations?** Check the [API Reference](./api-reference.md)
- **Creating extensions?** Follow the [Extending Guide](./extending.md)
- **Setting up CI/CD?** Use the [Deployment Guide](./deployment.md)

**Need help?** Join our community discussions or open an issue on GitHub!
