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

### Directory Structure Status

- ✅ Basic directory structure created
- ✅ All `__init__.py` files added
- ✅ Test files organized in appropriate directories
- ✅ Fixtures directories prepared

### Overall Statistics

- Current Coverage: 28% (as of latest test run)
- Target Coverage: 80% minimum
- Embedding Service Coverage: 87%

## Testing Priorities and Progress

### 1. Core Components (Priority: High)

#### State Management (`tests/unit/core/state/`)

- [ ] `test_state_manager.py`
  - [ ] State initialization (Unit)
  - [ ] State persistence (Integration)
  - [ ] State recovery (Integration)
  - [ ] Error handling (Both)

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

#### Configuration (`tests/unit/core/config/`)

- [ ] `test_config_loader.py`
  - [ ] YAML parsing (Unit)
  - [ ] Environment variables (Unit)
  - [ ] Validation (Unit)
  - [ ] Integration tests (Integration)

### 2. Source Connectors (Priority: High)

#### Base Classes (`tests/unit/sources/`)

- [ ] `test_base_connector.py`
  - [ ] Interface implementation (Unit)
  - [ ] Common functionality (Unit)
  - [ ] Error handling (Unit)
  - [ ] Event handling (Integration)

#### Source-Specific Implementation (`tests/unit/sources/`)

- [ ] Git Source (`git/`)
  - [ ] Repository cloning (Integration)
  - [ ] Change detection (Unit)
  - [ ] Content extraction (Unit)
  - [ ] Error scenarios (Both)

- [ ] Confluence Source (`confluence/`)
  - [ ] Authentication (Integration)
  - [ ] Page retrieval (Integration)
  - [ ] Change tracking (Unit)
  - [ ] Error handling (Both)

- [ ] Jira Source (`jira/`)
  - [ ] Issue retrieval (Integration)
  - [ ] Field mapping (Unit)
  - [ ] Update detection (Unit)
  - [ ] Error scenarios (Both)

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

#### Source Integration (`tests/integration/sources/`)

- [ ] Git repository synchronization
- [ ] Confluence space indexing
- [ ] Jira project synchronization
- [ ] Public docs crawling

#### End-to-End (`tests/integration/end_to_end/`)

- [ ] Complete document ingestion workflow
- [ ] Multi-source synchronization
- [ ] Search functionality
- [ ] Update detection and processing

## Implementation Guidelines

### Test Structure

```python
def test_feature_success():
    """Test successful execution of feature."""
    pass

def test_feature_edge_cases():
    """Test edge cases and boundary conditions."""
    pass

def test_feature_error_handling():
    """Test error scenarios and recovery."""
    pass
```

### Best Practices

1. **Test Isolation**
   - Independent test execution
   - Clean resource cleanup
   - Appropriate fixture scoping

2. **Test Data Management**
   - Use fixture directory structure
   - Maintain meaningful test data
   - Keep test data current

3. **Mocking Strategy**
   - Mock external services in unit tests
   - Use real services in integration tests
   - Document mock behaviors

4. **Error Handling**
   - Test success and failure cases
   - Verify error messages
   - Cover edge cases

## Progress Tracking

### Phase 1 (Current)

- [x] Set up test infrastructure
  - [x] Create directory structure
  - [x] Add `__init__.py` files
  - [x] Organize existing tests
  - [x] Configure pytest
  - [x] Set up coverage reporting
  - [x] Configure test environment
- [x] Implement core unit tests (Embedding Service)
- [ ] Achieve 50% coverage

Next steps:

1. Implement remaining core component tests
2. Start source connector tests
3. Work towards 50% overall coverage

### Phase 2

- [ ] Implement source connector tests
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
