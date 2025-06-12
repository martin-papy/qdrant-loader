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
COPY __init__.py ./

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
RUN groupadd -r qdrant && useradd -r -g qdrant -s /bin/bash qdrant

# Set working directory
WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /wheels /wheels

# Install Python packages from wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install /wheels/*.whl && \
    rm -rf /wheels

# Download spaCy models (commonly used)
RUN python -m spacy download en_core_web_sm || true

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R qdrant:qdrant /app

# Copy configuration files if they exist (optional)
# Note: This step is optional and will be skipped if conf/ directory doesn't exist

# Switch to non-root user
USER qdrant

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD qdrant-loader --help > /dev/null || exit 1

# Expose default port (if applicable)
EXPOSE 8000

# Set default command
ENTRYPOINT ["qdrant-loader"]
CMD ["--help"] 