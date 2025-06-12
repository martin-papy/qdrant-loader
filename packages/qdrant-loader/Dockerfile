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

# Copy pyproject.toml first for dependency caching
COPY pyproject.toml ./

# Install dependencies using local pip cache
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --upgrade pip && \
    pip install -e .

# Copy source code
COPY src/ ./src/
COPY README.md ./
COPY __init__.py ./

# Download spaCy models with error handling
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    python -m spacy download en_core_web_sm || \
    echo "Warning: Could not download spaCy model. Install manually if needed."

# Create non-root user
RUN groupadd -r qdrant --gid=1000 && \
    useradd -r -g qdrant --uid=1000 --home-dir=/app --shell=/bin/bash qdrant && \
    mkdir -p /app/data /app/logs /app/config && \
    chown -R qdrant:qdrant /app && \
    chmod 755 /app /app/data /app/logs /app/config

# Switch to non-root user
USER qdrant

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD qdrant-loader --help > /dev/null 2>&1 || exit 1

# Expose port
EXPOSE 8000

# Set default command
ENTRYPOINT ["qdrant-loader"]
CMD ["--help"] 