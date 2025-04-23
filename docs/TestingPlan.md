# QDrant Loader Testing Plan

## Overview

This document outlines the detailed plan for implementing comprehensive testing across the QDrant Loader project. It serves as a living document to track progress and priorities in our testing implementation.

## Testing Philosophy and Strategy

### Directory Structure

Following our established testing strategy, tests are organized as:

```text
tests/
├── fixtures/                    # Test data and fixtures
│   ├── unit/                   # Unit test fixtures
│   └── integration/            # Integration test fixtures
├── unit/                       # Unit tests
│   ├── core/                  # Core functionality tests
│   │   ├── config/           # Configuration tests
│   │   ├── embedding/        # Embedding service tests
│   │   └── state/           # State management tests
│   ├── connectors/              # Source-specific tests
│   │   ├── publicdocs/      # Public docs source tests
│   │   ├── git/            # Git source tests
│   │   ├── confluence/     # Confluence source tests
│   │   └── jira/          # Jira source tests
│   └── utils/              # Utility function tests
└── integration/            # Integration tests
    ├── core/              # Core integration tests
    ├── connectors/          # Source integration tests
    │   ├── publicdocs/  # Public docs integration
    │   ├── git/        # Git integration
    │   ├── confluence/ # Confluence integration
    │   └── jira/      # Jira integration
    └── end_to_end/    # End-to-end workflow tests
```

### Test Types and Distribution

Our testing approach consists of:

1. **Unit Tests** (80% of test effort)
   - Isolated component testing
   - Mock external dependencies
   - Focus on business logic
   - Quick execution time
   - Examples:
     - Configuration parsing
     - State management logic
     - Utility functions
     - Individual component behavior

2. **Integration Tests** (20% of test effort)
   - End-to-end workflows
   - Real service interactions
   - Minimal mocking
   - Complete feature testing
   - Examples:
     - Document ingestion workflow
     - Source synchronization
     - Search functionality

### Infrastructure Requirements

- Python 3.13.2
- pytest with pytest-cov
- Coverage threshold: 80% minimum
- Environment configuration:
  - `.env.test` for test environment variables
  - `config.test.yaml` for test configuration

## Current Test Coverage Status

### Existing Tests and Their Locations

- ✅ `test_release.py` → Moved to `tests/unit/utils/`
- ✅ `test_document_id.py` → Moved to `tests/unit/core/`
- ✅ `test_embedding_service.py` → Located in `tests/unit/core/embedding/`
- ✅ `test_state_manager.py` → Located in `tests/unit/core/state/`
- ✅ `test_config_loader.py` → Located in `tests/unit/core/config/`
- ✅ `test_base_connector.py` → Located in `tests/unit/connectors/`

### Directory Structure Status

- ✅ Basic directory structure created
- ✅ All `__init__.py` files added
- ✅ Test files organized in appropriate directories
- ✅ Fixtures directories prepared
- ✅ Moved source-specific tests to `connectors/` directory

### Overall Statistics

- Current Coverage: 61% (as of latest test run)
- Target Coverage: 80% minimum
- Configuration Module Coverage:
  - `config/__init__.py`: 88% coverage
  - `config/base.py`: 88% coverage
  - `config/chunking.py`: 90% coverage
  - `config/embedding.py`: 100% coverage
  - `config/global_config.py`: 95% coverage
  - `config/source_config.py`: 100% coverage
  - `config/sources.py`: 89% coverage
  - `config/types.py`: 100% coverage
- Connectors Module Coverage:
  - `connectors/jira/connector.py`: 89% coverage
  - `connectors/jira/models.py`: 100% coverage
  - `connectors/jira/config.py`: 84% coverage
  - `connectors/confluence/connector.py`: 83% coverage
  - `connectors/git/adapter.py`: 93% coverage

## Testing Priorities and Progress

### 1. Core Components (Priority: High)

#### Configuration (`tests/unit/core/config/`) ✅

- ✅ `test_config_loader.py`
  - ✅ Basic configuration initialization
  - ✅ Missing required fields validation
  - ✅ Environment variable substitution
  - ✅ Invalid YAML handling
  - ✅ Source-specific configuration validation
  - ✅ Configuration to dictionary conversion

#### State Management (`tests/unit/core/state/`)

- ✅ `test_state_manager.py`
  - ✅ State initialization (Unit)
  - ✅ State persistence (Integration)
  - ✅ State recovery (Integration)
  - ✅ Error handling (Both)
  - ✅ Read-only database handling
  - ✅ Context manager support
  - ✅ Document state tracking
  - ✅ Ingestion history management

#### Embedding Service (`tests/unit/core/embedding/`)

- ✅ `test_embedding_service.py`
  - ✅ Service initialization (Unit)
  - ✅ Text embedding (Unit)
  - ✅ Batch processing (Integration)
  - ✅ Error handling (Both)
  - ✅ Rate limiting (Unit)
  - ✅ Token counting (Unit)
  - ✅ Local service support (Unit)
  - ✅ OpenAI integration (Unit)

### 2. Source Connectors (Priority: High) 🔄

#### Base Classes (`tests/unit/connectors/`)

- ✅ `test_base_connector.py`
  - ✅ Interface implementation (Unit)
  - ✅ Common functionality (Unit)
  - ✅ Error handling (Unit)
  - ✅ Event handling (Integration)

#### Source-Specific Implementation (`tests/unit/connectors/`)

- ✅ Git Source (`git/`)
  - ✅ Repository cloning (Integration)
    - ✅ Successful cloning
    - ✅ Retry logic
    - ✅ Error handling
  - ✅ Change detection (Unit)
    - ✅ File listing
    - ✅ Last commit date tracking
  - ✅ Content extraction (Unit)
    - ✅ File content retrieval
    - ✅ Error handling
  - ✅ File processing (Unit)
    - ✅ File type filtering
    - ✅ Path inclusion/exclusion
    - ✅ Size limits
  - ✅ Metadata extraction (Unit)
    - ✅ File metadata
    - ✅ Repository metadata
    - ✅ Git-specific metadata
    - ✅ Encoding detection
    - ✅ Markdown features

- ✅ Confluence Source (`confluence/`)
  - ✅ Authentication (Unit)
    - ✅ Environment variable validation
    - ✅ Token and email validation
  - ✅ API Integration (Unit)
    - ✅ URL construction
    - ✅ Request handling
    - ✅ Error handling
  - ✅ Content Processing (Unit)
    - ✅ Space content retrieval
    - ✅ Label-based filtering
    - ✅ HTML cleaning
    - ✅ Document creation
  - ✅ Change tracking (Unit)
    - ✅ Version comparison
    - ✅ Missing version handling
    - ✅ Invalid version handling
  - ✅ Pagination handling (Unit)
    - ✅ Multiple pages
    - ✅ Invalid cursor handling
    - ✅ Missing next link handling
  - ✅ Error scenarios (Both)
    - ✅ Network error handling
    - ✅ Invalid response format
    - ✅ Missing required fields
    - ✅ Malformed content
    - ✅ Content processing errors

- ✅ Jira Source (`jira/`)
  - ✅ Authentication (Unit)
    - ✅ Environment variable validation
    - ✅ Token validation
    - ✅ Email validation
  - ✅ API Integration (Unit)
    - ✅ URL construction
    - ✅ JQL query formatting
    - ✅ Request handling
    - ✅ Error handling
  - ✅ Content Processing (Unit)
    - ✅ Issue data parsing
    - ✅ Field mapping
    - ✅ Document creation
    - ✅ Metadata extraction
  - ✅ Rate limiting (Unit)
    - ✅ Request throttling
  - ✅ Error scenarios (Unit)
    - ✅ Network error handling
    - ✅ Invalid response format
    - ✅ Missing required fields

- [ ] Public Docs Source (`publicdocs/`)
  - [ ] Document fetching (Integration)
  - [ ] Content parsing (Unit)
  - [ ] Update detection (Unit)
  - [ ] Error handling (Both)

### 3. Integration Tests (Priority: Medium)

#### Core Integration (`tests/integration/core/`)

- [ ] Complete ingestion pipeline
- [ ] State management persistence
- [ ] Configuration loading
- [ ] Embedding service integration

#### Source Integration (`tests/integration/connectors/`)

- [ ] Git repository synchronization
- [ ] Confluence space indexing
- [ ] Jira project synchronization
- [ ] Public docs crawling

## Progress Tracking

### Phase 1 (Current)

- [x] Set up test infrastructure
  - [x] Create directory structure
  - [x] Add `__init__.py` files
  - [x] Organize existing tests
  - [x] Configure pytest
  - [x] Set up coverage reporting
  - [x] Configure test environment
- [x] Implement core unit tests
  - [x] Embedding Service
  - [x] State Management
  - [x] Configuration Loader
  - [x] Base Connector
- [x] Implement source connector tests
  - [x] Git connector tests
  - [x] Confluence connector tests
  - [x] Jira connector tests
- [✅] Achieve 50% coverage (Current: 61%)

Next steps:

1. Implement Public Docs connector tests
2. Work towards 65% overall coverage

### Phase 2

- [ ] Complete remaining source connector tests
- [ ] Add integration tests
- [ ] Reach 65% coverage

### Phase 3

- [ ] Complete end-to-end tests
- [ ] Add remaining unit tests
- [ ] Achieve 80% coverage

## CI/CD Integration

- GitHub Actions pipeline
- Python 3.13.2 environment
- Coverage report generation
- Automatic report upload to:
  - GitHub Pages
  - Codacy

## Definition of Done

A component is considered fully tested when:

- Unit tests cover all functionality
- Integration tests verify workflows
- Edge cases are tested
- Coverage meets 80% threshold
- Tests are documented
- CI/CD passes all tests
