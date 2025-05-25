# 🏷️ Release Management Guide

This guide explains how to manage releases for the QDrant Loader project, which uses unified versioning across all packages.

## 📋 Overview

The QDrant Loader project consists of two packages that are always released together with the same version number:

- `qdrant-loader` - Core data loading functionality
- `qdrant-loader-mcp-server` - Model Context Protocol server

## 🔄 Unified Versioning

### Why Unified Versioning?

Both packages are part of the same ecosystem and are designed to work together. Using the same version number:

- **Simplifies dependency management** for users
- **Ensures compatibility** between packages
- **Reduces confusion** about which versions work together
- **Streamlines the release process**

### Version Source of Truth

The `qdrant-loader` package serves as the source of truth for the current version. When syncing versions, all packages will be updated to match the `qdrant-loader` version.

## 🛠️ Release Script (`release.py`)

The project includes a comprehensive release script that automates the entire release process with safety checks and user-friendly output.

### Features

- ✅ **Comprehensive Safety Checks** - Validates git status, branch, workflows, and more
- ✅ **Unified Versioning** - Ensures all packages have the same version
- ✅ **Dry Run Mode** - Preview changes without making them
- ✅ **Version Synchronization** - Automatically sync package versions
- ✅ **GitHub Integration** - Creates releases and tags automatically
- ✅ **User-Friendly Output** - Clear, actionable feedback with emojis and formatting
- ✅ **Error Recovery** - Continues through all checks in dry run mode to show all issues

## 🚀 Quick Start

### 1. Check Release Readiness

Always start with a dry run to see what would happen:

```bash
python release.py --dry-run
```

This will show you:

- Current safety check status
- Version changes that would be made
- All actions that would be performed
- Any issues that need to be fixed

### 2. Fix Any Issues

If the dry run shows failed checks, fix them:

```bash
# Example: Commit uncommitted changes
git add .
git commit -m "chore: prepare for release"

# Example: Push unpushed commits
git push origin main

# Example: Sync package versions
python release.py --sync-versions
```

### 3. Create the Release

Once all checks pass:

```bash
python release.py
```

## 📖 Detailed Usage

### Command Line Options

```bash
python release.py [OPTIONS]

Options:
  --dry-run        Simulate the release process without making any changes
  -v, --verbose    Enable verbose output for debugging
  --sync-versions  Sync all packages to the same version
  --help          Show help message
```

### Safety Checks

The script performs these safety checks:

| Check | Description | Fix |
|-------|-------------|-----|
| **Git Status** | Working directory is clean | Commit or stash changes |
| **Current Branch** | On main branch | `git checkout main` |
| **Unpushed Commits** | No unpushed commits | `git push origin main` |
| **Main Up To Date** | Local main matches remote | `git pull origin main` |
| **GitHub Workflows** | All workflows passing | Fix failing workflows |

### Version Bump Types

When creating a release, you can choose from:

1. **Major** (1.0.0) - Breaking changes
   - Use for incompatible API changes
   - Resets minor and patch to 0

2. **Minor** (0.2.0) - New features
   - Use for backward-compatible functionality
   - Resets patch to 0

3. **Patch** (0.1.4) - Bug fixes
   - Use for backward-compatible bug fixes
   - Increments patch number

4. **Beta** (0.1.3b2) - Pre-release
   - Use for testing versions
   - Increments beta number or adds b1

5. **Custom** - Specify exact version
   - Use for special versioning needs
   - Must follow semantic versioning

### Version Synchronization

If packages have different versions, use the sync command:

```bash
# Check what would be synced (dry run)
python release.py --sync-versions --dry-run

# Actually sync the versions
python release.py --sync-versions
```

This will:

1. Use `qdrant-loader` version as the source of truth
2. Update all other packages to match
3. Commit the changes with a descriptive message

## 🎯 Example Workflows

### Scenario 1: Regular Release

```bash
# 1. Check current status
python release.py --dry-run

# 2. If all checks pass, create release
python release.py
# Choose version bump type (e.g., 2 for minor)

# 3. Verify release was created
git log --oneline -5
git tag --list | tail -5
```

### Scenario 2: Packages Out of Sync

```bash
# 1. Check status - shows version mismatch
python release.py --dry-run
# ❌ Version mismatch detected!
#    qdrant-loader: 0.2.0
#    qdrant-loader-mcp-server: 0.1.5

# 2. Sync versions
python release.py --sync-versions
# ✅ All packages synced to 0.2.0

# 3. Now create release
python release.py --dry-run  # Verify everything looks good
python release.py            # Create the release
```

### Scenario 3: Failed Safety Checks

```bash
# 1. Check status - shows multiple issues
python release.py --dry-run
# ❌ Git Status
# ❌ Unpushed Commits
# ✅ Current Branch
# ✅ Main Up To Date
# ✅ Github Workflows

# 2. Fix issues one by one
git add .
git commit -m "fix: resolve pending changes"
git push origin main

# 3. Verify fixes
python release.py --dry-run
# ✅ All checks passed!

# 4. Create release
python release.py
```

## 🔧 Advanced Usage

### Verbose Mode

For debugging or detailed information:

```bash
python release.py --dry-run --verbose
```

This shows additional debug information including:

- Command execution details
- API calls being made
- Detailed git operations
- File system operations

### Custom Versions

For special releases (hotfixes, specific versions):

```bash
python release.py
# Choose option 5 (Custom)
# Enter version: 1.2.3-hotfix.1
```

### Beta Releases

For pre-release testing:

```bash
python release.py
# Choose option 4 (Beta)
# This will create versions like 0.2.0b1, 0.2.0b2, etc.
```

## 🤖 Automation Integration

### GitHub Actions

The release script integrates with GitHub Actions:

1. **Script creates tags** → Triggers GitHub Actions
2. **Actions run tests** → Ensures quality
3. **Actions build packages** → Creates distributions
4. **Actions publish to PyPI** → Makes packages available

### CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
name: Release
on:
  push:
    tags:
      - 'qdrant-loader-v*'
      - 'qdrant-loader-mcp-server-v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Build and publish
        run: |
          # Build and publish logic here
```

## 🛡️ Best Practices

### Before Releasing

1. **Run comprehensive tests**:

   ```bash
   pytest tests/ --cov=packages --cov-report=html
   ```

2. **Update changelogs**:
   - Update `packages/qdrant-loader/CHANGELOG.md`
   - Update `packages/qdrant-loader-mcp-server/CHANGELOG.md`

3. **Review documentation**:
   - Ensure README files are up to date
   - Check that new features are documented

4. **Test in staging environment**:
   - Deploy to staging
   - Run integration tests
   - Verify functionality

### During Release

1. **Always start with dry run**:

   ```bash
   python release.py --dry-run
   ```

2. **Fix issues before proceeding**:
   - Don't ignore failed safety checks
   - Ensure all workflows are passing

3. **Choose appropriate version bump**:
   - Follow semantic versioning principles
   - Consider impact on users

### After Release

1. **Verify PyPI packages**:
   - Check that packages are available
   - Test installation from PyPI

2. **Update documentation**:
   - Update version badges
   - Announce new features

3. **Monitor for issues**:
   - Watch for bug reports
   - Monitor download statistics

## 🚨 Troubleshooting

### Common Issues

#### Version Mismatch Error

```bash
❌ Version mismatch detected! All packages should have the same version.
```

**Solution**: Run `python release.py --sync-versions`

#### GitHub Token Missing

```bash
❌ GITHUB_TOKEN not found in .env file.
```

**Solution**: Add your GitHub token to `.env`:

```bash
echo "GITHUB_TOKEN=your_token_here" >> .env
```

#### Workflow Failures

```bash
❌ Workflow 'CI' is not passing. Latest run status: failure
```

**Solution**: Fix the failing workflow before releasing

#### Uncommitted Changes

```bash
❌ There are uncommitted changes. Please commit or stash them first.
```

**Solution**: Commit or stash your changes:

```bash
git add .
git commit -m "chore: prepare for release"
# or
git stash
```

### Getting Help

If you encounter issues:

1. **Check verbose output**:

   ```bash
   python release.py --dry-run --verbose
   ```

2. **Review the script help**:

   ```bash
   python release.py --help
   ```

3. **Check GitHub Issues**:
   - Search for similar problems
   - Create a new issue if needed

4. **Review this documentation**:
   - Check the troubleshooting section
   - Review best practices

## 📚 Related Documentation

- [Contributing Guide](./CONTRIBUTING.md) - Development workflow
- [Main README](../README.md) - Project overview
- [QDrant Loader README](../packages/qdrant-loader/README.md) - Core package docs
- [MCP Server README](../packages/qdrant-loader-mcp-server/README.md) - MCP server docs

---

**Happy Releasing! 🚀**
