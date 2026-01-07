#!/bin/bash

# DSH ETL Search AI - Unified Startup Script (UPGRADED)
# Runs entire setup: ETL + Indexing + Backend API + Frontend
# 
# Usage: 
#   chmod +x start-all-v2.sh
#   ./start-all-v2.sh [OPTIONS]
#
# OPTIONS:
#   --limit <N>              Limit ETL to N datasets (default: 200)
#   --force-etl              Force re-run ETL pipeline (skip existing data check)
#   --test                   Run test suite before starting services
#   --backend-only           Start only backend API (skips ETL & frontend)
#   --frontend-only          Start only frontend (assumes backend running)
#   --verbose                Enable verbose logging and output
#   --docker                 Use Docker Compose instead of local services [Future]
#   --help                   Show this help message

set -euo pipefail

# ═══════════════════════════════════════════════════════════
# Color Codes & Configuration
# ═══════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

BACKEND_PORT=8000
FRONTEND_PORT=5173
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "$LOG_DIR"

BACKEND_LOG="${LOG_DIR}/backend-$(date +%Y%m%d_%H%M%S).log"
FRONTEND_LOG="${LOG_DIR}/frontend-$(date +%Y%m%d_%H%M%S).log"
ETL_LOG="${LOG_DIR}/etl-$(date +%Y%m%d_%H%M%S).log"

BACKEND_PID=""
FRONTEND_PID=""

# Feature flags
FORCE_ETL=false
RUN_TESTS=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
VERBOSE=false
DATASET_LIMIT=200

# ═══════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_info() {
    echo -e "${CYAN}→ $1${NC}"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

clean_port() {
    local port=$1
    local name=$2
    
    if command_exists lsof; then
        local pids=$(lsof -ti:$port 2>/dev/null || echo "")
        if [ -n "$pids" ]; then
            log_warning "Port $port is in use by process(es): $pids. Attempting to free it..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
            sleep 1
            log_success "Port $port freed"
        fi
    fi
}

check_version() {
    local cmd=$1
    local version_flag=$2
    local min_version=$3
    local name=$4
    
    if ! command_exists "$cmd"; then
        log_error "$name not found. Please install it."
        return 1
    fi
    
    local version=$($cmd $version_flag 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if [ -z "$version" ]; then
        log_warning "$name version check inconclusive (found: $(which $cmd))"
        return 0
    fi
    
    if [ "$(printf '%s\n' "$min_version" "$version" | sort -V | head -n1)" = "$min_version" ]; then
        log_success "$name $version found"
        return 0
    else
        log_error "$name $version found, but $min_version or higher required"
        return 1
    fi
}

run_with_log() {
    local log_file=$1
    shift
    if [ "$VERBOSE" = "true" ]; then
        "$@" | tee -a "$log_file"
    else
        "$@" >> "$log_file" 2>&1
    fi
}

show_help() {
    grep '^# ' "$0" | head -20
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --limit)
                DATASET_LIMIT=$2
                shift 2
                ;;
            --force-etl)
                FORCE_ETL=true
                shift
                ;;
            --test)
                RUN_TESTS=true
                shift
                ;;
            --backend-only)
                BACKEND_ONLY=true
                shift
                ;;
            --frontend-only)
                FRONTEND_ONLY=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

# ═══════════════════════════════════════════════════════════
# Environment Check Functions
# ═══════════════════════════════════════════════════════════

check_dependencies() {
    log_info "Checking system dependencies..."
    
    local all_good=true
    
    check_version "uv" "--version" "0.1.0" "UV (Python package manager)" || all_good=false
    check_version "node" "--version" "20.0.0" "Node.js" || all_good=false
    check_version "npm" "--version" "10.0.0" "NPM" || all_good=false
    
    # Check if Python is available via UV (not system Python)
    if cd "$SCRIPT_DIR/backend" && uv run python --version >/dev/null 2>&1; then
        log_success "Python available via UV"
    else
        log_error "Python not available via UV. Run 'uv sync' in backend directory first"
        all_good=false
    fi
    
    if command_exists "sqlite3"; then
        log_success "SQLite3 found"
    else
        log_warning "SQLite3 not found (will use Python fallback)"
    fi
    
    if [ "$all_good" = false ]; then
        log_error "Missing critical dependencies"
        return 1
    fi
    
    return 0
}

validate_uv_environment() {
    log_info "Checking UV environment and dependencies..."
    
    cd "$SCRIPT_DIR/backend"
    
    # Check if .venv exists or UV has synced dependencies
    if [ ! -d ".venv" ] && [ ! -d "__pycache__" ]; then
        log_warning "UV environment not yet initialized"
        log_info "Running 'uv sync' to install dependencies..."
        
        if ! uv sync; then
            log_error "Failed to install backend dependencies with 'uv sync'"
            return 1
        fi
    fi
    
    # Verify key backend dependencies are available
    if ! uv run python -c "import fastapi, pytest, sqlalchemy" 2>/dev/null; then
        log_warning "Some Python dependencies may be missing, attempting sync..."
        if ! uv sync; then
            log_error "Failed to sync dependencies"
            return 1
        fi
    fi
    
    log_success "UV environment ready"
    return 0
}

validate_environment() {
    log_info "Validating project environment..."
    
    [ ! -d "$SCRIPT_DIR/backend" ] && { log_error "Backend directory not found"; return 1; }
    [ ! -d "$SCRIPT_DIR/frontend" ] && { log_error "Frontend directory not found"; return 1; }
    [ ! -f "$SCRIPT_DIR/backend/pyproject.toml" ] && { log_error "Backend pyproject.toml not found"; return 1; }
    [ ! -f "$SCRIPT_DIR/frontend/package.json" ] && { log_error "Frontend package.json not found"; return 1; }
    
    log_success "Project structure validated"
    
    # Validate UV environment and install dependencies if needed
    if ! validate_uv_environment; then
        return 1
    fi
    
    return 0
}

init_database() {
    log_info "Checking database..."
    
    cd "$SCRIPT_DIR/backend"
    
    if run_with_log "$ETL_LOG" uv run python -c "
from src.infrastructure.database import Database
db = Database()
db.connect()
db.create_tables()
db.close()
print('Database ready')
" >/dev/null 2>&1; then
        log_success "Database initialized"
    else
        log_warning "Database check completed (may already exist)"
    fi
    return 0
}

# ═══════════════════════════════════════════════════════════
# Service Management Functions
# ═══════════════════════════════════════════════════════════

wait_for_port() {
    local port=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    log_info "Waiting for ${name} on port ${port}..."
    
    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            log_success "${name} is ready on port ${port}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    log_error "${name} did not start on port ${port}"
    return 1
}

detect_frontend_port() {
    local base_port=5173
    local port=$base_port
    local max_port=5190
    
    while [ $port -le $max_port ]; do
        if nc -z localhost $port 2>/dev/null; then
            port=$((port + 1))
        else
            echo $port
            return 0
        fi
    done
    
    echo $base_port
}

validate_api() {
    local backend_port=$1
    local max_attempts=10
    local attempt=0
    
    log_info "Validating API health..."
    
    while [ $attempt -lt $max_attempts ]; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${backend_port}/health" 2>/dev/null || echo "000")
        
        if [ "$response" = "200" ]; then
            log_success "API health check passed"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 1
    done
    
    log_warning "API health check failed or endpoint not responding"
    return 1
}

run_tests() {
    log_info "Running test suite..."
    
    cd "$SCRIPT_DIR/backend"
    
    if run_with_log "$ETL_LOG" uv run pytest tests/ -q --tb=short; then
        log_success "All tests passed"
        return 0
    else
        log_error "Some tests failed"
        return 1
    fi
}

cleanup() {
    log_warning "Cleaning up services..."
    
    [ -n "${BACKEND_PID}" ] && kill ${BACKEND_PID} 2>/dev/null || true
    [ -n "${FRONTEND_PID}" ] && kill ${FRONTEND_PID} 2>/dev/null || true
    
    log_success "Cleanup complete"
    echo -e "\n${CYAN}Logs saved to:${NC}"
    [ -f "$BACKEND_LOG" ] && echo "  - Backend: $BACKEND_LOG"
    [ -f "$FRONTEND_LOG" ] && echo "  - Frontend: $FRONTEND_LOG"
    [ -f "$ETL_LOG" ] && echo "  - ETL: $ETL_LOG"
}

trap cleanup EXIT

# ═══════════════════════════════════════════════════════════
# Main Execution Flow
# ═══════════════════════════════════════════════════════════

main() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  DSH ETL Search AI - Complete Setup (Upgraded)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
    
    # Phase 0: Validation
    if ! check_dependencies; then
        log_error "Dependency check failed"
        return 1
    fi
    
    if ! validate_environment; then
        log_error "Environment validation failed"
        return 1
    fi
    
    # Test mode: run tests and exit
    if [ "$RUN_TESTS" = "true" ]; then
        log_info "Running test suite..."
        if ! run_tests; then
            return 1
        fi
        log_success "All tests passed!"
        return 0
    fi
    
    # Database initialization
    if [ "$BACKEND_ONLY" = "false" ] && [ "$FRONTEND_ONLY" = "false" ]; then
        init_database
    fi
    
    # Phase 1: ETL & Indexing
    if [ "$BACKEND_ONLY" = "false" ] && [ "$FRONTEND_ONLY" = "false" ]; then
        echo -e "\n${BLUE}[PHASE 1] ETL & Indexing${NC}"
        log_info "Processing ${DATASET_LIMIT} datasets...\n"
        
        cd "$SCRIPT_DIR/backend"
        
        SKIP_ETL=false
        DB_PATH="${SCRIPT_DIR}/backend/data/datasets.db"
        IDENTIFIERS_FILE="${SCRIPT_DIR}/backend/metadata-file-identifiers.txt"
        
        if [ -f "$IDENTIFIERS_FILE" ]; then
            IDENTIFIERS_COUNT=$(grep -vE '^\s*#' "$IDENTIFIERS_FILE" | sed '/^\s*$/d' | wc -l | tr -d ' ')
        else
            IDENTIFIERS_COUNT=0
        fi
        
        if [ -f "$DB_PATH" ] && command_exists sqlite3; then
            COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM datasets;" 2>/dev/null || echo 0)
            if [ "$FORCE_ETL" = "false" ] && [ "$COUNT" -gt 0 ]; then
                SKIP_ETL=true
                log_warning "Existing database detected with ${COUNT} datasets; skipping ETL (use --force-etl to override)"
            fi
        fi
        
        if [ "$SKIP_ETL" = "false" ]; then
            if ! run_with_log "$ETL_LOG" uv run python cli_main.py etl --limit $DATASET_LIMIT --verbose; then
                log_error "ETL pipeline failed (see $ETL_LOG)"
                return 1
            fi

            # If ETL produced only a single-line trivial log (e.g. "Database ready"), remove it to avoid noise
            if [ -f "$ETL_LOG" ]; then
                line_count=$(wc -l < "$ETL_LOG" || echo 0)
                if [ "$line_count" -le 1 ]; then
                    log_info "ETL log ($ETL_LOG) contains only $line_count line(s); removing to reduce noise"
                    rm -f "$ETL_LOG" || true
                fi
            fi
        fi
        
        log_success "ETL & Indexing complete\n"
    fi
    
    # Phase 2: Backend API
    if [ "$FRONTEND_ONLY" = "false" ]; then
        echo -e "\n${BLUE}[PHASE 2] Starting Backend API${NC}"
        log_info "Starting FastAPI on port ${BACKEND_PORT}...\n"
        
        # Clean up any old processes on the port (ensure port free before starting)
        clean_port $BACKEND_PORT "Backend"
        
        cd "$SCRIPT_DIR/backend"
        
        run_with_log "$BACKEND_LOG" uv run python main.py &
        BACKEND_PID=$!
        
        if ! wait_for_port $BACKEND_PORT "Backend API"; then
            log_error "Backend API failed to start"
            return 1
        fi
        
        if validate_api $BACKEND_PORT; then
            log_success "Backend API is running"
            log_info "API Docs: http://localhost:${BACKEND_PORT}/docs"
        else
            log_warning "Backend listening but health check inconclusive"
        fi
    fi
    
    # Phase 3: Frontend
    echo -e "\n${BLUE}[PHASE 3] Starting Frontend${NC}"
    log_info "Starting SvelteKit on port ${FRONTEND_PORT}...\n"
    
    # Clean up any old processes on the port
    clean_port $FRONTEND_PORT "Frontend"
    
    cd "$SCRIPT_DIR/frontend"
    
    if [ ! -d "node_modules" ]; then
        log_info "Installing npm dependencies..."
        npm install
    fi
    
    ACTUAL_FRONTEND_PORT=$(detect_frontend_port)
    # Start frontend. Use nohup for background capture when not verbose so output is reliably written to log
    if [ "$VERBOSE" = "true" ]; then
        VITE_API_URL="http://localhost:${BACKEND_PORT}" run_with_log "$FRONTEND_LOG" npm run dev &
        FRONTEND_PID=$!
    else
        cd "$SCRIPT_DIR/frontend"
        export VITE_API_URL="http://localhost:${BACKEND_PORT}"
        nohup npm run dev >> "$FRONTEND_LOG" 2>&1 &
        FRONTEND_PID=$!
    fi
    
    if ! wait_for_port $ACTUAL_FRONTEND_PORT "Frontend"; then
        log_error "Frontend failed to start"
        return 1
    fi
    
    log_success "Frontend is running"
    
    # Phase 4: Ready!
    echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ SETUP COMPLETE - Everything is running!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}\n"
    
    echo -e "${BLUE}Access your application:${NC}"
    echo -e "  ${GREEN}Web UI:${NC}       http://localhost:${ACTUAL_FRONTEND_PORT}"
    echo -e "  ${GREEN}API Docs:${NC}     http://localhost:${BACKEND_PORT}/docs"
    echo -e "  ${GREEN}Backend:${NC}      http://localhost:${BACKEND_PORT}\n"
    
    echo -e "${BLUE}Features:${NC}"
    echo -e "  • Search datasets by keyword"
    echo -e "  • View relevance scores"
    echo -e "  • Explore metadata details"
    echo -e "  • Browse multiple formats\n"
    
    echo -e "${YELLOW}Press Ctrl+C to stop everything${NC}\n"
    
    return 0
}

# ═══════════════════════════════════════════════════════════
# Script Entry Point
# ═══════════════════════════════════════════════════════════

parse_args "$@"
main "$@"

# Keep script running
wait
