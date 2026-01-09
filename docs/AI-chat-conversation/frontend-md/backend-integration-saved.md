# Backend Integration Guide - Best Practices

## Overview
This guide explains how to properly integrate the SvelteKit frontend with the Python backend API following software engineering best practices.

---

## 1. Environment Configuration

### 1.1 Environment Variables
Create `.env.local` in the project root:

```
# .env.local
VITE_API_BASE_URL=http://localhost:8000/api
VITE_API_TIMEOUT=30000
VITE_LOG_LEVEL=debug
```

### 1.2 Configuration File
Create `src/lib/config/api.config.ts`:

```typescript
// API endpoints configuration
export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: import.meta.env.VITE_API_TIMEOUT || 30000,
  logLevel: import.meta.env.VITE_LOG_LEVEL || 'error',
};

export const ENDPOINTS = {
  // Search
  searchDatasets: '/search',
  suggestQueries: '/search/suggestions',
  
  // Chat
  chat: '/chat',
  
  // Health
  health: '/health',
};
```

---

## 2. API Client - Best Practices

### 2.1 Error Handling Strategy

```typescript
// src/lib/api/errors.ts
export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}
```

### 2.2 Request/Response Types

```typescript
// src/lib/api/types.ts

// Generic API Response wrapper
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  timestamp: string;
}

// Search
export interface SearchRequest {
  query: string;
  limit?: number;
  offset?: number;
  filters?: {
    organisation?: string;
    dataType?: string;
    dateRange?: {
      start: string;
      end: string;
    };
  };
}

export interface SearchResult {
  id: string;
  title: string;
  abstract: string;
  organisation: string;
  relevance: number;
  keywords: string[];
  dataTypes: string[];
  url?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  offset: number;
}

// Chat
export interface ChatRequest {
  message: string;
  conversationId?: string;
  context?: {
    previousMessages: Array<{
      role: 'user' | 'assistant';
      content: string;
    }>;
  };
}

export interface ChatResponse {
  message: string;
  conversationId: string;
  sources?: Array<{
    title: string;
    url?: string;
    relevance: number;
  }>;
}

// Health Check
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
  services?: {
    database: boolean;
    cache: boolean;
    vectorStore: boolean;
  };
}
```

### 2.3 Enhanced API Client

```typescript
// src/lib/api/client.ts
import { API_CONFIG, ENDPOINTS } from './api.config';
import {
  ApiError,
  NetworkError,
  TimeoutError,
} from './errors';
import type {
  ApiResponse,
  SearchRequest,
  SearchResponse,
  ChatRequest,
  ChatResponse,
  HealthCheckResponse,
} from './types';

// Request/Response Interceptors
type RequestInterceptor = (config: RequestConfig) => RequestConfig;
type ResponseInterceptor<T> = (response: T) => T;

interface RequestConfig {
  headers: Record<string, string>;
  method: string;
  body?: string;
}

class ApiClient {
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor<any>[] = [];

  // Add request interceptor (e.g., auth headers, logging)
  public addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  // Add response interceptor (e.g., error handling, logging)
  public addResponseInterceptor<T>(interceptor: ResponseInterceptor<T>): void {
    this.responseInterceptors.push(interceptor);
  }

  // Core fetch method with interceptors
  private async request<T>(
    endpoint: string,
    options: {
      method?: string;
      body?: any;
      headers?: Record<string, string>;
      timeout?: number;
    } = {}
  ): Promise<T> {
    const method = options.method || 'GET';
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    let config: RequestConfig = {
      headers,
      method,
      body: options.body ? JSON.stringify(options.body) : undefined,
    };

    // Apply request interceptors
    for (const interceptor of this.requestInterceptors) {
      config = interceptor(config);
    }

    const url = `${API_CONFIG.baseUrl}${endpoint}`;
    const timeout = options.timeout || API_CONFIG.timeout;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        ...config,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const contentType = response.headers.get('content-type');
      const isJson = contentType?.includes('application/json');
      const data = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        throw new ApiError(
          response.status,
          data?.error?.message || `HTTP ${response.status}`,
          data?.error?.details
        );
      }

      let result = data as T;

      // Apply response interceptors
      for (const interceptor of this.responseInterceptors) {
        result = interceptor(result);
      }

      return result;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        throw new NetworkError('Failed to connect to server');
      }
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new TimeoutError('Request timed out');
      }
      throw new NetworkError(error instanceof Error ? error.message : 'Unknown error');
    }
  }

  // Search endpoint
  public async search(
    request: SearchRequest
  ): Promise<SearchResponse> {
    const response = await this.request<ApiResponse<SearchResponse>>(
      ENDPOINTS.searchDatasets,
      {
        method: 'POST',
        body: request,
      }
    );
    return response.data as SearchResponse;
  }

  // Chat endpoint
  public async chat(
    request: ChatRequest
  ): Promise<ChatResponse> {
    const response = await this.request<ApiResponse<ChatResponse>>(
      ENDPOINTS.chat,
      {
        method: 'POST',
        body: request,
      }
    );
    return response.data as ChatResponse;
  }

  // Health check
  public async healthCheck(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>(
      ENDPOINTS.health
    );
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Add default interceptors
apiClient.addRequestInterceptor((config) => {
  if (API_CONFIG.logLevel === 'debug') {
    console.debug('[API Request]', config.method, config);
  }
  return config;
});

apiClient.addResponseInterceptor((response) => {
  if (API_CONFIG.logLevel === 'debug') {
    console.debug('[API Response]', response);
  }
  return response;
});
```

---

## 3. Store Integration

### 3.1 Enhanced Search Store with Error Recovery

```typescript
// src/lib/stores/searchStore.ts
import { writable, derived } from 'svelte/store';
import { apiClient } from '$lib/api/client';
import { ApiError, NetworkError, TimeoutError } from '$lib/api/errors';
import type { SearchResult } from '$lib/api/types';

interface SearchState {
  query: string;
  results: SearchResult[];
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
  timestamp: number | null;
  retryCount: number;
}

function createSearchStore() {
  const { subscribe, set, update } = writable<SearchState>({
    query: '',
    results: [],
    loading: false,
    error: null,
    hasSearched: false,
    timestamp: null,
    retryCount: 0,
  });

  return {
    subscribe,
    
    setQuery: (query: string) => {
      update((state) => ({ ...state, query }));
    },

    search: async (query: string, maxRetries = 3) => {
      update((state) => ({
        ...state,
        query,
        loading: true,
        error: null,
        retryCount: 0,
      }));

      let lastError: Error | null = null;

      for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
          const response = await apiClient.search({
            query,
            limit: 20,
          });

          update((state) => ({
            ...state,
            results: response.results,
            loading: false,
            hasSearched: true,
            timestamp: Date.now(),
          }));

          return response;
        } catch (error) {
          lastError = error as Error;

          // Don't retry on client errors (4xx)
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
            update((state) => ({
              ...state,
              error: error.message,
              loading: false,
            }));
            return null;
          }

          // Retry on server errors (5xx) or network errors
          if (attempt < maxRetries - 1) {
            const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
            await new Promise((resolve) => setTimeout(resolve, delay));
            update((state) => ({ ...state, retryCount: attempt + 1 }));
          }
        }
      }

      // All retries failed
      const errorMessage = lastError instanceof TimeoutError
        ? 'Request timed out. Please try again.'
        : lastError instanceof NetworkError
          ? 'Network error. Please check your connection.'
          : lastError instanceof ApiError
            ? lastError.message
            : 'Search failed. Please try again.';

      update((state) => ({
        ...state,
        error: errorMessage,
        loading: false,
      }));

      return null;
    },

    clear: () => {
      set({
        query: '',
        results: [],
        loading: false,
        error: null,
        hasSearched: false,
        timestamp: null,
        retryCount: 0,
      });
    },
  };
}

export const searchStore = createSearchStore();
```

### 3.2 Enhanced Chat Store with Conversation History

```typescript
// src/lib/stores/chatStore.ts
import { writable } from 'svelte/store';
import { apiClient } from '$lib/api/client';
import type { ChatResponse } from '$lib/api/types';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  sources?: Array<{
    title: string;
    url?: string;
  }>;
}

interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  conversationId: string | null;
}

function createChatStore() {
  const { subscribe, set, update } = writable<ChatState>({
    messages: [],
    loading: false,
    error: null,
    conversationId: null,
  });

  return {
    subscribe,

    sendMessage: async (content: string) => {
      const messageId = `user-${Date.now()}`;

      // Add user message optimistically
      update((state) => ({
        ...state,
        messages: [
          ...state.messages,
          {
            id: messageId,
            role: 'user' as const,
            content,
            timestamp: Date.now(),
          },
        ],
        loading: true,
        error: null,
      }));

      try {
        let state: ChatState | null = null;
        let previousMessages: ChatMessage[] = [];

        // Get current state to build context
        const unsubscribe = subscribe((s) => {
          state = s;
          previousMessages = s.messages.slice(0, -1); // Exclude the message we just added
        });
        unsubscribe();

        const response = await apiClient.chat({
          message: content,
          conversationId: state?.conversationId || undefined,
          context: previousMessages.length > 0 ? {
            previousMessages: previousMessages.map((msg) => ({
              role: msg.role,
              content: msg.content,
            })),
          } : undefined,
        });

        update((state) => ({
          ...state,
          messages: [
            ...state.messages,
            {
              id: `assistant-${Date.now()}`,
              role: 'assistant' as const,
              content: response.message,
              timestamp: Date.now(),
              sources: response.sources,
            },
          ],
          loading: false,
          conversationId: response.conversationId,
        }));
      } catch (error) {
        update((state) => ({
          ...state,
          error: error instanceof Error ? error.message : 'Failed to send message',
          loading: false,
        }));
      }
    },

    clear: () => {
      set({
        messages: [],
        loading: false,
        error: null,
        conversationId: null,
      });
    },
  };
}

export const chatStore = createChatStore();
```

---

## 4. Component Integration

### 4.1 Search Component with Error Handling

```svelte
<!-- src/lib/custom/SearchBar.svelte -->
<script lang="ts">
  import { searchStore } from '$lib/stores/searchStore';
  
  let value = '';
  
  async function handleSearch() {
    if (!value.trim()) return;
    
    await searchStore.search(value);
  }
  
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  }
</script>

<div class="search-bar">
  <input
    type="text"
    placeholder="Search datasets..."
    bind:value
    on:keydown={handleKeydown}
    disabled={$searchStore.loading}
  />
  <button
    on:click={handleSearch}
    disabled={$searchStore.loading || !value.trim()}
  >
    {#if $searchStore.loading}
      Searching...
    {:else}
      Search
    {/if}
  </button>
</div>

{#if $searchStore.error}
  <div class="error-message">
    {$searchStore.error}
  </div>
{/if}
```

---

## 5. Testing Strategy

### 5.1 API Client Testing

```typescript
// src/lib/api/__tests__/client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '../client';
import { ApiError, NetworkError, TimeoutError } from '../errors';

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should make successful search request', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          data: {
            results: [],
            total: 0,
            offset: 0,
          },
        }),
    });

    const result = await apiClient.search({ query: 'test' });
    expect(result.results).toEqual([]);
  });

  it('should handle network errors with retry', async () => {
    global.fetch = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            data: { results: [] },
          }),
      });

    const result = await apiClient.search({ query: 'test' });
    expect(result).toBeDefined();
  });

  it('should throw timeout error', async () => {
    global.fetch = vi.fn().mockImplementation(
      () =>
        new Promise(() => {
          // Never resolves
        })
    );

    await expect(
      apiClient.search({ query: 'test' })
    ).rejects.toThrow(TimeoutError);
  });
});
```

---

## 6. Deployment Checklist

- [ ] Environment variables configured (.env.local)
- [ ] API base URL verified
- [ ] Error handling tested
- [ ] Network timeouts configured
- [ ] Request/response logging enabled in debug mode
- [ ] Retry logic tested for network failures
- [ ] Chat conversation history persisted
- [ ] Search results cached appropriately
- [ ] CORS headers properly configured on backend
- [ ] API rate limiting handled
- [ ] Health check endpoint monitored
- [ ] Error messages user-friendly
- [ ] Loading states visible
- [ ] Offline fallback considered

---

## 7. Security Considerations

1. **Input Validation:** Validate all user inputs before sending to API
2. **Content Security Policy:** Configure CSP headers
3. **HTTPS:** Use HTTPS in production
4. **API Keys:** Never commit API keys; use environment variables
5. **Rate Limiting:** Implement rate limiting on frontend (debounce/throttle)
6. **CORS:** Properly configure CORS on backend
7. **XSS Prevention:** Sanitize API responses
8. **CSRF Protection:** Include CSRF tokens if needed

---

## 8. Performance Optimization

1. **Request Deduplication:** Avoid duplicate requests
2. **Response Caching:** Cache search results by query
3. **Pagination:** Implement infinite scroll or pagination
4. **Lazy Loading:** Load results as needed
5. **Compression:** Use gzip compression for responses
6. **Request Batching:** Combine multiple API calls
7. **Conditional Requests:** Use ETags or If-Modified-Since headers

---

## Next Steps

1. Update frontend components to use the enhanced API client
2. Configure environment variables for your backend
3. Test API integration locally
4. Implement monitoring and logging
5. Set up error tracking (e.g., Sentry)
6. Deploy and monitor in production
