# Documentation Style Guide

This style guide ensures consistency, clarity, and professionalism across all QDrant Loader documentation.

## 📝 Writing Style

### Voice and Tone

- **Active Voice**: Use active voice whenever possible
  - ✅ "QDrant Loader processes your files"
  - ❌ "Your files are processed by QDrant Loader"

- **Present Tense**: Write in present tense for current functionality
  - ✅ "The system creates embeddings"
  - ❌ "The system will create embeddings"

- **Direct and Clear**: Be concise and specific
  - ✅ "Configure your API key in the environment file"
  - ❌ "You might want to consider setting up your API key"

- **Professional but Approachable**: Maintain professionalism while being helpful
  - ✅ "This guide helps you set up QDrant Loader quickly"
  - ❌ "This awesome guide will totally help you set up QDrant Loader"

### Audience Considerations

#### For Users

- Focus on **what** and **how**
- Provide step-by-step instructions
- Include practical examples
- Explain the benefits and outcomes

#### For Developers

- Include **why** and **how it works**
- Provide technical details and architecture
- Include code examples and API references
- Explain extension points and customization

## 🏗️ Document Structure

### Standard Document Format

```markdown
# Document Title

Brief introduction paragraph explaining the purpose and scope.

## 📋 Overview (if needed)

High-level summary of the content.

## 🔧 Prerequisites (if applicable)

What users need before starting.

## 🚀 Main Content Sections

Use descriptive headings that indicate the action or outcome.

## 🔗 Related Documentation

Links to relevant guides and references.

---

**Last Updated**: [Date]
**Maintainer**: [Name/Team]
```

### Heading Hierarchy

- **H1 (`#`)**: Document title only
- **H2 (`##`)**: Major sections
- **H3 (`###`)**: Subsections
- **H4 (`####`)**: Sub-subsections (use sparingly)

### Emoji Usage

Use emojis consistently for section types:

- 📋 Overview, Summary
- 🎯 Goals, Objectives
- 🔧 Prerequisites, Setup
- 🚀 Getting Started, Quick Start
- ⚙️ Configuration, Settings
- 📚 Examples, Tutorials
- 🔍 Advanced Topics
- 🔧 Troubleshooting
- 🔗 Related Links, References
- 📊 Metrics, Statistics
- 🆘 Help, Support

## 💻 Code and Technical Content

### Code Blocks

Always specify the language for syntax highlighting:

```markdown
```bash
# Good: Language specified
qdrant-loader ingest --source git
```

```
# Bad: No language specified
qdrant-loader ingest --source git
```

```

### Command Examples

- **Include comments** explaining what commands do
- **Show expected output** when helpful
- **Use realistic examples** with actual values

```bash
# Install QDrant Loader
pip install qdrant-loader

# Expected output:
# Successfully installed qdrant-loader-1.0.0
```

### Configuration Examples

- **Use complete, working examples**
- **Include comments** explaining options
- **Show both minimal and comprehensive configurations**

```yaml
# Minimal configuration
qdrant:
  url: "http://localhost:6333"
  
# Comprehensive configuration
qdrant:
  url: "http://localhost:6333"
  collection_name: "my_documents"
  timeout: 30
  batch_size: 100
```

### File Paths and Names

- Use **backticks** for file names: `config.yaml`
- Use **forward slashes** for paths: `docs/users/guides/`
- Use **relative paths** when possible: `./config/settings.yaml`

## 📋 Lists and Tables

### Lists

- Use **bullet points** for unordered lists
- Use **numbered lists** for sequential steps
- Use **consistent formatting** within lists

```markdown
# Good: Consistent formatting
- **Feature 1**: Description of the feature
- **Feature 2**: Description of the feature
- **Feature 3**: Description of the feature

# Bad: Inconsistent formatting
- Feature 1: Description
- **Feature 2** - Description
- Feature 3 (Description)
```

### Tables

- **Include headers** for all tables
- **Align content** appropriately
- **Keep tables readable** on mobile devices

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
```

## 🔗 Links and References

### Internal Links

- Use **relative paths** for internal documentation
- Include **descriptive link text**
- Test all links regularly

```markdown
# Good: Descriptive and relative
See the [Configuration Guide](../configuration/README.md) for details.

# Bad: Generic text and absolute
Click [here](https://github.com/user/repo/docs/config.md) for more info.
```

### External Links

- **Open in new tabs** for external resources (when applicable)
- **Include context** about what the link contains
- **Use HTTPS** when available

```markdown
# Good: Context provided
Learn more about vector databases in the [Pinecone documentation](https://docs.pinecone.io/docs/overview).

# Bad: No context
Check out [this link](https://docs.pinecone.io/docs/overview).
```

## ⚠️ Callouts and Alerts

Use consistent formatting for different types of callouts:

### Information

```markdown
> **Note**: This feature requires QDrant version 1.5 or higher.
```

### Warnings

```markdown
> **Warning**: This operation will delete all existing data in the collection.
```

### Tips

```markdown
> **Tip**: Use the `--dry-run` flag to preview changes before applying them.
```

### Important

```markdown
> **Important**: Always backup your data before performing major operations.
```

## 📊 Examples and Scenarios

### Real-World Examples

- Use **realistic data** and scenarios
- Include **complete workflows** from start to finish
- Show **expected outcomes** and results

```markdown
### Example: Processing a Git Repository

**Scenario**: You want to index documentation from a public GitHub repository.

**Steps**:
1. Configure your environment
2. Run the ingestion command
3. Verify the results

**Expected Outcome**: 150 documents indexed with embeddings generated.
```

### Code Examples

- **Test all code examples** before publishing
- **Include error handling** when relevant
- **Show both success and failure cases**

```python
# Good: Complete example with error handling
try:
    loader = QDrantLoader(config_path="config.yaml")
    result = loader.ingest_git_repo("https://github.com/user/repo")
    print(f"Successfully indexed {result.document_count} documents")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 🔧 Troubleshooting Documentation

### Error Messages

- **Quote exact error messages** when possible
- **Explain what the error means** in plain language
- **Provide step-by-step solutions**

```markdown
#### Error: `ConnectionError: Unable to connect to QDrant at localhost:6333`

**Meaning**: QDrant Loader cannot establish a connection to the QDrant database.

**Common Causes**:
- QDrant server is not running
- Incorrect URL configuration
- Network connectivity issues

**Solution**:
1. Verify QDrant is running: `docker ps | grep qdrant`
2. Check your configuration: `cat config.yaml`
3. Test connectivity: `curl http://localhost:6333/health`
```

## 📏 Formatting Standards

### Line Length

- **Aim for 80-100 characters** per line in markdown
- **Break long lines** at natural points (after punctuation)
- **Use line breaks** to improve readability

### Spacing

- **One blank line** between sections
- **Two blank lines** before major headings
- **No trailing whitespace** at line ends

### File Names

- Use **kebab-case** for file names: `getting-started.md`
- Use **descriptive names**: `confluence-integration.md` not `conf.md`
- Include **README.md** in every directory

## 🎯 Quality Checklist

Before publishing documentation, verify:

### Content Quality

- [ ] **Purpose is clear** from the introduction
- [ ] **Prerequisites are listed** and accurate
- [ ] **Steps are actionable** and complete
- [ ] **Examples work** as written
- [ ] **Expected outcomes** are described

### Technical Accuracy

- [ ] **Commands are correct** and tested
- [ ] **Configuration examples** are valid
- [ ] **API references** match implementation
- [ ] **Version requirements** are current

### Structure and Style

- [ ] **Headings follow hierarchy** (H1 → H2 → H3)
- [ ] **Links work** and are descriptive
- [ ] **Code blocks** have language specified
- [ ] **Formatting is consistent** throughout
- [ ] **Spelling and grammar** are correct

### User Experience

- [ ] **Navigation is clear** with good cross-references
- [ ] **Content flows logically** from basic to advanced
- [ ] **Troubleshooting covers** common issues
- [ ] **Related documentation** is linked

## 🔄 Maintenance Guidelines

### Regular Reviews

- **Monthly**: Check for broken links and outdated information
- **With releases**: Update version-specific content
- **With feature changes**: Update affected documentation immediately

### Version Control

- **Commit documentation** with related code changes
- **Use descriptive commit messages** for documentation updates
- **Tag documentation** with release versions when applicable

### Feedback Integration

- **Monitor user feedback** on documentation
- **Track common support questions** that indicate documentation gaps
- **Update based on user testing** and real-world usage

---

## 📚 Resources

### Tools

- **Markdown Editor**: VS Code with Markdown extensions
- **Link Checker**: markdown-link-check
- **Spell Checker**: Built-in spell checkers
- **Grammar**: Grammarly or similar tools

### References

- [GitHub Markdown Guide](https://guides.github.com/features/mastering-markdown/)
- [Google Developer Documentation Style Guide](https://developers.google.com/style)
- [Microsoft Writing Style Guide](https://docs.microsoft.com/en-us/style-guide/welcome/)

---

**Remember**: Good documentation is as important as good code. Take the time to write clearly, test thoroughly, and maintain consistently.
