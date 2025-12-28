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

## Current status (Issue #1 scope)

Issue #1 is focused on **backend project setup**, including:
- dependency management via `uv` and `pyproject.toml`
- a clean folder structure aligned with layered architecture
- environment configuration via `.env` (local) + `.env.example` (template)
- structured logging setup
- a small `main.py` smoke test to verify config/logging

### What the current backend code does

- `backend/src/config.py`
  - Defines a `Settings` object (Pydantic Settings) that loads configuration from environment variables and `.env`
  - Provides `get_settings()` which caches settings for reuse across the app

- `backend/src/logging_config.py`
  - Provides a structured log formatter and `setup_logging()` helper
  - Provides `get_logger()` helper for consistent logging across modules

- `backend/main.py`
  - Smoke test entry point:
    - loads settings
    - configures logging
    - logs key configuration values to confirm `.env` loading works

---

## Repo structure (today)

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
│   │   ├── repositories/
│   │   ├── models/
│   │   └── infrastructure/
│   └── tests/
└── frontend/               # will be added in later issues
```

---

## Getting started (backend)

## Setup

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
uv init backend
cd backend

# Install dependencies
uv sync
```

### 3. Configure environment
```bash
cp .env.example .env
```

### 4. Run the smoke test
```bash
uv run python main.py
```

If successful, you should see structured log lines confirming configuration was loaded.

---
## License

MIT
