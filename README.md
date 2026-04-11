# DSH ETL Search & AI - Dataset Discovery Platform

**Production-ready platform for CEH dataset discovery with ETL pipeline, semantic search, and AI chat interface.**

> **Quick Start:** Run `./start-all.sh` to launch the complete system  
> Then open **http://localhost:5173** to access the web interface

---

## System Overview

**DSH ETL Search AI** is a comprehensive solution for dataset management and discovery:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Python 3.12 + FastAPI | ETL pipeline, REST API, semantic search |
| **Frontend** | SvelteKit 5 + TypeScript | Responsive web UI with chat interface |
| **Database** | SQLite + ChromaDB | Structured data + vector embeddings |
| **LLM** | Ollama (Mistral) | AI-powered chat with context retrieval |

---

## Core Features

✅ **ETL Pipeline** - Automated extract, transform, load from CEH API  
✅ **Semantic Search** - Vector-based search with 384-dim embeddings  
✅ **RAG Chat** - AI conversations with document context  
✅ **Modern UI** - SvelteKit frontend with dark mode  
✅ **Vector Store** - ChromaDB for fast semantic matching  
✅ **Observability** - OpenTelemetry tracing & structured logging  
✅ **REST API** - Fully documented with Swagger/ReDoc  

---

## Quick Start

### Prerequisites

- **Python**: 3.11+ (3.12 recommended)
- **Node.js**: 16+ (18+ recommended)
- **uv**: Latest version ([install](https://astral.sh/uv))
- **Ollama** (optional): For AI chat features

### Setup & Run

**Option 1: Run Everything (Recommended)**

```bash
# Start backend ETL + API + frontend in one command
./start-all.sh

# Or with custom dataset limit
./start-all.sh 50    # Process first 50 datasets

# Access UI at http://localhost:5173
```

**Option 2: Manual Setup**

```bash
# Terminal 1: Backend ETL Pipeline
cd backend
uv sync
uv run dsh-etl etl --limit 100 --verbose

# Terminal 2: Backend API Server
cd backend
uv run python main.py
# API available at http://localhost:8000

# Terminal 3: Frontend Dev Server
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

---

## Directory Structure

```
dsh-etl-search-ai-2025/
├── backend/                    # Python FastAPI backend
│   ├── README.md              # Detailed backend setup guide
│   ├── src/
│   │   ├── cli.py            # CLI commands (dsh-etl)
│   │   ├── config.py         # Configuration settings
│   │   └── api/              # REST API endpoints
│   ├── pyproject.toml        # Python dependencies
│   └── main.py               # API entry point
│
├── frontend/                   # SvelteKit web UI
│   ├── README.md             # Detailed frontend setup guide
│   ├── src/
│   │   ├── routes/           # Page components
│   │   ├── lib/              # Reusable components & services
│   │   └── app.html          # Main template
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Build configuration
│
├── docker-compose.yml        # Multi-container setup
├── start-all.sh              # One-command startup script
└── README.md                 # This file
```

---

## Detailed Documentation

For comprehensive setup and troubleshooting, refer to component READMEs:

- **[Backend README](./backend/README.md)** - Python, dependencies, ETL pipeline, CLI commands, API server, troubleshooting
- **[Frontend README](./frontend/README.md)** - Node.js, npm scripts, SvelteKit setup, component structure, deployment

---

## Key CLI Commands

### Backend Commands

```bash
cd backend

# Validate configuration
uv run dsh-etl validate-config

# Run ETL pipeline (extract, transform, load)
uv run dsh-etl etl --limit 100 --verbose

# Dry-run ETL (validate without saving)
uv run dsh-etl etl --dry-run --limit 10

# Initialize database
uv run dsh-etl init-db

# Generate embeddings for semantic search
uv run dsh-etl index --rebuild

# Start REST API server
uv run python main.py
```

### Frontend Commands

```bash
cd frontend

# Start dev server with hot reload
npm run dev

# Type checking
npm run check

# Production build
npm run build

# Preview production build
npm run preview
```

---

## API Endpoints

**Base URL:** http://localhost:8000

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/docs` | GET | Interactive Swagger UI |
| `/openapi.json` | GET | OpenAPI specification |
| `/api/search` | POST | Search datasets |
| `/api/chat` | POST | AI chat with context |
| `/health` | GET | Health check |

**Access API docs:** http://localhost:8000/docs

---

## Environment Configuration

Both backend and frontend use `.env` files for configuration:

**Backend** (`backend/.env`):
```env
VITE_API_URL=http://localhost:8000
CEH_API_BASE_URL=https://catalogue.ceh.ac.uk
OLLAMA_HOST=http://localhost:11434
EMBEDDING_DEVICE=cpu        # or cuda for GPU
```

**Frontend** (`frontend/.env.local`):
```env
VITE_API_URL=http://localhost:8000
```

See component READMEs for complete configuration options.

---

## Docker Deployment

### Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Build Docker Images

```bash
# Backend
docker build -f backend/Dockerfile -t dsh-backend:latest .

# Frontend
docker build -f frontend/Dockerfile -t dsh-frontend:latest .
```

---

## Development Workflow

### Setting Up Development Environment

```bash
# Backend development
cd backend
uv sync --group dev      # Install with dev tools
npm run check:watch      # Type checking in watch mode

# Frontend development
cd frontend
npm install
npm run check:watch      # Watch TypeScript errors
npm run dev              # Start with hot reload
```

### Testing

```bash
cd backend
pytest tests/            # Run all tests
pytest tests/unit/ -v    # Run unit tests with verbose
```

### Code Quality

```bash
cd backend
black src/               # Format code
ruff check src/          # Lint check

cd frontend
npm run check            # Type checking
```

---

## Common Issues

### API Connection Failed

```bash
# 1. Verify backend is running
curl http://localhost:8000/docs

# 2. Check frontend .env.local
cat frontend/.env.local

# 3. Check browser console (F12) for errors
```

### ETL Pipeline Timeout

```bash
# 1. Check backend logs
tail -f backend/logs/app.log

# 2. Increase timeout in backend/.env
CEH_API_TIMEOUT=900      # 15 minutes

# 3. Run with smaller limit
uv run dsh-etl etl --limit 10 --verbose
```

### Ollama Not Available

```bash
# 1. Verify Ollama is running
curl http://localhost:11434/api/tags

# 2. Start Ollama
ollama serve

# 3. Pull required model
ollama pull mistral
```

### Port Already in Use

```bash
# Backend port 8000
lsof -i :8000
kill -9 <PID>

# Frontend port 5173
lsof -i :5173
kill -9 <PID>
```

For more troubleshooting, see component READMEs.

---

## Architecture

### Data Flow

```
CEH API
  ↓
[ETL Pipeline] Extract → Parse → Validate
  ↓
[SQLite Database] Store metadata, relationships
  ↓
[Embedding Generator] Create 384-dim vectors
  ↓
[ChromaDB Vector Store] Index for semantic search
  ↓
[REST API] Serve search & chat requests
  ↓
[Web UI] Display results & chat interface
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | SvelteKit 5, Vite, Tailwind CSS, TypeScript |
| **Backend** | Python 3.12, FastAPI, Pydantic |
| **Vectorization** | sentence-transformers, ChromaDB |
| **LLM** | Ollama, Mistral 7B |
| **Database** | SQLite, aiosqlite |
| **Observability** | OpenTelemetry, Prometheus |
| **Infrastructure** | Docker, Docker Compose |

---

## Performance Notes

- **Embedding Generation**: ~0.3s per dataset (CPU optimized)
- **ETL Pipeline**: ~0.5s average per dataset
- **Search Query**: <100ms average response time
- **Chat Response**: 5-30s depending on context size

### Optimization Tips

- Use GPU for embeddings: `EMBEDDING_DEVICE=cuda`
- Increase batch size for faster processing
- Run on machine with ≥8GB RAM
- Use production build for frontend

---

## Support & Resources

- **Backend Documentation**: [backend/README.md](./backend/README.md)
- **Frontend Documentation**: [frontend/README.md](./frontend/README.md)
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SvelteKit Docs**: https://svelte.dev/docs/kit
- **CEH Catalogue**: https://catalogue.ceh.ac.uk

---

## License & Attribution

**Built with:**
- Python & FastAPI ecosystem
- SvelteKit & modern web stack
- OpenTelemetry for observability
- ChromaDB for vector search

---

For detailed setup, configuration, and troubleshooting, see component-specific READMEs.
