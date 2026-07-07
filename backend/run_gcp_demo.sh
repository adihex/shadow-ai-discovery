#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export SHADOW_AI_GCP_PROJECT_ID=shadow-ai-agent-501704
export SHADOW_AI_DATABASE_PATH="$(pwd)/database-gcp-demo.db"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
