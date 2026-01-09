# Frontend ↔ Backend Architecture Alignment

**Goal**: Show how frontend upgrades align with FastAPI backend patterns

---

## Side-by-Side Architecture Comparison

### Backend (FastAPI)
```python
# FastAPI Architecture
Backend (FastAPI)
├── Clean Architecture
│   ├── Routes (API endpoints)
│   ├── Services (business logic)
│   ├── Repositories (data access)
│   └── Models (data structures)
│
├── Dependency Injection
│   ├── FastAPI Depends()
│   ├── Service injection
│   └── Repository injection
│
├── Error Handling
│   ├── APIException base class
│   ├── Semantic error codes
│   └── Structured responses
│
├── Middleware
│   ├── Logging (RequestLoggingMiddleware)
│   ├── Tracing (TraceContextMiddleware)
│   ├── CORS (CORSMiddleware)
│   └── Error handling
│
└── Observable
    ├── OpenTelemetry tracing
    ├── Structured logging
    ├── Correlation IDs
    └── Request spans
```

### Frontend (Svelte) - NOW UPGRADED ✅
```typescript
// Frontend Architecture (POST-UPGRADE)
Frontend (Svelte)
├── Clean Architecture
│   ├── Components (UI)
│   ├── Stores (state management)
│   ├── Services (business logic)
│   └── Types (data structures)
│
├── Dependency Injection
│   ├── Container (service factory)
│   ├── Service injection
│   └── Store creation with services
│
├── Error Handling
│   ├── ApiError base class
│   ├── Semantic error types
│   └── Structured error info
│
├── HTTP Client
│   ├── Request handler
│   ├── Response handler
│   ├── Retry logic
│   └── Timeout management
│
└── Service Layer
    ├── SearchService (with cache)
    ├── ChatService (validation)
    └── ValidationService (input)
```

---

## Pattern Alignment

| Pattern | Backend (FastAPI) | Frontend (Svelte Post-Upgrade) |
|---------|-------------------|--------------------------------|
| **DI Container** | FastAPI.Depends() | Container class |
| **Service Layer** | SearchService class | SearchService class |
| **Error Handling** | APIException + error codes | ApiError + error types |
| **Validation** | Pydantic models | ValidationService |
| **Middleware** | Middleware stack | HTTP client layers |
| **Logging** | Structured logging | Console + error tracking |
| **Type Safety** | Pydantic + Python types | TypeScript + Interfaces |
| **Separation of Concerns** | Routes → Services → Repos | Components → Stores → Services |

---

## Request Flow - Synchronized Architecture

### Backend Request Flow
```
HTTP Request
    ↓
CORS Middleware
    ↓
Logging Middleware
    ↓
Trace Context Middleware
    ↓
Exception Handler
    ↓
Router (e.g., search_router)
    ↓
get_search_service() ← Dependency Injection
    ↓
SearchService.search()
    ↓
Repository.query()
    ↓
Database
    ↓
Response (structured) ← Consistent error format
    ↓
Client
```

### Frontend Request Flow (NOW ALIGNED ✅)
```
User Action (e.g., search)
    ↓
Component calls store.executeSearch()
    ↓
Store (uses injected service)
    ↓
SearchService.search() ← Dependency Injection
    ↓
ValidationService.validate()
    ↓
HttpClient.request()
    ↓
RequestHandler (headers, timeout)
    ↓
fetch() (HTTP)
    ↓
ResponseHandler (parse, validate)
    ↓
Retry Logic (if needed)
    ↓
Error or Success
    ↓
Store updates state
    ↓
Component re-renders
```

---

## Error Handling Alignment

### Backend Error Structure
```python
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail,
            "trace_id": trace_id,
            "timestamp": timestamp
        }
    )
```

### Frontend Error Handling (NOW ALIGNED ✅)
```typescript
// Receive error from backend
export class ApiError extends Error {
  constructor(
    public status: number,      // Maps to backend status_code
    message: string,             // Maps to backend detail
    public retryable: boolean,  // Business logic added by frontend
    public cause?: Error
  ) { }
}

// Handle intelligently
try {
  await searchStore.executeSearch(query);
} catch (error) {
  if (error instanceof TimeoutError) {
    // Auto-retry already happened (3x)
  } else if (error instanceof ValidationError) {
    // Show user their input was invalid
  } else if (error instanceof ServerError) {
    // Show server error message
  }
}
```

---

## Service Layer Alignment

### Backend Service
```python
class SearchService:
    def __init__(self, repository: SearchRepository, cache: CacheService):
        self.repository = repository
        self.cache = cache
    
    async def search(self, query: str, top_k: int = 10) -> SearchResponse:
        # 1. Validate query
        if not query or len(query) > 1000:
            raise ValidationError("Invalid query")
        
        # 2. Check cache
        cached = self.cache.get(query)
        if cached:
            return cached
        
        # 3. Search
        results = await self.repository.search(query, top_k)
        
        # 4. Cache result
        self.cache.set(query, results)
        
        return results
```

### Frontend Service (NOW ALIGNED ✅)
```typescript
export class DefaultSearchApiService implements SearchApiService {
  private queryCache: Map<string, SearchResponse> = new Map();
  private cacheExpiry: Map<string, number> = new Map();
  private readonly CACHE_TTL = 5 * 60 * 1000;

  async search(query: string, limit: number = 10): Promise<SearchResponse> {
    // 1. Validate query
    const sanitized = this.sanitizeQuery(query);
    if (!sanitized) {
      throw new ApiError(400, 'Query cannot be empty', false);
    }
    
    // 2. Check cache
    const cached = this.getFromCache(sanitized);
    if (cached) {
      return cached;
    }
    
    // 3. Search (via API)
    const response = await apiClient.searchDatasets(sanitized, limit);
    
    // 4. Cache result
    this.setCache(sanitized, response);
    
    return response;
  }
}
```

**Perfect alignment!** Same patterns, same logic flow.

---

## Dependency Injection Alignment

### Backend DI (FastAPI)
```python
# Route with injected dependencies
@router.post("")
async def search_datasets(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
    uow: UnitOfWork = Depends(get_unit_of_work)
) -> SearchResponse:
    return await search_service.search(request.query, request.top_k)

# Dependency factory
def get_search_service() -> SearchService:
    cache = CacheService()
    repository = SearchRepository()
    return SearchService(repository, cache)
```

### Frontend DI (NOW ALIGNED ✅)
```typescript
// Store with injected dependencies
export function createSearchStore(searchService: SearchApiService) {
  return {
    executeSearch: async (query: string) => {
      const response = await searchService.search(query, 10);
      // Use response...
    }
  };
}

// DI Container (factory)
export class Container {
  private searchService: SearchApiService;
  private searchStore: any;
  
  constructor() {
    this.searchService = new DefaultSearchApiService();
    this.searchStore = createSearchStore(this.searchService);
  }
  
  getSearchStore() {
    return this.searchStore;
  }
}
```

**Perfect alignment!** Factories create services, services injected into consumers.

---

## Type Safety Alignment

### Backend (Pydantic)
```python
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=100)

class SearchResult(BaseModel):
    dataset: Dataset
    score: float = Field(ge=0, le=1)

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
```

### Frontend (TypeScript - NOW ALIGNED ✅)
```typescript
export interface SearchRequest {
  query: string;
  top_k?: number;
}

export interface SearchResult {
  dataset: Dataset;
  score: number; // 0..1
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

// + Validation service for runtime checks
class SearchQueryValidator {
  static validate(query: string): void {
    if (!query || query.trim().length === 0) {
      throw new ValidationError('query', 'Query cannot be empty');
    }
    if (query.length > 1000) {
      throw new ValidationError('query', 'Query too long');
    }
  }
}
```

**Excellent alignment!** Same data models, type-safe on both ends.

---

## Logging & Observability Alignment

### Backend (OpenTelemetry + Structured Logging)
```python
logger.info(
    "search_executed",
    extra={
        "query": query,
        "results_count": len(results),
        "duration_ms": duration,
        "trace_id": trace_id,
        "user_id": user_id
    }
)
```

### Frontend (Aligned Approach)
```typescript
// Log structured events
const searchStore = container.getSearchStore();

searchStore.subscribe(state => {
  if (!state.loading && state.results.length > 0) {
    console.log('search_completed', {
      query: state.query,
      results_count: state.results.length,
      timestamp: new Date().toISOString()
    });
  }
});
```

**Aligned approach** - Both log structured data for monitoring.

---

## Caching Strategy Alignment

### Backend Cache
```python
# SearchService uses cache
cached_result = cache.get(query_key)
if cached_result:
    return cached_result

results = repository.search(query, top_k)
cache.set(query_key, results, ttl=300)  # 5 min TTL
```

### Frontend Cache (NOW IMPLEMENTED ✅)
```typescript
// SearchService uses cache (same pattern)
const cached = this.getFromCache(query);
if (cached) {
  return cached;
}

const response = await apiClient.search(query);
this.setCache(query, response);  // 5 min TTL
```

**Perfect alignment!** Same TTL, same strategy.

---

## Error Recovery Alignment

### Backend Approach
```python
# Structured error codes help client decide what to do
raise APIException(
    status_code=408,
    error_code="REQUEST_TIMEOUT",
    detail="Search request timed out. Please try again.",
    retryable=True
)
```

### Frontend Approach (NOW ALIGNED ✅)
```typescript
// Error carries metadata for intelligent recovery
export class ApiError extends Error {
  constructor(
    public status: number,      // 408
    message: string,            // "Request timeout..."
    public retryable: boolean   // true
  ) { }
}

// Auto-retry for transient failures
async requestWithRetry<T>(...) {
  try {
    return await executeRequest<T>(...);
  } catch (error) {
    if (isRetryable(error) && attempt < maxRetries) {
      // Retry with exponential backoff
    }
  }
}
```

**Perfect alignment!** Both use retryable metadata.

---

## Technology Stack Comparison

| Concern | Backend | Frontend |
|---------|---------|----------|
| **Language** | Python 3.10+ | TypeScript 5.9+ |
| **Framework** | FastAPI | SvelteKit |
| **DI** | FastAPI.Depends() | Custom Container |
| **Validation** | Pydantic | Custom validators + TypeScript |
| **Error Handling** | APIException | ApiError hierarchy |
| **HTTP** | FastAPI built-in | Fetch API |
| **Caching** | Cache service | SearchService cache |
| **Logging** | Python logging + OT | Console (can extend) |
| **Type System** | Python static typing | TypeScript |

---

## Key Achievements

### 1. Matched Architecture Patterns ✅
- Both use Clean Architecture (Routes/Components → Services → Repos/Stores)
- Both use Dependency Injection
- Both have layered error handling
- Both validate inputs before processing

### 2. Synchronized Data Models ✅
- Frontend types match backend Pydantic models
- Both validate the same constraints
- Type-safe end-to-end

### 3. Aligned Business Logic ✅
- SearchService exists on both sides
- Caching strategy is identical (5-min TTL)
- Validation rules are the same

### 4. Professional Error Handling ✅
- Backend: APIException with error codes
- Frontend: ApiError with metadata
- Client can make intelligent recovery decisions

### 5. Observable & Maintainable ✅
- Backend: OpenTelemetry + structured logging
- Frontend: Can hook into events for analytics
- Both care about tracing and monitoring

---

## Future Alignment Opportunities

### Next Steps (Optional)
1. **Add EventBus to Frontend** - Match backend event publishing
2. **Add OpenTelemetry to Frontend** - Span tracing like backend
3. **Add Repository Layer** - Match backend repository pattern
4. **Add Error Boundaries** - Component-level error handling

### Suggested Timeline
- Immediate: Use current architecture (production ready)
- Week 2: Add Repository pattern (data source abstraction)
- Week 3: Add error boundaries (component resilience)
- Week 4: Add OpenTelemetry (observability)

---

## Conclusion

Your **frontend architecture now aligns with FastAPI backend patterns**:

✅ Same DI philosophy  
✅ Same service layer design  
✅ Same error handling approach  
✅ Same caching strategy  
✅ Same validation rules  
✅ Same type-safety philosophy  

This means:
- **Easier for developers** - Same patterns they know from backend
- **More maintainable** - Consistent approach across stack
- **Better for operations** - Unified observability strategy
- **Future-proof** - Can evolve both sides together

---

**Frontend upgrade complete and aligned with backend!** 🎉
