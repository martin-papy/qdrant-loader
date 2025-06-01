# Migration Guide: Legacy to Multi-Project Configuration

This guide helps you migrate from the legacy single-project configuration format to the new multi-project format introduced in qdrant-loader v2.0.

## Overview

The new multi-project configuration format provides:

- **Multiple Projects**: Define multiple projects in a single configuration file
- **Project Isolation**: Separate collections and metadata for different projects
- **Better Organization**: Clearer separation between global settings and project-specific sources
- **Enhanced Flexibility**: Mix different source types within projects

## Configuration Structure Changes

### Legacy Format (No Longer Supported)

```yaml
# OLD FORMAT - No longer supported
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  # ... other global settings

sources:
  git:
    my-repo:
      base_url: "https://github.com/example/repo.git"
      # ... git config
  confluence:
    my-space:
      base_url: "https://company.atlassian.net/wiki"
      # ... confluence config
```

### New Multi-Project Format

```yaml
# NEW FORMAT - Required
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "default_collection"
  # ... other global settings

projects:
  my-project:
    project_id: "my-project"
    display_name: "My Project"
    description: "Migrated from legacy configuration"
    collection_name: "documents"  # Optional: use specific collection
    
    sources:
      git:
        my-repo:
          base_url: "https://github.com/example/repo.git"
          # ... git config
      confluence:
        my-space:
          base_url: "https://company.atlassian.net/wiki"
          # ... confluence config
```

## Step-by-Step Migration

### Step 1: Update Global Configuration

**Before:**

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  chunking:
    chunk_size: 1500
  # ... other settings
```

**After:**

```yaml
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "default_collection"  # This becomes the default
  chunking:
    chunk_size: 1500
  # ... other settings
```

### Step 2: Wrap Sources in Project Structure

**Before:**

```yaml
sources:
  git:
    docs-repo:
      base_url: "https://github.com/company/docs.git"
      branch: "main"
      # ... other git settings
  confluence:
    wiki-space:
      base_url: "https://company.atlassian.net/wiki"
      space_key: "DOCS"
      # ... other confluence settings
```

**After:**

```yaml
projects:
  main-project:  # Choose a meaningful project name
    project_id: "main-project"
    display_name: "Main Documentation Project"
    description: "Migrated from legacy single-project configuration"
    collection_name: "documents"  # Keep your original collection name
    
    sources:
      git:
        docs-repo:
          base_url: "https://github.com/company/docs.git"
          branch: "main"
          # ... other git settings
      confluence:
        wiki-space:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "DOCS"
          # ... other confluence settings
```

### Step 3: Choose Collection Strategy

You have two options for collections:

#### Option A: Keep Existing Collection (Recommended for Migration)

```yaml
projects:
  main-project:
    project_id: "main-project"
    display_name: "Main Project"
    collection_name: "documents"  # Keep your existing collection
    # ... sources
```

#### Option B: Use Default Collection

```yaml
projects:
  main-project:
    project_id: "main-project"
    display_name: "Main Project"
    # No collection_name specified - uses global default
    # ... sources
```

## Complete Migration Example

### Legacy Configuration

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "company_docs"
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"

sources:
  git:
    main-repo:
      base_url: "https://github.com/company/docs.git"
      branch: "main"
      include_paths:
        - "docs/**"
      file_types:
        - "*.md"
      token: "${GITHUB_TOKEN}"
  
  confluence:
    company-wiki:
      base_url: "https://company.atlassian.net/wiki"
      deployment_type: "cloud"
      space_key: "DOCS"
      token: "${CONFLUENCE_TOKEN}"
      email: "${CONFLUENCE_EMAIL}"
```

### Migrated Configuration

```yaml
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "default_collection"
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"

projects:
  company-docs:
    project_id: "company-docs"
    display_name: "Company Documentation"
    description: "Main company documentation from Git and Confluence"
    collection_name: "company_docs"  # Keep original collection name
    
    sources:
      git:
        main-repo:
          base_url: "https://github.com/company/docs.git"
          branch: "main"
          include_paths:
            - "docs/**"
          file_types:
            - "*.md"
          token: "${GITHUB_TOKEN}"
      
      confluence:
        company-wiki:
          base_url: "https://company.atlassian.net/wiki"
          deployment_type: "cloud"
          space_key: "DOCS"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
```

## Advanced Migration: Splitting into Multiple Projects

If you want to take advantage of the multi-project capabilities, you can split your sources into logical projects:

```yaml
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "default_collection"
  # ... other global settings

projects:
  # Documentation project
  docs-project:
    project_id: "docs-project"
    display_name: "Documentation"
    description: "User and developer documentation"
    collection_name: "docs_collection"
    
    sources:
      git:
        docs-repo:
          base_url: "https://github.com/company/docs.git"
          # ... git config
  
  # Knowledge base project
  kb-project:
    project_id: "kb-project"
    display_name: "Knowledge Base"
    description: "Internal knowledge base and wiki"
    collection_name: "kb_collection"
    
    sources:
      confluence:
        company-wiki:
          base_url: "https://company.atlassian.net/wiki"
          # ... confluence config
```

## Migration Checklist

- [ ] **Backup your existing configuration** - Save a copy of your current `config.yaml`
- [ ] **Update global section** - Change `global:` to `global_config:`
- [ ] **Create project structure** - Wrap your sources in a project definition
- [ ] **Choose project details** - Set meaningful `project_id`, `display_name`, and `description`
- [ ] **Decide on collection strategy** - Keep existing collection name or use default
- [ ] **Test the configuration** - Validate the new configuration works
- [ ] **Update environment variables** - Ensure all required environment variables are set
- [ ] **Run fresh ingestion** - Perform a fresh ingestion with the new configuration

## Common Migration Issues

### Issue: "Legacy configuration format detected"

**Solution**: You're still using the old format. Follow the migration steps above.

### Issue: "Project configuration validation failed"

**Solution**: Ensure each project has required fields:

- `project_id` (string)
- `display_name` (string)
- `sources` (object with at least one source type)

### Issue: "Collection name conflicts"

**Solution**: If using multiple projects with the same collection name, consider:

- Using different collection names per project
- Using the global default collection
- Performing fresh ingestion to avoid conflicts

### Issue: "Environment variables not found"

**Solution**: Ensure all environment variables referenced in your configuration are set:

```bash
export GITHUB_TOKEN="your_token_here"
export CONFLUENCE_TOKEN="your_token_here"
export CONFLUENCE_EMAIL="your_email_here"
```

## Getting Help

If you encounter issues during migration:

1. **Check the logs** - Look for specific error messages
2. **Validate your YAML** - Ensure proper YAML syntax
3. **Review the template** - Compare with `conf/config.template.yaml`
4. **Test incrementally** - Start with a minimal configuration and add sources gradually

## Benefits After Migration

Once migrated, you'll have access to:

- **Project-specific processing** - Process documents for specific projects
- **Better organization** - Logical separation of different content types
- **Enhanced metadata** - Project information included in all documents
- **Flexible collections** - Use different collections for different projects
- **Future features** - Access to upcoming multi-project search capabilities

## Example Commands After Migration

```bash
# Process all projects
qdrant-loader ingest

# Process specific project
qdrant-loader ingest --project-id docs-project

# List available projects
qdrant-loader projects list

# Get project information
qdrant-loader projects info docs-project
```

---

**Note**: The legacy configuration format is no longer supported. You must migrate to the new multi-project format to use qdrant-loader v2.0 and later.
