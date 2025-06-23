# Test Pyramid Rebalancing Plan

**Date:** December 23, 2025  
**Objective:** Transform current 12:1 unit:integration ratio to optimal 70/20/10 pyramid  
**Timeline:** 6 weeks (Phases 2-3 of overall testing strategy)

## Current State vs Target

### Current Distribution (Audit Findings)

- **Unit Tests**: 221 files (~92%) - **TARGET: 70%**
- **Integration Tests**: 18 files (~7.5%) - **TARGET: 20%**
- **E2E Tests**: 0 files (0%) - **TARGET: 10%**
- **Uncategorized**: 3,517 files (need classification)
- **Over-mocking**: 881 files use mocking (23% of all tests)

### Target Distribution (Based on 3,756 total test files)

- **Unit Tests**: ~2,629 files (70%) - **Need to reduce by ~1,127 files**
- **Integration Tests**: ~751 files (20%) - **Need to add ~733 files**
- **E2E Tests**: ~376 files (10%) - **Need to add 376 files**

## Strategic Approach

### Phase 1: Test Categorization and Cleanup (Week 1)

#### 1.1 Fix Test Collection Issues

**Priority**: CRITICAL - Must resolve before rebalancing

```bash
# Immediate fixes needed:
- packages/qdrant-loader/tests/unit/cli/test_ingest_commands_targeted.py
  ImportError: cannot import name 'ingest_command'
```

**Actions:**

- Audit all test files for import errors
- Fix missing imports and broken dependencies
- Ensure 100% test collection success

#### 1.2 Categorize Existing Tests

**Goal**: Classify 3,517 uncategorized test files

**Classification Criteria:**

```python
# Unit Test Criteria:
- Tests single function/class in isolation
- Uses mocks for external dependencies
- Fast execution (<100ms per test)
- No network/database/file system access

# Integration Test Criteria:  
- Tests interaction between 2+ components
- Uses real services (minimal mocking)
- Moderate execution time (100ms-5s per test)
- May use test databases/services

# E2E Test Criteria:
- Tests complete user workflows
- Uses real services and data
- Slower execution (5s+ per test)
- Full system integration
```

**Implementation:**

1. Create automated classification script
2. Add pytest markers to all tests
3. Update directory structure if needed
4. Validate classification accuracy

### Phase 2: Strategic Test Reduction (Week 2-3)

#### 2.1 Identify Redundant Unit Tests

**Target**: Reduce unit tests by ~1,127 files

**Reduction Strategy:**

1. **Over-tested Utilities** - Reduce excessive coverage of simple functions
2. **Duplicate Test Logic** - Merge similar test cases
3. **Over-mocked Integration Points** - Convert to integration tests
4. **Trivial Getters/Setters** - Remove tests for simple properties

**High-Value Reduction Targets:**

```python
# Example: GraphitiManager has 730 lines of heavily mocked tests
# Current: 100% mocked external dependencies
# Target: Keep 30% as unit tests, convert 70% to integration tests

# Before (Over-mocked Unit Test):
@patch("qdrant_loader.core.managers.graphiti_manager.Graphiti")
@patch("qdrant_loader.core.managers.graphiti_manager.OpenAIClient")
def test_graphiti_initialization():
    # All dependencies mocked - misses real initialization issues

# After (Reduced Unit Test):
def test_graphiti_config_validation():
    # Test only config validation logic - no external deps
```

#### 2.2 Reduce Over-Mocking

**Target**: Reduce mocking usage from 881 files to ~500 files

**De-mocking Strategy:**

1. **Configuration Loading**: Use real YAML files instead of mocks
2. **Database Connections**: Use test databases instead of mocks
3. **API Clients**: Use real test endpoints or test doubles
4. **Service Managers**: Test real initialization flows

### Phase 3: Integration Test Development (Week 3-4)

#### 3.1 Critical Integration Test Categories

**Target**: Add ~733 integration test files

**Priority 1: Configuration Integration (150 tests)**

```python
# Real configuration loading scenarios
class TestConfigurationIntegration:
    def test_multi_file_loading_with_env_substitution(self):
        # Test real YAML loading + environment variable substitution
        
    def test_optional_domain_auto_discovery(self):
        # Test real file system discovery of optional configs
        
    def test_configuration_validation_chain(self):
        # Test complete config validation pipeline
```

**Priority 2: Service Initialization Integration (200 tests)**

```python
# Real service startup and dependency injection
class TestServiceInitializationIntegration:
    def test_graphiti_manager_real_initialization(self):
        # Test real GraphitiManager startup with actual dependencies
        
    def test_neo4j_connection_establishment(self):
        # Test real Neo4j connection with retry logic
        
    def test_qdrant_client_initialization(self):
        # Test real Qdrant client setup and collection creation
```

**Priority 3: Cross-Service Integration (200 tests)**

```python
# Multi-service interaction testing
class TestCrossServiceIntegration:
    def test_pipeline_with_all_services(self):
        # Test complete ingestion pipeline with real services
        
    def test_entity_extraction_to_neo4j_flow(self):
        # Test Graphiti → Neo4j entity storage flow
        
    def test_search_across_qdrant_and_neo4j(self):
        # Test hybrid search using both databases
```

**Priority 4: Error Propagation Integration (183 tests)**

```python
# Error handling across service boundaries
class TestErrorPropagationIntegration:
    def test_neo4j_failure_handling(self):
        # Test system behavior when Neo4j is unavailable
        
    def test_partial_service_failure_recovery(self):
        # Test graceful degradation scenarios
        
    def test_configuration_error_propagation(self):
        # Test how config errors propagate through system
```

#### 3.2 Integration Test Infrastructure

**Requirements:**

- Test database instances (Neo4j, Qdrant)
- Test configuration management
- Service lifecycle management
- Test data fixtures
- Parallel execution support

### Phase 4: E2E Test Framework (Week 4-5)

#### 4.1 E2E Test Categories

**Target**: Add ~376 E2E test files

**Category 1: Complete Workflows (150 tests)**

```python
# End-to-end user scenarios
class TestCompleteWorkflows:
    def test_document_ingestion_to_search_workflow(self):
        # Upload → Process → Index → Search → Results
        
    def test_multi_project_workspace_management(self):
        # Create projects → Configure → Ingest → Query across projects
        
    def test_graphiti_knowledge_graph_building(self):
        # Ingest → Extract entities → Build graph → Query relationships
```

**Category 2: Configuration Scenarios (100 tests)**

```python
# Different configuration combinations
class TestConfigurationScenarios:
    def test_minimal_configuration_workflow(self):
        # Core domains only - complete workflow
        
    def test_full_configuration_workflow(self):
        # All domains enabled - complete workflow
        
    def test_configuration_migration_workflow(self):
        # Config format changes - migration testing
```

**Category 3: Failure Recovery (76 tests)**

```python
# System resilience testing
class TestFailureRecovery:
    def test_network_failure_recovery(self):
        # Network interruption → Auto-recovery → Resume processing
        
    def test_service_restart_recovery(self):
        # Service crash → Restart → State recovery
        
    def test_data_corruption_recovery(self):
        # Corrupted data → Detection → Recovery procedures
```

**Category 4: Performance Scenarios (50 tests)**

```python
# Performance and scalability
class TestPerformanceScenarios:
    def test_large_document_processing(self):
        # Large file ingestion → Memory management → Completion
        
    def test_concurrent_user_scenarios(self):
        # Multiple users → Concurrent operations → Data consistency
```

### Phase 5: Test Organization and Tooling (Week 5-6)

#### 5.1 Directory Structure Reorganization

```text
tests/
├── unit/                    # 70% - Fast, isolated tests
│   ├── core/               # Business logic units
│   ├── config/             # Configuration validation only
│   ├── utils/              # Utility functions
│   └── models/             # Data model tests
├── integration/            # 20% - Component interaction tests
│   ├── config/             # Real configuration loading
│   ├── services/           # Service initialization
│   ├── databases/          # Database integration
│   └── pipelines/          # Multi-component workflows
├── e2e/                    # 10% - Complete workflow tests
│   ├── workflows/          # User scenario testing
│   ├── scenarios/          # Configuration scenarios
│   ├── recovery/           # Failure recovery testing
│   └── performance/        # Performance scenarios
└── fixtures/               # Shared test data and utilities
    ├── configs/            # Test configuration files
    ├── data/               # Test datasets
    └── services/           # Service test utilities
```

#### 5.2 Test Execution Strategy

```yaml
# pytest.ini configuration
[tool:pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (real services)
    e2e: End-to-end tests (complete workflows)
    slow: Tests that take >5 seconds
    requires_services: Tests requiring external services

# Execution strategies:
# Development: pytest -m "unit"
# CI/CD: pytest -m "unit or integration"
# Nightly: pytest -m "unit or integration or e2e"
```

#### 5.3 Test Infrastructure Requirements

**Service Management:**

- Docker Compose for test services
- Test database initialization scripts
- Service health checks
- Test data seeding

**CI/CD Integration:**

- Parallel test execution
- Service dependency management
- Test result reporting
- Performance monitoring

## Implementation Timeline

### Week 1: Foundation

- [ ] Fix test collection errors
- [ ] Implement test classification script
- [ ] Add pytest markers to existing tests
- [ ] Validate test categorization

### Week 2: Reduction

- [ ] Identify redundant unit tests
- [ ] Remove/merge duplicate tests
- [ ] Reduce over-mocking in unit tests
- [ ] Convert over-mocked tests to integration tests

### Week 3: Integration Development

- [ ] Create integration test infrastructure
- [ ] Implement configuration integration tests
- [ ] Add service initialization integration tests
- [ ] Develop cross-service integration tests

### Week 4: E2E Framework

- [ ] Set up E2E test infrastructure
- [ ] Implement workflow E2E tests
- [ ] Add configuration scenario tests
- [ ] Create failure recovery tests

### Week 5: Organization

- [ ] Reorganize test directory structure
- [ ] Update CI/CD pipeline configuration
- [ ] Create test execution strategies
- [ ] Document test guidelines

### Week 6: Validation

- [ ] Validate test pyramid ratios
- [ ] Measure test execution performance
- [ ] Verify defect detection capability
- [ ] Document lessons learned

## Success Metrics

### Quantitative Targets

- **Test Distribution**: 70% unit, 20% integration, 10% E2E
- **Execution Time**: Integration tests <5min, E2E tests <15min
- **Defect Detection**: >95% of recent production issues caught by tests
- **Test Reliability**: >99% test suite stability

### Qualitative Targets

- **Real Integration Coverage**: Minimal mocking in integration/E2E tests
- **Failure Detection**: Tests catch configuration and initialization issues
- **Maintainability**: Clear test organization and documentation
- **Developer Experience**: Fast feedback for unit tests, comprehensive coverage for integration

## Risk Mitigation

### Technical Risks

- **Test Infrastructure Complexity**: Start with simple Docker setup
- **Test Execution Time**: Implement parallel execution from start
- **Service Dependencies**: Use test doubles when real services unavailable
- **Data Management**: Implement proper test data isolation

### Process Risks

- **Team Adoption**: Provide clear migration guidelines and examples
- **Knowledge Transfer**: Document patterns and best practices
- **Regression Risk**: Maintain existing test coverage during transition
- **Timeline Pressure**: Prioritize high-impact areas first

## Next Steps

1. **Begin Week 1 activities** - Fix test collection and categorization
2. **Set up tracking metrics** - Monitor progress against targets
3. **Establish review checkpoints** - Weekly progress reviews
4. **Prepare team communication** - Share plan and gather feedback

---

**Dependencies**: This plan builds on the audit findings and strategic framework from Tasks 31.1 and 31.2.  
**Next Task**: Task 31.4 (Critical Integration Test Development) will implement the integration test strategy defined here.
