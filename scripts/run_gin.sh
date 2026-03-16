#!/usr/bin/env bash
# =============================================================================
# run_gin.sh — Run the GIN index experiment
#
# Compatible with: macOS, Linux (all distros), Windows Git Bash, WSL
#
# Usage:
#   bash scripts/run_gin.sh          # start DB, run demo, leave DB running
#   bash scripts/run_gin.sh --clean  # same, but stop & remove DB afterwards
#   bash scripts/run_gin.sh --down   # only stop & remove DB, no demo run
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers (disabled automatically on non-TTY / Windows plain cmd)
# ---------------------------------------------------------------------------
if [ -t 1 ] && command -v tput &>/dev/null && tput setaf 1 &>/dev/null; then
  RED="$(tput setaf 1)"   GREEN="$(tput setaf 2)"
  YELLOW="$(tput setaf 3)" CYAN="$(tput setaf 6)"
  BOLD="$(tput bold)"     RESET="$(tput sgr0)"
else
  RED="" GREEN="" YELLOW="" CYAN="" BOLD="" RESET=""
fi

info()    { echo "${CYAN}[info]${RESET}  $*"; }
success() { echo "${GREEN}[ok]${RESET}    $*"; }
warn()    { echo "${YELLOW}[warn]${RESET}  $*"; }
error()   { echo "${RED}[error]${RESET} $*" >&2; }
banner()  { echo; echo "${BOLD}${CYAN}$*${RESET}"; echo; }

# ---------------------------------------------------------------------------
# Resolve the repo root (the directory that contains this scripts/ folder)
# Works regardless of where the caller invokes the script from.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
RUN_CLEAN=false
ONLY_DOWN=false

for arg in "$@"; do
  case "$arg" in
    --clean) RUN_CLEAN=true ;;
    --down)  ONLY_DOWN=true ;;
    --help|-h)
      echo "Usage: bash scripts/run_gin.sh [--clean | --down]"
      echo "  (no flag)  Start DB, run GIN demo, leave DB running"
      echo "  --clean    Start DB, run GIN demo, then stop & remove DB"
      echo "  --down     Stop & remove the DB container only (no demo)"
      exit 0
      ;;
    *) error "Unknown argument: $arg"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Detect OS / shell environment
# ---------------------------------------------------------------------------
detect_os() {
  case "$(uname -s)" in
    Darwin*)  echo "macos"   ;;
    Linux*)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl"
      else
        echo "linux"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*) echo "gitbash" ;;
    *)         echo "unknown" ;;
  esac
}

OS="$(detect_os)"
info "Detected environment: ${BOLD}${OS}${RESET}"

# ---------------------------------------------------------------------------
# Helper: resolve a command that may have multiple possible names
# e.g. docker compose (v2) vs docker-compose (v1)
# ---------------------------------------------------------------------------
require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" &>/dev/null; then
    error "Required command not found: ${BOLD}${cmd}${RESET}"
    error "Please install it and re-run."
    exit 1
  fi
}

# Docker Compose: v2 bundled plugin (docker compose) preferred over v1 (docker-compose)
compose_cmd() {
  if docker compose version &>/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose &>/dev/null; then
    echo "docker-compose"
  else
    error "Neither 'docker compose' (v2) nor 'docker-compose' (v1) found."
    error "Install Docker Desktop (macOS/Windows) or 'docker-compose' package (Linux)."
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
banner "═══  Checking dependencies  ═══"

require_cmd docker

COMPOSE="$(compose_cmd)"
info "Docker Compose command: ${BOLD}${COMPOSE}${RESET}"

# uv is the project's Python runner — fall back to python/python3 if absent
if command -v uv &>/dev/null; then
  PYTHON_RUN="uv run"
  info "Python runner: ${BOLD}uv run${RESET}"
elif command -v python3 &>/dev/null; then
  PYTHON_RUN="python3 -m"
  warn "uv not found — falling back to ${BOLD}python3 -m${RESET}"
  warn "Install uv for reproducible environments: https://docs.astral.sh/uv/"
elif command -v python &>/dev/null; then
  PYTHON_RUN="python -m"
  warn "uv not found — falling back to ${BOLD}python -m${RESET}"
else
  error "No Python interpreter found. Install Python 3.12+ or uv."
  exit 1
fi

# Make sure Docker daemon is running
if ! docker info &>/dev/null; then
  error "Docker daemon is not running."
  case "$OS" in
    macos)   error "Start Docker Desktop from Applications." ;;
    wsl)     error "Start Docker Desktop on Windows, or run: sudo service docker start" ;;
    gitbash) error "Start Docker Desktop on Windows." ;;
    linux)   error "Run: sudo systemctl start docker  (or sudo service docker start)" ;;
  esac
  exit 1
fi

success "All dependencies satisfied."

# ---------------------------------------------------------------------------
# --down only: stop and exit
# ---------------------------------------------------------------------------
if [ "$ONLY_DOWN" = true ]; then
  banner "═══  Stopping database  ═══"
  cd "$REPO_ROOT"
  $COMPOSE down
  success "Database stopped and removed."
  exit 0
fi

# ---------------------------------------------------------------------------
# Load .env (so we can read the health-check credentials below)
# .env is optional — docker-compose picks it up automatically too.
# ---------------------------------------------------------------------------
ENV_FILE="${REPO_ROOT}/.env"
if [ -f "$ENV_FILE" ]; then
  # Export only simple KEY=VALUE lines; skip comments and blanks
  set -o allexport
  # shellcheck disable=SC1090
  source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE")
  set +o allexport
  info "Loaded .env from ${ENV_FILE}"
else
  warn ".env file not found — using docker-compose defaults (postgres/postgres)"
fi

PG_USER="${POSTGRES_USER:-postgres}"
PG_PORT="${POSTGRES_PORT:-5432}"

# ---------------------------------------------------------------------------
# Start the database
# ---------------------------------------------------------------------------
banner "═══  Starting PostgreSQL via Docker Compose  ═══"
cd "$REPO_ROOT"

$COMPOSE up -d db
success "Container started."

# ---------------------------------------------------------------------------
# Wait for PostgreSQL to accept connections
# ---------------------------------------------------------------------------
banner "═══  Waiting for PostgreSQL to be ready  ═══"

MAX_WAIT=60   # seconds
INTERVAL=2
elapsed=0

until docker exec pgindexes_db pg_isready -U "$PG_USER" -q 2>/dev/null; do
  if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    error "PostgreSQL did not become ready within ${MAX_WAIT}s."
    error "Check container logs: docker logs pgindexes_db"
    exit 1
  fi
  info "Waiting... (${elapsed}s elapsed)"
  sleep "$INTERVAL"
  elapsed=$(( elapsed + INTERVAL ))
done

success "PostgreSQL is ready."

# ---------------------------------------------------------------------------
# Install Python dependencies (only needed when using plain python fallback)
# uv handles its own venv automatically; pip install is a no-op if up to date.
# ---------------------------------------------------------------------------
if [ "$PYTHON_RUN" != "uv run" ]; then
  banner "═══  Installing Python dependencies  ═══"
  # Detect pip
  if command -v pip3 &>/dev/null; then
    PIP="pip3"
  else
    PIP="pip"
  fi
  $PIP install --quiet -e "${REPO_ROOT}[dev]" 2>/dev/null \
    || $PIP install --quiet -e "${REPO_ROOT}"
  success "Python dependencies installed."
fi

# ---------------------------------------------------------------------------
# Run the GIN experiment
# ---------------------------------------------------------------------------
banner "═══  Running GIN Index Experiment  ═══"

cd "$REPO_ROOT"

if [ "$PYTHON_RUN" = "uv run" ]; then
  uv run pgindexes
else
  $PYTHON_RUN pgindexes
fi

success "GIN experiment complete."

# ---------------------------------------------------------------------------
# Optionally stop the database
# ---------------------------------------------------------------------------
if [ "$RUN_CLEAN" = true ]; then
  banner "═══  Cleaning up (--clean flag set)  ═══"
  $COMPOSE down
  success "Database stopped and removed."
else
  info "Database is still running."
  info "To stop it later, run:  ${BOLD}bash scripts/run_gin.sh --down${RESET}"
fi

echo
echo "${BOLD}${GREEN}════  Done  ════${RESET}"
echo
