# Developer Documentation
Welcome to the QDrant Loader developer documentation! This guide provides everything you need to understand, extend, test, and deploy QDrant Loader. Whether you're contributing to the core project or building custom extensions, you'll find detailed technical information and practical examples here.
## 🎯 Quick Navigation
### Core Development
- **[Architecture Guide](./architecture.md)** - System design, components, and data flow
- **[Extending QDrant Loader](./extending.md)** - Custom connectors and processors
### Quality & Deployment
- **[Testing Guide](./testing.md)** - Testing strategies, frameworks, and best practices
- **[Deployment Guide](./deployment.md)** - Production deployment, containerization, and CI/CD
### Documentation
- **[Documentation Maintenance](./documentation/)** - Maintaining and updating documentation
## 🏗️ Architecture Overview
QDrant Loader follows a modular architecture designed for multi-project document ingestion and vector storage:
```
┌─────────────────────────────────────────────────────────────┐
│ QDrant Loader Core │
├─────────────────────────────────────────────────────────────┤
│ Data Sources │ Processing │ Vector Storage │
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────────┐ │
│ │ Connectors │ │ │ Processors │ │ │ QDrant Client │ │
│ │ - Local │ │ │ - MarkItDown│ │ │ - Collections │ │
│ │ - Git │ │ │ - Text │ │ │ - Vectors │ │
│ │ - Confluence│ │ │ - Chunking │ │ │ - Search │ │
│ │ - Jira │ │ │ - Embedding │ │ │ - Metadata │ │
│ │ - PublicDocs│ │ │ │ │ │ │ │
│ └─────────────┘ │ └─────────────┘ │ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ MCP Server │ CLI Interface │ Configuration │
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────────┐ │
│ │ Search APIs │ │ │ Commands │ │ │ YAML Config │ │
│ │ - Semantic │ │ │ - init │ │ │ - Multi-project │ │
│ │ - Hierarchy │ │ │ - ingest │ │ │ - Workspace │ │
│ │ - Attachment│ │ │ - config │ │ │ - Environment │ │
│ │ │ │ │ - project │ │ │ - Validation │ │
│ └─────────────┘ │ └─────────────┘ │ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```
## 🚀 Getting Started for Developers
### 1. Development Environment Setup
```bash
# Clone the repository
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader
# Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
# Install development dependencies
cd packages/qdrant-loader
pip install -e ".[dev]"
# Install MCP server package
cd ../qdrant-loader-mcp-server
pip install -e ".[dev]"
# Start QDrant for development
docker run -p 6333:6333 qdrant/qdrant:latest
```
### 2. Running Tests
```bash
# Run all tests from workspace root
make test
# Run specific package tests
cd packages/qdrant-loader
pytest
# Run with coverage
pytest --cov=qdrant_loader --cov-report=html
# Run MCP server tests
cd packages/qdrant-loader-mcp-server
pytest
```
### 3. Code Quality Checks
```bash
# From workspace root
make lint
make format
# Or manually
cd packages/qdrant-loader
black src/
isort src/
flake8 src/
mypy src/
```
## 📚 Core Concepts for Developers
### Data Flow Architecture
Understanding the data flow is crucial for development:
1. **Configuration Phase** - Multi-project workspace configuration - Global settings and project-specific sources - Environment variable management - Validation and initialization
2. **Ingestion Phase** - Connectors fetch documents from data sources - File conversion using MarkItDown library - Content extraction and cleaning - Chunking strategies for large documents - Metadata extraction and enrichment
3. **Embedding Phase** - Text content converted to embeddings via OpenAI - Batch processing for efficiency - Error handling and retries - Progress tracking and metrics
4. **Storage Phase** - Vectors stored in QDrant collections - Metadata indexed for filtering - Project-based organization - State tracking and change detection
5. **Search Phase (MCP Server)** - Semantic similarity search - Hierarchy-aware search - Attachment-specific search - Project filtering and organization
### Connector System
QDrant Loader uses a connector-based architecture for data sources:
```python
# Example connector implementation
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document
class CustomConnector(BaseConnector): async def get_documents(self) -> list[Document]: """Get documents from the source.""" documents = [] # Your custom logic here for item in self.fetch_data(): doc = Document( content=item.content, metadata=item.metadata, source_type="custom", source_name=self.config.name ) documents.append(doc) return documents
```
Available connectors:
- `LocalFileConnector` - Local file system
- `GitConnector` - Git repositories
- `ConfluenceConnector` - Confluence spaces
- `JiraConnector` - Jira projects
- `PublicDocsConnector` - Public documentation sites
## 🔧 Development Workflows
### Contributing to Core
1. **Fork and Clone** ```bash git clone https://github.com/your-username/qdrant-loader.git cd qdrant-loader git remote add upstream https://github.com/martin-papy/qdrant-loader.git ```
2. **Create Feature Branch** ```bash git checkout -b feature/your-feature-name ```
3. **Development Cycle** ```bash # Make changes # Run tests make test # Check code quality make lint # Commit changes git commit -m "feat: add new feature" ```
4. **Submit Pull Request** - Ensure all tests pass - Update documentation - Add changelog entry - Request review
### Custom Connector Development
1. **Create Connector Structure** ``` my-connector/ ├── src/ │ └── my_connector/ │ ├── __init__.py │ ├── connector.py │ └── config.py ├── tests/ └── pyproject.toml ```
2. **Implement Connector Interface** ```python from qdrant_loader.connectors.base import BaseConnector from qdrant_loader.config.source_config import SourceConfig class MyConnector(BaseConnector): def __init__(self, config: SourceConfig): super().__init__(config) # Initialize your connector async def get_documents(self) -> list[Document]: # Implement document fetching logic pass ```
3. **Add Configuration Support** ```python from pydantic import BaseModel class MyConnectorConfig(SourceConfig): source_type: str = "my_connector" api_key: str base_url: str # Add your configuration fields ```
## 📖 Detailed Guides
### [Architecture Guide](./architecture.md)
Deep dive into system design, component interactions, and architectural decisions. Essential reading for understanding how QDrant Loader works internally.
**Key Topics:**
- Multi-project workspace architecture
- Connector and processor interfaces
- Async ingestion pipeline design
- State management and change detection
- MCP server integration
### [Extending Guide](./extending.md)
Comprehensive guide for building custom functionality and connectors. Learn how to extend QDrant Loader for your specific needs.
**Key Topics:**
- Custom connector development
- File conversion extensions
- Configuration schema extensions
- Testing custom components
- Packaging and distribution
### [Testing Guide](./testing.md)
Testing strategies, frameworks, and best practices for ensuring code quality and reliability.
**Key Topics:**
- Unit testing with pytest
- Integration testing strategies
- Async testing patterns
- Mock and fixture usage
- CI/CD integration
### [Deployment Guide](./deployment.md)
Production deployment strategies, containerization, and operational best practices.
**Key Topics:**
- Docker containerization
- Environment configuration
- Monitoring and logging
- Performance optimization
- Security considerations
## 🛠️ Development Tools and Utilities
### Available CLI Commands
```bash
# Initialize QDrant collection\1init --workspace .
# Ingest documents\1ingest --workspace .
# View configuration\1config --workspace .
# Project management\1project\1--workspace\1\1 project\1--workspace\1\1 project\1--workspace\1# Start MCP server
mcp-qdrant-loader
```
### Debugging and Profiling
```bash
# Enable debug logging
qdrant-loader --log-level DEBUG --workspace . ingest
# Profile performance\1ingest --workspace . --profile
# Memory profiling (requires memory_profiler)
python -m memory_profiler your_script.py
```
### Development Scripts
```bash
# Makefile targets
make test # Run all tests
make lint # Run linting
make format # Format code
make docs # Build documentation
make clean # Clean build artifacts
```
## 🔗 Integration Examples
### Workspace Configuration
```yaml
# config.yaml
global_config: qdrant: url: "http://localhost:6333" collection_name: "my_collection" openai: api_key: "${OPENAI_API_KEY}"
projects: - project_id: "docs" sources: - source_type: "local_files" name: "documentation" config: base_url: "file://./docs" include_paths: ["**/*.md"]
```
### Programmatic Usage
```python
from qdrant_loader.config import Settings, get_settings
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline
# Load settings
settings = get_settings()
# Create and run pipeline
pipeline = AsyncIngestionPipeline(settings)
await pipeline.run()
```
### MCP Server Integration
```python
# The MCP server runs as a separate process
# Start with: mcp-qdrant-loader
# It provides search tools to AI development environments
# Tools available:
# - search_documents
# - search_with_hierarchy
# - search_attachments
```
## 📋 Development Checklist
### Before Submitting Code
- [ ] All tests pass (`make test`)
- [ ] Code style checks pass (`make lint`)
- [ ] Type checking passes (`mypy`)
- [ ] Documentation updated
- [ ] Changelog entry added (if applicable)
### For New Features
- [ ] Design document created (for major features)
- [ ] Tests cover all code paths
- [ ] Documentation includes examples
- [ ] Backward compatibility maintained
- [ ] Configuration schema updated (if needed)
### For Bug Fixes
- [ ] Root cause identified
- [ ] Regression test added
- [ ] Fix verified in multiple environments
- [ ] Documentation updated (if needed)
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
- **Core Features** - Enhanced search capabilities and performance
- **Connectors** - Additional data source integrations
- **Developer Experience** - Better tooling and documentation
- **Enterprise Features** - Advanced security and compliance
---
**Ready to start developing?** Choose your path:
- **New to QDrant Loader?** Start with the [Architecture Guide](./architecture.md)
- **Creating connectors?** Follow the [Extending Guide](./extending.md)
- **Setting up CI/CD?** Use the [Deployment Guide](./deployment.md)
**Need help?** Join our community discussions or open an issue on GitHub!
