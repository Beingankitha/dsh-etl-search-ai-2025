# Issue #10 - Architecture & Design Decisions

## API Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│         FastAPI Application (main.py)               │
│  - CORS Middleware                                  │
│  - Request Logging Middleware                       │
│  - Global Exception Handler                         │
└─────────────────────────────────────────────────────┘
         │
         ├─ Dependency Injection
         │
┌─────────────────────────────────────────────────────┐
│              Router Layer (src/api/)                │
├──────────────────┬──────────────────┬───────────────┤
│ health.py        │ search.py        │ datasets.py   │
│ ─────────────    │ ──────────────   │ ───────────   │
│ /health          │ /api/search      │ /api/datasets │
│ /health/ready    │ /suggestions     │ /{id}         │
│ /health/live     │                  │ /{id}/related │
└──────────────────┴──────────────────┴───────────────┘
         │
         ├─ Dependency Injection
         │
┌─────────────────────────────────────────────────────┐
│         Service Layer (src/services/)               │
├──────────────────┬──────────────────┬───────────────┤
│ SearchService    │ EmbeddingService │ VectorStore   │
│ - search()       │ - embed_text()   │ - search_*()  │
│ - validation     │ - batch embed    │ - similarity  │
│ - hydration      │                  │ - retrieval   │
└──────────────────┴──────────────────┴───────────────┘
         │
         ├─ Uses Repository Pattern
         │
┌─────────────────────────────────────────────────────┐
│    Repository Layer (src/repositories/)             │
│ - UnitOfWork (transaction mgmt)                     │
│ - BaseRepository (generic CRUD)                     │
│ - DatasetRepository                                 │
└─────────────────────────────────────────────────────┘
         │
┌─────────────────────────────────────────────────────┐
│    Database Layer (SQLite)                          │
│ - datasets table                                    │
│ - metadata_documents table                          │
│ - data_files table                                  │
│ - supporting_documents table                        │
└─────────────────────────────────────────────────────┘
```

### Request-Response Flow for Search

```
┌─────────────────────────────────────────────────────────┐
│ Client (Frontend - SvelteKit)                           │
│ POST /api/search                                        │
│ {"query": "climate data", "top_k": 10}                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ FastAPI Request Handler (search.py)                     │
│ - Validate request with Pydantic                        │
│ - Inject SearchService via Depends()                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ SearchService.search()                                  │
│ 1. Validate query (not empty, not too long)             │
│ 2. Generate query embedding via EmbeddingService        │
│ 3. Search ChromaDB via VectorStore                      │
│ 4. Hydrate results from database                        │
│ 5. Sort by relevance score (descending)                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Return SearchResponse                                   │
│ {                                                       │
│   "query": "climate data",                              │
│   "results": [                                          │
│     {                                                   │
│       "dataset": {...},                                 │
│       "score": 0.95                                     │
│     },                                                  │
│     ...                                                 │
│   ]                                                     │
│ }                                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Client receives JSON response                           │
│ Frontend renders results                                │
└─────────────────────────────────────────────────────────┘
```

### Dependency Injection Pattern

```python
# Example: SearchService Dependency Chain

# 1. Define dependency getter
def get_search_service() -> SearchService:
    embedding_service = EmbeddingService()      # Inner dependency
    vector_store = VectorStore()                # Inner dependency
    unit_of_work = UnitOfWork()                 # Inner dependency
    
    return SearchService(                       # Top-level dependency
        embedding_service=embedding_service,
        vector_store=vector_store,
        unit_of_work=unit_of_work,
    )

# 2. Inject into endpoint
@router.post("")
async def search_datasets(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    return SearchResponse(
        query=request.query,
        results=search_service.search(
            query=request.query,
            top_k=request.top_k,
        ),
    )

# 3. For testing, override dependency
from fastapi.testclient import TestClient

mock_service = MagicMock()
mock_service.search.return_value = [...]

app.dependency_overrides[get_search_service] = lambda: mock_service
response = client.post("/api/search", json={...})
app.dependency_overrides.clear()
```

## Error Handling Strategy

### Exception Hierarchy

```
┌────────────────────────────────────────┐
│ Client Request                         │
└────────────────────┬───────────────────┘
                     │
                     ↓
        ┌─────────────────────────┐
        │ Request Validation      │
        │ (Pydantic)              │
        └────────┬────────────────┘
                 │
        ┌────────▼────────────────────────────────────────┐
        │ Validation Error → 422 Unprocessable Entity    │
        │ Automatic from Pydantic                         │
        └─────────────────────────────────────────────────┘
                 │
                 ↓
        ┌─────────────────────────┐
        │ Service Layer           │
        │ (SearchService, etc.)   │
        └────────┬────────────────┘
                 │
     ┌───────────┴───────────┐
     │                       │
     ↓                       ↓
 Success              Exception
   │                    │
   │              ┌─────▼──────────────────────────┐
   │              │ Custom Service Exception       │
   │              │ (SearchServiceError)           │
   │              │ Raised with meaningful message │
   │              └─────┬──────────────────────────┘
   │                    │
   │              ┌─────▼──────────────────────────┐
   │              │ Catch in Endpoint Handler     │
   │              │ Convert to HTTPException      │
   │              │ with status_code=500         │
   │              └─────┬──────────────────────────┘
   │                    │
   │              ┌─────▼──────────────────────────┐
   │              │ Return Error Response          │
   │              │ {                              │
   │              │   "detail": "...",             │
   │              │   "error_code": "..."          │
   │              │ }                              │
   │              └────────────────────────────────┘
   │
   └─────────────┬─────────────────────┐
                 │                     │
            (Success)               (Success)
                 │                     │
                 ↓                     ↓
        Convert DB Model      Build Pydantic Model
        to Pydantic Schema     with Results/Data
                 │                     │
                 └─────────┬───────────┘
                           │
                           ↓
                   Return 200 Response
                   {valid JSON body}
```

### Error Response Examples

```json
// Validation Error (422)
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "query"],
      "msg": "ensure this value has at least 1 characters",
      "input": ""
    }
  ]
}

// Not Found (404)
{
  "detail": "Dataset 'unknown-123' not found"
}

// Search Service Error (500)
{
  "detail": "Search failed: Query embedding generation failed"
}

// Unhandled Exception (500)
{
  "detail": "Internal server error",
  "error_code": "INTERNAL_ERROR"
}
```

## Data Model Conversions

### Search Endpoint Flow

```
Client Request
    ↓
SearchRequest (Pydantic)
├─ query: str (validated)
└─ top_k: int (validated, 1-100)
    ↓
SearchService.search()
    ↓
Vector Results
├─ id: str
├─ similarity_score: float (0-1, already normalized)
├─ metadata: dict
└─ content: str
    ↓
Hydration: Fetch from DB
├─ DBDataset (dataclass)
│  ├─ file_identifier: str
│  ├─ title: str
│  ├─ topic_category: str (JSON string)
│  └─ keywords: str (JSON string)
    ↓
Convert to Pydantic Schema
├─ Dataset (Pydantic)
│  ├─ file_identifier: str
│  ├─ title: str
│  ├─ topic_category: list[str] (parsed)
│  └─ keywords: list[str] (parsed)
    ↓
Create SearchResult
├─ dataset: Dataset
└─ score: float (0-1)
    ↓
SearchResponse
├─ query: str
└─ results: list[SearchResult]
    ↓
JSON Response (200 OK)
```

## CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React/Next.js
        "http://localhost:5173",      # SvelteKit
        "http://127.0.0.1:5173",      # SvelteKit (127.0.0.1)
        "http://127.0.0.1:3000",      # React (127.0.0.1)
    ],
    allow_credentials=True,            # Allow cookies/auth
    allow_methods=["*"],               # GET, POST, OPTIONS, etc.
    allow_headers=["*"],               # Any headers
)
```

**How It Works**:
1. Browser sends CORS preflight (OPTIONS) request
2. Middleware checks `Origin` header against `allow_origins`
3. If allowed, responds with appropriate CORS headers
4. Browser allows actual request (GET/POST)
5. Response includes CORS headers

**Allowed Headers**:
- `content-type`: application/json
- `authorization`: Bearer token
- Custom headers

## Request Logging Middleware

```
Incoming Request
    ↓
Log: "GET /api/datasets start"
    ↓
Process Request
    │
    ├─ Call endpoint handler
    ├─ Validate request
    ├─ Inject dependencies
    ├─ Execute business logic
    └─ Generate response
    ↓
Log: "GET /api/datasets 200 (0.234s)"
    ↓
Return Response to Client
```

## Testing Strategy

### Unit Tests for Services (Existing)
```
test_search_service.py
├─ SearchService initialization
├─ Query validation
├─ Embedding generation
├─ Vector store search
├─ Result hydration
└─ Error handling
```

### Integration Tests for API (New)
```
test_api.py
├─ Health endpoints (4)
├─ Root endpoints (2)
├─ Search endpoints (4)
├─ Dataset endpoints (6)
├─ CORS configuration (2)
├─ Error handling (2)
└─ Response validation (1)
```

### Dependency Override Pattern for Testing

```python
# Normal operation
app.dependency_overrides = {}  # Empty, real deps used

# Testing
mock_service = MagicMock()
app.dependency_overrides[get_search_service] = lambda: mock_service

# After test
app.dependency_overrides.clear()
```

## Configuration

### Environment Variables Used

```
API_HOST=0.0.0.0              # Bind to all interfaces
API_PORT=8000                 # Default port
DEBUG=true                    # Enable debug mode
DATABASE_PATH=./data/datasets.db
CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Application Settings (src/config.py)

```python
class Settings:
    app_name: str = "CEH Dataset Discovery"
    app_env: str = "development"
    debug: bool = True
    
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    database_path: str = "./data/datasets.db"
    chroma_path: str = "./data/chroma"
```

## Performance Considerations

### Pagination

```
Client: GET /api/datasets?limit=20&offset=40

Database Query:
SELECT * FROM datasets LIMIT 20 OFFSET 40

Response Time: ~10-50ms depending on database size
Memory Usage: O(limit) - only current page in memory
```

### Search Performance

```
Query: "climate data"

1. Embedding generation: ~50-200ms (CPU dependent)
2. Vector similarity search: ~10-50ms (ChromaDB)
3. Database hydration: ~1-5ms per result
4. Total expected: <2 seconds for typical queries
```

### Caching (Future Enhancement)

Currently disabled but can be enabled:
```python
search_service = SearchService(
    ...,
    enable_caching=True  # Future: Redis/LRU cache
)
```

---

## Key Design Decisions Explained

### 1. Why Dependency Injection?

✅ **Testability**: Easy to mock dependencies  
✅ **Loose Coupling**: Services don't know about HTTP  
✅ **Single Responsibility**: Each layer has one job  
✅ **Flexibility**: Can swap implementations  

### 2. Why Pydantic for Validation?

✅ **Automatic Validation**: 422 responses auto-generated  
✅ **Type Safety**: Full type hints  
✅ **Documentation**: Fields documented in Swagger UI  
✅ **Performance**: Fast validation  

### 3. Why Separate Routers?

✅ **Maintainability**: Each domain in separate file  
✅ **Scalability**: Easy to add new endpoints  
✅ **Testing**: Can test each router independently  
✅ **Organization**: Clear code structure  

### 4. Why Middleware for Logging?

✅ **Cross-cutting**: Applied to all endpoints  
✅ **Consistent**: Same format for all requests  
✅ **Non-intrusive**: Doesn't clutter endpoint code  
✅ **Extensible**: Can add other middleware  

---

**Issue #10 Architecture**: ✅ **CLEAN, TESTABLE, PRODUCTION-READY**
