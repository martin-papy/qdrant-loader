# Release Notes

## Version 0.4.0 (Upcoming)

**Release Date**: TBD  
**Type**: Maintenance Release  
**Compatibility**: Backward Compatible

### 🆕 New Features

#### Workspace Mode

**New**: `--workspace` flag for simplified configuration management and project organization.

- **Auto-discovery**: Automatically finds `config.yaml` and `.env` files in workspace directory
- **Centralized storage**: All logs, metrics, and database files stored in workspace
- **Environment isolation**: Workspace `.env` takes precedence over global environment
- **Simplified commands**: No need to specify individual file paths

**Usage Examples**:

```bash
# Create workspace
mkdir my-project && cd my-project

# Copy templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template

# Use workspace mode
qdrant-loader --workspace . init
qdrant-loader --workspace . ingest
qdrant-loader --workspace . status
```

**Workspace Structure**:

```
my-workspace/
├── config.yaml              # Configuration file (required)
├── .env                     # Environment variables (optional)
├── qdrant-loader.db         # State database (auto-created)
├── qdrant-loader.log        # Application logs
└── metrics/                 # Performance metrics
```

### 🔧 Configuration Improvements

#### API Key Configuration Structure (Internal)

**For Developers**: Improved internal configuration structure for better maintainability and consistency.

- **Changed**: Internal API key access pattern from `settings.OPENAI_API_KEY` to `settings.global_config.embedding.api_key`
- **User Impact**: **None** - All existing `.env` files and `config.yaml` files continue to work unchanged
- **Developer Impact**: Code extending the embedding service should use the new access pattern

#### Configuration Template Organization

**Improved**: Configuration templates moved to dedicated `conf/` directory for better organization.

- **New Locations**:
  - `packages/qdrant-loader/conf/config.template.yaml`
  - `packages/qdrant-loader/conf/.env.template`
- **Old Locations**: Previous paths still work but are deprecated
- **Documentation**: All documentation updated to reference new paths

### 🧪 Testing Improvements

- **Fixed**: All test files updated to use correct configuration structure
- **Enhanced**: Test coverage for embedding service configuration
- **Improved**: Mock settings structure in test files

### 📚 Documentation Updates

- **Updated**: All README files to reference new configuration template paths
- **Enhanced**: Migration guide with API key structure information
- **Improved**: Cross-references and links throughout documentation

### 🔄 Migration Notes

This is a **backward compatible** release:

- ✅ **No user action required** - existing configurations continue to work
- ✅ **No breaking changes** - all APIs remain the same
- ✅ **Optional**: Update template download commands to use new paths
- ✅ **Developers**: Update code to use new internal API key access pattern

---

## Version 0.3.2

**Release Date**: May 31, 2025  
**Type**: Major Feature Release  
**Compatibility**: Backward Compatible
