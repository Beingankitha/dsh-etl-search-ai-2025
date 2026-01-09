# Frontend System Design Upgrades
## DSH ETL Search AI 2025 - Best Practices Implementation Guide

**Analysis Date**: January 4, 2026  
**Current State**: Functional MVP (Issues 12-20 Complete)  
**Goal**: Enterprise-Grade Architecture with SOLID Principles & Design Patterns

---

## EXECUTIVE SUMMARY

Your frontend is **functionally complete** and builds successfully, but has opportunities for **professional-grade system design improvements**. Below are 8 major upgrades organized by priority.

### Quick Wins (Can Implement in 4-6 hours)
1. **API Client Refactoring** - Separate concerns (errors, validation, requests)
2. **Store Action Refactoring** - Remove circular dependency on search function
3. **Repository Pattern** - Abstract data access from stores

### Medium Effort (8-12 hours)
4. **Dependency Injection** - Decouple components from services
5. **Error Boundary Components** - Isolate component failures
6. **Input Validation Layer** - Centralized validation utilities

### Advanced (16+ hours, High ROI)
7. **Service Layer** - Encapsulate business logic
8. **Observable Pattern** - Replace function passing with event bus

---

## UPGRADE #1: API CLIENT REFACTORING (QUICK WIN)

### Current Design Issues
```typescript
// ❌ Problem: All concerns mixed in one function
async function apiRequest<T>(
	endpoint: string,
	method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
	body?: unknown
): Promise<T>
```

**Issues**:
- Single Responsibility Principle violated (HTTP, errors, logging all mixed)
- Hard to test error handling separately
- No request/response transformation layer
- No logging or monitoring hooks
- No retry logic despite transient errors being common

### Recommended Design

**Step 1**: Create error class hierarchy
```typescript
// src/lib/api/errors.ts (NEW)
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public retryable: boolean = false,
    public cause?: Error
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends ApiError {
  constructor(message: string, cause?: Error) {
    super(0, message, true, cause); // retryable = true
  }
}

export class ValidationError extends ApiError {
  constructor(message: string) {
    super(400, message, false); // retryable = false
  }
}

export class ServerError extends ApiError {
  constructor(status: number, message: string) {
    super(status, message, status >= 500); // 5xx are retryable
  }
}

export class TimeoutError extends ApiError {
  constructor(message: string) {
    super(408, message, true); // retryable = true
  }
}
```

**Step 2**: Create request/response handlers
```typescript
// src/lib/api/handlers.ts (NEW)
export interface RequestConfig {
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
}

export class RequestHandler {
  static addHeaders(headers: HeadersInit, config?: RequestConfig): HeadersInit {
    return {
      ...headers,
      'Content-Type': 'application/json',
      'X-Request-ID': crypto.randomUUID(),
      ...config?.headers
    };
  }

  static timeout(ms: number): Promise<never> {
    return new Promise((_, reject) =>
      setTimeout(() => reject(new TimeoutError(`Request timeout after ${ms}ms`)), ms)
    );
  }
}

export class ResponseHandler {
  static async parseJson(response: Response) {
    try {
      return await response.json();
    } catch {
      throw new ValidationError('Invalid JSON response from server');
    }
  }

  static validateOk(response: Response, body: any) {
    if (!response.ok) {
      const status = response.status;
      const message = body?.detail || body?.message || response.statusText;
      
      if (status >= 500) {
        throw new ServerError(status, message);
      } else if (status >= 400) {
        throw new ValidationError(message);
      }
    }
  }
}
```

**Step 3**: Create HTTP client with retry logic
```typescript
// src/lib/api/http-client.ts (NEW)
export class HttpClient {
  private readonly baseUrl: string;
  private readonly defaultTimeout: number = 30000;
  private readonly maxRetries: number = 3;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async request<T>(
    endpoint: string,
    options: {
      method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
      body?: unknown;
      config?: RequestConfig;
    } = {}
  ): Promise<T> {
    const { method = 'GET', body, config = {} } = options;
    const url = `${this.baseUrl}${endpoint}`;
    const maxRetries = config.retries ?? this.maxRetries;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeout = config.timeout ?? this.defaultTimeout;

        const response = await Promise.race([
          fetch(url, {
            method,
            headers: RequestHandler.addHeaders({}, config),
            body: body ? JSON.stringify(body) : undefined,
            signal: controller.signal
          }),
          RequestHandler.timeout(timeout)
        ]);

        const responseBody = await ResponseHandler.parseJson(response as Response);
        ResponseHandler.validateOk(response as Response, responseBody);
        return responseBody as T;
      } catch (error) {
        const apiError = this.normalizeError(error);

        if (apiError.retryable && attempt < maxRetries) {
          // Exponential backoff: 100ms, 200ms, 400ms
          const delay = Math.pow(2, attempt) * 100;
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        throw apiError;
      }
    }

    throw new Error('Max retries exceeded');
  }

  private normalizeError(error: unknown): ApiError {
    if (error instanceof ApiError) return error;
    if (error instanceof TypeError) return new NetworkError(error.message, error);
    if (error instanceof Error) return new ApiError(500, error.message, false, error);
    return new ApiError(500, 'Unknown error', false);
  }
}
```

**Step 4**: Refactor existing client.ts
```typescript
// src/lib/api/client.ts (REFACTORED)
import { HttpClient } from './http-client';
import type { SearchResponse, ChatResponse, ChatMessage } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const httpClient = new HttpClient(API_BASE_URL);

export async function searchDatasets(
  query: string,
  limit: number = 10
): Promise<SearchResponse> {
  return httpClient.request<SearchResponse>('/api/search', {
    method: 'POST',
    body: { query, top_k: limit },
    config: { timeout: 30000, retries: 2 }
  });
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[] = []
): Promise<ChatResponse> {
  return httpClient.request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: { message, history },
    config: { timeout: 60000, retries: 1 } // Chat might take longer
  });
}

// ... other endpoints
```

### Benefits
✅ **Single Responsibility**: Each class has one reason to change  
✅ **Testability**: Mock HttpClient, RequestHandler, ResponseHandler separately  
✅ **Reusability**: RequestHandler logic available to other clients  
✅ **Error Context**: Rich error information for debugging  
✅ **Retry Logic**: Automatic recovery from transient failures  
✅ **Monitoring**: Request ID in headers for tracing  

---

## UPGRADE #2: STORE ACTION REFACTORING (QUICK WIN)

### Current Design Issues
```typescript
// ❌ Problem: Store actions take function as parameter
executeSearch: async (
  query: string,
  searchFn: (query: string, limit: number) => Promise<any> // ← Tight coupling
)
```

**Issues**:
- Components must pass API function to store (violation of DIP - Dependency Inversion Principle)
- Hard to change API implementation (affects all components)
- Store tests require passing mock functions
- Circular dependency: component → store → component's function

### Recommended Design

**Step 1**: Create abstract service interface
```typescript
// src/lib/services/api.service.ts (NEW)
import type { SearchResponse, ChatResponse, ChatMessage } from '$lib/api/types';

export interface SearchApiService {
  search(query: string, limit?: number): Promise<SearchResponse>;
}

export interface ChatApiService {
  sendMessage(message: string, history?: ChatMessage[]): Promise<ChatResponse>;
}

export class DefaultSearchApiService implements SearchApiService {
  constructor(private httpClient: any) {} // Injected

  async search(query: string, limit: number = 10): Promise<SearchResponse> {
    return this.httpClient.request<SearchResponse>('/api/search', {
      method: 'POST',
      body: { query, top_k: limit }
    });
  }
}

export class DefaultChatApiService implements ChatApiService {
  constructor(private httpClient: any) {}

  async sendMessage(
    message: string,
    history: ChatMessage[] = []
  ): Promise<ChatResponse> {
    return this.httpClient.request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: { message, history }
    });
  }
}
```

**Step 2**: Inject services into stores
```typescript
// src/lib/stores/searchStore.ts (REFACTORED)
import { writable, derived } from 'svelte/store';
import type { SearchResult } from '$lib/api/types';
import type { SearchApiService } from '$lib/services/api.service';

interface SearchState {
  query: string;
  results: SearchResult[];
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
}

const initialState: SearchState = {
  query: '',
  results: [],
  loading: false,
  error: null,
  hasSearched: false
};

export function createSearchStore(apiService: SearchApiService) {
  const store = writable<SearchState>(initialState);

  return {
    subscribe: store.subscribe,
    
    setQuery: (query: string) => {
      store.update(state => ({ ...state, query }));
    },

    startSearch: () => {
      store.update(state => ({
        ...state,
        loading: true,
        error: null,
        hasSearched: true
      }));
    },

    setResults: (results: SearchResult[]) => {
      store.update(state => ({
        ...state,
        results,
        loading: false,
        error: null
      }));
    },

    setError: (error: string) => {
      store.update(state => ({
        ...state,
        error,
        loading: false
      }));
    },

    clear: () => {
      store.set(initialState);
    },

    // ✅ Key change: Service injected, no more function parameters
    executeSearch: async (query: string) => {
      this.setQuery(query);
      this.startSearch();

      try {
        const response = await apiService.search(query, 10);
        this.setResults(response.results || []);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Search failed';
        this.setError(errorMessage);
      }
    }
  };
}

// Create singleton store instance
export const searchStore = createSearchStore(new DefaultSearchApiService(httpClient));
```

**Step 3**: Components use store without passing functions
```typescript
// src/routes/+page.svelte (REFACTORED)
<script lang="ts">
  import { searchStore } from '$lib/stores';

  let searchQuery = $state('');

  async function handleSearch(event: Event) {
    const customEvent = event as CustomEvent;
    const query = customEvent.detail?.query || searchQuery;

    if (!query.trim()) return;

    // ✅ No need to pass searchDatasets function anymore!
    await searchStore.executeSearch(query);
  }
</script>
```

### Benefits
✅ **Inversion of Dependency**: Store depends on interface, not component  
✅ **Loose Coupling**: Easy to swap implementations (mock, real, cache)  
✅ **Single Responsibility**: Store doesn't care where data comes from  
✅ **Testability**: Create store with mock service in tests  
✅ **Cleaner Components**: Less parameter passing  

---

## UPGRADE #3: REPOSITORY PATTERN (QUICK WIN)

### Why Add Repository Layer?

Currently: `Component → Store → API Client`

With Repository: `Component → Store → Repository → API Client`

**Benefits**:
- Repository handles caching, filtering, sorting
- API client doesn't need to know about business logic
- Easy to add data source options (cache, localStorage, etc.)

### Implementation

```typescript
// src/lib/repositories/search.repository.ts (NEW)
import type { Dataset, SearchResult, SearchResponse } from '$lib/api/types';
import type { HttpClient } from '$lib/api/http-client';

export class SearchRepository {
  private cache: Map<string, SearchResult[]> = new Map();
  private cacheTimeout: Map<string, number> = new Map();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  constructor(private httpClient: HttpClient) {}

  async search(query: string, limit: number = 10): Promise<SearchResult[]> {
    // Check cache first
    const cached = this.getFromCache(query);
    if (cached) return cached;

    // Fetch from API
    const response = await this.httpClient.request<SearchResponse>(
      '/api/search',
      {
        method: 'POST',
        body: { query, top_k: limit }
      }
    );

    // Store in cache
    this.setCache(query, response.results);
    return response.results;
  }

  async getById(fileIdentifier: string): Promise<Dataset> {
    return this.httpClient.request<Dataset>(
      `/api/datasets/${fileIdentifier}`,
      { method: 'GET' }
    );
  }

  async listAll(limit: number = 20, offset: number = 0): Promise<Dataset[]> {
    return this.httpClient.request<Dataset[]>(
      `/api/datasets?limit=${limit}&offset=${offset}`,
      { method: 'GET' }
    );
  }

  clearCache(): void {
    this.cache.clear();
    this.cacheTimeout.clear();
  }

  private getFromCache(key: string): SearchResult[] | null {
    const expiry = this.cacheTimeout.get(key);
    if (!expiry || Date.now() > expiry) {
      this.cache.delete(key);
      return null;
    }
    return this.cache.get(key) ?? null;
  }

  private setCache(key: string, value: SearchResult[]): void {
    this.cache.set(key, value);
    this.cacheTimeout.set(key, Date.now() + this.CACHE_TTL);
  }
}
```

### Benefits
✅ **Caching**: Centralized cache management without duplicating in stores  
✅ **Abstraction**: Repository handles WHERE data comes from  
✅ **Testability**: Mock repository in component tests  
✅ **Flexibility**: Easy to add localStorage or IndexedDB layer later  

---

## UPGRADE #4: DEPENDENCY INJECTION (MEDIUM EFFORT)

### Problem: Hard-Coded Dependencies

```typescript
// ❌ Components directly import and instantiate services
import { searchDatasets } from '$lib/api/client';
import { searchStore } from '$lib/stores';
```

### Solution: Service Container

```typescript
// src/lib/container.ts (NEW)
import { HttpClient } from '$lib/api/http-client';
import { SearchRepository } from '$lib/repositories/search.repository';
import { ChatRepository } from '$lib/repositories/chat.repository';
import { createSearchStore } from '$lib/stores/searchStore';
import { createChatStore } from '$lib/stores/chatStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create singleton instances
const httpClient = new HttpClient(API_BASE_URL);
const searchRepository = new SearchRepository(httpClient);
const chatRepository = new ChatRepository(httpClient);

// Create stores with injected dependencies
export const searchStore = createSearchStore(searchRepository);
export const chatStore = createChatStore(chatRepository);

// Export container for testing
export const container = {
  httpClient,
  searchRepository,
  chatRepository,
  searchStore,
  chatStore
};
```

### Benefits
✅ **Centralized Configuration**: All dependencies in one place  
✅ **Easy Testing**: Create test container with mocks  
✅ **Flexibility**: Swap implementations without changing components  
✅ **Scalability**: Add new services without modifying existing code  

---

## UPGRADE #5: ERROR BOUNDARY COMPONENTS (MEDIUM EFFORT)

### Problem: Component Errors Crash Entire Page

```typescript
// ❌ If DatasetCard has error, whole SearchResults crashes
{#each results as result}
  <DatasetCard {result} />
{/each}
```

### Solution: Error Boundary Component

```typescript
// src/lib/custom/ErrorBoundary.svelte (NEW)
<script lang="ts">
  import { AlertCircle } from 'lucide-svelte';

  let error: Error | null = $state(null);
  let hasError = $derived(error !== null);

  export function captureError(err: Error) {
    error = err;
    console.error('Error caught by boundary:', err);
  }

  function reset() {
    error = null;
  }
</script>

{#if hasError}
  <div class="error-boundary">
    <div class="error-content">
      <AlertCircle size={32} />
      <h3>Something went wrong</h3>
      <p>{error?.message || 'An unexpected error occurred'}</p>
      <button on:click={reset}>Try again</button>
    </div>
  </div>
{:else}
  <slot />
{/if}

<style>
  .error-boundary {
    padding: 1rem;
    border: 1px solid #fee2e2;
    border-radius: 0.5rem;
    background: #fef2f2;
    color: #991b1b;
  }
</style>
```

### Usage in Components

```typescript
// src/lib/custom/SearchResults.svelte (ENHANCED)
<script lang="ts">
  import ErrorBoundary from './ErrorBoundary.svelte';
  import DatasetCard from './DatasetCard.svelte';

  let errorBoundary: ErrorBoundary;

  function handleCardError(event: CustomEvent) {
    errorBoundary?.captureError(new Error(event.detail));
  }
</script>

<ErrorBoundary bind:this={errorBoundary}>
  <div class="results-grid">
    {#each results as result (result.dataset.file_identifier)}
      <DatasetCard
        {result}
        on:error={handleCardError}
      />
    {/each}
  </div>
</ErrorBoundary>
```

### Benefits
✅ **Isolation**: One component error doesn't crash others  
✅ **Better UX**: User can retry individual items  
✅ **Debugging**: Errors logged with full context  
✅ **Resilience**: Graceful degradation  

---

## UPGRADE #6: INPUT VALIDATION LAYER (MEDIUM EFFORT)

### Problem: No Centralized Validation

```typescript
// ❌ Validation scattered in components
if (!query.trim()) return;
if (query.length > 500) return;
```

### Solution: Validation Service

```typescript
// src/lib/services/validation.service.ts (NEW)
export class ValidationError extends Error {
  constructor(public field: string, message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class SearchQueryValidator {
  static validate(query: string): void {
    if (!query) {
      throw new ValidationError('query', 'Search query is required');
    }

    if (query.trim().length === 0) {
      throw new ValidationError('query', 'Search query cannot be empty');
    }

    if (query.length > 1000) {
      throw new ValidationError('query', 'Search query too long (max 1000 characters)');
    }

    if (/^[<>{}'"]/i.test(query)) {
      throw new ValidationError('query', 'Query contains invalid characters');
    }
  }

  static sanitize(query: string): string {
    return query.trim().replace(/\s+/g, ' ').slice(0, 1000);
  }
}

export class ChatMessageValidator {
  static validate(message: string): void {
    if (!message) {
      throw new ValidationError('message', 'Message is required');
    }

    if (message.trim().length === 0) {
      throw new ValidationError('message', 'Message cannot be empty');
    }

    if (message.length > 2000) {
      throw new ValidationError('message', 'Message too long (max 2000 characters)');
    }
  }
}
```

### Usage

```typescript
// src/routes/+page.svelte
<script lang="ts">
  import { SearchQueryValidator, ValidationError } from '$lib/services/validation.service';

  async function handleSearch(event: Event) {
    const customEvent = event as CustomEvent;
    const query = customEvent.detail?.query || searchQuery;

    try {
      SearchQueryValidator.validate(query);
      const sanitized = SearchQueryValidator.sanitize(query);
      await searchStore.executeSearch(sanitized);
    } catch (error) {
      if (error instanceof ValidationError) {
        searchStore.setError(error.message);
      }
    }
  }
</script>
```

### Benefits
✅ **Consistency**: Same validation rules everywhere  
✅ **Security**: Centralized sanitization  
✅ **Maintainability**: Change validation in one place  
✅ **Testing**: Easy to unit test validators  

---

## UPGRADE #7: SERVICE LAYER (ADVANCED)

### Current Problem: Store Has Too Many Responsibilities

```typescript
// Store handles: state, API calls, error handling, caching
```

### Solution: Service Layer Abstraction

```typescript
// src/lib/services/search.service.ts (NEW)
import { SearchRepository } from '$lib/repositories/search.repository';
import { SearchQueryValidator } from './validation.service';
import type { SearchResult } from '$lib/api/types';

export class SearchService {
  constructor(private repository: SearchRepository) {}

  async performSearch(query: string): Promise<SearchResult[]> {
    // 1. Validate
    SearchQueryValidator.validate(query);
    const sanitized = SearchQueryValidator.sanitize(query);

    // 2. Fetch
    const results = await this.repository.search(sanitized, 10);

    // 3. Post-process
    return this.postProcessResults(results);
  }

  private postProcessResults(results: SearchResult[]): SearchResult[] {
    // Sort by relevance
    return results.sort((a, b) => b.score - a.score);
  }
}

// src/lib/stores/searchStore.ts (REFACTORED)
export function createSearchStore(searchService: SearchService) {
  // ...
  
  executeSearch: async (query: string) => {
    this.setQuery(query);
    this.startSearch();

    try {
      const results = await searchService.performSearch(query);
      this.setResults(results);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Search failed';
      this.setError(errorMessage);
    }
  }
}
```

### Benefits
✅ **Layered Architecture**: Clear separation of concerns  
✅ **Business Logic Encapsulation**: Service owns validation, post-processing  
✅ **Testability**: Service tested independently from store  
✅ **Reusability**: Service can be used by multiple stores/components  

---

## UPGRADE #8: OBSERVABLE PATTERN / EVENT BUS (ADVANCED)

### Problem: Function Passing for Communication

```typescript
// ❌ Current: Passing functions around
executeSearch(query, searchFn);
```

### Solution: Event Bus for Decoupled Communication

```typescript
// src/lib/events/event-bus.ts (NEW)
type Listener<T> = (data: T) => void;

export class EventBus {
  private listeners: Map<string, Listener<any>[]> = new Map();

  on<T>(event: string, listener: Listener<T>): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(listener);

    // Return unsubscribe function
    return () => {
      const list = this.listeners.get(event);
      if (list) {
        const index = list.indexOf(listener);
        if (index > -1) list.splice(index, 1);
      }
    };
  }

  emit<T>(event: string, data: T): void {
    const list = this.listeners.get(event);
    if (list) {
      list.forEach(listener => listener(data));
    }
  }

  clear(): void {
    this.listeners.clear();
  }
}

export const eventBus = new EventBus();
```

### Usage

```typescript
// Events definition
export const SEARCH_EVENTS = {
  SEARCH_REQUESTED: 'search:requested',
  SEARCH_COMPLETED: 'search:completed',
  SEARCH_FAILED: 'search:failed'
};

// Store emits events
export function createSearchStore(searchService: SearchService) {
  return {
    executeSearch: async (query: string) => {
      this.startSearch();
      eventBus.emit(SEARCH_EVENTS.SEARCH_REQUESTED, query);

      try {
        const results = await searchService.performSearch(query);
        this.setResults(results);
        eventBus.emit(SEARCH_EVENTS.SEARCH_COMPLETED, results);
      } catch (error) {
        this.setError(error.message);
        eventBus.emit(SEARCH_EVENTS.SEARCH_FAILED, error);
      }
    }
  };
}

// Components listen to events
export let SearchMetrics = {
  searchCount: 0,
  lastSearchTime: null
};

eventBus.on(SEARCH_EVENTS.SEARCH_COMPLETED, (results) => {
  SearchMetrics.searchCount++;
  SearchMetrics.lastSearchTime = new Date();
  console.log(`Search completed: ${results.length} results in ${Date.now() - startTime}ms`);
});
```

### Benefits
✅ **Decoupling**: Components don't know about each other  
✅ **Observability**: Analytics can hook into events  
✅ **Testing**: Easy to verify events are emitted  
✅ **Extensibility**: New subscribers can be added without changing existing code  

---

## IMPLEMENTATION PRIORITY & EFFORT MATRIX

| Upgrade | Priority | Effort | Impact | Days |
|---------|----------|--------|--------|------|
| API Client Refactor | 🔴 Critical | 2 hours | High | 0.25 |
| Store Refactor | 🔴 Critical | 1.5 hours | High | 0.2 |
| Repository Pattern | 🟠 High | 2.5 hours | High | 0.3 |
| Error Boundaries | 🟠 High | 3 hours | Medium | 0.4 |
| Validation Layer | 🟠 High | 2 hours | Medium | 0.25 |
| Dependency Injection | 🟡 Medium | 2 hours | Medium | 0.25 |
| Service Layer | 🟡 Medium | 4 hours | Medium | 0.5 |
| Observable Pattern | 🟢 Nice-to-Have | 3 hours | Low | 0.4 |

**Total: ~5 days for all upgrades** (can do incrementally)

---

## RECOMMENDED IMPLEMENTATION PATH

### Phase 1: Foundation (1 day)
1. API Client Refactoring ← Start here
2. Store Action Refactoring
3. Dependency Injection

### Phase 2: Data Access (0.5 day)
4. Repository Pattern

### Phase 3: Resilience (1 day)
5. Error Boundaries
6. Validation Layer

### Phase 4: Architecture (1.5 days)
7. Service Layer
8. Observable Pattern

### Phase 5: Testing
- Add tests for each new layer
- Verify no regressions

---

## BEFORE & AFTER COMPARISON

### Component Code Size & Complexity

**Before** (Current):
```typescript
// +page.svelte: 35 lines with mixed concerns
async function handleSearch(event: Event) {
  const query = event.detail?.query || searchQuery;
  if (!query.trim()) return;
  await searchActions.executeSearch(query, searchDatasets);
}
```

**After** (Refactored):
```typescript
// +page.svelte: 20 lines, single responsibility
async function handleSearch(event: Event) {
  const query = event.detail?.query || searchQuery;
  try {
    await searchStore.executeSearch(query);
  } catch (error) {
    console.error('Search failed:', error);
  }
}
```

### Testability

**Before**:
```typescript
// Hard to test: needs mock for searchDatasets function
test('search updates store', async () => {
  const mockSearch = vi.fn().mockResolvedValue({ results: [] });
  await searchActions.executeSearch('query', mockSearch);
  // ✗ Hard to verify error handling, retries, validation
});
```

**After**:
```typescript
// Easy to test: inject mock repository
test('search validates query', async () => {
  const mockRepo = createMockRepository();
  const service = new SearchService(mockRepo);
  await expect(service.performSearch('')).rejects.toThrow();
  // ✓ Clear separation of concerns
});
```

---

## QUESTIONS TO ASK LLM BEFORE IMPLEMENTING

To align with Task.txt Section 5 (evaluation on questions asked):

1. **Architecture Question**:  
   > "Should we implement the Repository pattern first before refactoring stores, or should we refactor stores and API client first?"

2. **Design Pattern Question**:  
   > "For the Service layer, should we use a class-based approach with methods, or a functional composition pattern with Svelte stores?"

3. **Error Handling Question**:  
   > "How should we prioritize between implementing error boundaries vs. implementing a comprehensive error recovery strategy with retry logic?"

4. **Testing Question**:  
   > "What's the best pattern for testing async store actions in Svelte 5? Should we use Vitest with mocked repositories?"

5. **Dependency Injection Question**:  
   > "Should we implement a full DI container, or is a simpler factory function pattern sufficient for a frontend app?"

---

## NEXT STEPS

**Ready to implement?**

1. **Pick one upgrade** from Phase 1 (API Client Refactoring is easiest)
2. **Ask LLM architectural questions** using prompts above
3. **Implement the code** based on recommendations
4. **Test thoroughly** before moving to next upgrade
5. **Commit to git** after each successful upgrade
6. **Document changes** in architecture decision log

Would you like me to help implement any of these upgrades?
