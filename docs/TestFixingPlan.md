# 🧪 QDrant Loader Test Fixing Plan

## 📊 Current Status Summary

**Current Coverage**: 48% (2,949 missed lines out of 5,674 total)
**Target Coverage**: 80% minimum
**Gap to Close**: 32 percentage points
**Tests Status**: 184 tests (153 passed, 17 failed, 14 errors)

### ✅ Issues Resolved (Phase 1)

1. ✅ **Import Errors**: All 11 test files now working - 0 import errors
2. ✅ **Pytest Configuration**: Test discovery and async support fixed
3. ✅ **Test Collection**: 193 tests now discoverable (98 additional tests)

### 🚨 Remaining Critical Issues

1. **Missing Test Infrastructure**: Test environment files and fixtures needed
2. **Low Test Coverage**: Core components need comprehensive test coverage
3. **Connector Testing**: Connector tests need enhancement and mocking

---

## 🎯 Phase 1: Fix Critical Import Issues (Priority: URGENT) ✅ COMPLETED

### Issue 1.1: Connector Test Import Failures

**Status**: ✅ RESOLVED - All connector tests now discoverable and runnable
**Files Affected**: 10 test files
**Root Cause**: `__init__.py` files in test directories caused pytest to treat them as packages

#### Action Items

- [x] **Fix Confluence Connector Tests** ✅
  - File: `tests/unit/connectors/confluence/test_confluence_connector.py`
  - Issue: `ModuleNotFoundError: No module named 'connectors.confluence.test_confluence_connector'`
  - Fix: Removed `tests/unit/connectors/confluence/__init__.py`

- [x] **Fix Git Connector Tests** (4 files) ✅
  - Files:
    - `tests/unit/connectors/git/test_adapter.py`
    - `tests/unit/connectors/git/test_file_processor.py`
    - `tests/unit/connectors/git/test_git_connector.py`
    - `tests/unit/connectors/git/test_metadata_extractor.py`
  - Issue: Same import path issues
  - Fix: Removed `tests/unit/connectors/git/__init__.py`

- [x] **Fix Jira Connector Tests** ✅
  - File: `tests/unit/connectors/jira/test_jira_connector.py`
  - Issue: Import path issues
  - Fix: Removed `tests/unit/connectors/jira/__init__.py`

- [x] **Fix Public Docs Connector Tests** (3 files) ✅
  - Files:
    - `tests/unit/connectors/publicdocs/test_publicdocs_connector.py`
    - `tests/unit/connectors/publicdocs/test_publicdocs_content_extraction.py`
    - `tests/unit/connectors/publicdocs/test_publicdocs_title_extraction.py`
  - Issue: Import path issues
  - Fix: Removed `tests/unit/connectors/publicdocs/__init__.py`

- [x] **Fix Base Connector Tests** ✅
  - File: `tests/unit/connectors/test_base_connector.py`
  - Issue: Import path issues
  - Fix: Removed `tests/unit/connectors/__init__.py`

### Issue 1.2: Release Test Import Failure

**Status**: ✅ RESOLVED - Release tests now working
**File**: `tests/unit/utils/test_release.py`
**Issue**: `ModuleNotFoundError: No module named 'release'`
**Fix**: Updated sys.path to correctly reference root directory

#### Action Items

- [x] **Fix Release Test Import** ✅
  - Updated import path from `"../../.."` to `"../../../../../"`
  - Release module now accessible from test context

### Issue 1.3: Pytest Configuration Issues

**Status**: ✅ RESOLVED - Test discovery and async support fixed
**Root Cause**: Missing pytest configuration and async fixture scope

#### Action Items

- [x] **Fix Pytest Configuration** ✅
  - Added `asyncio_default_fixture_loop_scope = "function"` to `pyproject.toml`
  - Created dedicated `pytest.ini` for qdrant-loader package
  - Configured proper test discovery patterns

### 📊 Phase 1 Results

- **Before**: 95 tests collected with 11 import errors, ~20% coverage
- **After**: 184 tests collected with 0 import errors, 48% coverage
- **Improvement**: +89 additional tests now discoverable and runnable
- **Test Results**: 153 passed, 17 failed, 14 errors
- **Status**: ✅ ALL IMPORT ISSUES RESOLVED

### 🔍 Current Test Issues (Post Phase 1)

1. **Document Model Issues** (11 failures): Missing required fields (`url`, `content_type`)
2. **HTML Strategy Errors** (10 errors): Missing `SemanticAnalyzer` import
3. **State Manager Errors** (4 errors): Document validation issues
4. **Release Test Failures** (4 failures): Test assertion mismatches
5. **Performance Issues** (1 timeout): Local file connector hanging

---

## 🎯 Phase 2: Fix Critical Test Failures (Priority: URGENT)

### Issue 2.1: Document Model Validation Failures

**Status**: 🔴 Critical - 11 test failures
**Root Cause**: Missing required fields in Document model (`url`, `content_type`)
**Impact**: Blocking markdown strategy, embedding service, and state manager tests

#### Action Items

- [ ] **Fix Document Model Test Fixtures** (Priority: URGENT)
  - Update all Document creation in tests to include required fields
  - Files affected:
    - `tests/unit/core/chunking/strategy/test_markdown_strategy.py` (6 failures)
    - `tests/unit/core/embedding/test_embedding_service.py` (1 failure)
    - `tests/unit/core/state/test_state_manager.py` (4 failures)
  - **Estimated Effort**: 0.5 days

### Issue 2.2: HTML Strategy Import Errors

**Status**: 🔴 Critical - 10 test errors
**Root Cause**: Missing `SemanticAnalyzer` import in HTML strategy tests
**Impact**: All HTML strategy tests failing

#### Action Items

- [ ] **Fix HTML Strategy Test Imports** (Priority: URGENT)
  - Update import path for `SemanticAnalyzer` in test file
  - File: `tests/unit/core/chunking/strategy/test_html_strategy.py`
  - **Estimated Effort**: 0.25 days

### Issue 2.3: Release Test Assertion Mismatches

**Status**: 🟡 Medium - 4 test failures
**Root Cause**: Test assertions don't match actual function behavior
**Impact**: Release utility tests failing

#### Action Items

- [ ] **Fix Release Test Assertions** (Priority: MEDIUM)
  - Update test assertions to match actual log messages
  - File: `tests/unit/utils/test_release.py`
  - **Estimated Effort**: 0.25 days

### Issue 2.4: Performance and Timeout Issues

**Status**: 🟡 Medium - 1 timeout
**Root Cause**: Local file connector scanning large directories
**Impact**: One test timing out after 30 seconds

#### Action Items

- [ ] **Fix Local File Connector Performance** (Priority: MEDIUM)
  - Add directory size limits for tests
  - Improve file scanning efficiency
  - File: `tests/unit/connectors/localfile/test_localfile_id_consistency.py`
  - **Estimated Effort**: 0.5 days

### Issue 2.5: Test Infrastructure Setup

**Status**: 🟡 Partially configured → ✅ Pytest config completed
**Current**: Pytest configuration completed, test environment setup needed
**Needed**: Test environment files and fixtures

#### Action Items

- [x] **Fix Pytest Configuration** ✅
  - Added `asyncio_default_fixture_loop_scope = "function"` to `pyproject.toml`
  - Created dedicated `pytest.ini` for qdrant-loader package
  - Configured proper test discovery patterns and coverage

- [ ] **Create Test Environment Files**
  - Ensure `.env.test` exists with proper test variables
  - Ensure `config.test.yaml` exists with test configuration
  - Document required environment variables

- [ ] **Set Up Test Fixtures**
  - Create common fixtures for database setup
  - Create mock fixtures for external services
  - Set up test data fixtures

---

## 🎯 Phase 3: Core Component Test Coverage (Priority: HIGH)

### Issue 3.1: Core Module Coverage Analysis

**Current Coverage by Module**:

| Module | Current Coverage | Target | Gap | Priority |
|--------|------------------|--------|-----|----------|
| `core/async_ingestion_pipeline.py` | 0% | 80% | 80% | 🔴 Critical |
| `core/embedding/embedding_service.py` | 16% | 80% | 64% | 🔴 Critical |
| `core/state/state_manager.py` | 13% | 80% | 67% | 🔴 Critical |
| `core/chunking/chunking_service.py` | 23% | 80% | 57% | 🟡 High |
| `core/document.py` | 31% | 80% | 49% | 🟡 High |

#### Action Items

- [ ] **Async Ingestion Pipeline Tests** (0% → 80%)
  - **File**: `tests/unit/core/test_async_ingestion_pipeline.py` (CREATE)
  - **Coverage Target**: 650 lines to test
  - **Test Areas**:
    - Pipeline initialization and configuration
    - Document processing workflow
    - Batch processing logic
    - Error handling and recovery
    - State management integration
    - Performance monitoring
  - **Estimated Effort**: 3-4 days

- [ ] **Enhanced Embedding Service Tests** (16% → 80%)
  - **File**: `tests/unit/core/embedding/test_embedding_service.py` (ENHANCE)
  - **Coverage Target**: 93 additional lines
  - **Test Areas**:
    - OpenAI API integration
    - Local model support
    - Batch processing optimization
    - Rate limiting and retry logic
    - Error handling scenarios
  - **Estimated Effort**: 1-2 days

- [ ] **Enhanced State Manager Tests** (13% → 80%)
  - **File**: `tests/unit/core/state/test_state_manager.py` (ENHANCE)
  - **Coverage Target**: 169 additional lines
  - **Test Areas**:
    - Database operations (CRUD)
    - Transaction management
    - Concurrent access handling
    - Migration and schema updates
    - Error recovery scenarios
  - **Estimated Effort**: 2-3 days

- [ ] **Enhanced Chunking Service Tests** (23% → 80%)
  - **File**: `tests/unit/core/chunking/test_chunking_service.py` (CREATE)
  - **Coverage Target**: 41 additional lines
  - **Test Areas**:
    - Strategy selection logic
    - Chunk size optimization
    - Overlap handling
    - Metadata preservation
  - **Estimated Effort**: 1 day

- [ ] **Enhanced Document Tests** (31% → 80%)
  - **File**: `tests/unit/core/test_document.py` (ENHANCE)
  - **Coverage Target**: 68 additional lines
  - **Test Areas**:
    - Document creation and validation
    - Metadata handling
    - Serialization/deserialization
    - Document comparison logic
  - **Estimated Effort**: 1 day

### Issue 3.2: Chunking Strategy Tests

**Current Coverage**: 13-20% across all strategies
**Target**: 80% for each strategy

#### Action Items

- [ ] **Markdown Strategy Tests** (16% → 80%)
  - **File**: `tests/core/chunking/strategy/test_markdown_strategy.py` (EXISTS - ENHANCE)
  - **Coverage Target**: 252 additional lines
  - **Test Areas**: Header detection, code block handling, list processing

- [ ] **Code Strategy Tests** (20% → 80%)
  - **File**: `tests/unit/core/chunking/strategy/test_code_strategy.py` (EXISTS - ENHANCE)
  - **Coverage Target**: 292 additional lines
  - **Test Areas**: Language detection, function extraction, comment handling

- [ ] **HTML Strategy Tests** (16% → 80%)
  - **File**: `tests/unit/core/chunking/strategy/test_html_strategy.py` (EXISTS - ENHANCE)
  - **Coverage Target**: 308 additional lines
  - **Test Areas**: Tag parsing, content extraction, structure preservation

- [ ] **JSON Strategy Tests** (16% → 80%)
  - **File**: `tests/unit/core/chunking/strategy/test_json_strategy.py` (EXISTS - ENHANCE)
  - **Coverage Target**: 257 additional lines
  - **Test Areas**: Schema detection, nested object handling, array processing

---

## 🎯 Phase 4: Connector Test Implementation (Priority: HIGH)

### Issue 4.1: Connector Coverage Analysis

**Current Coverage by Connector**:

| Connector | Current Coverage | Target | Gap | Priority |
|-----------|------------------|--------|-----|----------|
| `confluence/connector.py` | 13% | 80% | 67% | 🔴 Critical |
| `git/connector.py` | 16% | 80% | 64% | 🔴 Critical |
| `jira/connector.py` | 23% | 80% | 57% | 🔴 Critical |
| `publicdocs/connector.py` | 12% | 80% | 68% | 🔴 Critical |
| `localfile/connector.py` | 30% | 80% | 50% | 🟡 High |

#### Action Items

- [ ] **Fix and Enhance Confluence Connector Tests** (13% → 80%)
  - **Files**:
    - `tests/unit/connectors/confluence/test_confluence_connector.py` (FIX + ENHANCE)
  - **Coverage Target**: 146 additional lines
  - **Test Areas**:
    - Authentication and API setup
    - Space content retrieval
    - Page processing and HTML cleaning
    - Comment extraction
    - Label-based filtering
    - Pagination handling
    - Error scenarios and retry logic
  - **Estimated Effort**: 2-3 days

- [ ] **Fix and Enhance Git Connector Tests** (16% → 80%)
  - **Files**:
    - `tests/unit/connectors/git/test_git_connector.py` (FIX + ENHANCE)
    - `tests/unit/connectors/git/test_adapter.py` (FIX + ENHANCE)
    - `tests/unit/connectors/git/test_file_processor.py` (FIX + ENHANCE)
    - `tests/unit/connectors/git/test_metadata_extractor.py` (FIX + ENHANCE)
  - **Coverage Target**: 442 additional lines across all files
  - **Test Areas**:
    - Repository cloning and authentication
    - Branch selection and file filtering
    - Content extraction and processing
    - Metadata extraction (commits, authors, dates)
    - Change detection logic
    - File type handling
  - **Estimated Effort**: 3-4 days

- [ ] **Fix and Enhance Jira Connector Tests** (23% → 80%)
  - **Files**:
    - `tests/unit/connectors/jira/test_jira_connector.py` (FIX + ENHANCE)
  - **Coverage Target**: 84 additional lines
  - **Test Areas**:
    - Authentication and API setup
    - JQL query construction
    - Issue retrieval and processing
    - Comment and attachment handling
    - Status and type filtering
    - Rate limiting
  - **Estimated Effort**: 2 days

- [ ] **Fix and Enhance Public Docs Connector Tests** (12% → 80%)
  - **Files**:
    - `tests/unit/connectors/publicdocs/test_publicdocs_connector.py` (FIX + ENHANCE)
    - `tests/unit/connectors/publicdocs/test_publicdocs_content_extraction.py` (FIX + ENHANCE)
    - `tests/unit/connectors/publicdocs/test_publicdocs_title_extraction.py` (FIX + ENHANCE)
  - **Coverage Target**: 214 additional lines
  - **Test Areas**:
    - URL fetching and content retrieval
    - CSS selector-based extraction
    - Content cleaning and normalization
    - Title extraction logic
    - Version detection
    - Error handling for network issues
  - **Estimated Effort**: 2-3 days

- [ ] **Enhance Local File Connector Tests** (30% → 80%)
  - **Files**:
    - `tests/unit/connectors/localfile/test_localfile_id_consistency.py` (EXISTS - ENHANCE)
    - `tests/unit/connectors/localfile/test_localfile_connector.py` (CREATE)
    - `tests/unit/connectors/localfile/test_localfile_file_processor.py` (CREATE)
    - `tests/unit/connectors/localfile/test_localfile_metadata_extractor.py` (CREATE)
  - **Coverage Target**: 134 additional lines across all files
  - **Test Areas**:
    - Directory scanning and file discovery
    - Pattern matching and filtering
    - Metadata extraction
    - File content processing
    - Change detection
  - **Estimated Effort**: 1-2 days

---

## 🎯 Phase 5: CLI and Integration Tests (Priority: MEDIUM)

### Issue 5.1: CLI Module Coverage

**Current Coverage**: 0% across all CLI modules
**Target**: 60% (CLI modules typically have lower coverage due to user interaction)

#### Action Items

- [ ] **CLI Core Tests** (0% → 60%)
  - **File**: `tests/unit/cli/test_cli.py` (CREATE)
  - **Coverage Target**: 116 lines out of 193
  - **Test Areas**:
    - Command parsing and validation
    - Configuration loading
    - Error handling and user feedback
    - Integration with core components
  - **Estimated Effort**: 2 days

- [ ] **CLI Asyncio Tests** (0% → 60%)
  - **File**: `tests/unit/cli/test_asyncio.py` (CREATE)
  - **Coverage Target**: 13 lines out of 22
  - **Test Areas**:
    - Async context management
    - Event loop handling
  - **Estimated Effort**: 0.5 days

### Issue 5.2: Integration Test Implementation

**Current Status**: Minimal integration tests exist
**Target**: Comprehensive end-to-end testing

#### Action Items

- [ ] **End-to-End Workflow Tests**
  - **File**: `tests/integration/end_to_end/test_full_ingestion.py` (CREATE)
  - **Test Areas**:
    - Complete ingestion pipeline
    - Multi-source ingestion
    - State persistence across runs
    - Error recovery scenarios
  - **Estimated Effort**: 2-3 days

- [ ] **Connector Integration Tests**
  - **Files**: Create integration tests for each connector
  - **Test Areas**:
    - Real API interactions (with test data)
    - Database persistence
    - Performance under load
  - **Estimated Effort**: 3-4 days

---

## 🎯 Phase 6: Monitoring and Utilities (Priority: LOW)

### Issue 6.1: Monitoring Module Coverage

**Current Coverage**: 0-43% across monitoring modules
**Target**: 70% (monitoring modules often have external dependencies)

#### Action Items

- [ ] **Prometheus Metrics Tests** (0% → 70%)
  - **File**: `tests/unit/core/monitoring/test_prometheus_metrics.py` (CREATE)
  - **Coverage Target**: 22 lines out of 31
  - **Estimated Effort**: 1 day

- [ ] **Resource Monitor Tests** (0% → 70%)
  - **File**: `tests/unit/core/monitoring/test_resource_monitor.py` (CREATE)
  - **Coverage Target**: 19 lines out of 27
  - **Estimated Effort**: 1 day

- [ ] **Enhanced Monitoring Tests**
  - Enhance existing monitoring tests to reach 70% coverage
  - **Estimated Effort**: 1-2 days

### Issue 6.2: Search Module Coverage

**Current Coverage**: 12-20% across search modules
**Target**: 80%

#### Action Items

- [ ] **FAISS Search Tests** (12% → 80%)
  - **File**: `tests/core/search/test_faiss_search.py` (EXISTS - ENHANCE)
  - **Coverage Target**: 106 additional lines
  - **Estimated Effort**: 1-2 days

- [ ] **Hybrid Search Tests** (20% → 80%)
  - **File**: `tests/core/search/test_hybrid_search.py` (EXISTS - ENHANCE)
  - **Coverage Target**: 110 additional lines
  - **Estimated Effort**: 1-2 days

---

## 📅 Implementation Timeline

### ✅ Week 1: Critical Fixes (Phase 1) - COMPLETED

- ✅ **Days 1-2**: Fix all import errors in connector tests
- ✅ **Days 3-4**: Fix release test imports and basic infrastructure  
- ✅ **Day 5**: Verify all tests can run without import errors

**Results**: 193 tests now discoverable (up from 95), 0 import errors

### Week 2: Critical Test Fixes (Phase 2) - IN PROGRESS

- **Days 1-2**: Fix Document model validation failures (11 tests)
- **Day 3**: Fix HTML strategy import errors (10 tests)  
- **Day 4**: Fix release test assertions and performance issues (5 tests)
- **Day 5**: Set up remaining test infrastructure and fixtures

**Target**: Get to 170+ passing tests with 55%+ coverage

### Week 3-4: Core Component Tests (Phase 3)

- **Week 3**: Focus on async ingestion pipeline and state manager
- **Week 4**: Focus on embedding service and chunking strategies

### Week 5-6: Connector Tests (Phase 4)

- **Week 5**: Git and Confluence connectors
- **Week 6**: Jira, Public Docs, and Local File connectors

### Week 7: CLI and Integration (Phase 5)

- **Days 1-3**: CLI module tests
- **Days 4-5**: Integration tests

### Week 8: Final Push (Phase 6)

- **Days 1-3**: Monitoring and search modules
- **Days 4-5**: Final coverage optimization and cleanup

---

## 🎯 Success Metrics

### Coverage Targets by Phase

- **Phase 1 Complete**: All tests run without import errors
- **Phase 2 Complete**: 30% overall coverage
- **Phase 3 Complete**: 50% overall coverage
- **Phase 4 Complete**: 70% overall coverage
- **Phase 5 Complete**: 75% overall coverage
- **Phase 6 Complete**: 80% overall coverage

### Quality Gates

- [ ] All tests pass without import errors
- [ ] No test skips due to missing dependencies
- [ ] Coverage reports generate successfully
- [ ] CI/CD pipeline runs all tests
- [ ] Documentation updated with test instructions

---

## 🛠️ Tools and Commands

### Running Tests

```bash
# Run all tests with coverage
PYTHONPATH=src python -m pytest tests/ --cov=src/qdrant_loader --cov-report=html --cov-report=term-missing

# Run specific test categories
PYTHONPATH=src python -m pytest tests/unit/ --cov=src/qdrant_loader
PYTHONPATH=src python -m pytest tests/integration/ --cov=src/qdrant_loader

# Run tests for specific modules
PYTHONPATH=src python -m pytest tests/unit/core/ --cov=src/qdrant_loader/core
PYTHONPATH=src python -m pytest tests/unit/connectors/ --cov=src/qdrant_loader/connectors
```

### Coverage Analysis

```bash
# Generate detailed coverage report
PYTHONPATH=src python -m pytest tests/ --cov=src/qdrant_loader --cov-report=html --cov-branch

# View coverage in browser
open htmlcov/index.html

# Generate coverage badge
coverage-badge -o coverage.svg
```

### Test Development

```bash
# Run tests in watch mode during development
PYTHONPATH=src python -m pytest tests/unit/core/ --cov=src/qdrant_loader/core -f

# Run with verbose output for debugging
PYTHONPATH=src python -m pytest tests/ -v --tb=long
```

---

## 📚 Resources and References

### Testing Guidelines

- [Testing Strategy](./TestingStrategy.md)
- [Coding Standards](./CodingStandards.md)
- [Contributing Guide](./CONTRIBUTING.md)

### External Documentation

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

---

## 🤝 Team Coordination

### Responsibilities

- **Phase 1-2**: Infrastructure and critical fixes (1 developer)
- **Phase 3**: Core component tests (1-2 developers)
- **Phase 4**: Connector tests (2 developers, can work in parallel)
- **Phase 5-6**: Integration and final cleanup (1 developer)

### Communication

- Daily standup to track progress
- Weekly review of coverage metrics
- Blockers escalated immediately
- Code reviews for all test implementations

---

**Total Estimated Effort**: 6-8 weeks with 1-2 developers
**Priority**: High - Required for production readiness
**Success Criteria**: 80% test coverage with all tests passing
