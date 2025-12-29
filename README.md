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
