# DSH ETL SEARCH AI 2025

Dataset search and discovery solution with **ETL**, **semantic search**, and optional **conversational (RAG) chat** capabilities, developed for CEH(UK Center for Ecology and Hydrology) catalogue. 

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
│                 (python -m src.cli etl)                         │
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

### with Small Dataset

**Command:**
```bash
uv run python -m src.cli etl --limit 3 --verbose --enable-data-files
```

**What happens:**
1. Reads first 3 identifiers from `metadata-file-identifiers.txt`
2. For each identifier:
   - Attempts to fetch metadata (XML → JSON → RDF → Schema.org)
   - Caches result (25% hit rate if re-run)
   - Parses metadata with appropriate parser
   - Stores dataset in database
   - Extracts data files from ZIPs or web folders
   - Downloads supporting documents
   - Extracts text from documents

**Duration:** ~2-5 seconds per identifier (depends on network and file sizes)

### Step 3: Run with Supporting Documents

```bash
uv run python -m src.cli etl --limit 3 --enable-data-files --enable-supporting-docs
```

**Additional output:**
- Supporting documents discovered
- Documents downloaded
- Text extracted from each document

### Step 4: Dry-Run Mode (No Database Writes)

```bash
uv run python -m src.cli etl --limit 3 --dry-run --verbose
```

**Use case:** Test without committing to database

### Step 5: Full Pipeline

```bash
uv run python -m src.cli etl --enable-data-files --enable-supporting-docs --verbose
```

### Sample Test Run Output

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

[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ XML fetch SUCCESS (cached)
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Parsed: "UK Environmental Change Network..."
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Found 12 supporting docs
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Downloaded 12 docs
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Extracted text from 12 docs
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Found 3 data files
[be0bdc0e-bc2e-4f1d-b524-2c02798dd893] ✓ Stored 3 files

[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ XML fetch SUCCESS (cached)
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Parsed: "CEH Species Distribution..."
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Found 8 supporting docs
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Downloaded 8 docs
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Extracted text from 8 docs
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Found 2 data files
[af6c4679-99aa-4352-9f63-af3bd7bc87a4] ✓ Stored 2 files

[3aaa52d3-918a-4f95-b065-32f33e45d4f6] ✓ XML fetch SUCCESS (cache miss)
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
│                                │       │
│ Cache Hits                     │     3 │
│ Cache Misses                   │     0 │
│ Hit Rate                       │ 100%  │
│ Duration (seconds)             │  2.32 │
└────────────────────────────────┴───────┘

Cache Breakdown by Metadata Type:
 Format           Hits  Misses  Hit Rate
 XML                 3       0    100.0%
 JSON                0       0      0.0%
 RDF                 0       0      0.0%
 SCHEMA_ORG          0       0      0.0%

✓ Data successfully committed to database

✓ ETL Pipeline completed successfully
```

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
