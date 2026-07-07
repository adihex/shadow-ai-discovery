#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Shadow AI Discovery — Demo CLI
#
# Usage:
#   ./demo.sh mock          Start backend (mock data) + frontend
#   ./demo.sh live          Start backend (live GCP project) + frontend
#   ./demo.sh infra-up      Provision the GCP demo project via Terraform
#   ./demo.sh infra-down    Tear down the GCP demo resources
#   ./demo.sh test          Run the full pytest suite
#   ./demo.sh stop          Stop all running demo processes
#   ./demo.sh status        Show running demo processes
# ─────────────────────────────────────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
INFRA_DIR="$ROOT_DIR/infra"
PID_DIR="$ROOT_DIR/.demo-pids"

# Defaults — override via environment or infra/variables.tf
GCP_PROJECT_ID="${SHADOW_AI_GCP_PROJECT_ID:-shadow-ai-agent-501704}"
GCP_REGION="${SHADOW_AI_GCP_REGION:-us-central1}"
BACKEND_PORT="${SHADOW_AI_BACKEND_PORT:-8000}"
FRONTEND_PORT="${SHADOW_AI_FRONTEND_PORT:-5173}"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

banner() {
  echo ""
  echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${CYAN}${BOLD}  🛡️  Shadow AI Discovery — Demo CLI${NC}"
  echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
}

info()    { echo -e "${GREEN}▸${NC} $*"; }
warn()    { echo -e "${YELLOW}▸${NC} $*"; }
err()     { echo -e "${RED}✖${NC} $*" >&2; }
section() { echo -e "\n${BOLD}$*${NC}"; }

ensure_deps() {
  command -v uv   >/dev/null 2>&1 || { err "uv not found. Install: https://docs.astral.sh/uv/"; exit 1; }
  command -v node >/dev/null 2>&1 || { err "node not found. Install Node.js 18+"; exit 1; }
  command -v npm  >/dev/null 2>&1 || { err "npm not found. Install Node.js 18+"; exit 1; }
}

ensure_terraform() {
  command -v terraform >/dev/null 2>&1 || { err "terraform not found. Install: https://developer.hashicorp.com/terraform/install"; exit 1; }
}

ensure_gcloud() {
  command -v gcloud >/dev/null 2>&1 || { err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"; exit 1; }
}

mkdir -p "$PID_DIR"

save_pid() {
  echo "$2" > "$PID_DIR/$1.pid"
}

read_pid() {
  local f="$PID_DIR/$1.pid"
  [[ -f "$f" ]] && cat "$f" || echo ""
}

kill_by_name() {
  local pid
  pid=$(read_pid "$1")
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    info "Stopped $1 (PID $pid)"
  fi
  rm -f "$PID_DIR/$1.pid"
}

stop_all() {
  section "Stopping demo processes..."
  kill_by_name backend
  kill_by_name frontend
  # Also kill by port as a fallback
  lsof -ti ":$BACKEND_PORT" 2>/dev/null | xargs -r kill 2>/dev/null || true
  lsof -ti ":$FRONTEND_PORT" 2>/dev/null | xargs -r kill 2>/dev/null || true
  info "All demo processes stopped."
}

show_status() {
  section "Demo Process Status"
  for name in backend frontend; do
    local pid
    pid=$(read_pid "$name")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      info "$name: ${GREEN}running${NC} (PID $pid)"
    else
      warn "$name: ${YELLOW}not running${NC}"
    fi
  done
}

start_backend() {
  local mode="$1"  # "mock" or "live"

  section "Starting backend ($mode mode)..."

  cd "$BACKEND_DIR"

  # Sync dependencies
  info "Syncing Python dependencies..."
  uv sync --quiet 2>/dev/null || uv sync

  # Set environment variables
  local db_path="$BACKEND_DIR/database.db"
  export SHADOW_AI_DATABASE_PATH="$db_path"

  if [[ "$mode" == "live" ]]; then
    export SHADOW_AI_GCP_PROJECT_ID="$GCP_PROJECT_ID"
    export SHADOW_AI_GCP_REGIONS="$GCP_REGION"
    db_path="$BACKEND_DIR/database-gcp-demo.db"
    export SHADOW_AI_DATABASE_PATH="$db_path"

    # Check for GCP credentials
    if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
      info "No GOOGLE_APPLICATION_CREDENTIALS set. Attempting ADC impersonation..."
      local scanner_sa="shadow-ai-scanner@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
      if gcloud auth application-default print-access-token --impersonate-service-account="$scanner_sa" >/dev/null 2>&1; then
        info "Using impersonated ADC as $scanner_sa"
      else
        warn "Could not impersonate scanner SA. Falling back to user ADC."
        warn "Run: gcloud auth application-default login"
      fi
    else
      info "Using service account key: $GOOGLE_APPLICATION_CREDENTIALS"
    fi

    info "GCP Project: $GCP_PROJECT_ID"
    info "GCP Region:  $GCP_REGION"
    info "Database:    $db_path"
  else
    info "Running in mock/demo mode (no GCP credentials needed)"
    info "Database: $db_path"
  fi

  # Kill any existing backend
  kill_by_name backend
  lsof -ti ":$BACKEND_PORT" 2>/dev/null | xargs -r kill 2>/dev/null || true
  sleep 0.5

  # Start uvicorn
  uv run uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$ROOT_DIR/.demo-backend.log" 2>&1 &
  save_pid backend $!

  info "Backend starting on http://localhost:$BACKEND_PORT"
  info "Swagger docs: http://localhost:$BACKEND_PORT/docs"
  info "Logs: $ROOT_DIR/.demo-backend.log"

  # Wait for it to become healthy
  local retries=0
  while ! curl -sf "http://localhost:$BACKEND_PORT/api/scan/history" >/dev/null 2>&1; do
    retries=$((retries + 1))
    if [[ $retries -gt 30 ]]; then
      err "Backend failed to start within 30s. Check logs: $ROOT_DIR/.demo-backend.log"
      tail -20 "$ROOT_DIR/.demo-backend.log" 2>/dev/null || true
      exit 1
    fi
    sleep 1
  done
  info "Backend is healthy ✓"
}

start_frontend() {
  section "Starting frontend dashboard..."

  cd "$FRONTEND_DIR"

  # Install npm dependencies if needed
  if [[ ! -d "node_modules" ]]; then
    info "Installing npm dependencies..."
    npm install --silent 2>/dev/null || npm install
  fi

  # Kill any existing frontend
  kill_by_name frontend

  export VITE_API_BASE_URL="http://localhost:$BACKEND_PORT/api"
  npx vite --port "$FRONTEND_PORT" --host \
    > "$ROOT_DIR/.demo-frontend.log" 2>&1 &
  save_pid frontend $!

  info "Frontend starting on http://localhost:$FRONTEND_PORT"
  info "Logs: $ROOT_DIR/.demo-frontend.log"

  # Wait for it to become ready
  local retries=0
  while ! curl -sf "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; do
    retries=$((retries + 1))
    if [[ $retries -gt 30 ]]; then
      warn "Frontend may still be compiling. Check: http://localhost:$FRONTEND_PORT"
      break
    fi
    sleep 1
  done
  info "Frontend is ready ✓"
}

cmd_mock() {
  banner
  ensure_deps
  start_backend mock
  start_frontend
  section "🎉 Demo Ready (Mock Mode)"
  info "Dashboard: http://localhost:$FRONTEND_PORT"
  info "API:       http://localhost:$BACKEND_PORT/docs"
  echo ""
  info "Trigger a scan from the dashboard or: curl -X POST http://localhost:$BACKEND_PORT/api/scan"
  info "Stop with: ./demo.sh stop"
  echo ""
}

cmd_live() {
  banner
  ensure_deps
  ensure_gcloud
  start_backend live
  start_frontend
  section "🎉 Demo Ready (Live GCP Mode)"
  info "Dashboard: http://localhost:$FRONTEND_PORT"
  info "API:       http://localhost:$BACKEND_PORT/docs"
  info "Project:   $GCP_PROJECT_ID"
  echo ""
  info "Trigger a scan from the dashboard or: curl -X POST http://localhost:$BACKEND_PORT/api/scan"
  info "Stop with: ./demo.sh stop"
  echo ""
}

cmd_infra_up() {
  banner
  ensure_terraform
  section "Provisioning GCP demo infrastructure..."
  cd "$INFRA_DIR"
  terraform init -input=false
  terraform apply -auto-approve
  echo ""
  section "Terraform Outputs"
  terraform output
  echo ""
  info "Demo infrastructure is live. Run './demo.sh live' to scan it."
}

cmd_infra_down() {
  banner
  ensure_terraform
  section "Tearing down GCP demo infrastructure..."
  cd "$INFRA_DIR"
  terraform destroy -auto-approve
  info "All demo GCP resources destroyed."
}

cmd_test() {
  banner
  section "Running test suite..."
  cd "$BACKEND_DIR"
  uv run pytest -v
}

cmd_help() {
  banner
  echo "Usage: ./demo.sh <command>"
  echo ""
  echo "Commands:"
  echo "  ${BOLD}mock${NC}          Start the full stack with mock/demo data (no GCP needed)"
  echo "  ${BOLD}live${NC}          Start the full stack scanning a real GCP project"
  echo "  ${BOLD}infra-up${NC}      Provision the GCP demo project via Terraform"
  echo "  ${BOLD}infra-down${NC}    Tear down the GCP demo resources"
  echo "  ${BOLD}test${NC}          Run the pytest suite"
  echo "  ${BOLD}stop${NC}          Stop all running demo processes"
  echo "  ${BOLD}status${NC}        Show running demo processes"
  echo ""
  echo "Environment variables:"
  echo "  SHADOW_AI_GCP_PROJECT_ID    GCP project (default: shadow-ai-agent-501704)"
  echo "  SHADOW_AI_GCP_REGION        GCP region  (default: us-central1)"
  echo "  SHADOW_AI_BACKEND_PORT      Backend port (default: 8000)"
  echo "  SHADOW_AI_FRONTEND_PORT     Frontend port (default: 5173)"
  echo "  GOOGLE_APPLICATION_CREDENTIALS  Path to SA key JSON (optional)"
  echo ""
}

# ── Main dispatch ──────────────────────────────────────────────────────────

case "${1:-help}" in
  mock)       cmd_mock ;;
  live)       cmd_live ;;
  infra-up)   cmd_infra_up ;;
  infra-down) cmd_infra_down ;;
  test)       cmd_test ;;
  stop)       stop_all ;;
  status)     show_status ;;
  help|--help|-h) cmd_help ;;
  *)
    err "Unknown command: $1"
    cmd_help
    exit 1
    ;;
esac
