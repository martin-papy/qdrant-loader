# Workspace Flag Implementation Plan

## Overview

This document outlines the implementation plan for adding a `--workspace` flag to the QDrant Loader CLI. The workspace flag will serve as a convenient shortcut that:

1. Automatically looks for `config.yaml` and `.env` files in the specified workspace directory
2. Redirects all output (logs, metrics, SQLite database) to the workspace directory
3. Overrides the database path configuration from `config.yaml` to use a workspace-local SQLite file
4. Provides a clean, self-contained workspace for each project

## Current State Analysis

### Current CLI Structure

The CLI currently supports these configuration-related flags:

- `--config`: Path to config file
- `--env`: Path to .env file  
- `--log-level`: Logging level

### Current Configuration Loading

1. **Config File Discovery**:
   - Uses provided `--config` path, or
   - Falls back to `config.yaml` in current directory
   - Raises error if no config found

2. **Environment File Loading**:
   - Uses provided `--env` path, or
   - Falls back to `.env` in current directory (if exists)

3. **Output Locations**:
   - **Logs**: Currently hardcoded to `"qdrant-loader.log"` in current directory
   - **Metrics**: Hardcoded to `Path.cwd() / "metrics"` directory
   - **SQLite DB**: Configured via `STATE_DB_PATH` environment variable in config

### Current Issues

1. **Scattered Output**: Logs, metrics, and database files are created in different locations
2. **Manual Configuration**: Users must manually specify config and env file paths
3. **Database Path Override**: No clean way to override database path without modifying config
4. **Project Isolation**: No easy way to create isolated workspaces for different projects

## Implementation Plan

### Phase 1: Core Infrastructure Changes

#### 1.1 CLI Flag Addition

**File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/cli/cli.py`

**Changes**:

- Add `--workspace` option to all relevant commands (`init`, `ingest`, `config`)
- Add workspace validation and setup logic
- Modify `_load_config()` to support workspace mode

```python
@option(
    "--workspace", 
    type=ClickPath(path_type=Path), 
    help="Workspace directory containing config.yaml and .env files. All output will be stored here."
)
```

#### 1.2 Workspace Configuration Handler

**New File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/config/workspace.py`

**Purpose**: Handle workspace-specific configuration logic

**Key Functions**:

- `setup_workspace(workspace_path: Path) -> WorkspaceConfig`
- `validate_workspace(workspace_path: Path) -> bool`
- `create_workspace_structure(workspace_path: Path) -> None`

```python
@dataclass
class WorkspaceConfig:
    """Configuration for workspace mode."""
    workspace_path: Path
    config_path: Path
    env_path: Path | None
    logs_path: Path
    metrics_path: Path
    database_path: Path
    
    def __post_init__(self):
        """Validate workspace configuration."""
        if not self.workspace_path.exists():
            raise ValueError(f"Workspace directory does not exist: {self.workspace_path}")
        
        if not self.config_path.exists():
            raise ValueError(f"config.yaml not found in workspace: {self.config_path}")
```

#### 1.3 Configuration Loading Enhancement

**File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/config/__init__.py`

**Changes**:

- Modify `initialize_config()` to accept workspace configuration
- Add workspace-aware environment variable substitution
- Override database path when in workspace mode

**New Function**:

```python
def initialize_config_with_workspace(
    workspace_config: WorkspaceConfig,
    skip_validation: bool = False
) -> None:
    """Initialize configuration using workspace settings."""
```

### Phase 2: Output Redirection

#### 2.1 Logging Enhancement

**File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/utils/logging.py`

**Changes**:

- Modify `LoggingConfig.setup()` to accept custom log file path
- Update CLI logging setup to use workspace log path when available

**Enhanced Function**:

```python
@classmethod
def setup(
    cls,
    level: str = "INFO",
    format: str = "console",
    file: str | None = None,
    workspace_path: Path | None = None,  # New parameter
    suppress_qdrant_warnings: bool = True,
    clean_output: bool = True,
) -> None:
```

#### 2.2 Metrics Path Configuration

**File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/core/async_ingestion_pipeline.py`

**Changes**:

- Modify `AsyncIngestionPipeline.__init__()` to accept custom metrics directory
- Update factory pattern to support workspace-aware metrics path

**File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/core/pipeline/factory.py`

**Changes**:

- Update `PipelineComponentsFactory.create_components()` to accept metrics path
- Modify metrics directory creation logic

#### 2.3 Database Path Override

**File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/config/state.py`

**Changes**:

- Add workspace mode support to `StateManagementConfig`
- Allow runtime override of database path

**New Method**:

```python
def override_database_path(self, new_path: str) -> 'StateManagementConfig':
    """Create a new config with overridden database path."""
    return StateManagementConfig(
        database_path=new_path,
        table_prefix=self.table_prefix,
        connection_pool=self.connection_pool
    )
```

### Phase 3: CLI Integration

#### 3.1 Command Updates

**File**: `qdrant-loader/packages/qdrant-loader/src/qdrant_loader/cli/cli.py`

**Functions to Update**:

- `init()`: Add workspace support
- `ingest()`: Add workspace support  
- `config()`: Add workspace support

**New Helper Functions**:

```python
def _setup_workspace(workspace_path: Path) -> WorkspaceConfig:
    """Setup and validate workspace configuration."""

def _load_config_with_workspace(
    workspace_config: WorkspaceConfig | None = None,
    config_path: Path | None = None,
    env_path: Path | None = None,
    skip_validation: bool = False,
) -> None:
    """Load configuration with workspace or traditional mode."""

def _setup_workspace_logging(
    log_level: str, 
    workspace_config: WorkspaceConfig | None = None
) -> None:
    """Setup logging with workspace-aware paths."""
```

#### 3.2 Validation Logic

**Workspace Validation Rules**:

1. Workspace directory must exist
2. `config.yaml` must exist in workspace directory
3. `.env` file is optional but will be used if present
4. Workspace directory must be writable
5. Cannot use `--workspace` with `--config` or `--env` flags (mutually exclusive)

#### 3.3 Error Handling

**Enhanced Error Messages**:

- Clear guidance when workspace directory doesn't exist
- Helpful suggestions when config.yaml is missing
- Warnings about conflicting flags

### Phase 4: Backward Compatibility

#### 4.1 Flag Precedence

**Priority Order**:

1. `--workspace` flag (if provided)
2. `--config` and `--env` flags (if provided)
3. Default behavior (current directory lookup)

#### 4.2 Migration Support

**Considerations**:

- Existing scripts using `--config` and `--env` continue to work unchanged
- No breaking changes to existing configuration format
- Clear documentation on migration path

### Phase 5: Testing Strategy

#### 5.1 Unit Tests

**New Test Files**:

- `tests/unit/config/test_workspace.py`
- `tests/unit/cli/test_workspace_cli.py`

**Test Coverage**:

- Workspace configuration validation
- File discovery logic
- Output path redirection
- Error handling scenarios
- Flag precedence logic

#### 5.2 Integration Tests

**Test Scenarios**:

- End-to-end workspace setup and ingestion
- Output file creation in correct locations
- Database path override functionality
- Logging and metrics in workspace directory

#### 5.3 CLI Tests

**Test Cases**:

- Workspace flag with valid directory
- Workspace flag with missing config.yaml
- Workspace flag with non-existent directory
- Conflicting flags (workspace + config/env)
- Permission issues

### Phase 6: Documentation

#### 6.1 User Documentation

**Updates Needed**:

- CLI help text
- README.md examples
- Configuration guide
- Migration guide

#### 6.2 Example Usage

```bash
# Create a workspace directory
mkdir my-project-workspace
cd my-project-workspace

# Copy your config files
cp /path/to/config.yaml .
cp /path/to/.env .

# Run with workspace flag
qdrant-loader --workspace . init
qdrant-loader --workspace . ingest

# All output will be in the workspace:
# - my-project-workspace/qdrant-loader.log
# - my-project-workspace/metrics/
# - my-project-workspace/qdrant-loader.db
```

## Implementation Details

### Workspace Directory Structure

```
my-workspace/
├── config.yaml          # Required: Main configuration
├── .env                 # Optional: Environment variables
├── qdrant-loader.log    # Generated: Application logs
├── qdrant-loader.db     # Generated: SQLite state database
└── metrics/             # Generated: Metrics output
    └── ingestion_metrics_*.json
```

### Configuration Override Logic

1. **Database Path Override**:
   - Original: Uses `STATE_DB_PATH` from environment/config
   - Workspace Mode: Uses `{workspace}/qdrant-loader.db`
   - Implementation: Override `STATE_DB_PATH` environment variable before config loading

2. **Environment Variable Precedence**:
   - Workspace `.env` file variables
   - System environment variables
   - Config file defaults

### Error Scenarios and Handling

| Scenario | Error Message | Suggested Action |
|----------|---------------|------------------|
| Workspace doesn't exist | `Workspace directory does not exist: {path}` | Create directory or check path |
| No config.yaml | `config.yaml not found in workspace: {path}` | Copy config.yaml to workspace |
| Permission denied | `Cannot write to workspace directory: {path}` | Check directory permissions |
| Conflicting flags | `Cannot use --workspace with --config or --env` | Use either workspace or individual flags |

## Benefits

### For Users

1. **Simplified CLI Usage**: Single flag instead of multiple paths
2. **Project Isolation**: Each workspace is self-contained
3. **Organized Output**: All files in one location
4. **Easy Cleanup**: Delete workspace directory to remove all traces
5. **Portable Workspaces**: Easy to move/backup entire project

### For Development

1. **Cleaner Testing**: Isolated test environments
2. **Better Debugging**: All relevant files in one place
3. **Simplified CI/CD**: Workspace-based build processes
4. **Configuration Management**: Version control entire workspace

## Migration Path

### Existing Users

1. **No Immediate Changes Required**: Current CLI usage continues to work
2. **Optional Migration**: Users can gradually adopt workspace pattern
3. **Documentation**: Clear examples of workspace setup

### Recommended Workflow

1. Create workspace directory for each project
2. Copy existing config.yaml and .env files
3. Switch to using `--workspace` flag
4. Enjoy organized, isolated project environments

## Risk Assessment

### Low Risk

- **Backward Compatibility**: No breaking changes to existing functionality
- **Incremental Adoption**: Users can migrate at their own pace
- **Isolated Changes**: New functionality doesn't affect existing code paths

### Medium Risk

- **Configuration Complexity**: Additional logic for path resolution
- **Testing Overhead**: Need comprehensive test coverage for new scenarios

### Mitigation Strategies

- **Comprehensive Testing**: Unit, integration, and CLI tests
- **Clear Documentation**: Examples and migration guides
- **Gradual Rollout**: Feature flag or beta testing period
- **Fallback Behavior**: Robust error handling and clear error messages

## Success Criteria

### Functional Requirements

- [ ] `--workspace` flag works with all CLI commands
- [ ] Config and env files are automatically discovered in workspace
- [ ] All output (logs, metrics, database) goes to workspace directory
- [ ] Database path is correctly overridden
- [ ] Backward compatibility is maintained

### Quality Requirements

- [ ] >95% test coverage for new functionality
- [ ] Clear error messages for all failure scenarios
- [ ] Comprehensive documentation with examples
- [ ] Performance impact <5% compared to current implementation

### User Experience Requirements

- [ ] Intuitive CLI interface
- [ ] Clear help text and examples
- [ ] Smooth migration path from existing usage
- [ ] Organized workspace structure

## Timeline

### Week 1: Core Infrastructure

- Implement workspace configuration handler
- Add CLI flag and basic validation
- Update configuration loading logic

### Week 2: Output Redirection

- Implement logging path override
- Update metrics path configuration
- Implement database path override

### Week 3: CLI Integration

- Update all CLI commands
- Implement validation and error handling
- Add comprehensive CLI tests

### Week 4: Testing and Documentation

- Complete unit and integration tests
- Update documentation and examples
- Perform end-to-end testing

## Conclusion

The workspace flag implementation will significantly improve the user experience by providing a clean, organized way to manage QDrant Loader projects. The implementation maintains full backward compatibility while offering a more intuitive and powerful workflow for users who want better project organization and isolation.

The modular approach ensures that the changes are maintainable and testable, while the comprehensive error handling and documentation will provide a smooth user experience.
