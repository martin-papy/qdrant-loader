# 🚀 Release Notes

## 🆕 Latest Features

### Confluence Data Center Support

QDrant Loader now supports **both Confluence Cloud and Data Center/Server** deployments:

- **Secure authentication methods**: API tokens (Cloud) and Personal Access Tokens (Data Center)
- **Deployment-specific optimization**: Proper pagination and API handling for each deployment type
- **Seamless migration**: Easy transition from Cloud to Data Center configurations
- **Auto-detection**: Automatic deployment type detection based on URL patterns

See our [Confluence Data Center Support Guide](./docs/ConfluenceDataCenterSupport.md) for detailed setup instructions.

## 📋 Release Process Updates

The QDrant Loader project has been updated with a new unified versioning approach and enhanced release management system.

## 🔄 Major Changes

### Unified Versioning

- **Both packages now use the same version number** instead of independent versioning
- **`qdrant-loader` is the source of truth** for the current version
- **Automatic version mismatch detection** prevents releases with inconsistent versions
- **Version synchronization command** to easily sync packages when needed

### Enhanced Release Script

The `release.py` script has been completely rewritten with:

- ✅ **Comprehensive safety checks** (git status, branch, workflows, etc.)
- ✅ **Dry run mode** that continues through all steps to show all issues
- ✅ **User-friendly output** with emojis, clear formatting, and actionable guidance
- ✅ **Version synchronization** with `--sync-versions` flag
- ✅ **GitHub integration** for automated tag and release creation
- ✅ **Error recovery** that shows all problems instead of stopping at the first one

## 🎯 Benefits

### For Developers

- **Clearer release process** with step-by-step guidance
- **Safer releases** with comprehensive pre-flight checks
- **Better debugging** with verbose mode and detailed error messages
- **Faster iteration** with dry-run mode to preview changes

### For Users

- **Simplified dependency management** with unified versions
- **Guaranteed compatibility** between packages
- **Clearer versioning** without confusion about which versions work together
- **More reliable releases** with automated safety checks

## 🚀 Quick Start

### Check Release Readiness

```bash
python release.py --dry-run
```

### Sync Package Versions (if needed)

```bash
python release.py --sync-versions
```

### Create a Release

```bash
python release.py
```

## 📚 Documentation

- **[Release Management Guide](./docs/RELEASE.md)** - Comprehensive documentation
- **[Contributing Guide](./docs/CONTRIBUTING.md)** - Updated with new release process
- **[Main README](./README.md)** - Updated with unified versioning information

## 🔧 Migration

### For Existing Developers

1. **Update your workflow**:
   - Use `python release.py --dry-run` before releasing
   - Use `python release.py --sync-versions` if packages get out of sync
   - Follow the new safety checks and fix any issues

2. **Update documentation references**:
   - Both packages now have the same version
   - Reference the new release documentation

### For CI/CD

- The release script creates the same tags as before
- GitHub Actions workflows should continue to work
- Consider updating workflows to use the new script

## ⚠️ Breaking Changes

- **Unified versioning**: Both packages must have the same version
- **Release process**: Must use the new `release.py` script
- **Safety checks**: All checks must pass before releasing

## 🆘 Support

If you encounter issues:

1. **Check the verbose output**: `python release.py --dry-run --verbose`
2. **Review the documentation**: [Release Management Guide](./docs/RELEASE.md)
3. **Create an issue**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)

---

**Happy Releasing! 🎉**
