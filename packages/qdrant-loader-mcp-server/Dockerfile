# syntax=docker/dockerfile:1.4

# Build stage
FROM python:3.12-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy pyproject.toml first for better dependency caching
COPY pyproject.toml ./

# Install build tools
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel build

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Build all wheels (dependencies + package) with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/wheels .

# Runtime stage
FROM python:3.12-slim as runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mcpserver && useradd -r -g mcpserver -s /bin/bash mcpserver

# Set working directory
WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /wheels /wheels

# Install Python packages from wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install /wheels/*.whl && \
    rm -rf /wheels

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R mcpserver:mcpserver /app

# Switch to non-root user
USER mcpserver

# Health check for MCP server
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD mcp-qdrant-loader --help > /dev/null || exit 1

# Expose MCP server port
EXPOSE 3000

# Set default command
ENTRYPOINT ["mcp-qdrant-loader"]
CMD ["--help"] 