# DSH ETL SEARCH AI 2025

Dataset search and discovery solution with **ETL**, **semantic search**, and optional **conversational (RAG) chat** capabilities, developed for CEH(UK Center for Ecology and Hydrology) catalogue. 

> **🚀 QUICK START**: Run one command to start everything (ETL + API + Frontend):
> ```python
> ./start-all.sh 
> #./start-all.sh 50 # run for 50 identifiers
> ```
> Then open http://localhost:5173 and search for datasets!

## Status: ✅ COMPLETE & INTEGRATED

- ✅ ETL Pipeline (Extract → Transform → Load)
- ✅ Vector Embeddings (384-dim with all-MiniLM-L6-v2)
- ✅ Semantic Search (ChromaDB vector store)
- ✅ Search API (FastAPI with validation)
- ✅ Frontend Integration (Svelte search UI connected)
- ✅ One-command startup script

---

This repository is a **mono-repo** and will contain:
- `backend/` — Python services for ETL, storage, embeddings, semantic search, and API
- `frontend/` — Svelte web app (to be added) for semantic search + chat UI
- `docs/` — Chat conversation with git copilot through out development of the project
- `data/` — Will contain the database files.
---

## Task summary

The goal is to build a working prototype that demonstrates:
1. **ETL subsystem** to extract dataset metadata (and optionally datasets/supporting docs) from the **CEH Catalogue Service** for a given list of dataset file identifiers.
2. **Structured storage** in **SQLite**:
   - store the full metadata documents (raw XML/JSON/etc.)
   - extract key fields (at minimum: **title** and **abstract**, plus identifiers and relationships)
   - model relationships between datasets, metadata documents, and data/supporting files
3. **Semantic database**:
   - generate vector embeddings for titles/abstracts (and optionally supporting documents)
   - store embeddings in a vector store to enable semantic search + RAG
4. **Search & discovery frontend**:
   - web app with semantic search and natural language queries
   - bonus: conversational assistant to help discover datasets

The evaluation focuses on **software engineering practices and evolution**, not only a final solution.

---

## Tech Stack

### Backend (Python)
- **Python 3.11+**
- **uv** (dependency + Python version management)
- **FastAPI** (API layer)
- **SQLite** (metadata & relationships store)
- **ChromaDB** (vector store)
- **sentence-transformers** (embeddings)
- **Ollama** (local LLM for chat/RAG, optional)

### Frontend (to be added)
- **Svelte / SvelteKit**
- **shadcn-svelte** UI components
- **Tailwind CSS**

---

## Repo structure

```
dsh-etl-search-ai-2025/
├── backend/
│   ├── pyproject.toml
│   ├── .python-version
│   ├── uv.lock
│   ├── .env.example
│   ├── .env                # not committed
│   ├── main.py
│   ├── src/
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   ├── api/
│   │   ├── services/
│   │   │   ├── extractors/
│   │   │   ├── parsers/
│   │   │   ├── document_extraction/
│   │   │   ├── supporting_documents/
│   │   │   ├── etl/
│   │   │   ├── observability/
│   │   │   ├──parsers/
│   │   ├── repositories/
│   │   ├── models/
│   │   └── infrastructure/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── svelte.config.js
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── components.json            # shadcn-svelte config
│   ├── src/
│   │   ├── app.css                # Tailwind + theme tokens
│   │   ├── app.d.ts
│   │   ├── app.html
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   ├── stores/
│   │   │   ├── custom/
│   │   │   ├── utils.ts
│   │   │   └── components/
│   │   │       └── ui/             # shadcn components (button, input, card, badge, scroll-area)
│   │   └── routes/
│   │       ├── +layout.svelte
│   │       ├── +page.svelte        # smoke test page
│   │       └── layout.css
│   └── static/
│       └── robots.txt
├── docs/                           # development notes / chat logs
└── README.md
```
---

## Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                           │
│              (python cli_main.py etl ...)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │     ETL Service (Orchestrator)        │
         │  - Coordinates 3-phase pipeline       │
         │  - Manages errors & retries           │
         │  - Tracks metrics                     │
         └───────────────────┬───────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         │                                       │
   ┌─────▼────────┐  ┌──────────────┐  ┌───────▼─────┐
   │   EXTRACT    │  │  TRANSFORM   │  │    LOAD     │
   ├──────────────┤  ├──────────────┤  ├─────────────┤
   │ CEH API      │  │ 4 Parsers:   │  │ Database    │
   │ Metadata     │  │ • ISO19139   │  │ Upsert:     │
   │ Cache        │  │ • JSON       │  │ • Datasets  │
   │              │  │ • RDF        │  │ • Metadata  │
   │              │  │ • Schema.org │  │ • DataFiles │
   │              │  │              │  │ • Supp.Docs │
   └─────┬────────┘  └──────────────┘  └─────┬───────┘
         │                                    │
         └────────────────┬───────────────────┘
                          │
           ┌──────────────▼──────────────┐
           │  Data Extractors            │
           ├─────────────────────────────┤
           │ • ZipExtractor              │
           │ • WebFolderTraverser        │
           │ • DatasetFileExtractor      │
           └──────────────┬──────────────┘
                          │
           ┌──────────────▼──────────────┐
           │  Supporting Docs Pipeline   │
           ├─────────────────────────────┤
           │ • Discoverer (find URLs)    │
           │ • Downloader (fetch files)  │
           │ • TextExtractor (PDF/DOCX)  │
           └─────────────────────────────┘
```

### Infrastructure Layers

```
┌─────────────────────────────────────────┐
│        Application Layer                │
│  (CLI, ETL Service, Business Logic)     │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│        Services Layer                   │
│  ┌─────────────────────────────────────┐│
│  │ Extractors: CEH, ZIP, Web, Files    ││
│  │ Parsers: ISO19139, JSON, RDF, etc   ││
│  │ Document Extraction: PDF, DOCX, TXT ││
│  │ Supporting Docs: Discover, Download ││
│  │ Observability: Tracing, Logging     ││
│  └─────────────────────────────────────┘│
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Infrastructure Layer                │
│  ┌─────────────────────────────────────┐ │
│  │ Database: SQLite with relationships │ │
│  │ HTTP Client: Async, retries, cache  │ │
│  │ Metadata Cache: TTL-based,persistent│ │
│  │ Repositories: CRUD for all entities │ │
│  │ Unit of Work: Transaction management│ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## Getting started

## Backend Setup

### 1. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

From the repository root:

### 2. Install dependencies
```bash
# uv init backend 
cd backend

# (optional) initialize project with uv if not already initialized
# uv init

# Install dependencies
uv sync
```

### 3. Configure environment
```bash
# copy the service-specific example into backend/.env and edit values locally
cp backend/.env.example backend/.env
```

### 4. Run the smoke test
```bash
uv run python main.py
```

If successful, you should see structured log lines confirming configuration was loaded.

## Run Test ETL CLI

### Quick test with 3 datasets

```bash
cd backend && uv run python cli_main.py etl --limit 3
```

### With verbose output (shows per-dataset progress)

```bash
cd backend && uv run python cli_main.py etl --limit 3 --verbose
```

**What the `--verbose` flag shows:**
- Metadata fetch status (XML/JSON/RDF/Schema.org attempts)
- Parsed dataset title  
- Supporting documents found/downloaded/extracted counts
- Data files found/stored counts
- Blank line between datasets for readability

### Full ETL with data files and supporting docs

```bash
cd backend && uv run python cli_main.py etl --limit 50 --enable-data-files --enable-supporting-docs --verbose
```

### Dry-run mode (no database writes)

```bash
cd backend && uv run python cli_main.py etl --limit 3 --dry-run --verbose
```

**Use case:** Test the full pipeline without committing to database

### Step 5: Full production run (all 600+ datasets)

```bash
cd backend && uv run python cli_main.py etl --enable-data-files --enable-supporting-docs
```

## Sample Test Run Output

When running `uv run python cli_main.py etl --limit 3 --verbose 2>&1 | grep "^\[" 2>&1`:

```
✓ Distributed tracing initialized

═══ DSH ETL Pipeline ═══
                                            Configuration
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting                        ┃ Value                                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Identifiers File               │ metadata-file-identifiers.txt            │
│ Database Path                  │ ./data/datasets.db                       │
│ Batch Size                     │ 10                                       │
│ Max Concurrent Downloads       │ 5                                        │
│ Limit                          │ 3                                        │
│ Supporting Docs                │ ✓ Enabled                                │
│ Dry Run                        │ ✗ No (will commit)                       │
│ Verbose                        │ ✓ Yes                                    │
│ Tracing                        │ ✓ Enabled                                │
└────────────────────────────────┴──────────────────────────────────────────┘
✓ Database initialized

→ Starting ETL Pipeline...

[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Parsed: "UK Environmental Change Network..."
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Found 12 supporting docs
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Downloaded 12 docs
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Extracted text from 12 docs
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Found 3 data files
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Stored 3 files

[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Parsed: "CEH Species Distribution..."
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Found 8 supporting docs
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Downloaded 8 docs
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Extracted text from 8 docs
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Found 2 data files
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Stored 2 files

[3aaa52d3-918a-4f95-b065-32f33e45d4f6] ✓ Parsed: "Long-term Air Quality..."
[3aaa52d3-918a-4f95-b065-32f33e45d4f6] ✓ Found 9 supporting docs
[3aaa52d3-918a-4f95-b065-32f33e45d4f6] ✓ Downloaded 9 docs
[3aaa52d3-918a-4f95-b065-32f33e45d4f6] ✓ Extracted text from 9 docs
[3aaa52d3-918a-4f95-b065-32f33e45d4f6] ✓ Found 4 data files
[3aaa52d3-918a-4f95-b065-32f33e45d4f6] ✓ Stored 4 files

═══ ETL Pipeline Complete ═══
             Pipeline Results
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                         ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Identifiers              │     3 │
│ Successfully Processed         │     3 │
│ Failed                         │     0 │
│ Metadata Extracted             │     3 │
│ Supporting Docs Found          │    29 │
│ Supporting Docs Downloaded     │    29 │
│ Text Extracted                 │    29 │
│ Data Files Extracted           │     9 │
│ Data Files Stored              │     9 │
│ Duration (seconds)             │  2.32 │
└────────────────────────────────┴───────┘

✓ Data successfully committed to database

✓ ETL Pipeline completed successfully
```

**What happened:**
- Fetched metadata for 3 datasets (XML/JSON/RDF formats attempted)
- Parsed titles and key metadata
- Discovered 29 supporting documents across 3 datasets
- Downloaded and extracted text from all 29 documents
- Extracted and stored 9 data files total
- All results committed to SQLite database

### step 6: Generate Embeddings and Test Search

Generate embeddings for the datasets:

```bash
cd backend && uv run python cli_main.py index --verbose
```

**Expected output:**
- Embeddings generated for 3 datasets using all-MiniLM-L6-v2 model
- ChromaDB vector store updated
- Check: `./data/chroma/` directory contains parquet files

Test semantic search:

```bash
cd backend && uv run python -c "
from src.services.embeddings import EmbeddingService, VectorStore
service = EmbeddingService()
store = VectorStore()
query = service.embed_text('climate data')
results = store.search_datasets(query, limit=3)
for r in results:
    print(f\"Score: {r['similarity_score']:.3f} - {r['metadata']['title']}\")
"
```

**Expected:** Returns 3 results with similarity scores > 0.5

---

## Quick Start with Startup Scripts

Instead of running ETL, Backend API, and Frontend separately, use the all-in-one startup script:

### Python version (recommended - cross-platform)

```bash
# Run everything: ETL (first 50 datasets) + Backend API + Frontend
python start-all.py --limit 50

# Options:
python start-all.py --limit 100             # Increase limit
python start-all.py --etl-only              # Only run ETL
python start-all.py --api-only              # Only run backend API
python start-all.py --backend-port 8001     # Custom backend port
python start-all.py --frontend-port 5174    # Custom frontend port
```

### Bash version (macOS/Linux)

```bash
# Run everything with first 50 datasets
./start-all.sh 50

# Full production run (all 600+ datasets)
./start-all.sh
```

**What happens:**
1. Runs ETL pipeline with specified dataset limit
2. Waits for ETL to complete (shows progress with --verbose)
3. Starts backend API server on port 8000
4. Starts frontend dev server on port 5173
5. Opens http://localhost:5173 in your browser

**View output:**
- Each component logs to console with color formatting
- Press `Ctrl+C` to stop all services

---

## Frontend (SvelteKit) — Setup

This project uses SvelteKit + TypeScript, Tailwind CSS and shadcn-svelte for UI components.

Quick start (from repo root)
1. Scaffold (if not already created):
```bash
#npx sv create frontend
cd frontend
npm install
```

2. Install Tailwind (if not added by scaffold):
```bash
npx sv add tailwindcss
npm install
```

3. Initialize shadcn-svelte and add base components:
```bash
npx shadcn-svelte@latest init
npx shadcn-svelte@latest add button input card badge scroll-area
```

4. Run dev server and verify:
```bash
cd frontend
npm run dev
# open http://localhost:5173 and confirm Tailwind styles and shadcn Button render
```

---
## License

MIT
