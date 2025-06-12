# Development Workflow

This document explains how to set up and use the development environment for qdrant-loader.

## Development vs Production Docker Setup

### Production Setup (`docker-compose.yml`)
- **Code is baked into images**: Source code is copied during build time
- **Requires rebuild**: Any code changes require rebuilding Docker images
- **Optimized for deployment**: Smaller, self-contained images
- **Use case**: Production deployments, CI/CD, testing final builds

```bash
# Production setup
make docker-build    # Build images with code baked in
make docker-up       # Start production environment
```

### Development Setup (`docker-compose.dev.yml`)
- **Live code mounting**: Source code is mounted from host filesystem
- **Immediate updates**: Code changes are reflected immediately (like `pip install -e`)
- **Development tools**: Debug logging, relaxed health checks
- **Use case**: Active development, debugging, rapid iteration

```bash
# Development setup
make docker-dev      # Build images + start development environment
make docker-up-dev   # Start development environment (if already built)
```

## Development Workflow

### 1. Initial Setup
```bash
# Set up environment
make env-setup

# Build Docker images (one time)
make docker-build

# Start development environment
make docker-up-dev
```

### 2. Active Development
With the development environment running:

- **Edit code locally** in `packages/qdrant-loader/src/` or `packages/qdrant-loader-mcp-server/src/`
- **Changes are immediately available** in the containers (no rebuild needed)
- **Test your changes** by running commands in the containers

```bash
# Test your changes
make docker-shell-loader-dev
# Inside container:
qdrant-loader --help  # Your changes are live!

# Or test MCP server
make docker-shell-mcp-dev
# Inside container:
mcp-qdrant-loader --help  # Your changes are live!
```

### 3. Package Dependencies
If you modify `pyproject.toml` (add/remove dependencies):

```bash
# Reload packages with new dependencies
make docker-reload-dev

# Or restart the development environment
make docker-restart-dev
```

### 4. Monitoring and Debugging
```bash
# View logs from all services
make docker-logs-dev

# View logs from specific service
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f qdrant-loader

# Check container status
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# Monitor resource usage
make docker-stats
```

## Key Development Features

### Live Code Mounting
- **Source code**: `./packages/*/src` → `/app/src` (read-write)
- **Configuration**: `./packages/*/pyproject.toml` → `/app/pyproject.toml` (read-only)
- **Data persistence**: `./data`, `./logs`, `./config` mounted for persistence

### Development Environment Variables
- `PYTHONPATH=/app/src:/app` - Ensures Python finds your live code
- `*_ENV=development` - Signals development mode to applications
- `*_DEBUG=true` - Enables debug features
- `*_LOG_LEVEL=DEBUG` - Verbose logging for development

### Editable Installation
Containers automatically run `pip install -e .` on startup, making your packages available in development mode.

## Common Commands

```bash
# Development lifecycle
make docker-dev              # Build and start development environment
make docker-up-dev-logs      # Start and follow logs
make docker-down-dev         # Stop development environment
make docker-restart-dev      # Restart development environment

# Development tools
make docker-shell-loader-dev # Shell into qdrant-loader container
make docker-shell-mcp-dev    # Shell into MCP server container
make docker-reload-dev       # Reload packages after dependency changes
make docker-logs-dev         # Follow logs from all services

# Monitoring
make docker-stats            # Resource usage
make docker-inspect-resources # Check resource limits
```

## Troubleshooting

### Code changes not reflected
1. Ensure you're using the development environment: `make docker-up-dev`
2. Check that volumes are mounted correctly: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml config`
3. Restart if needed: `make docker-restart-dev`

### Import errors after dependency changes
1. Reload packages: `make docker-reload-dev`
2. Or restart environment: `make docker-restart-dev`

### Container won't start
1. Check logs: `make docker-logs-dev`
2. Verify environment setup: `make env-check`
3. Rebuild if needed: `make docker-build`

## Best Practices

1. **Use development environment for coding**: Always use `make docker-dev` when actively developing
2. **Test with production setup**: Periodically test with `make docker-up` to ensure production compatibility
3. **Keep dependencies in sync**: Update `pyproject.toml` and run `make docker-reload-dev`
4. **Monitor resources**: Use `make docker-stats` to ensure containers aren't resource-constrained
5. **Clean up regularly**: Use `make docker-clean` to free up disk space 