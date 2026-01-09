# DSH ETL Search AI - Backend README

**CEH Dataset Discovery System with Semantic Search and AI Chat**

This document provides comprehensive installation, configuration, and operational guidance for IT professionals managing the DSH ETL Search AI backend system.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [About UV Package Manager](#about-uv-package-manager)
3. [Python Version & Dependencies](#python-version--dependencies)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [ETL Pipeline Operations](#etl-pipeline-operations)
8. [CLI Commands Reference](#cli-commands-reference)
9. [API Server](#api-server)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Configuration](#advanced-configuration)

---

## System Requirements

### Minimum System Specifications

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **CPU** | 4 cores minimum | 8+ cores recommended for faster ETL processing |
| **RAM** | 8 GB minimum | 16+ GB recommended for embedding generation |
| **Storage** | 50 GB free | Depends on dataset volume and vector store size |
| **OS** | macOS, Linux, Windows | WSL2 recommended for Windows |
| **Network** | Internet connection | Required for CEH Catalogue API access |

### Software Prerequisites

- **Python**: 3.11 or higher (3.12 recommended - see `.python-version` file)
- **uv**: Latest version (see [Installation & Setup](#installation--setup))
- **Git**: For repository management
- **Docker** (optional): For containerized deployment
- **Ollama** (optional): For local LLM inference without API calls

### Required External Services

- **CEH Catalogue API**: https://catalogue.ceh.ac.uk (CEH metadata source)
- **Ollama Server** (optional): http://localhost:11434 (for AI features)
- **OpenTelemetry Collector** (optional): For distributed tracing

---

## About UV Package Manager

### What is UV?

**UV** is a modern, blazingly fast Python package installer and resolver written in Rust. It replaces traditional `pip` and `venv` with significantly improved performance.

**Key Features:**
- ⚡ **10-100x faster** than pip
- 🔒 **Deterministic** dependency resolution
- 🎯 **Unified** lock file for reproducible builds
- 📦 **Built-in** virtual environment management
- ✅ **Supports** all existing PyPI packages

### Why UV Instead of pip?

| Aspect | UV | pip |
|--------|----|----|
| Speed | ~100ms | ~10-20s |
| Resolution | Deterministic | Variable |
| Lock File | ✅ Yes | ❌ No (pipenv/poetry needed) |
| Virtual Env | Built-in | Requires venv |
| Caching | Smart | Basic |

### Installation

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy BypassCurrentUser -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Verify Installation
```bash
uv --version
# Output: uv 0.x.x
```

### UV Common Commands

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# Install dependencies from pyproject.toml
uv sync

# Install specific package
uv pip install package_name

# Run Python script with dependencies
uv run python script.py

# Run command in virtual environment
uv run <command>

# Lock dependencies
uv lock

# Show environment info
uv pip list
```

---

## Python Version & Dependencies

### Python Version

This project requires **Python 3.11** or higher, with **3.12 recommended**.

**Version File:** `.python-version` contains `3.12`

#### Check Your Python Version

```bash
python --version
# Python 3.12.x or higher
```

#### Install Python 3.12 (if needed)

**macOS (via Homebrew):**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install python3.12 python3.12-venv python3.12-dev
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install python3.12 python3.12-devel
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/) or use Windows Package Manager:
```powershell
winget install Python.Python.3.12
```

### Core Dependencies

#### Main Dependencies (pyproject.toml)

| Package | Version | Purpose |
|---------|---------|---------|
| **fastapi** | ≥0.115.0 | REST API framework |
| **uvicorn[standard]** | ≥0.32.0 | ASGI server for FastAPI |
| **pydantic** | ≥2.10.0 | Data validation & settings |
| **chromadb** | ≥0.5.0 | Vector database for embeddings |
| **sentence-transformers** | ≥3.3.0 | Embedding model inference |
| **ollama** | ≥0.4.0 | Local LLM inference client |
| **typer** | ≥0.9.0 | CLI framework |
| **python-dotenv** | ≥1.0.0 | Environment variable loading |
| **httpx** | ≥0.28.0 | Async HTTP client |
| **aiohttp** | ≥3.8.0 | Async HTTP library |
| **requests** | ≥2.31.0 | Sync HTTP client |
| **pypdf** | ≥3.17.0 | PDF text extraction |
| **python-docx** | ≥0.8.11 | DOCX text extraction |
| **beautifulsoup4** | ≥4.12.0 | HTML parsing |
| **rdflib** | ≥6.3.0 | RDF/XML parsing |
| **lxml** | ≥5.3.0 | XML parsing |
| **xmltodict** | ≥0.13.0 | XML to dict conversion |
| **torch** | ≥2.2.0 | Deep learning framework (used by embeddings) |
| **rich** | ≥13.0.0 | Colored CLI output |
| **tenacity** | ≥8.2.0 | Retry logic |
| **aiosqlite** | ≥0.20.0 | Async SQLite access |

#### Observability/Tracing Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **opentelemetry-api** | ≥1.21.0 | OpenTelemetry API |
| **opentelemetry-sdk** | ≥1.21.0 | OpenTelemetry SDK |
| **opentelemetry-exporter-otlp** | ≥0.42b0 | OTLP trace exporter |
| **opentelemetry-instrumentation** | ≥0.42b0 | Auto-instrumentation |

#### Development Dependencies

```
pytest≥8.3.0              - Testing framework
pytest-asyncio≥0.24.0    - Async test support
pytest-cov≥4.1.0         - Code coverage
ruff≥0.8.0                - Fast Python linter
black≥23.0.0              - Code formatter
mypy≥1.8.0                - Static type checker
aioresponses≥0.7.8        - Mock async HTTP responses
httpx≥0.28.0              - HTTP client for testing
```

### Dependency Installation

All dependencies are specified in `pyproject.toml` and automatically installed with:

```bash
uv sync
```

For development environment (includes test tools):
```bash
uv sync --group dev
```

---

## Installation & Setup

### Step 1: System Preparation

```bash
# Create working directory
mkdir -p /path/to/workspace
cd /path/to/workspace

# Clone or navigate to project
cd dsh-etl-search-ai-2025/backend
```

### Step 2: Verify Python Installation

```bash
python --version
# Expected: Python 3.11.x or 3.12.x

python -m venv --help
# Verify venv is available
```

### Step 3: Create Virtual Environment with UV

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate           # macOS/Linux
# OR
.venv\Scripts\activate              # Windows
```

**Verification:**
```bash
which python    # Should show .venv path
python --version
```

### Step 4: Install Dependencies

```bash
# Install all dependencies from pyproject.toml
uv sync

# For development (includes testing tools)
uv sync --group dev
```

**Verification:**
```bash
# Check installed packages
uv pip list | head -20

# Verify key packages
python -c "import fastapi, chromadb, torch; print('✓ Core packages installed')"
```

### Step 5: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration with your settings
# See Configuration section below
nano .env  # or your preferred editor
```

### Step 6: Initialize Database & Directories

```bash
# Initialize database and create required directories
uv run python cli_main.py init-db

# Verify directories created
ls -la data/
# Should show: chroma/, metadata_cache/, supporting_docs/
```

### Step 7: Verify Installation

```bash
# Run validation command
uv run python cli_main.py validate-config

# Output should show:
# ✓ Configuration loaded successfully
# ✓ Required directories exist
# ✓ Database initialized
```

### Complete Installation Checklist

- [ ] Python 3.11+ installed
- [ ] uv package manager installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`uv sync`)
- [ ] `.env` file configured
- [ ] Database initialized
- [ ] Configuration validated

---

## Configuration

### Environment Variables (.env File)

The `.env` file controls all application behavior. Copy from `.env.example`:

```bash
cp .env.example .env
```

### Application Settings

```env
# Application Identification
APP_NAME="CEH Dataset Discovery"
APP_ENV=development              # development, staging, production
DEBUG=true                        # Enable debug mode
ENVIRONMENT=development          # Alias for APP_ENV
```

### API Server Configuration

```env
# API Server Binding
API_HOST=0.0.0.0                # 0.0.0.0 = listen on all interfaces
API_PORT=8000                    # Default FastAPI port
```

**Explanation:**
- `API_HOST=0.0.0.0`: Listens on all network interfaces (localhost + network)
- `API_PORT=8000`: HTTP port
- For remote access: `API_HOST=0.0.0.0`
- For local only: `API_HOST=127.0.0.1`

### Database Configuration

```env
# SQLite Database Path
DATABASE_PATH=./data/datasets.db
DATABASE_ECHO=false              # Set true to log all SQL queries
SUPPORTING_DOCS_DIR=data/supporting_docs
```

**Notes:**
- SQLite file location (relative to backend directory)
- Automatically created if doesn't exist
- For troubleshooting: set `DATABASE_ECHO=true` to see SQL queries

### CEH Catalogue API Configuration

```env
# CEH API Endpoint
CEH_API_BASE_URL=https://catalogue.ceh.ac.uk
CEH_API_TIMEOUT=600              # Timeout in seconds (10 minutes)
CEH_API_MAX_RETRIES=5            # Retry attempts for failed requests
CEH_API_RETRY_DELAY=2            # Delay between retries (seconds)
```

**Important:**
- `CEH_API_TIMEOUT=600`: Large datasets may require 10+ minutes
- Increase `CEH_API_MAX_RETRIES` for unstable networks
- `CEH_API_RETRY_DELAY` increases with backoff factor

### HTTP Client Configuration

```env
# HTTP Client Behavior
HTTP_TIMEOUT=600                 # Connection timeout
HTTP_MAX_RETRIES=5               # Maximum retry attempts
HTTP_RETRY_BACKOFF_FACTOR=0.5    # Exponential backoff multiplier
```

### Vector Store & Embeddings

```env
# Chroma Vector Database
CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Sentence embedding model
EMBEDDING_BATCH_SIZE=32            # Process embeddings in batches
EMBEDDING_DEVICE=cpu               # 'cpu' or 'cuda' (GPU)
EMBEDDING_NORMALIZE=true           # Normalize for faster similarity
TEXT_CHUNK_SIZE=1000               # Characters per chunk
TEXT_CHUNK_OVERLAP=200             # Overlap between chunks
```

**GPU Configuration:**
```env
# For GPU acceleration (requires CUDA)
EMBEDDING_DEVICE=cuda
```

### Ollama LLM Configuration

```env
# Local LLM Inference
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral              # Available: mistral, llama2, neural-chat, etc.
OLLAMA_TIMEOUT=120                # LLM response timeout (seconds)
```

**Install Ollama:**
```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Or download from: https://ollama.ai
```

**Pull Models:**
```bash
ollama pull mistral
ollama pull llama2
ollama list
```

### Logging Configuration

```env
# Logging Setup
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=./logs/app.log          # Log file path
```

**Log Levels:**
- `DEBUG`: Verbose, all low-level details
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages only
- `CRITICAL`: Critical errors only

### Distributed Tracing (OpenTelemetry)

```env
# Tracing Configuration
JAEGER_ENABLED=false              # Disable by default (prevent errors)
JAEGER_HOST=localhost
JAEGER_PORT=6831
JAEGER_SERVICE_NAME=dsh-etl-search-ai
JAEGER_ENVIRONMENT=development
JAEGER_SAMPLE_RATE=0.1           # 10% sampling
```

**Enable Tracing:**

Option 1: Disable (development - no errors):
```env
JAEGER_ENABLED=false
```

Option 2: Enable with local collector:
```bash
# Start OpenTelemetry Collector
docker run --rm -p 4317:4317 otel/opentelemetry-collector:latest
```

### ETL Pipeline Configuration

```env
# ETL Settings
METADATA_IDENTIFIERS_FILE=metadata-file-identifiers.txt
METADATA_FORMATS=["iso19139", "json", "schema_org", "rdf"]
ETL_BATCH_SIZE=10                # Process in batches of 10
MAX_CONCURRENT_DOWNLOADS=5       # Max parallel downloads
EXTRACT_TEXT_FROM_PDFS=true      # Extract text from PDF documents
EXTRACT_TEXT_FROM_DOCX=true      # Extract text from DOCX documents
```

### Complete .env Example

```env
# Application
APP_NAME="CEH Dataset Discovery"
APP_ENV=development
DEBUG=true
ENVIRONMENT=development

# API
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_PATH=./data/datasets.db
DATABASE_ECHO=false
SUPPORTING_DOCS_DIR=data/supporting_docs

# CEH API
CEH_API_BASE_URL=https://catalogue.ceh.ac.uk
CEH_API_TIMEOUT=600
CEH_API_MAX_RETRIES=5
CEH_API_RETRY_DELAY=2

# HTTP Client
HTTP_TIMEOUT=600
HTTP_MAX_RETRIES=5
HTTP_RETRY_BACKOFF_FACTOR=0.5

# Vector Store
CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_DEVICE=cpu
TEXT_CHUNK_SIZE=1000
TEXT_CHUNK_OVERLAP=200

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
OLLAMA_TIMEOUT=120

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# Tracing
JAEGER_ENABLED=false
JAEGER_HOST=localhost
JAEGER_PORT=6831
JAEGER_SERVICE_NAME=dsh-etl-search-ai
JAEGER_ENVIRONMENT=development
JAEGER_SAMPLE_RATE=0.1

# ETL
METADATA_IDENTIFIERS_FILE=metadata-file-identifiers.txt
METADATA_FORMATS=["iso19139", "json", "schema_org", "rdf"]
ETL_BATCH_SIZE=10
MAX_CONCURRENT_DOWNLOADS=5
EXTRACT_TEXT_FROM_PDFS=true
EXTRACT_TEXT_FROM_DOCX=true
```

---

## Running the Application

### Application Entry Points

There are **three ways** to run the backend application:

| Method | Purpose | Command | Use Case |
|--------|---------|---------|----------|
| **CLI via dsh-etl** | Command-line operations | `uv run dsh-etl etl` | Production ETL jobs |
| **CLI via cli_main.py** | Alternative CLI entry | `uv run python cli_main.py etl` | Development & testing |
| **API Server (main.py)** | REST API server | `uv run python main.py` | API queries & chat |

### Option 1: Using dsh-etl Command (Recommended for Production)

This is the **preferred production method** - it's a registered command in `pyproject.toml`.

```bash
# Activate virtual environment
source .venv/bin/activate

# Show help
uv run dsh-etl --help

# Run ETL pipeline
uv run dsh-etl etl

# Run ETL with options
uv run dsh-etl etl --limit 10 --verbose
```

**Why use dsh-etl:**
✅ Cleaner command syntax  
✅ Registered as project script  
✅ Easier for production automation  

### Option 2: Using cli_main.py (Direct Python Entry Point)

This method explicitly calls the Python script.

```bash
# Activate virtual environment
source .venv/bin/activate

# Show help
uv run python cli_main.py --help

# Run ETL pipeline
uv run python cli_main.py etl

# Run ETL with options
uv run python cli_main.py etl --limit 10 --verbose
```

**When to use:**
- Development and testing
- Debugging
- When you need to modify entry point

### Option 3: Using main.py (API Server)

This starts the FastAPI REST API server for programmatic access.

```bash
# Activate virtual environment
source .venv/bin/activate

# Run API server (development with auto-reload)
uv run python main.py

# Run with custom host/port
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production mode (no reload)
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

**API Access:**
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json
- ReDoc: http://localhost:8000/redoc

### Comparison: When to Use Which

```bash
# ✅ For ETL operations (most common)
uv run dsh-etl etl --limit 50 --verbose

# ✅ For API-based access to search/chat
uv run python main.py
# Then access: http://localhost:8000/docs

# ✅ For development/debugging
uv run python cli_main.py etl --dry-run --verbose

# ✅ For long-running production server
nohup uv run python main.py > api.log 2>&1 &
```

---

## ETL Pipeline Operations

### What is the ETL Pipeline?

**ETL = Extract, Transform, Load**

1. **EXTRACT**: Fetch dataset identifiers and metadata from CEH Catalogue API
2. **TRANSFORM**: Parse XML/JSON/RDF metadata into structured Python models
3. **LOAD**: Save datasets and related entities to SQLite database

### ETL Pipeline Flow

```
CEH Catalogue API
        ↓
   Fetch Metadata (XML/JSON/RDF)
        ↓
   Parse & Validate
        ↓
   Extract Supporting Documents
        ↓
   Transform to Database Models
        ↓
   Generate Embeddings
        ↓
   Load to SQLite Database
        ↓
   Update Vector Store (Chroma)
```

### Running ETL Pipeline

#### Basic ETL Run (Process All Datasets)

```bash
# Activate virtual environment
source .venv/bin/activate

# Run ETL with default settings
uv run dsh-etl etl

# With verbose logging
uv run dsh-etl etl --verbose
```

**What happens:**
1. Fetches all dataset identifiers from CEH Catalogue
2. Parses metadata (ISO19139, JSON, RDF, Schema.org)
3. Extracts text from PDFs and DOCX files
4. Generates embeddings for semantic search
5. Stores in database and vector store

#### ETL with Limit (Process N Datasets)

```bash
# Process only first 10 datasets (useful for testing)
uv run dsh-etl etl --limit 10

# Process first 100
uv run dsh-etl etl --limit 100

# With verbose output
uv run dsh-etl etl --limit 10 --verbose
```

**Use cases:**
- Testing configuration
- Development/debugging
- Small-scale processing

#### Dry Run Mode (Validate Without Committing)

```bash
# Validate ETL without saving to database
uv run dsh-etl etl --dry-run

# With limit
uv run dsh-etl etl --dry-run --limit 10 --verbose
```

**Output:**
- Validates all steps
- Shows what would be processed
- No data saved to database
- Useful for testing

#### Custom Dataset Identifiers

```bash
# Create file with dataset identifiers (one per line)
cat > custom_datasets.txt << 'EOF'
dataset-id-1
dataset-id-2
dataset-id-3
EOF

# Process only specified datasets
uv run dsh-etl etl --identifiers-file custom_datasets.txt --verbose
```

#### Control Processing Features

```bash
# Disable supporting documents processing
uv run dsh-etl etl --no-enable-supporting-docs

# Disable data files extraction
uv run dsh-etl etl --no-enable-data-files

# Both disabled
uv run dsh-etl etl --no-enable-supporting-docs --no-enable-data-files
```

### ETL Command Options Reference

| Option | Default | Description |
|--------|---------|-------------|
| `--limit N` | None | Process only N datasets |
| `--verbose` / `-v` | false | Enable DEBUG logging |
| `--dry-run` | false | Validate without saving |
| `--identifiers-file FILE` | None | File with dataset IDs |
| `--enable-supporting-docs` | true | Process supporting docs |
| `--enable-data-files` | true | Extract data files |

### Complete ETL Examples

**Scenario 1: Test run with first 5 datasets**
```bash
uv run dsh-etl etl --limit 5 --verbose --dry-run
```

**Scenario 2: Production run (all datasets, no verbose)**
```bash
uv run dsh-etl etl
```

**Scenario 3: Process specific datasets**
```bash
echo "dataset-123" > datasets.txt
echo "dataset-456" >> datasets.txt
uv run dsh-etl etl --identifiers-file datasets.txt --verbose
```

**Scenario 4: Fast processing (no docs, limited)**
```bash
uv run dsh-etl etl --limit 100 --no-enable-supporting-docs
```

### ETL Output & Logging

**Log Location:** `./logs/app.log`

**View logs in real-time:**
```bash
tail -f logs/app.log

# Follow with grep for errors
tail -f logs/app.log | grep -i error
```

**Sample log output:**
```
2025-01-09 10:23:45 INFO     Starting ETL pipeline
2025-01-09 10:23:46 INFO     Processing batch 1/10
2025-01-09 10:23:47 INFO     Extracted 10 dataset identifiers
2025-01-09 10:23:52 INFO     Parsed metadata for 10 datasets
2025-01-09 10:24:15 INFO     Generated embeddings (0.42s)
2025-01-09 10:24:16 INFO     Loaded 10 records to database
2025-01-09 10:24:16 INFO     ETL complete: 10 processed, 0 errors
```

### ETL Performance Metrics

The ETL command displays a summary:

```
Pipeline Results             
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                         ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Identifiers              │     5 │
│ Successfully Processed         │     5 │
│ Failed                         │     0 │
│ Metadata Extracted             │     5 │
│ Supporting Docs Found          │     5 │
│ Supporting Docs Downloaded     │     5 │
│ Text Extracted                 │     5 │
│ Data Files Extracted           │    14 │
│ Data Files Stored              │    14 │
│                                │       │
│ Cache Hits                     │     5 │
│ Cache Misses                   │    15 │
│ Hit Rate                       │ 25.0% │
│ Duration (seconds)             │  4.66 │
└────────────────────────────────┴───────┘

Cache Breakdown by Metadata Type:
 Format           Hits  Misses  Hit Rate 
 XML                 5       0    100.0% 
 JSON                0       5      0.0% 
 RDF                 0       5      0.0% 
 SCHEMA_ORG          0       5      0.0% 

 Indexing Results              
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Metric                         ┃  Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Total Datasets                 │      5 │
│ Successfully Indexed           │      5 │
│ Failed                         │      0 │
│ Success Rate                   │ 100.0% │
│ Duration (seconds)             │   0.14 │
└────────────────────────────────┴────────┘

✓ Indexing completed successfully

✓ ETL Pipeline completed successfully

```

**Optimization Tips:**
- Increase `ETL_BATCH_SIZE` for faster processing (default: 10)
- Enable GPU with `EMBEDDING_DEVICE=cuda` for embeddings
- Increase `MAX_CONCURRENT_DOWNLOADS` for network parallelism
- Run in production environment (no debug mode)

---

## CLI Commands Reference

Complete list of available CLI commands:

### ETL Command

```bash
uv run dsh-etl etl [OPTIONS]

Options:
  --limit INTEGER                    Maximum number of datasets to process
  --verbose / -v                     Enable verbose (DEBUG) logging
  --dry-run                          Validate without committing to database
  --identifiers-file TEXT            File with dataset identifiers (one/line)
  --enable-supporting-docs / --no-enable-supporting-docs
                                     Process supporting documents
  --enable-data-files / --no-enable-data-files
                                     Extract dataset data files
  --help                             Show help message
```

### Validate Config Command

```bash
uv run dsh-etl validate-config

Purpose: Verify environment configuration
Output:
  ✓ Configuration loaded
  ✓ Required directories exist
  ✓ Database accessible
  ✓ Embedding model available
  ✓ API endpoints reachable
```

### Initialize Database Command

```bash
uv run dsh-etl init-db

Purpose: Create SQLite database schema
Output:
  ✓ Database created
  ✓ Schema initialized
  ✓ Tables created
```

### Index Command

```bash
uv run dsh-etl index [OPTIONS]

Options:
  --limit INTEGER                    Maximum datasets to index
  --rebuild / --no-rebuild           Rebuild entire index
  --force                            Force re-indexing
  --verbose / -v                     Enable verbose logging

Purpose: Generate vector embeddings for semantic search
```

### Check Supporting Docs Command

```bash
uv run dsh-etl check-supporting-docs [OPTIONS]

Options:
  --sample-size INTEGER              Number of docs to check (default: 10)
  --verbose / -v                     Verbose output

Purpose: Validate supporting document extraction
```

### Vectorize Supporting Docs Command

```bash
uv run dsh-etl vectorize-supporting-docs [OPTIONS]

Options:
  --limit INTEGER                    Max documents to vectorize
  --rebuild / --no-rebuild           Rebuild vector index
  --device TEXT                      'cpu' or 'cuda'
  --verbose / -v                     Verbose logging

Purpose: Create embeddings for supporting documents
```

### Help Command

```bash
# Show all available commands
uv run dsh-etl --help

# Show help for specific command
uv run dsh-etl etl --help
```

---

## API Server

### Starting the API Server

```bash
# Development mode (auto-reload on file changes)
uv run python main.py

# Or explicitly with uvicorn
uv run uvicorn main:app --reload

# Production mode (no reload, no debug)
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### API Endpoints

**Base URL:** http://localhost:8000

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/docs` | GET | Swagger UI (interactive API documentation) |
| `/openapi.json` | GET | OpenAPI specification (JSON) |
| `/redoc` | GET | ReDoc API documentation |
| `/health` | GET | Health check |
| `/api/search` | POST | Search across datasets |
| `/api/chat` | POST | AI chat interface |

### Access Swagger UI

Open browser: **http://localhost:8000/docs**

This provides an interactive interface to:
- View all available endpoints
- Try API calls directly
- See request/response examples
- Explore data models

### API Configuration

Configured in `.env`:

```env
API_HOST=0.0.0.0        # Listen address
API_PORT=8000           # Port number
DEBUG=true              # Enable debug mode
```

### Running API in Background

**macOS/Linux:**
```bash
# Start in background
nohup uv run python main.py > api.log 2>&1 &

# Check status
ps aux | grep main.py

# View logs
tail -f api.log

# Stop process
kill <PID>
```

**Windows (PowerShell):**
```powershell
# Start in background
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run python main.py" -RedirectStandardOutput "api.log"

# View logs
Get-Content api.log -Wait
```

---

## Troubleshooting

### Common Issues & Solutions

#### 1. Python Version Mismatch

**Problem:** 
```
RuntimeError: Python 3.10 is less than minimum required 3.11
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.12
brew install python@3.12              # macOS
sudo apt-get install python3.12       # Linux
# Windows: Download from python.org

# Update symlink
python3 --version  # Try python3 instead
```

#### 2. UV Installation/Permission Issues

**Problem:**
```
Permission denied while trying to connect to Docker daemon
uv: command not found
```

**Solution:**
```bash
# Reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH (macOS/Linux)
export PATH="$HOME/.local/bin:$PATH"

# Verify
uv --version
```

#### 3. Virtual Environment Not Activated

**Problem:**
```
ModuleNotFoundError: No module named 'fastapi'
uv: command not found
```

**Solution:**
```bash
# Verify activation
which python  # Should show .venv path

# Activate properly
source .venv/bin/activate             # macOS/Linux
.venv\Scripts\activate                # Windows

# If still not working, recreate
rm -rf .venv
uv venv
source .venv/bin/activate
uv sync
```

#### 4. Dependency Installation Fails

**Problem:**
```
error: failed to build wheels for torch
```

**Solution:**
```bash
# For M1/M2 Mac
ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future uv sync

# For Linux, ensure build tools installed
sudo apt-get install build-essential python3.12-dev

# Clear cache
uv sync --reinstall-package torch
```

#### 5. Database Lock Error

**Problem:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Kill any existing processes
pkill -f cli_main.py
pkill -f main.py

# Remove lock file
rm -f data/datasets.db-journal

# Reinitialize
uv run dsh-etl init-db
```

#### 6. CEH API Connection Timeout

**Problem:**
```
requests.exceptions.ConnectTimeout: HTTPConnectionPool(host='catalogue.ceh.ac.uk')
```

**Solution:**
```bash
# Check connectivity
curl -I https://catalogue.ceh.ac.uk

# Increase timeout in .env
CEH_API_TIMEOUT=900              # 15 minutes
HTTP_TIMEOUT=900
CEH_API_MAX_RETRIES=10

# Test with dry-run
uv run dsh-etl etl --dry-run --limit 1 --verbose
```

#### 7. Ollama Not Running

**Problem:**
```
ollama.ResponseError: ('Connection aborted.', RemoteDisconnected())
```

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama (macOS)
/Applications/Ollama.app/Contents/MacOS/ollama serve

# Or use background
nohup ollama serve > ollama.log 2>&1 &

# Pull required model
ollama pull mistral

# Verify
ollama list
```

#### 8. Out of Memory Error

**Problem:**
```
RuntimeError: CUDA out of memory
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**Solution:**
```bash
# Disable GPU (use CPU)
EMBEDDING_DEVICE=cpu

# Or reduce batch size
EMBEDDING_BATCH_SIZE=16              # Default: 32
EMBEDDING_BATCH_SIZE=8               # Even smaller

# Restart
uv run dsh-etl etl --limit 10 --verbose
```

#### 9. Port Already in Use

**Problem:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000                         # macOS/Linux
netstat -ano | findstr :8000          # Windows

# Kill process
kill -9 <PID>                         # macOS/Linux
taskkill /PID <PID> /F               # Windows

# Use different port
uv run uvicorn main:app --port 8001
```

#### 10. .env File Not Found

**Problem:**
```
Configuration error: .env file not found
Variables not loaded
```

**Solution:**
```bash
# Copy example
cp .env.example .env

# Verify in backend directory
ls -la .env

# Load explicitly
export $(cat .env | xargs)
uv run dsh-etl etl
```

### Debugging Mode

Enable maximum verbosity for troubleshooting:

```bash
# Set all debugging flags
export DEBUG=true
export LOG_LEVEL=DEBUG
export DATABASE_ECHO=true

# Run with verbose
uv run dsh-etl etl --verbose --dry-run --limit 1

# Watch logs
tail -f logs/app.log
```

### Health Check

Verify system health:

```bash
# Validate configuration
uv run dsh-etl validate-config

# Check database
sqlite3 data/datasets.db ".tables"
sqlite3 data/datasets.db "SELECT COUNT(*) FROM datasets;"

# Check vector store
ls -lh data/chroma/

# Check logs
tail -20 logs/app.log

# Test API
curl http://localhost:8000/health
```

### Performance Troubleshooting

**Slow ETL Processing:**
```bash
# Check system resources
top                                   # macOS/Linux
Resource Monitor                      # Windows

# Profile with timing
time uv run dsh-etl etl --limit 10

# Increase parallelism in .env
MAX_CONCURRENT_DOWNLOADS=10           # Default: 5
ETL_BATCH_SIZE=20                     # Default: 10
```

**Slow Embeddings:**
```bash
# Use GPU if available
EMBEDDING_DEVICE=cuda

# Increase batch size
EMBEDDING_BATCH_SIZE=64               # Default: 32

# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"
```

### Log Analysis

**Find errors:**
```bash
grep -i error logs/app.log

# Show context (5 lines before/after)
grep -i error -C 5 logs/app.log

# Show recent errors
tail -100 logs/app.log | grep -i error
```

---

## Advanced Configuration

### Performance Tuning

#### For Large Datasets

```env
# Increase batch processing
ETL_BATCH_SIZE=50               # Process 50 at a time
MAX_CONCURRENT_DOWNLOADS=10     # 10 parallel downloads

# Embeddings optimization
EMBEDDING_BATCH_SIZE=64         # Larger batches = faster
EMBEDDING_DEVICE=cuda           # Use GPU if available

# API timeouts (allow more time)
CEH_API_TIMEOUT=900             # 15 minutes
HTTP_TIMEOUT=900
CEH_API_MAX_RETRIES=10

# Database optimization
DATABASE_ECHO=false             # Disable SQL logging
```

#### For Low Resource Environments

```env
# Reduce resource usage
ETL_BATCH_SIZE=5                # Smaller batches
MAX_CONCURRENT_DOWNLOADS=2      # Sequential-ish

# CPU-only embeddings
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=8          # Small batches

# Smaller models
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Lightweight model

# Longer timeouts
CEH_API_TIMEOUT=1200            # 20 minutes
```

### Database Optimization

**Enable Query Logging:**
```env
DATABASE_ECHO=true
```

View all SQL queries in logs for performance analysis.

**Backup Database:**
```bash
# Create backup
cp data/datasets.db data/datasets.db.backup

# Restore from backup
cp data/datasets.db.backup data/datasets.db
```

**Check Database Size:**
```bash
# Check file size
du -h data/datasets.db

# Check record counts
sqlite3 data/datasets.db "SELECT name, COUNT(*) FROM sqlite_master WHERE type='table' GROUP BY name;"
```

### Distributed Tracing Setup

**Enable OpenTelemetry tracing:**

```bash
# 1. Start OpenTelemetry Collector (Docker required)
docker run --rm \
  -p 4317:4317 \
  -p 16686:16686 \
  -v $(pwd)/otel-config.yaml:/etc/otel/config.yaml \
  otel/opentelemetry-collector:latest

# 2. Update .env
JAEGER_ENABLED=true
JAEGER_HOST=localhost
JAEGER_PORT=4317

# 3. View traces
# Access Jaeger UI: http://localhost:16686
```

### Custom Models & Configurations

**Use Different Embedding Model:**

```env
# Larger, more accurate model (slower)
EMBEDDING_MODEL=all-MiniLM-L12-v2

# GPU-optimized
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Use Different LLM:**

```bash
# Pull different model
ollama pull neural-chat
ollama pull llama2

# Configure in .env
OLLAMA_MODEL=neural-chat
```

### Monitoring & Observability

**Real-time Log Monitoring:**

```bash
# Follow logs with highlighting
tail -f logs/app.log | grep --line-buffered -E "ERROR|WARNING|INFO"

# Search for specific operations
grep -E "EXTRACT|TRANSFORM|LOAD" logs/app.log

# Count by level
grep -o "ERROR\|WARNING\|INFO" logs/app.log | sort | uniq -c
```

**Metrics Collection:**

OpenTelemetry automatically collects:
- Request latency
- Error rates
- Batch processing times
- Database query times
- Embedding generation times

---

## Best Practices & Recommendations

### For System Administrators

1. **Regular Backups**
   ```bash
   # Daily backup script
   cp -r data/datasets.db data/datasets.db.$(date +%Y%m%d)
   ```

2. **Monitor Disk Space**
   ```bash
   # Check space (especially data/chroma/ grows large)
   du -sh data/*
   ```

3. **Log Rotation**
   - Logs in `./logs/app.log` grow over time
   - Consider logrotate on production

4. **Resource Monitoring**
   - Monitor memory usage (torch/embeddings are memory-intensive)
   - Monitor CPU during ETL processing

### For Developers

1. **Development Setup**
   ```bash
   uv sync --group dev
   ```

2. **Testing**
   ```bash
   pytest tests/
   pytest tests/unit/ -v
   ```

3. **Code Formatting**
   ```bash
   black src/
   ruff check src/
   ```

### For DevOps/Deployment

1. **Use UV for reproducibility**
   ```bash
   uv export > requirements.txt  # Generate pip-compatible file
   ```

2. **Container Support**
   ```bash
   docker build -f Dockerfile -t dsh-etl:latest .
   docker run -d -p 8000:8000 dsh-etl:latest
   ```

3. **Systemd Service** (Linux)
   Create `/etc/systemd/system/dsh-etl.service`:
   ```ini
   [Unit]
   Description=DSH ETL Service
   After=network.target

   [Service]
   Type=simple
   User=dsh
   WorkingDirectory=/opt/dsh-etl/backend
   ExecStart=/usr/local/bin/uv run python main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable:
   ```bash
   sudo systemctl enable dsh-etl
   sudo systemctl start dsh-etl
   ```

---

## Support & Additional Resources

### Documentation Files

- Root README: `../README.md`
- Docker Setup: `../docker-compose.yml`
- Start Scripts: `../start-all.sh`

### External Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Pydantic Docs**: https://docs.pydantic.dev
- **ChromaDB Docs**: https://docs.trychroma.com
- **UV Documentation**: https://astral.sh/uv
- **Ollama**: https://ollama.ai
- **CEH Catalogue API**: https://www.ceh.ac.uk

### Quick Reference

```bash
# Common commands summary
source .venv/bin/activate           # Activate environment
uv sync                             # Install dependencies
uv run dsh-etl validate-config     # Check configuration
uv run dsh-etl init-db             # Initialize database
uv run dsh-etl etl --limit 10      # Run ETL on 10 datasets
uv run python main.py               # Start API server
tail -f logs/app.log               # Monitor logs
```

---

## Version Information

| Component | Version | Date |
|-----------|---------|------|
| Python | 3.12 | 2025-01-09 |
| FastAPI | ≥0.115.0 | 2025-01-09 |
| ChromaDB | ≥0.5.0 | 2025-01-09 |
| UV | Latest | 2025-01-09 |

---

**Last Updated:** January 9, 2025  
**Document Version:** 1.0  
**Status:** Production Ready

For issues or updates, please refer to the project repository or contact the development team.
