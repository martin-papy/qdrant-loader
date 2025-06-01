# Documentation Update Workflow

This guide provides step-by-step workflows for updating documentation as part of your development process. Follow these workflows to ensure documentation stays current and accurate.

## 🎯 Overview

Documentation updates should be integrated into your development workflow, not treated as an afterthought. This guide shows you exactly when and how to update documentation for different types of changes.

## 🔄 General Workflow Principles

### Documentation-First Development

1. **Plan documentation impact** during feature planning
2. **Write documentation** alongside code development
3. **Review documentation** as part of code review
4. **Test documentation** before merging changes

### Integration with Git Workflow

```bash
# Standard development workflow with documentation
git checkout -b feature/new-feature
# 1. Write code
# 2. Write/update documentation
# 3. Test both code and documentation
git add . && git commit -m "feat: add new feature with documentation"
git push origin feature/new-feature
# 4. Create PR with both code and documentation changes
```

## 🛠️ Workflow by Change Type

### 1. Adding a New Feature

#### Planning Phase

```markdown
## Documentation Impact Assessment

**Feature**: Multi-project workspace support
**Developer**: @your-username
**Documentation Impact**: High

### Required Documentation Updates:
- [x] User guide for workspace configuration
- [x] CLI reference for new commands
- [x] Configuration reference for workspace settings
- [x] Examples for multi-project scenarios
- [x] Troubleshooting for workspace issues

### New Documentation Needed:
- [x] New user guide: "Managing Multiple Projects"
- [x] New developer guide: "Workspace Architecture"
- [x] Updated examples: CLI usage with workspaces
```

#### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/multi-project-support

# 2. Create documentation structure first
mkdir -p docs_new/docs/users/detailed-guides/workspace-management
touch docs_new/docs/users/detailed-guides/workspace-management/README.md

# 3. Write initial documentation outline
# (Use feature template from templates/feature-template.md)

# 4. Implement feature code
# ... code development ...

# 5. Update documentation with actual implementation details
# ... documentation updates ...

# 6. Test both code and documentation
pytest tests/
# Test all documentation examples manually

# 7. Commit together
git add .
git commit -m "feat: add multi-project workspace support

- Add workspace configuration system
- Add CLI commands for workspace management
- Add user guide for workspace setup
- Add developer documentation for workspace architecture
- Add examples and troubleshooting

Closes #123"
```

#### Documentation Checklist for New Features

- [ ] **User Documentation**
  - [ ] Feature overview and benefits
  - [ ] Step-by-step setup guide
  - [ ] Configuration options
  - [ ] Usage examples
  - [ ] Troubleshooting section

- [ ] **Developer Documentation**
  - [ ] Architecture explanation
  - [ ] API reference updates
  - [ ] Extension points
  - [ ] Testing guidelines

- [ ] **Cross-References**
  - [ ] Update related guides
  - [ ] Add navigation links
  - [ ] Update main README if needed

### 2. Modifying Existing Features

#### Identify Documentation Impact

```bash
# Find all documentation that mentions the feature
grep -r "workspace" docs_new/ --include="*.md"
grep -r "multi-project" docs_new/ --include="*.md"

# Check for configuration references
grep -r "workspace_config" docs_new/ --include="*.md"
```

#### Update Workflow

```bash
# 1. Create branch for changes
git checkout -b fix/workspace-configuration-update

# 2. Identify affected documentation
echo "Affected documentation files:" > doc_update_plan.md
grep -l "workspace" docs_new/docs/**/*.md >> doc_update_plan.md

# 3. Update code
# ... implement changes ...

# 4. Update documentation systematically
# Start with API reference, then user guides, then examples

# 5. Test updated examples
# Run through all examples in updated documentation

# 6. Commit with clear documentation changes
git add .
git commit -m "fix: update workspace configuration handling

Code changes:
- Fix workspace config validation
- Improve error messages

Documentation changes:
- Update configuration reference
- Fix examples in workspace guide
- Add new troubleshooting section

Fixes #456"
```

### 3. Bug Fixes

#### Documentation Updates for Bug Fixes

```bash
# 1. Identify if bug affects documented behavior
# If yes, update documentation

# 2. Add to troubleshooting if it's a common issue
# docs_new/docs/users/troubleshooting/common-issues.md

# 3. Update examples if they were incorrect
# Test all related examples

# 4. Update error message documentation if changed
# docs_new/docs/users/troubleshooting/error-messages.md
```

#### Example Bug Fix Documentation Update

```markdown
# In troubleshooting/common-issues.md

#### Issue: Workspace Configuration Not Loading

**Symptoms**:
- Error: "Workspace configuration file not found"
- Default configuration used instead of workspace config

**Cause**: Bug in configuration file discovery (fixed in v1.2.1)

**Solution**:
```bash
# Ensure workspace config is in the correct location
ls -la .qdrant-loader/workspace.yaml

# If missing, create with:
qdrant-loader workspace init
```

**Fixed In**: Version 1.2.1

```

### 4. API Changes

#### Breaking Changes Workflow

```bash
# 1. Update API reference first
# docs_new/docs/developers/api-reference/

# 2. Update all user guides that use the API
grep -r "old_api_method" docs_new/docs/users/

# 3. Update examples and code snippets
# Test all examples with new API

# 4. Add migration guide if needed
# docs_new/docs/users/migration/api-changes.md

# 5. Update troubleshooting for new error messages
```

#### Non-Breaking Changes Workflow

```bash
# 1. Add new API documentation
# 2. Update examples to show new capabilities
# 3. Add to feature guides where relevant
# 4. No migration documentation needed
```

## 📝 Documentation Review Process

### Self-Review Checklist

Before submitting your PR, verify:

```markdown
## Documentation Self-Review Checklist

### Content Quality
- [ ] **Purpose is clear** - Reader knows what they'll learn
- [ ] **Prerequisites listed** - Required setup is documented
- [ ] **Examples work** - All code examples tested
- [ ] **Steps are complete** - No missing steps in procedures
- [ ] **Outcomes described** - What success looks like

### Technical Accuracy
- [ ] **Commands tested** - All CLI commands work as shown
- [ ] **Config examples valid** - All YAML/JSON examples are valid
- [ ] **API references current** - Matches actual implementation
- [ ] **Version info correct** - Requirements and compatibility accurate

### Structure and Navigation
- [ ] **File location correct** - Follows documentation structure
- [ ] **Cross-references added** - Links to related documentation
- [ ] **Navigation updated** - README files updated if needed
- [ ] **Formatting consistent** - Follows style guide

### User Experience
- [ ] **Audience appropriate** - Content matches intended users
- [ ] **Flow logical** - Information builds appropriately
- [ ] **Troubleshooting included** - Common issues addressed
- [ ] **Related docs linked** - Easy to find related information
```

### Peer Review Process

#### For Reviewers

```markdown
## Documentation Review Guidelines

### Review Focus Areas

1. **Accuracy**: Do the examples work? Are the commands correct?
2. **Completeness**: Are there missing steps or information?
3. **Clarity**: Is it easy to understand and follow?
4. **Consistency**: Does it follow our style guide?

### Review Comments Format

Use this format for documentation feedback:

**Issue**: [Describe the problem]
**Suggestion**: [Provide specific improvement]
**Priority**: [High/Medium/Low]

Example:
**Issue**: The configuration example is missing the required `api_key` field
**Suggestion**: Add `api_key: "your-api-key-here"` to the YAML example
**Priority**: High
```

#### Review Checklist for Reviewers

- [ ] **Test examples** - Run through key examples yourself
- [ ] **Check links** - Verify internal and external links work
- [ ] **Validate structure** - Ensure it follows our documentation patterns
- [ ] **Consider user perspective** - Is this helpful for the target audience?

## 🔧 Tools and Automation

### Documentation Testing

```bash
# Test all code examples in documentation
python scripts/test_docs_examples.py

# Check for broken links
find docs_new -name "*.md" -exec markdown-link-check {} \;

# Spell check
aspell check docs_new/docs/users/new-guide.md

# Style check
markdownlint docs_new/docs/users/new-guide.md
```

### Automated Checks in CI

```yaml
# .github/workflows/docs.yml
name: Documentation
on: [push, pull_request]

jobs:
  docs-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Check links
        run: |
          npm install -g markdown-link-check
          find docs_new -name "*.md" -exec markdown-link-check {} \;
      
      - name: Test code examples
        run: |
          python scripts/test_docs_examples.py
      
      - name: Check formatting
        run: |
          npm install -g markdownlint-cli
          markdownlint docs_new/**/*.md
```

### Documentation Metrics

Track these metrics to ensure documentation quality:

```bash
# Documentation coverage
python scripts/check_doc_coverage.py

# Example success rate
python scripts/test_example_success_rate.py

# Link health
python scripts/check_link_health.py
```

## 🚀 Common Scenarios

### Scenario 1: Adding a New CLI Command

```bash
# 1. Implement the command
# 2. Update CLI reference
echo "## qdrant-loader new-command" >> docs_new/docs/users/cli-reference/commands.md

# 3. Add to user guide if it's a major feature
# 4. Add examples
# 5. Update help text documentation
```

### Scenario 2: Changing Configuration Format

```bash
# 1. Update configuration reference
# docs_new/docs/users/configuration/config-file-reference.md

# 2. Update all examples that use the old format
grep -r "old_config_format" docs_new/ --include="*.md"

# 3. Add migration guide if breaking
# docs_new/docs/users/migration/config-migration.md

# 4. Update troubleshooting for new validation errors
```

### Scenario 3: Adding a New Data Source

```bash
# 1. Create new data source guide
cp docs_new/docs/users/detailed-guides/data-sources/git-repositories.md \
   docs_new/docs/users/detailed-guides/data-sources/new-source.md

# 2. Update data sources overview
# docs_new/docs/users/detailed-guides/data-sources/README.md

# 3. Add configuration documentation
# 4. Add examples and troubleshooting
# 5. Update main README if it's a major addition
```

## 📊 Documentation Maintenance Schedule

### Weekly Tasks

- [ ] **Review open documentation issues** on GitHub
- [ ] **Test getting started guides** with fresh environment
- [ ] **Check for broken links** in recently updated docs

### Monthly Tasks

- [ ] **Full documentation audit** - Test all major workflows
- [ ] **Update version-specific information**
- [ ] **Review and update troubleshooting** based on support tickets
- [ ] **Check documentation metrics** and identify improvement areas

### Release Tasks

- [ ] **Update version references** throughout documentation
- [ ] **Test all examples** with new release
- [ ] **Update changelog** with documentation changes
- [ ] **Review and update** getting started guides

## 🆘 Getting Help

### Documentation Questions

- **GitHub Issues**: Use `documentation` label for doc-specific issues
- **Slack**: #documentation channel for quick questions
- **Code Review**: Tag @docs-team for documentation review

### Templates and Resources

- **Feature Template**: `docs_new/docs/developers/documentation/templates/feature-template.md`
- **Style Guide**: `docs_new/docs/developers/documentation/style-guide.md`
- **Examples**: Look at existing documentation for patterns

---

## 📋 Quick Reference

### Common Commands

```bash
# Create new documentation from template
cp docs_new/docs/developers/documentation/templates/feature-template.md \
   docs_new/docs/users/detailed-guides/new-feature.md

# Test documentation examples
python scripts/test_docs_examples.py docs_new/docs/users/new-guide.md

# Check links in specific file
markdown-link-check docs_new/docs/users/new-guide.md

# Find all references to a feature
grep -r "feature_name" docs_new/ --include="*.md"
```

### Documentation Structure

```
When adding documentation, place it in:
- User guides: docs_new/docs/users/detailed-guides/
- Configuration: docs_new/docs/users/configuration/
- CLI reference: docs_new/docs/users/cli-reference/
- Troubleshooting: docs_new/docs/users/troubleshooting/
- Developer guides: docs_new/docs/developers/
```

Remember: **Documentation is part of the feature**. Plan it, write it, test it, and maintain it with the same care you give to your code.
