# Workspace Mode Configuration

This guide covers how to configure QDrant Loader for different workspace scenarios, from single projects to complex multi-project team environments. Workspace mode determines how QDrant Loader organizes and manages your data across different projects and contexts.

## 🎯 Overview

Workspace mode in QDrant Loader allows you to organize your knowledge base according to your project structure and team needs. Whether you're working on a single project, managing multiple projects, or collaborating with a team, the right workspace configuration ensures optimal organization and searchability.

### Workspace Types

```
📁 Single Project    - One project, one collection
📁 Multi-Project     - Multiple projects, organized collections
📁 Team Workspace    - Shared team knowledge with access control
📁 Hybrid Workspace  - Mix of personal and shared collections
```

## 🏗️ Single Project Workspace

### Basic Single Project Setup

Perfect for individual developers or small teams working on one main project.

```yaml
# qdrant-loader.yaml - Single project configuration
workspace:
  mode: "single"
  name: "my-awesome-project"
  
qdrant:
  url: "http://localhost:6333"
  collection_name: "my_awesome_project_docs"
  
data_sources:
  git:
    repositories:
      - url: "https://github.com/company/my-awesome-project"
        branch: "main"
        include_patterns:
          - "docs/**"
          - "*.md"
          - "README*"
  
  confluence:
    base_url: "https://company.atlassian.net"
    username: "user@company.com"
    api_token: "${CONFLUENCE_API_TOKEN}"
    spaces: ["PROJ"]

processing:
  chunk_size: 1000
  chunk_overlap: 200
  metadata:
    project: "my-awesome-project"
    workspace: "single"
```

### Single Project with Multiple Sources

```yaml
# qdrant-loader.yaml - Single project with multiple data sources
workspace:
  mode: "single"
  name: "documentation-hub"
  description: "Central documentation for our main product"
  
qdrant:
  url: "http://localhost:6333"
  collection_name: "documentation_hub"
  
data_sources:
  # Main project repository
  git:
    repositories:
      - url: "https://github.com/company/main-product"
        branch: "main"
        name: "main-repo"
        include_patterns:
          - "docs/**"
          - "*.md"
          - "api/**/*.yaml"
      
      # Documentation repository
      - url: "https://github.com/company/product-docs"
        branch: "main"
        name: "docs-repo"
        include_patterns:
          - "**/*.md"
          - "**/*.rst"
  
  # Confluence documentation
  confluence:
    base_url: "https://company.atlassian.net"
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
    spaces: ["DOCS", "API", "GUIDES"]
  
  # JIRA for requirements and issues
  jira:
    base_url: "https://company.atlassian.net"
    username: "${JIRA_USERNAME}"
    api_token: "${JIRA_API_TOKEN}"
    projects: ["PROD"]
    settings:
      issue_types: ["Story", "Epic", "Bug"]
      include_comments: true

processing:
  metadata:
    project: "documentation-hub"
    workspace: "single"
    tags:
      - "documentation"
      - "main-product"
```

## 🏢 Multi-Project Workspace

### Basic Multi-Project Setup

Ideal for teams managing multiple related projects with separate but connected knowledge bases.

```yaml
# qdrant-loader.yaml - Multi-project configuration
workspace:
  mode: "multi"
  name: "company-projects"
  
  # Project definitions
  projects:
    frontend:
      name: "Frontend Application"
      collection: "frontend_docs"
      description: "React frontend application documentation"
      
    backend:
      name: "Backend API"
      collection: "backend_docs"
      description: "Node.js backend API documentation"
      
    mobile:
      name: "Mobile App"
      collection: "mobile_docs"
      description: "React Native mobile application"
      
    shared:
      name: "Shared Resources"
      collection: "shared_docs"
      description: "Common documentation and resources"

qdrant:
  url: "http://localhost:6333"
  # Collection names will be auto-generated from project definitions

# Global data sources (applied to all projects)
global_data_sources:
  confluence:
    base_url: "https://company.atlassian.net"
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
    spaces: ["COMPANY", "GENERAL"]

# Project-specific data sources
project_data_sources:
  frontend:
    git:
      repositories:
        - url: "https://github.com/company/frontend-app"
          branch: "main"
          include_patterns:
            - "docs/**"
            - "*.md"
            - "src/**/*.md"
    confluence:
      spaces: ["FRONTEND", "UI"]
  
  backend:
    git:
      repositories:
        - url: "https://github.com/company/backend-api"
          branch: "main"
          include_patterns:
            - "docs/**"
            - "*.md"
            - "api/**/*.yaml"
    confluence:
      spaces: ["BACKEND", "API"]
    jira:
      projects: ["BACK"]
  
  mobile:
    git:
      repositories:
        - url: "https://github.com/company/mobile-app"
          branch: "main"
          include_patterns:
            - "docs/**"
            - "*.md"
    confluence:
      spaces: ["MOBILE", "APP"]
  
  shared:
    git:
      repositories:
        - url: "https://github.com/company/shared-docs"
          branch: "main"
        - url: "https://github.com/company/design-system"
          branch: "main"
          include_patterns:
            - "docs/**"
            - "*.md"
    confluence:
      spaces: ["DESIGN", "STANDARDS", "PROCESS"]

processing:
  # Global processing settings
  chunk_size: 1000
  chunk_overlap: 200
  
  # Project-specific processing
  project_settings:
    frontend:
      metadata:
        project: "frontend"
        team: "ui-team"
        technology: "react"
    
    backend:
      metadata:
        project: "backend"
        team: "api-team"
        technology: "nodejs"
    
    mobile:
      metadata:
        project: "mobile"
        team: "mobile-team"
        technology: "react-native"
    
    shared:
      metadata:
        project: "shared"
        team: "all"
        type: "shared-resource"
```

### Advanced Multi-Project with Cross-References

```yaml
# qdrant-loader.yaml - Advanced multi-project with cross-references
workspace:
  mode: "multi"
  name: "enterprise-platform"
  
  # Project hierarchy
  projects:
    platform:
      name: "Core Platform"
      collection: "platform_docs"
      parent: null
      children: ["auth", "api-gateway", "monitoring"]
      
    auth:
      name: "Authentication Service"
      collection: "auth_docs"
      parent: "platform"
      dependencies: ["platform"]
      
    api-gateway:
      name: "API Gateway"
      collection: "gateway_docs"
      parent: "platform"
      dependencies: ["platform", "auth"]
      
    monitoring:
      name: "Monitoring & Observability"
      collection: "monitoring_docs"
      parent: "platform"
      dependencies: ["platform"]
      
    frontend:
      name: "Web Frontend"
      collection: "frontend_docs"
      dependencies: ["auth", "api-gateway"]
      
    mobile:
      name: "Mobile Apps"
      collection: "mobile_docs"
      dependencies: ["auth", "api-gateway"]

  # Cross-project search configuration
  cross_project:
    enabled: true
    # When searching in a project, also search dependencies
    include_dependencies: true
    # Weight for dependency results (0.0-1.0)
    dependency_weight: 0.3

qdrant:
  url: "http://localhost:6333"

# Project-specific configurations
project_data_sources:
  platform:
    git:
      repositories:
        - url: "https://github.com/company/platform-core"
          branch: "main"
    confluence:
      spaces: ["PLATFORM", "ARCH"]
    jira:
      projects: ["PLAT"]
  
  auth:
    git:
      repositories:
        - url: "https://github.com/company/auth-service"
          branch: "main"
    confluence:
      spaces: ["AUTH", "SECURITY"]
    jira:
      projects: ["AUTH"]
  
  # ... other projects

mcp_server:
  # Multi-project search configuration
  search:
    # Default project for searches (if not specified)
    default_project: "platform"
    
    # Enable project-aware search
    project_aware: true
    
    # Include project context in results
    include_project_context: true
    
    # Cross-project search settings
    cross_project:
      enabled: true
      max_projects: 3
      similarity_threshold: 0.6
```

## 👥 Team Workspace

### Shared Team Environment

Perfect for teams that need shared knowledge with individual workspaces.

```yaml
# qdrant-loader.yaml - Team workspace configuration
workspace:
  mode: "team"
  name: "engineering-team"
  
  # Team configuration
  team:
    name: "Engineering Team"
    members:
      - username: "alice"
        role: "lead"
        projects: ["platform", "auth", "frontend"]
      - username: "bob"
        role: "developer"
        projects: ["frontend", "mobile"]
      - username: "charlie"
        role: "developer"
        projects: ["platform", "auth"]
    
    # Shared collections
    shared_collections:
      - name: "team_knowledge"
        description: "Shared team documentation"
        access: "all"
      - name: "architecture_docs"
        description: "System architecture documentation"
        access: "lead"
      - name: "onboarding"
        description: "Team onboarding materials"
        access: "all"
    
    # Personal collections
    personal_collections:
      enabled: true
      prefix: "personal_"
      # Each team member gets: personal_alice, personal_bob, etc.

qdrant:
  url: "http://qdrant.team.local:6333"

# Shared data sources (accessible to all team members)
shared_data_sources:
  git:
    repositories:
      - url: "https://github.com/company/team-docs"
        branch: "main"
        collection: "team_knowledge"
      - url: "https://github.com/company/architecture"
        branch: "main"
        collection: "architecture_docs"
        access_control:
          roles: ["lead"]
  
  confluence:
    base_url: "https://company.atlassian.net"
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
    spaces: ["TEAM", "PROCESS", "STANDARDS"]
    collection: "team_knowledge"

# Personal data sources (user-specific)
personal_data_sources:
  git:
    repositories:
      # Users can add their own repositories
      - url: "${USER_REPO_URL}"
        branch: "main"
        collection: "personal_${USER}"
        include_patterns:
          - "notes/**"
          - "personal/**"
          - "drafts/**"
  
  local_files:
    paths:
      - "~/Documents/work-notes"
      - "~/Projects/personal-docs"
    collection: "personal_${USER}"

# Access control
access_control:
  enabled: true
  
  # Collection-level permissions
  collections:
    team_knowledge:
      read: ["all"]
      write: ["all"]
    
    architecture_docs:
      read: ["lead", "senior"]
      write: ["lead"]
    
    onboarding:
      read: ["all"]
      write: ["lead", "hr"]
    
    "personal_*":
      read: ["owner"]
      write: ["owner"]

mcp_server:
  # Team-aware search
  search:
    # Include user context in searches
    user_aware: true
    
    # Default search scope
    default_scope: "accessible"  # all, shared, personal, accessible
    
    # Search result personalization
    personalization:
      enabled: true
      # Boost results from user's projects
      project_boost: 1.2
      # Boost results from user's recent activity
      recency_boost: 1.1
```

### Team Workspace with Role-Based Access

```yaml
# qdrant-loader.yaml - Role-based team workspace
workspace:
  mode: "team"
  name: "product-development"
  
  # Role definitions
  roles:
    admin:
      permissions: ["read", "write", "manage", "configure"]
      collections: ["*"]
    
    lead:
      permissions: ["read", "write", "manage"]
      collections: ["team_*", "project_*", "architecture_*"]
    
    senior:
      permissions: ["read", "write"]
      collections: ["team_*", "project_*"]
    
    developer:
      permissions: ["read", "write"]
      collections: ["team_knowledge", "project_docs", "personal_*"]
    
    intern:
      permissions: ["read"]
      collections: ["team_knowledge", "onboarding", "personal_*"]

  # Team structure
  team:
    name: "Product Development Team"
    departments:
      engineering:
        lead: "alice"
        members: ["bob", "charlie", "diana"]
        collections: ["eng_docs", "tech_specs"]
      
      design:
        lead: "eve"
        members: ["frank"]
        collections: ["design_docs", "ui_specs"]
      
      product:
        lead: "grace"
        members: ["henry"]
        collections: ["product_docs", "requirements"]

# Department-specific data sources
department_data_sources:
  engineering:
    git:
      repositories:
        - url: "https://github.com/company/backend"
        - url: "https://github.com/company/frontend"
    confluence:
      spaces: ["ENG", "TECH"]
    collection: "eng_docs"
  
  design:
    git:
      repositories:
        - url: "https://github.com/company/design-system"
    confluence:
      spaces: ["DESIGN", "UX"]
    local_files:
      paths: ["/shared/design-assets"]
    collection: "design_docs"
  
  product:
    confluence:
      spaces: ["PRODUCT", "REQUIREMENTS"]
    jira:
      projects: ["PROD"]
      settings:
        issue_types: ["Epic", "Story"]
    collection: "product_docs"

# Workflow-based collections
workflow_collections:
  sprint_planning:
    sources:
      - collection: "product_docs"
        filter: "type:requirement"
      - collection: "eng_docs"
        filter: "type:technical-spec"
    access: ["lead", "senior"]
  
  code_review:
    sources:
      - collection: "eng_docs"
        filter: "type:code-review OR type:best-practice"
    access: ["developer", "senior", "lead"]
  
  onboarding:
    sources:
      - collection: "team_knowledge"
        filter: "type:onboarding"
      - collection: "process_docs"
    access: ["all"]
```

## 🔄 Hybrid Workspace

### Mixed Personal and Shared Environment

Combines personal productivity with team collaboration.

```yaml
# qdrant-loader.yaml - Hybrid workspace configuration
workspace:
  mode: "hybrid"
  name: "flexible-workspace"
  
  # Workspace layers
  layers:
    personal:
      enabled: true
      collection_prefix: "personal_"
      isolation: "strict"  # strict, loose, none
    
    team:
      enabled: true
      collection_prefix: "team_"
      sharing: "opt-in"  # opt-in, opt-out, automatic
    
    company:
      enabled: true
      collection_prefix: "company_"
      access: "read-only"  # read-only, read-write

# Layer-specific configurations
layer_configurations:
  personal:
    data_sources:
      local_files:
        paths:
          - "~/Documents/notes"
          - "~/Projects/personal"
      git:
        repositories:
          - url: "${PERSONAL_REPO}"
            branch: "main"
    
    processing:
      chunk_size: 500  # Smaller chunks for personal notes
      metadata:
        layer: "personal"
        private: true
  
  team:
    data_sources:
      git:
        repositories:
          - url: "https://github.com/team/shared-docs"
      confluence:
        spaces: ["TEAM"]
    
    processing:
      metadata:
        layer: "team"
        shareable: true
  
  company:
    data_sources:
      confluence:
        spaces: ["COMPANY", "POLICIES", "STANDARDS"]
        settings:
          read_only: true
    
    processing:
      metadata:
        layer: "company"
        official: true

# Cross-layer search configuration
cross_layer_search:
  enabled: true
  
  # Search priority (higher number = higher priority)
  layer_priority:
    personal: 3
    team: 2
    company: 1
  
  # Context mixing
  context_mixing:
    enabled: true
    # Include context from other layers
    max_context_layers: 2

mcp_server:
  search:
    # Layer-aware search
    layer_aware: true
    
    # Default search layers
    default_layers: ["personal", "team"]
    
    # Layer-specific result limits
    layer_limits:
      personal: 5
      team: 8
      company: 3
```

## ⚙️ Workspace Management

### Workspace Initialization

```bash
# Initialize single project workspace
qdrant-loader workspace init --mode single --name "my-project"

# Initialize multi-project workspace
qdrant-loader workspace init --mode multi --name "company-projects"

# Initialize team workspace
qdrant-loader workspace init --mode team --name "engineering-team"

# Initialize hybrid workspace
qdrant-loader workspace init --mode hybrid --name "flexible-workspace"
```

### Workspace Operations

```bash
# Show workspace status
qdrant-loader workspace status

# List all collections in workspace
qdrant-loader workspace collections

# Switch between projects (multi-project mode)
qdrant-loader workspace switch frontend

# Add new project to workspace
qdrant-loader workspace add-project backend \
  --collection backend_docs \
  --description "Backend API documentation"

# Remove project from workspace
qdrant-loader workspace remove-project old-project

# Backup workspace configuration
qdrant-loader workspace backup --output workspace-backup.yaml

# Restore workspace from backup
qdrant-loader workspace restore --input workspace-backup.yaml
```

### Collection Management

```bash
# Create new collection
qdrant-loader collection create shared_resources \
  --description "Shared team resources"

# List collections with access info
qdrant-loader collection list --show-access

# Set collection permissions
qdrant-loader collection permissions shared_resources \
  --read "all" \
  --write "lead,senior"

# Merge collections
qdrant-loader collection merge source_collection target_collection

# Archive old collection
qdrant-loader collection archive old_project_docs
```

## 🔍 Workspace-Aware Search

### Search Scoping

```bash
# Search in current project only
qdrant-loader search "API documentation" --scope current

# Search across all accessible collections
qdrant-loader search "deployment guide" --scope all

# Search in specific project
qdrant-loader search "authentication" --project auth

# Search in multiple projects
qdrant-loader search "database schema" --projects backend,platform

# Search with layer filtering (hybrid mode)
qdrant-loader search "meeting notes" --layers personal,team
```

### MCP Server Search Configuration

```yaml
mcp_server:
  search:
    # Workspace-aware search settings
    workspace_aware: true
    
    # Default search behavior
    default_search:
      scope: "accessible"  # current, accessible, all
      include_metadata: true
      max_results_per_collection: 5
    
    # Search result aggregation
    aggregation:
      # Group results by project/collection
      group_by: "collection"
      
      # Sort groups by relevance
      sort_groups: true
      
      # Include collection context in results
      include_collection_context: true
    
    # Search personalization
    personalization:
      enabled: true
      
      # Boost results from user's active projects
      active_project_boost: 1.3
      
      # Boost recent documents
      recency_boost: 1.1
      
      # Boost frequently accessed documents
      frequency_boost: 1.2
```

## 📊 Workspace Analytics

### Usage Tracking

```yaml
workspace:
  analytics:
    enabled: true
    
    # Track search patterns
    search_analytics:
      enabled: true
      retention_days: 90
      
      # Track popular queries
      popular_queries: true
      
      # Track search success rates
      success_tracking: true
    
    # Track collection usage
    collection_analytics:
      enabled: true
      
      # Track access patterns
      access_patterns: true
      
      # Track content freshness
      freshness_tracking: true
    
    # User activity tracking
    user_analytics:
      enabled: true
      
      # Track active users
      active_users: true
      
      # Track collaboration patterns
      collaboration_tracking: true

# Analytics reporting
analytics_reporting:
  # Generate daily reports
  daily_reports:
    enabled: true
    recipients: ["team-leads@company.com"]
    
  # Generate weekly summaries
  weekly_summaries:
    enabled: true
    recipients: ["management@company.com"]
    
  # Custom dashboards
  dashboards:
    team_dashboard:
      url: "http://grafana.company.com/team-workspace"
      metrics:
        - "search_volume"
        - "collection_usage"
        - "user_activity"
```

## 🔗 Related Documentation

- **[Environment Variables Reference](./environment-variables.md)** - Environment variable configuration
- **[Configuration File Reference](./config-file-reference.md)** - YAML configuration options
- **[Security Considerations](./security-considerations.md)** - Security best practices
- **[Multi-Project Setup](../workflow-examples/multi-project-setup.md)** - Practical multi-project examples

## 📋 Workspace Configuration Checklist

- [ ] **Workspace mode** selected based on your needs
- [ ] **Project structure** defined (for multi-project mode)
- [ ] **Team roles** configured (for team mode)
- [ ] **Access control** set up appropriately
- [ ] **Data sources** configured for each project/layer
- [ ] **Collection naming** follows consistent patterns
- [ ] **Search configuration** optimized for your workspace
- [ ] **Analytics** enabled for usage tracking
- [ ] **Backup strategy** implemented
- [ ] **Team onboarding** process documented

---

**Workspace configuration complete!** 🎉

Your QDrant Loader workspace is now configured to match your project structure and team needs. This provides organized, scalable knowledge management that grows with your organization.
