#!/bin/bash

# DSH ETL Search AI - Unified Startup Script
# Runs entire setup: ETL + Indexing + Backend API + Frontend
# 
# Usage: 
#   chmod +x start-all.sh
#   ./start-all.sh [--limit 50]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=5173

# CLI args: optional --force-etl then limit
FORCE_ETL=false
if [ "${1:-}" = "--force-etl" ]; then
    FORCE_ETL=true
    DATASET_LIMIT=${2:-200}
else
    DATASET_LIMIT=${1:-200}
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# PIDs for started services
BACKEND_PID=""
FRONTEND_PID=""

# Ensure `uv` is available
if ! command -v uv >/dev/null 2>&1; then
    echo -e "${RED}✗ 'uv' command not found. Please install and run 'uv sync' in backend.${NC}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  DSH ETL Search AI - Complete Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    # Kill backend if running
    if [ -n "${BACKEND_PID}" ]; then
        kill ${BACKEND_PID} 2>/dev/null || true
        wait ${BACKEND_PID} 2>/dev/null || true
    fi
    # Kill frontend if running
    if [ -n "${FRONTEND_PID}" ]; then
        kill ${FRONTEND_PID} 2>/dev/null || true
        wait ${FRONTEND_PID} 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}
trap cleanup EXIT

# Function to wait for service
wait_for_port() {
    local port=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo -e "${YELLOW}→ Waiting for ${name} on port ${port}...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}✓ ${name} is ready on port ${port}${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    echo -e "${RED}✗ ${name} did not start on port ${port}${NC}"
    return 1
}

# Function to detect actual frontend port (handles auto-increment if busy)
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

# Function to validate API endpoint
validate_api() {
    local backend_port=$1
    local max_attempts=10
    local attempt=0
    
    echo -e "${YELLOW}→ Validating API health...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${backend_port}/health" 2>/dev/null || echo "000")
        
        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✓ API health check passed${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 1
    done
    
    echo -e "${YELLOW}⚠ API health check failed or endpoint not responding${NC}"
    return 1
}

# PHASE 1: ETL + Indexing
echo -e "${BLUE}[PHASE 1] ETL & Indexing${NC}"
echo -e "${YELLOW}→ Processing ${DATASET_LIMIT} datasets with automatic indexing...${NC}\n"

cd "$SCRIPT_DIR/backend"

# Determine whether to run ETL: skip if DB already has datasets unless forced
SKIP_ETL=false
# Use shell path for the database (avoid calling 'python')
DB_PATH="${SCRIPT_DIR}/backend/data/datasets.db"

if [ -f "$DB_PATH" ] && command -v sqlite3 >/dev/null 2>&1; then
    COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM datasets;" 2>/dev/null || echo 0)
    if [ "$COUNT" -gt 0 ] && [ "$FORCE_ETL" = "false" ]; then
        SKIP_ETL=true
        echo -e "${YELLOW}→ Detected existing database with ${COUNT} datasets; skipping ETL. Use --force-etl to re-run.${NC}"
    fi
fi

if [ "$SKIP_ETL" = "false" ]; then
    if ! uv run python -m src.cli etl --limit $DATASET_LIMIT --verbose; then
        echo -e "${RED}✗ ETL pipeline failed${NC}"
        exit 1
    fi
else
    echo -e "\n${GREEN}✓ ETL skipped (existing data present)${NC}\n"
fi

echo -e "\n${GREEN}✓ ETL & Indexing complete${NC}"

# PHASE 2: Start Backend API
echo -e "\n${BLUE}[PHASE 2] Starting Backend API${NC}"
echo -e "${YELLOW}→ Starting FastAPI server on port ${BACKEND_PORT}...${NC}\n"

cd "$SCRIPT_DIR/backend"
# Start backend (run from backend directory so imports resolve)
uv run uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!

if wait_for_port $BACKEND_PORT "Backend API"; then
    if validate_api $BACKEND_PORT; then
        echo -e "${GREEN}✓ Backend API is running${NC}"
        echo -e "${GREEN}  → API Docs: http://localhost:${BACKEND_PORT}/docs${NC}"
        echo -e "${GREEN}  → API Health: http://localhost:${BACKEND_PORT}/health${NC}"
    else
        echo -e "${YELLOW}⚠ Backend API is listening but health check inconclusive${NC}"
    fi
else
    echo -e "${RED}✗ Backend API failed to start${NC}"
    exit 1
fi

# PHASE 3: Start Frontend
echo -e "\n${BLUE}[PHASE 3] Starting Frontend${NC}"
echo -e "${YELLOW}→ Starting SvelteKit dev server on port ${FRONTEND_PORT}...${NC}\n"

cd "$SCRIPT_DIR/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}→ Installing npm dependencies...${NC}"
    npm install
fi

# Detect which port frontend will actually use (handles port conflicts)
ACTUAL_FRONTEND_PORT=$(detect_frontend_port)

# Start frontend (run from frontend directory)
VITE_API_URL="http://localhost:${BACKEND_PORT}" npm run dev &
FRONTEND_PID=$!

if wait_for_port $ACTUAL_FRONTEND_PORT "Frontend"; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
    echo -e "${GREEN}  → Web UI: http://localhost:${ACTUAL_FRONTEND_PORT}${NC}"
else
    echo -e "${RED}✗ Frontend failed to start${NC}"
    exit 1
fi

# PHASE 4: Ready!
echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ SETUP COMPLETE - Everything is running!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}\n"

echo -e "${BLUE}Access your application:${NC}"
echo -e "  ${GREEN}Web UI:${NC}       http://localhost:${ACTUAL_FRONTEND_PORT}"
echo -e "  ${GREEN}API Docs:${NC}     http://localhost:${BACKEND_PORT}/docs"
echo -e "  ${GREEN}Backend API:${NC}  http://localhost:${BACKEND_PORT}\n"

echo -e "${BLUE}What you can do:${NC}"
echo -e "  1. Open http://localhost:${FRONTEND_PORT} in your browser"
echo -e "  2. Search for datasets (e.g., 'climate', 'water quality')"
echo -e "  3. View search results with relevance scores"
echo -e "  4. Click on results to view details\n"

echo -e "${YELLOW}To stop everything, press Ctrl+C${NC}\n"

# Keep script running
wait
