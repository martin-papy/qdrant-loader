#!/bin/bash
set -e

# Validate required files with clear error messages
if [ ! -f "config.yaml" ]; then
    echo "ERROR: config.yaml not found in /qdrant-loader" >&2
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "ERROR: .env not found in /qdrant-loader" >&2
    exit 1
fi

# Allow environment variable overrides
export _ENTRYPOINT_HOST="${WEBHOOK_HOST:-0.0.0.0}"
export _ENTRYPOINT_PORT="${WEBHOOK_PORT:-8081}"
export _ENTRYPOINT_LOG_LEVEL="${WEBHOOK_LOG_LEVEL:-INFO}"

# Run the webhook command
exec python -c "
import asyncio, os
from pathlib import Path
from qdrant_loader.cli.commands.webhook_cmd import run_webhook_command

asyncio.run(run_webhook_command(
    workspace=None,
    config=Path('config.yaml'),
    env=Path('.env'),
    host=os.environ['_ENTRYPOINT_HOST'],
    port=int(os.environ['_ENTRYPOINT_PORT']),
    log_level=os.environ['_ENTRYPOINT_LOG_LEVEL'],
))
"
