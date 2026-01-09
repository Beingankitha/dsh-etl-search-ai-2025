# System Architecture & Data Flow

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DSH ETL SEARCH AI 2025                                  │
│                          COMPLETE SYSTEM                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ EXTERNAL DATA SOURCE                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ CEH Catalogue (catalogue.ceh.ac.uk)                                    │  │
│ │ • REST API with 4 metadata formats: XML, JSON, RDF, Schema.org        │  │
│ │ • 1000+ environmental datasets                                        │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │ dataset IDs
                                 │ one per line
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────┐
│ COMMAND: python start-all.py                                                 │
│ (Or: python start-all.py --limit 50)                                        │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────────┐  ┌─────────────────────┐  ┌──────────────────┐
│ PHASE 1           │  │ PHASE 2             │  │ PHASE 3          │
│ ETL + INDEXING    │  │ BACKEND API         │  │ FRONTEND         │
│ (1-2 min)         │  │ (5 sec)             │  │ (10 sec)         │
└─────────┬─────────┘  └─────────┬───────────┘  └────────┬─────────┘
          │                      │                      │
          ▼                      ▼                      ▼
    ┌──────────┐           ┌──────────┐           ┌──────────┐
    │ EXTRACT  │           │ VALIDATE │           │ RENDER  │
    │ DATASET  │           │ REQUEST  │           │ UI      │
    │ METADATA │           │ (Pydantic)           │ (Svelte)│
    └─────┬────┘           └────┬─────┘           └────┬────┘
          │                     │                      │
          ▼                     ▼                      ▼
    ┌──────────┐           ┌──────────┐           ┌──────────┐
    │TRANSFORM │           │ GENERATE │           │ DISPATCH │
    │ TO MODEL │           │EMBEDDING │           │ REQUEST  │
    └─────┬────┘           │(all-Mini)│           └────┬─────┘
          │                └────┬─────┘                │
          │                     │                      │
          ▼                     ▼                      ▼
    ┌──────────┐           ┌──────────────┐        ┌─────────┐
    │ LOAD TO  │           │ SEARCH VECTOR│        │ CALL    │
    │ SQLITE   │           │ STORE        │        │ API     │
    │ DATABASE │           │ (ChromaDB)   │        └────┬────┘
    └─────┬────┘           └──────┬───────┘             │
          │                      │                      │
          │◄─────────────────────┘                      │
          │                                              │
          ▼                                              ▼
    ┌──────────────────────────────────────────┐   ┌────────────┐
    │ AUTO-INDEX (NEW)                         │   │HTTP POST  │
    │ • Load datasets from SQLite              │   │/api/search│
    │ • Generate embeddings (384-dim vectors) │   └─────┬──────┘
    │ • Store in ChromaDB                      │         │
    │ • Create search index                    │         ▼
    └─────────────────┬──────────────────────────────────────┐
                      │                                       │
                      └─────────────────────────┬─────────────┘
                                                │
                                    ┌───────────▼─────────────┐
                                    │   SEARCHSERVICE        │
                                    │ ─────────────────────  │
                                    │ 1. Query embedding     │
                                    │ 2. Search ChromaDB     │
                                    │ 3. Fetch from SQLite   │
                                    │ 4. Rank by score       │
                                    └───────────┬─────────────┘
                                                │
                        ┌───────────────────────┼───────────────────────┐
                        │                       │                       │
                        ▼                       ▼                       ▼
                   ┌──────────┐            ┌──────────┐            ┌──────────┐
                   │ChromaDB  │            │ SQLite   │            │ JSON     │
                   │(Vectors) │            │(Metadata)│            │Response  │
                   │- 384-dim │            │- Titles  │            │- Results │
                   │- Cosine  │            │- Keywords│            │- Scores  │
                   │- Persist │            │- URLs    │            │- Details │
                   └──────────┘            └──────────┘            └────┬─────┘
                                                                         │
                                    ┌────────────────────────────────────┘
                                    │
                                    ▼
                            ┌─────────────────────┐
                            │  Frontend Receives  │
                            │  Search Results     │
                            └────────────┬────────┘
                                         │
                                         ▼
                            ┌─────────────────────┐
                            │SearchResults.svelte │
                            │• Render results     │
                            │• Show scores        │
                            │• Display details    │
                            └────────────┬────────┘
                                         │
                                         ▼
                            ┌─────────────────────┐
                            │   USER SEES         │
                            │  SEARCH RESULTS     │
                            │  • Title            │
                            │  • Score (0-1)      │
                            │  • Keywords         │
                            │  • Full description │
                            └─────────────────────┘
```

---

## Detailed Component Interaction

### 1. Frontend Search Component
```
User Input (SearchBar)
    │
    └─→ SearchStore.executeSearch()
        │
        ├─→ Validate query (1-1000 chars)
        │
        ├─→ search.service.ts
        │   └─→ apiClient.searchDatasets()
        │
        └─→ HTTP POST /api/search
            {
              "query": "climate data",
              "top_k": 10,
              "min_relevance_score": 0.0
            }
```

### 2. Backend Processing
```
/api/search Endpoint
    │
    ├─→ Validate with Pydantic
    │
    ├─→ SearchService.search()
    │   ├─→ EmbeddingService.embed_text()
    │   │   └─→ Generate 384-dim vector
    │   │
    │   ├─→ VectorStore.search_datasets()
    │   │   ├─→ ChromaDB cosine similarity
    │   │   └─→ Return top 10 vectors
    │   │
    │   └─→ Hydrate from SQLite
    │       ├─→ Fetch titles
    │       ├─→ Fetch keywords
    │       └─→ Fetch URLs
    │
    └─→ Return JSON Response
        {
          "query": "climate data",
          "results": [
            {
              "id": "uuid",
              "title": "Dataset 1",
              "relevance_score": 0.85,
              "keywords": ["climate", "data"],
              "url": "..."
            },
            ...
          ],
          "total_results": 5,
          "processing_time_ms": 45
        }
```

### 3. Frontend Display
```
JSON Response
    │
    └─→ searchStore.update()
        │
        ├─→ Set results
        ├─→ Set loading = false
        └─→ Re-render
            │
            └─→ SearchResults.svelte
                │
                ├─→ For each result:
                │   ├─→ Show title
                │   ├─→ Show score (0-1 scale)
                │   ├─→ Show keywords
                │   └─→ Show description
                │
                └─→ User sees search results
```

---

## Data Flow Diagram

### End-to-End Flow

```
[USER INPUT]
     │
     ├─ Type: "climate precipitation"
     ├─ Press: Enter
     └─ Submit: Search
     │
     ▼
[FRONTEND - SearchBar.svelte]
     │
     ├─ Capture input
     ├─ Dispatch event
     └─ Call: searchStore.executeSearch()
     │
     ▼
[FRONTEND - searchStore.ts]
     │
     ├─ Validate: query.length > 0
     ├─ Validate: query.length < 1000
     ├─ Set: loading = true
     ├─ Set: error = null
     └─ Call: search.service.search(query)
     │
     ▼
[FRONTEND - search.service.ts]
     │
     ├─ Sanitize input
     ├─ Check cache
     └─ Call: apiClient.searchDatasets(query)
     │
     ▼
[FRONTEND - api/client.ts]
     │
     ├─ Build URL: http://localhost:8000/api/search
     ├─ Build request body
     ├─ POST with headers
     └─ Await response
     │
     ╔════════════════════════════════════════════════════╗
     ║           HTTP BOUNDARY                            ║
     ╚════════════════════════════════════════════════════╝
     │
     ▼
[BACKEND - api/routes/search.py]
     │
     ├─ Receive POST /api/search
     ├─ Parse JSON
     ├─ Validate with Pydantic
     └─ Call: search_service.search(request)
     │
     ▼
[BACKEND - SearchService]
     │
     ├─ Receive SearchRequest
     ├─ Call: embedding_service.embed_text(query)
     │
     ├─ [Generate Embedding]
     │  ├─ Load model: all-MiniLM-L6-v2
     │  ├─ Tokenize: "climate precipitation"
     │  └─ Output: 384-dim vector
     │
     ├─ Call: vector_store.search_datasets(embedding)
     │
     ├─ [Search ChromaDB]
     │  ├─ Cosine similarity: embedding vs stored vectors
     │  ├─ Find top 10 matches
     │  └─ Get: [dataset_ids, distances]
     │
     ├─ For each result dataset_id:
     │  └─ Fetch from SQLite:
     │     ├─ title
     │     ├─ keywords
     │     ├─ description
     │     └─ url
     │
     ├─ Normalize scores to 0-1 scale
     ├─ Rank by score (highest first)
     └─ Return SearchResponse
     │
     ▼
[BACKEND - SearchResponse]
     │
     ├─ query: "climate precipitation"
     ├─ results: [
     │   {
     │     id: "uuid1",
     │     title: "Gridded simulations...",
     │     relevance_score: 0.85,
     │     keywords: ["climate", "precipitation"],
     │     url: "..."
     │   },
     │   ...
     │ ]
     ├─ total_results: 5
     └─ processing_time_ms: 45
     │
     ╔════════════════════════════════════════════════════╗
     ║           HTTP BOUNDARY                            ║
     ╚════════════════════════════════════════════════════╝
     │
     ▼
[FRONTEND - api/client.ts]
     │
     ├─ Receive response
     ├─ Parse JSON
     ├─ Return SearchResponse
     │
     ▼
[FRONTEND - search.service.ts]
     │
     ├─ Cache result (5 min TTL)
     ├─ Return response
     │
     ▼
[FRONTEND - searchStore.ts]
     │
     ├─ Update results
     ├─ Set: loading = false
     ├─ Set: hasSearched = true
     └─ Notify subscribers
     │
     ▼
[FRONTEND - SearchResults.svelte]
     │
     ├─ Receive updated results
     ├─ Render results
     └─ For each result:
        ├─ Show title
        ├─ Show score bar (0-1)
        ├─ Show keywords
        └─ Show description
     │
     ▼
[USER SEES RESULTS]
     │
     ├─ "Gridded simulations of available precipitation..." [Score: 0.85]
     ├─ "Daily soil moisture maps for the UK..." [Score: 0.72]
     ├─ "Topsoil nitrogen concentration estimates..." [Score: 0.68]
     └─ ... (more results)
```

---

## Database Schema

### SQLite (Metadata)
```
┌─────────────────┐
│ datasets        │
├─────────────────┤
│ id (PK)        │─────────┐
│ title          │         │
│ abstract       │         │
│ identifier     │         │
│ keywords       │         │
│ url            │         │
│ created_at     │         │
└─────────────────┘         │
                            │
┌────────────────────────────┴────────────┐
│ metadata_documents                     │
├────────────────────────────────────────┤
│ id (PK)                               │
│ dataset_id (FK)                       │
│ format (XML/JSON/RDF/Schema.org)     │
│ raw_content                           │
│ parsed_at                             │
└────────────────────────────────────────┘
```

### ChromaDB (Vectors)
```
┌─────────────────────────────────────┐
│ collection: "datasets"              │
├─────────────────────────────────────┤
│ documents: [                        │
│   {                                 │
│     id: "uuid",                    │
│     embedding: [384-dim vector],   │
│     metadata: {                     │
│       title: "...",                │
│       keywords: "..."              │
│     }                               │
│   },                                │
│   ...                               │
│ ]                                   │
└─────────────────────────────────────┘
```

---

## Technology Stack

```
┌────────────────────────┬───────────────────────────────────────┐
│ Layer                  │ Technology                            │
├────────────────────────┼───────────────────────────────────────┤
│ Web Browser            │ Modern browser (Chrome, Firefox, etc) │
│                        │                                       │
│ Frontend Framework     │ SvelteKit 1.0+                        │
│ Language               │ TypeScript                            │
│ HTTP Client            │ Native fetch API                      │
│ State Management       │ Svelte Stores                         │
│ UI Components          │ shadcn-svelte                         │
│                        │                                       │
│ Backend Framework      │ FastAPI 0.104+                        │
│ Language               │ Python 3.10+                          │
│ CLI Framework          │ Typer                                 │
│ Async Runtime          │ asyncio                               │
│                        │                                       │
│ Embedding Model        │ sentence-transformers                 │
│ Model                  │ all-MiniLM-L6-v2 (384-dim)          │
│ Library                │ PyTorch/TensorFlow                    │
│                        │                                       │
│ Vector Store           │ ChromaDB                              │
│ Storage                │ Parquet (persistent)                  │
│ Search Method          │ Cosine similarity                     │
│                        │                                       │
│ Metadata DB            │ SQLite3                               │
│ ORM Pattern            │ Unit of Work                          │
│ Transaction Mgmt       │ DEFERRED isolation                    │
│                        │                                       │
│ Data Source            │ CEH Catalogue REST API                │
│ Protocols              │ HTTP/HTTPS                            │
│ Formats                │ XML, JSON, RDF, Schema.org           │
│                        │                                       │
│ Observability          │ OpenTelemetry                         │
│ Tracing                │ Jaeger                                │
│ Logging                │ Python logging                        │
└────────────────────────┴───────────────────────────────────────┘
```

---

## Deployment Architecture

```
                    ┌──────────────────┐
                    │    User Browser  │
                    └────────┬─────────┘
                             │ HTTPS
                    ┌────────▼──────────┐
                    │   Web Server      │
                    │  (nginx/Apache)   │
                    │  Serves: dist/    │
                    │  Port: 443/80     │
                    └────────┬──────────┘
                             │ HTTP
                    ┌────────▼────────────────┐
                    │  API Gateway / Proxy    │
                    │  (nginx/HAProxy)        │
                    └────────┬────────────────┘
                             │
                    ┌────────▼──────────────┐
                    │   FastAPI Server      │
                    │   (Gunicorn/Uvicorn)  │
                    │   Port: 8000          │
                    └────────┬──────────────┘
                             │
                ┌────────────┴───────────────┐
                │                           │
        ┌───────▼─────────┐        ┌────────▼─────────┐
        │    SQLite DB    │        │  ChromaDB Vector │
        │  (metadata)     │        │  Store           │
        └─────────────────┘        └──────────────────┘
```

---

## Development vs Production

### Development (Now)
```bash
python start-all.py
├─ Backend: http://localhost:8000
├─ Frontend: http://localhost:5173
└─ DB: data/dsh.db (local)
```

### Production (Optional)
```
Frontend:
├─ Build: npm run build
└─ Deploy dist/ to CDN/web server

Backend:
├─ Deploy with gunicorn/uvicorn
├─ Connect to production database
└─ Set environment variables

Example:
gunicorn -w 4 -b 0.0.0.0:8000 src.main:app
```

---

## Summary

**Complete end-to-end integration**:
1. ✅ Frontend captures user input
2. ✅ Calls backend API
3. ✅ Backend processes query
4. ✅ Searches vector store
5. ✅ Hydrates from SQLite
6. ✅ Returns results with scores
7. ✅ Frontend displays results
8. ✅ User sees search results

**All orchestrated by one script**: `python start-all.py`
