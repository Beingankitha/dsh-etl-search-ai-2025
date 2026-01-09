# Frontend-Backend Integration Plan
## DSH ETL Search AI 2025 - Backend Integration Strategy

**Status**: Planning Phase - Ready for Implementation  
**Scope**: Issues 12-20 Frontend Complete → Integration Phase  
**Date**: December 2025

---

## 1. FRONTEND ISSUES 12-20 FILE MAPPING

### Overview
| Issue | Title | Files Created/Modified | Purpose |
|-------|-------|----------------------|---------|
| **12** | Layout & Navigation | `layout.css`, `+layout.svelte`, `app.css` | Root layout with header/footer, responsive design |
| **13** | State Management | `stores/searchStore.ts`, `stores/chatStore.ts`, `stores/index.ts` | Centralized reactive state for search & chat |
| **14** | API Client Module | `api/client.ts`, `api/types.ts` | HTTP abstraction layer, endpoint definitions |
| **15** | SearchBar Component | `custom/SearchBar.svelte` | Search input with green button, Enter support |
| **16** | DatasetCard & Results | `custom/DatasetCard.svelte`, `custom/SearchResults.svelte` | Dataset display cards, responsive grid |
| **17** | Search Page | `routes/+page.svelte` | Hero section, SearchBar integration, results display |
| **18** | Chat Components | `custom/ChatMessage.svelte`, `custom/ChatInterface.svelte` | Message bubbles, chat input, typing indicator |
| **19** | Chat Page | `routes/chat/+page.svelte` | Chat UI with header, tips, interface |
| **20** | Build Testing | `package.json` | Dependencies, npm run build validation |

### File Directory Structure
```
frontend/src/
├── lib/
│   ├── api/
│   │   ├── client.ts           ← Issue 14: HTTP client (searchDatasets, sendChatMessage)
│   │   └── types.ts            ← Issue 14: TypeScript interfaces for API contracts
│   ├── stores/
│   │   ├── searchStore.ts      ← Issue 13: Search state + executeSearch action
│   │   ├── chatStore.ts        ← Issue 13: Chat state + sendMessage action
│   │   └── index.ts            ← Issue 13: Central export
│   ├── custom/
│   │   ├── SearchBar.svelte    ← Issue 15: Search input component
│   │   ├── DatasetCard.svelte  ← Issue 16: Dataset display card
│   │   ├── SearchResults.svelte← Issue 16: Results grid container
│   │   ├── ChatMessage.svelte  ← Issue 18: Message bubble component
│   │   └── ChatInterface.svelte← Issue 18: Chat interaction container
│   ├── assets/
│   │   └── favicon.svg         ← Issue 12: Green theme favicon
│   └── app.css                 ← Issue 12/20: Global theme variables, green colors
├── routes/
│   ├── +layout.svelte          ← Issue 12: Root layout (header/footer)
│   ├── layout.css              ← Issue 12: Layout-specific styling
│   ├── +page.svelte            ← Issue 17: Search page (hero + SearchBar)
│   └── chat/
│       └── +page.svelte        ← Issue 19: Chat page interface
└── app.d.ts                    ← Global TypeScript definitions

package.json                    ← Issue 20: Dependencies
```

---

## 2. CURRENT FRONTEND STATE

### API Client Endpoints (Ready for Backend)
```typescript
// src/lib/api/client.ts
searchDatasets(query: string, limit: number = 10)
  → POST /api/search
  → Input: { query, top_k }
  → Output: SearchResponse { query, results[] }

sendChatMessage(message: string, history: ChatMessage[] = [])
  → POST /api/chat
  → Input: { message, history }
  → Output: ChatResponse { message, sources[] }

getDatasets(limit: number = 20, offset: number = 0)
  → GET /api/datasets

getDatasetById(fileIdentifier: string)
  → GET /api/datasets/{fileIdentifier}

checkHealth()
  → GET /api/health
```

### TypeScript Types (Expecting Backend Match)
```typescript
interface Dataset {
  file_identifier: string
  title: string
  abstract: string
  topic_category: string[]
  keywords: string[]
  lineage?: string
  supplemental_info?: string
}

interface SearchResult {
  dataset: Dataset
  score: number    // 0..1 semantic relevance
}

interface ChatMessage {
  role: "system" | "user" | "assistant"
  content: string
}
```

### State Management Architecture
```
searchStore (Issue 13):
├── state: { query, results, loading, error, hasSearched }
├── actions:
│   ├── setQuery(string)
│   ├── executeSearch(query)  ← Calls searchDatasets() from client.ts
│   ├── setResults(SearchResult[])
│   ├── setError(string)
│   └── clear()
└── subscribers: SearchResults.svelte, ChatInterface.svelte

chatStore (Issue 13):
├── state: { messages[], loading, error }
├── actions:
│   ├── addMessage(ChatMessage)
│   ├── sendMessage(text)     ← Calls sendChatMessage() from client.ts
│   ├── setLoading(boolean)
│   ├── setError(string)
│   └── clear()
└── subscribers: ChatInterface.svelte
```

---

## 3. BACKEND INTEGRATION REQUIREMENTS (Per Task.txt)

### Task.txt Key Requirements (Section 5: Evaluation Criteria)
The DSH team will evaluate us on:
- **5.1** System architecture questions asked to LLM
- **5.2** Code architecture questions for clean design
- **5.3** Software engineering best practices questions
- **5.4** OOP code generation with design patterns
- **5.5** Code refactoring based on architecture needs
- **5.6** Error correction and improvement iterations

**Critical**: Evaluation is on **questions asked**, NOT just code submitted.

### Professional Architecture Requirements
1. **API Contract Validation**
   - Match backend response formats exactly
   - Type safety with TypeScript interfaces
   - Backward compatibility handling

2. **Error Handling Architecture**
   - Network error recovery with exponential backoff
   - User-facing error messages vs technical logs
   - Error boundaries for component failure isolation
   - Graceful fallbacks for missing data

3. **State Management Patterns**
   - Optimistic updates for user experience
   - Conflict resolution between frontend/backend state
   - Cached responses with invalidation strategies
   - Offline capability considerations

4. **Request/Response Interceptors**
   - Authentication token injection (Bearer tokens)
   - Request logging and monitoring
   - Response transformation and validation
   - Rate limiting and request queuing

5. **Loading States & UI Feedback**
   - Skeleton loaders for search results
   - Typing indicator animations for chat
   - Progressive loading indicators
   - Estimated time remaining for long operations

6. **Security & Validation**
   - Input sanitization for search queries
   - XSS prevention for chat messages
   - CORS and authentication headers
   - Sensitive data redaction in logs

---

## 4. PROPOSED INTEGRATION ARCHITECTURE

### Layer 1: Enhanced API Client (Production-Ready)
```typescript
// src/lib/api/client.ts (enhanced)
├── Error Handling
│   ├── ApiClientError class with retry logic
│   ├── Exponential backoff for transient failures
│   └── Error categorization (network/validation/auth/server)
├── Request Interceptors
│   ├── Add Bearer token from auth store
│   ├── Add request ID for tracing
│   ├── Add timestamp and request metadata
│   └── Log all outgoing requests
├── Response Interceptors
│   ├── Validate response schema against types
│   ├── Transform backend data if needed
│   ├── Parse error responses into user-friendly messages
│   └── Log responses for debugging
└── Request Queue & Throttling
    ├── Queue concurrent requests
    ├── Enforce rate limits
    └── Handle request deduplication
```

### Layer 2: Repository Pattern (Data Access)
```typescript
// src/lib/repositories/SearchRepository.ts (new)
├── search(query, options): Promise<SearchResult[]>
├── getDatasetById(id): Promise<Dataset>
├── getDatasets(pagination): Promise<Dataset[]>
└── cache management and invalidation

// src/lib/repositories/ChatRepository.ts (new)
├── sendMessage(message, context): Promise<ChatResponse>
├── getConversationHistory(): Promise<ChatMessage[]>
└── clearConversation(): void
```

### Layer 3: Service Layer (Business Logic)
```typescript
// src/lib/services/SearchService.ts (new)
├── SearchStrategy interface (semantic, keyword, hybrid)
├── QueryParser and validation
├── ResultsPostProcessor (sorting, filtering, deduplication)
├── CacheManager with TTL
└── AnalyticsTracker

// src/lib/services/ChatService.ts (new)
├── ConversationManager (context, history, memory)
├── MessageValidator and sanitization
├── ResponseFormatter (markdown, citations, formatting)
├── RAG integration (source citation)
└── ConversationAnalytics
```

### Layer 4: Store Enhancements (State Management)
```typescript
// src/lib/stores/searchStore.ts (enhanced)
├── Pagination state { page, pageSize, totalCount }
├── Filters state { category, dateRange, relevanceThreshold }
├── Sort preferences { field, direction }
├── Search history (last 10 queries)
├── Cached results with TTL
└── Optimistic updates and rollback

// src/lib/stores/chatStore.ts (enhanced)
├── Conversation context and memory
├── Message retry queue
├── Typing indicators per participant
├── User preferences (compact view, auto-scroll)
├── Conversation history navigation
└── Source citations management
```

### Layer 5: Component Enhancements (UI/UX)
```typescript
// Components with error boundaries and loading states
├── SearchResults.svelte
│   ├── Skeleton loader state
│   ├── Error message component with retry
│   ├── Empty state with suggestions
│   └── Pagination controls
├── ChatInterface.svelte
│   ├── Message retry buttons on failed sends
│   ├── Optimistic message display
│   ├── Source citations as expandable badges
│   ├── Connection status indicator
│   └── Offline mode awareness
└── New: ErrorBoundary.svelte
    ├── Catch component-level errors
    ├── Display user-friendly error UI
    └── Log errors for debugging
```

---

## 5. INTEGRATION QUESTIONS FOR LLM (Task.txt Section 5.1-5.5)

### System Architecture Questions
1. **Monolithic vs Modular**: Should we implement Repository, Service, and Store layers, or keep API client simple?
2. **Caching Strategy**: Where should caching happen - API client, service layer, or Svelte stores?
3. **Error Recovery**: What exponential backoff strategy is best for network errors?
4. **State Sync**: How should we handle conflicts when backend state diverges from frontend assumptions?

### Code Architecture Questions
1. **Design Patterns**: Should we implement Repository, Factory, and Strategy patterns?
2. **Dependency Injection**: How should services receive dependencies (constructor, containers)?
3. **Component Composition**: Should SearchResults and ChatInterface use child components or slot-based design?
4. **Type Safety**: How deeply should we validate responses against TypeScript interfaces?

### Software Engineering Questions
1. **Testing Strategy**: What's the best approach for testing async store actions and API calls?
2. **Error Logging**: How should we structure error logs for debugging in production?
3. **Performance**: What metrics should we track (request latency, cache hit rate, error rates)?
4. **Security**: How should we handle authentication tokens securely in the frontend?

### OOP & Clean Code Questions
1. **Data Transformation**: Should we use OOP classes (SearchResultsCollection, ChatConversation) or functional utilities?
2. **Validation**: Where should input/output validation happen - client, service, or component level?
3. **Extensibility**: How should the code support future search strategies (keyword, vector, hybrid)?
4. **Separation of Concerns**: What should each layer own (business logic, data access, presentation)?

### Code Improvement Questions
1. **API Error Handling**: How can we standardize error handling across all endpoints?
2. **Request Deduplication**: Should we prevent duplicate simultaneous search queries?
3. **Memory Leaks**: How do we ensure Svelte store subscriptions are properly cleaned up?
4. **Load Testing**: How should the frontend behave under slow networks or large result sets?

---

## 6. IMPLEMENTATION ROADMAP

### Phase 1: API Client Enhancement (Foundation)
- [ ] Error handling with retry logic
- [ ] Request/response interceptors
- [ ] Request queuing and deduplication
- [ ] Response validation against types

### Phase 2: Repository & Service Layers
- [ ] Repository pattern implementation
- [ ] Service layer with business logic
- [ ] Cache management strategy
- [ ] Validation and sanitization

### Phase 3: Store Enhancement
- [ ] Pagination and filtering state
- [ ] Optimistic updates
- [ ] Conversation context management
- [ ] Message retry queue

### Phase 4: Component Enhancements
- [ ] Error boundary component
- [ ] Skeleton loaders
- [ ] Retry UI patterns
- [ ] Loading state indicators

### Phase 5: Testing & Monitoring
- [ ] Unit tests for services
- [ ] Integration tests for API calls
- [ ] Error logging implementation
- [ ] Performance metrics tracking

---

## 7. EXPECTED BACKEND ENDPOINTS

The frontend assumes the following backend API:

### Search Endpoint
```
POST /api/search
Request:  { query: string, top_k?: number }
Response: {
  query: string,
  results: [{
    dataset: {
      file_identifier: string,
      title: string,
      abstract: string,
      topic_category: string[],
      keywords: string[],
      lineage?: string,
      supplemental_info?: string
    },
    score: number (0-1)
  }]
}
```

### Chat Endpoint
```
POST /api/chat
Request:  {
  message: string,
  history?: [{ role: string, content: string }]
}
Response: {
  message: { role: "assistant", content: string },
  sources: [{
    dataset: Dataset,
    score: number
  }]
}
```

### Dataset Endpoints
```
GET /api/datasets?limit=20&offset=0
GET /api/datasets/{file_identifier}
GET /api/health
```

---

## 8. NEXT STEPS

1. **Review Questions Above**: Which questions should we ask the LLM first?
2. **Validate Backend Contract**: Confirm backend endpoints match expected types
3. **Implement API Enhancement**: Start with error handling and interceptors
4. **Add Repository Pattern**: Create data access abstraction layer
5. **Enhance Stores**: Add pagination, caching, optimization
6. **Component Improvements**: Add loading states and error handling
7. **Testing**: Implement comprehensive test suite
8. **Documentation**: Update API documentation and architecture diagrams

---

## 9. SUCCESS CRITERIA

✅ **Code Quality**:
- Clean architecture with separation of concerns
- DRY principle applied (no duplicate error handling)
- SOLID principles followed (SRP, OCP, LSP, ISP, DIP)
- TypeScript strict mode, all types defined

✅ **Error Handling**:
- All API errors caught and transformed to user-friendly messages
- Retry logic for transient failures
- Graceful degradation when services unavailable
- Error logging for debugging

✅ **State Management**:
- Single source of truth for each domain
- Optimistic updates with rollback
- Conversation context preserved across page navigation
- Cache invalidation when needed

✅ **User Experience**:
- Loading states visible for all async operations
- Error messages actionable and helpful
- Search results paginated and filtered
- Chat messages sent and received smoothly

✅ **Task.txt Compliance**:
- Questions document shows thoughtful architecture planning
- LLM used to refine and improve code
- OOP patterns and clean code principles applied
- Iterative improvements based on LLM feedback

---

## Questions for Next Step?

**Should we proceed with:**
1. Error handling & retry logic first?
2. Repository pattern implementation?
3. Enhanced store architecture?
4. Component error boundaries?

Or would you like to ask the LLM specific architecture questions first per Task.txt requirements?
