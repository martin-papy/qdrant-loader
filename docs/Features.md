# 🚀 QDrant Loader Features

This document provides a comprehensive overview of all features and capabilities available in the QDrant Loader monorepo ecosystem.

## 📦 Package Overview

The QDrant Loader monorepo consists of two main packages that work together to provide a complete RAG (Retrieval-Augmented Generation) solution:

- **[qdrant-loader](../packages/qdrant-loader/)**: Core data ingestion and processing engine
- **[qdrant-loader-mcp-server](../packages/qdrant-loader-mcp-server/)**: Model Context Protocol server for AI tool integration

## 🔄 QDrant Loader Core Features

### Data Source Connectors

#### Git Repository Connector

- **Multi-repository support**: Ingest from multiple Git repositories simultaneously
- **Branch selection**: Choose specific branches for ingestion
- **File filtering**: Include/exclude files using glob patterns
- **File type support**: Process various file types (Markdown, code, documentation)
- **Commit metadata**: Extract author, date, and commit message information
- **Size limits**: Configurable file size limits to prevent memory issues
- **Depth control**: Limit directory traversal depth for performance

**Supported file types:**

- Documentation: `*.md`, `*.rst`, `*.txt`
- Code: `*.py`, `*.js`, `*.ts`, `*.java`, `*.go`, `*.rb`, `*.php`
- Configuration: `*.yaml`, `*.yml`, `*.json`, `*.toml`
- Web: `*.html`, `*.css`

#### Confluence Connector

- **Multi-deployment support**: Works with Confluence Cloud, Data Center, and Server
- **Secure authentication**: API tokens (Cloud) and Personal Access Tokens (Data Center/Server)
- **Space-based ingestion**: Process entire Confluence spaces
- **Content type filtering**: Select pages, blog posts, or both
- **Label-based filtering**: Include/exclude content based on labels
- **Rich content support**: Handle attachments, images, and formatted content
- **Comment processing**: Extract and process page comments
- **Version tracking**: Track content versions and updates
- **HTML cleaning**: Intelligent HTML-to-text conversion
- **Deployment-specific pagination**: Optimized pagination for each deployment type

**Advanced features:**

- Automatic content cleaning and normalization
- Metadata extraction (author, creation date, labels)
- Hierarchical content structure preservation
- Rate limiting to respect Confluence API limits
- Auto-detection of deployment type based on URL patterns
- Comprehensive error handling for secure authentication methods

#### Jira Connector

- **Multi-deployment support**: Works with JIRA Cloud, Data Center, and Server
- **Secure authentication**: API tokens (Cloud) and Personal Access Tokens (Data Center/Server)
- **Project-based ingestion**: Process entire Jira projects
- **Issue type filtering**: Select specific issue types to process
- **Status-based filtering**: Include/exclude based on issue status
- **Attachment processing**: Handle issue attachments and files
- **Comment extraction**: Process issue comments and discussions
- **Relationship tracking**: Capture issue links and dependencies
- **Incremental sync**: Track last sync time for efficient updates
- **User field compatibility**: Handles different user formats between deployments
- **Deployment-specific optimization**: Optimized settings for each deployment type

**Advanced features:**

- Automatic deployment type detection based on URL patterns
- Deployment-specific authentication (Basic Auth for Cloud, Bearer tokens for Data Center)
- User data format handling (`accountId` for Cloud, `name`/`key` for Data Center)
- Rate limiting optimized for each deployment type
- Comprehensive error handling for secure authentication methods

**Metadata captured:**

- Issue details (key, summary, description, status, priority)
- User information (reporter, assignee, commenters) with cross-deployment compatibility
- Timestamps (created, updated, resolved)
- Custom fields and labels
- Issue relationships, subtasks, and linked issues
- Attachment metadata with author information

#### Public Documentation Connector

- **Website scraping**: Extract content from public documentation sites
- **CSS selector support**: Use CSS selectors for precise content extraction
- **Version detection**: Automatically detect and track documentation versions
- **Content cleaning**: Remove navigation, headers, and irrelevant content
- **Code block preservation**: Maintain formatting for code examples
- **Link resolution**: Handle relative and absolute links

**Configuration options:**

- Custom CSS selectors for content extraction
- Element removal patterns
- Version pattern matching
- Path filtering and exclusion

#### Local File Connector

- **Directory scanning**: Recursively scan local directories
- **Pattern matching**: Use glob patterns for file selection
- **File type filtering**: Process specific file extensions
- **Metadata extraction**: Capture file system metadata
- **Symbolic link handling**: Follow or ignore symbolic links
- **Size and depth limits**: Configurable limits for performance

### 🆕 File Conversion Support (v0.3.1)

QDrant Loader now includes comprehensive file conversion capabilities, enabling automatic processing of diverse file formats:

#### Supported File Types (20+)

**Documents:**

- **PDF**: Text extraction with layout preservation
- **Microsoft Office**: Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
- **OpenDocument**: ODT, ODS, ODP formats

**Images:**

- **Formats**: PNG, JPEG, GIF, BMP, TIFF, WebP
- **OCR Support**: Optional text extraction from images using AI
- **Metadata**: EXIF data preservation and analysis

**Data Formats:**

- **Structured**: JSON, CSV, XML, YAML
- **Tabular**: Excel spreadsheets with multiple sheets
- **Configuration**: INI, TOML files

**Archives:**

- **ZIP Files**: Automatic extraction and processing of contents
- **Nested Archives**: Support for archives within archives

**Audio:**

- **Formats**: MP3, WAV, M4A
- **Transcription**: Automatic speech-to-text conversion
- **Metadata**: Duration, format, and quality information

**E-books:**

- **EPUB**: Chapter extraction and metadata
- **Text Preservation**: Formatting and structure maintained

#### Universal Connector Support

File conversion works across **all data source connectors**:

- **Git Repositories**: Convert files found in repositories
- **Confluence**: Download and convert page attachments
- **JIRA**: Process issue attachments automatically
- **Public Documentation**: Extract and convert linked files
- **Local Files**: Convert files in local directories

#### Conversion Features

**Intelligent Detection:**

- Automatic MIME type detection
- File extension-based fallback
- Content-based format identification

**Performance Optimization:**

- Configurable file size limits (default 50MB)
- Conversion timeouts (default 5 minutes)
- Lazy loading of conversion dependencies
- Memory-efficient processing

**Error Handling:**

- Graceful fallback for unsupported files
- Minimal document creation for failed conversions
- Comprehensive error logging and reporting
- Continuation of processing despite individual failures

**Metadata Preservation:**

- Original file type and name tracking
- Conversion method and timestamp
- File size and format information
- Parent-child relationships for attachments

#### Configuration

**Global Settings:**

```yaml
global:
  file_conversion:
    max_file_size: 52428800  # 50MB
    conversion_timeout: 300  # 5 minutes
    markitdown:
      enable_llm_descriptions: false  # AI image descriptions
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
```

**Per-Connector Settings:**

```yaml
sources:
  git:
    my-repo:
      enable_file_conversion: true  # Enable conversion
  
  confluence:
    my-space:
      enable_file_conversion: true
      download_attachments: true    # Required for attachments
```

#### Advanced Features

**Attachment Processing:**

- Automatic download from Confluence, JIRA, and documentation sites
- Parent-child document relationships
- Attachment metadata preservation
- Secure authentication handling

**AI-Powered Image Processing:**

- Optional LLM integration for image descriptions
- Support for GPT-4 Vision and compatible models
- Configurable AI endpoints and models

**State Management Integration:**

- Conversion metadata tracking in database
- Incremental processing of converted files
- Change detection for file modifications
- Comprehensive metrics and monitoring

See the [File Conversion Guide](./FileConversionGuide.md) for detailed setup and usage instructions.

### Document Processing Pipeline

#### Intelligent Chunking

- **Token-based chunking**: Split documents based on token count
- **Semantic boundaries**: Respect paragraph and section boundaries
- **Configurable overlap**: Maintain context between chunks
- **Size optimization**: Balance chunk size for optimal retrieval
- **Metadata preservation**: Maintain source information in chunks

**Chunking strategies:**

- Fixed-size chunking with overlap
- Semantic chunking based on content structure
- Adaptive chunking based on content type
- Custom chunking rules per source type

#### Content Cleaning and Normalization

- **HTML processing**: Clean and convert HTML to plain text
- **Markdown normalization**: Standardize Markdown formatting
- **Code block handling**: Preserve code formatting and syntax
- **Special character handling**: Normalize Unicode and special characters
- **Whitespace normalization**: Clean up excessive whitespace

#### Metadata Extraction

- **Source metadata**: Track origin, type, and source-specific information
- **Content metadata**: Extract titles, authors, dates, and tags
- **Structural metadata**: Capture document hierarchy and relationships
- **Custom metadata**: Support for source-specific metadata fields

### Vector Embedding System

#### Embedding Model Support

- **OpenAI models**: Support for all OpenAI embedding models
- **Local models**: Integration with local embedding services
- **Custom endpoints**: Support for custom embedding APIs
- **Model switching**: Easy switching between different models
- **Batch processing**: Efficient batch embedding for performance

**Supported models:**

- OpenAI: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`
- Local: `BAAI/bge-small-en-v1.5`, `sentence-transformers` models
- Custom: Any OpenAI-compatible embedding API

#### Performance Optimization

- **Batch processing**: Process multiple documents simultaneously
- **Rate limiting**: Respect API rate limits and quotas
- **Caching**: Cache embeddings to avoid recomputation
- **Retry logic**: Robust error handling and retry mechanisms
- **Progress tracking**: Monitor embedding progress and performance

### State Management System

#### Incremental Processing

- **Change detection**: Detect modified, added, and deleted documents
- **State tracking**: Maintain ingestion state across runs
- **Selective updates**: Only process changed content
- **Rollback capability**: Ability to rollback to previous states
- **Audit trail**: Complete history of ingestion operations

#### Database Management

- **SQLite backend**: Lightweight, file-based state storage
- **Connection pooling**: Efficient database connection management
- **Transaction support**: Atomic operations for data consistency
- **Schema migrations**: Automatic schema updates and migrations
- **Backup and restore**: State database backup and recovery

### Command Line Interface

#### Core Commands

```bash
# Collection management
qdrant-loader init                    # Initialize QDrant collection
qdrant-loader status                  # Show ingestion status
qdrant-loader stats                   # Collection statistics
qdrant-loader validate                # Validate data integrity

# Ingestion operations
qdrant-loader ingest                  # Full ingestion
qdrant-loader ingest --source-type git  # Source-specific ingestion
qdrant-loader ingest --force-full     # Force complete re-ingestion

# Configuration management
qdrant-loader config                  # Show current configuration
qdrant-loader config --validate       # Validate configuration
```

#### Advanced Options

- **Logging control**: Configurable log levels and formats
- **Parallel processing**: Multi-worker ingestion support
- **Dry run mode**: Validate operations without execution
- **Custom configuration**: Support for multiple configuration files
- **Environment integration**: Environment variable substitution

## 🔌 MCP Server Features

### Protocol Implementation

#### MCP 2024-11-05 Compliance

- **Full protocol support**: Complete implementation of MCP specification
- **Tool integration**: Seamless integration with AI development tools
- **Resource management**: Efficient resource allocation and management
- **Error handling**: Robust error handling and recovery
- **Capability negotiation**: Dynamic capability discovery and negotiation

#### Supported MCP Methods

- `initialize`: Server initialization and capability exchange
- `tools/list`: List available search tools
- `tools/call`: Execute search operations
- `resources/list`: List available document resources
- `notifications`: Handle client notifications

### Search Capabilities

#### Semantic Search

- **Vector similarity**: Advanced vector similarity search
- **Query processing**: Intelligent query understanding and expansion
- **Result ranking**: Relevance-based result ordering
- **Similarity thresholds**: Configurable similarity cutoffs
- **Multi-vector search**: Support for multiple embedding models

#### Advanced Search Features

- **Hybrid search**: Combine semantic and keyword search
- **Source filtering**: Filter results by source type or specific sources
- **Metadata filtering**: Filter by document metadata and properties
- **Faceted search**: Group results by various facets
- **Query expansion**: Automatic query term expansion

#### Search Parameters

```json
{
  "query": "natural language query",
  "source_types": ["git", "confluence", "jira"],
  "limit": 10,
  "similarity_threshold": 0.7,
  "filters": {
    "project": "backend",
    "author": "john.doe",
    "created_after": "2024-01-01"
  }
}
```

### Performance Features

#### Caching System

- **Query caching**: Cache frequent search queries
- **Result caching**: Cache search results for performance
- **Embedding caching**: Cache document embeddings
- **TTL management**: Configurable cache expiration
- **Cache invalidation**: Smart cache invalidation on updates

#### Optimization

- **Connection pooling**: Efficient QDrant connection management
- **Batch operations**: Batch multiple operations for efficiency
- **Lazy loading**: Load resources on demand
- **Memory management**: Efficient memory usage and cleanup
- **Response streaming**: Stream large result sets

### Integration Support

#### AI Development Tools

- **Cursor IDE**: Full integration with Cursor's AI assistant
- **Windsurf**: Compatible with Windsurf development environment
- **Claude Desktop**: Direct integration with Claude Desktop
- **Custom tools**: RESTful API for custom integrations

#### API Endpoints

```bash
# Health and status
GET /health                           # Health check
GET /stats                           # Server statistics
GET /sources                         # Available data sources

# Search operations
POST /search                         # Semantic search
GET /documents/{id}                  # Get specific document
GET /collections                     # List collections
```

## 🔧 Configuration System

### Global Configuration

- **Unified settings**: Shared configuration across both packages
- **Environment variables**: Support for environment-based configuration
- **YAML configuration**: Structured configuration files
- **Configuration validation**: Automatic validation and error reporting
- **Hot reloading**: Dynamic configuration updates without restart

### Source-Specific Configuration

- **Per-source settings**: Customizable settings for each data source
- **Inheritance**: Global settings with source-specific overrides
- **Conditional configuration**: Environment-based configuration switching
- **Template support**: Configuration templates and examples

## 🔍 Monitoring and Observability

### Logging System

- **Structured logging**: JSON-formatted logs for analysis
- **Log levels**: Configurable logging levels (DEBUG, INFO, WARN, ERROR)
- **Context preservation**: Maintain context across operations
- **Performance logging**: Track operation timing and performance
- **Error tracking**: Comprehensive error logging and tracking

### Metrics and Analytics

- **Ingestion metrics**: Track documents processed, errors, and timing
- **Search metrics**: Monitor query performance and result quality
- **Resource usage**: Track memory, CPU, and storage usage
- **API metrics**: Monitor API call rates and response times

### Health Monitoring

- **Health checks**: Built-in health check endpoints
- **Status reporting**: Detailed status information
- **Dependency monitoring**: Monitor external service health
- **Alerting integration**: Support for external alerting systems

## 🔐 Security Features

### Authentication and Authorization

- **API key management**: Secure API key handling
- **Token-based auth**: Support for various authentication methods
- **Environment security**: Secure environment variable handling
- **Access control**: Fine-grained access control options

### Data Security

- **Encryption in transit**: TLS/HTTPS for all communications
- **Secure storage**: Encrypted storage options
- **Data sanitization**: Automatic PII and sensitive data handling
- **Audit logging**: Complete audit trail of all operations

## 🚀 Performance Characteristics

### Scalability

- **Horizontal scaling**: Support for distributed processing
- **Vertical scaling**: Efficient resource utilization
- **Load balancing**: Built-in load balancing capabilities
- **Auto-scaling**: Dynamic resource allocation

### Performance Metrics

- **Ingestion speed**: >1000 documents per minute
- **Search latency**: <200ms average response time
- **Memory efficiency**: <10MB per 1000 documents
- **Concurrent users**: Support for multiple simultaneous users

## 🔄 Integration Ecosystem

### Development Workflow Integration

- **CI/CD pipelines**: Integration with continuous integration
- **Git hooks**: Pre-commit and post-commit hook support
- **Automated ingestion**: Scheduled and event-driven ingestion
- **Deployment automation**: Automated deployment and configuration

### Third-Party Integrations

- **Monitoring tools**: Integration with Prometheus, Grafana
- **Alerting systems**: Support for PagerDuty, Slack notifications
- **Analytics platforms**: Export data to analytics platforms
- **Backup systems**: Integration with backup and archival systems

## 🛠️ Extensibility

### Plugin Architecture

- **Custom connectors**: Framework for building custom data source connectors
- **Processing plugins**: Custom document processing pipelines
- **Search plugins**: Custom search algorithms and ranking
- **Integration plugins**: Custom integrations with external tools

### API Extensibility

- **RESTful APIs**: Comprehensive REST API for all operations
- **Webhook support**: Event-driven integrations via webhooks
- **GraphQL support**: Planned GraphQL API for flexible queries
- **SDK support**: Client SDKs for various programming languages

## 📊 Analytics and Insights

### Usage Analytics

- **Search analytics**: Track search patterns and popular queries
- **Content analytics**: Analyze content usage and popularity
- **User behavior**: Track user interaction patterns
- **Performance analytics**: Monitor system performance trends

### Reporting

- **Dashboard support**: Built-in dashboard for monitoring
- **Custom reports**: Configurable reporting system
- **Export capabilities**: Export data in various formats
- **Scheduled reports**: Automated report generation and delivery

## 🔮 Future Roadmap

### Planned Features

- **Advanced AI features**: Query understanding, intent recognition
- **Multi-modal support**: Support for images, videos, and audio
- **Real-time sync**: Real-time synchronization with data sources
- **Advanced analytics**: Machine learning-powered insights
- **Enterprise features**: SSO, advanced security, compliance tools

### Community Features

- **Plugin marketplace**: Community-driven plugin ecosystem
- **Template library**: Shared configuration templates
- **Best practices**: Community-driven best practices and guides
- **Integration examples**: Real-world integration examples and tutorials
