# syntax=docker/dockerfile:1.7
# Enable advanced BuildKit features for optimal build performance and security

FROM python:3.12-slim

# Set environment variables for optimal Python runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# Install system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy pyproject.toml and source files first for dependency caching and build
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

# Install dependencies using local pip cache
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --upgrade pip && \
    pip install -e .

# Ensure git is in PATH and set GIT_PYTHON_GIT_EXECUTABLE
ENV PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git

# Create non-root user
RUN groupadd -r mcpserver --gid=1001 && \
    useradd -r -g mcpserver --uid=1001 --home-dir=/app --shell=/bin/bash mcpserver && \
    mkdir -p /app/data /app/logs /app/config && \
    chown -R mcpserver:mcpserver /app && \
    chmod 755 /app /app/data /app/logs /app/config

# Switch to non-root user
USER mcpserver

# Health check - same as docker-compose.yml
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import qdrant_loader_mcp_server; print('OK')" || exit 1

# Expose port
EXPOSE 3000

# Set default command - keep container running
ENTRYPOINT ["tail"]
CMD ["-f", "/dev/null"] 