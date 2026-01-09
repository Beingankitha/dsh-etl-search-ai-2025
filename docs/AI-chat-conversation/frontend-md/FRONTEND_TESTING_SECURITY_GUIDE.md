# Frontend Testing & Security Implementation Guide

## Part 1: Testing Strategy

### Unit Testing Setup

```bash
# Install testing dependencies
npm install -D vitest @vitest/ui jsdom @testing-library/svelte
```

**Example Test: SearchBar Component**

```typescript
// src/lib/custom/__tests__/SearchBar.test.ts
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import SearchBar from '../SearchBar.svelte';

describe('SearchBar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render search input', () => {
    render(SearchBar);
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
  });

  it('should debounce suggestions', async () => {
    const { getByRole } = render(SearchBar);
    const input = getByRole('textbox') as HTMLInputElement;

    // Type quickly
    fireEvent.input(input, { target: { value: 'soil' } });
    fireEvent.input(input, { target: { value: 'soil carbon' } });

    // Should only call suggestions once (debounced)
    await waitFor(() => {
      expect(input.value).toBe('soil carbon');
    });
  });

  it('should cleanup on destroy', () => {
    const { unmount } = render(SearchBar);
    unmount();
    // Verify no memory leaks (checked via memory profiler)
  });
});
```

**Example Test: Logger**

```typescript
// src/lib/__tests__/logger.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { logger } from '../logger';

describe('Logger', () => {
  beforeEach(() => {
    logger.clearLogs();
  });

  it('should log messages with levels', () => {
    logger.info('Test message', { context: 'value' });
    const logs = logger.getLogs();

    expect(logs).toHaveLength(1);
    expect(logs[0].level).toBe('INFO');
    expect(logs[0].message).toBe('Test message');
    expect(logs[0].context).toEqual({ context: 'value' });
  });

  it('should track requests', () => {
    logger.logRequest('GET', '/api/test', 200, 100);
    const requests = logger.getRequestLogs();

    expect(requests).toHaveLength(1);
    expect(requests[0].method).toBe('GET');
    expect(requests[0].status).toBe(200);
  });

  it('should maintain max log size', () => {
    // Log 1001 messages
    for (let i = 0; i < 1001; i++) {
      logger.info(`Message ${i}`);
    }

    const logs = logger.getLogs();
    expect(logs.length).toBeLessThanOrEqual(1000);
  });

  it('should sanitize URLs', async () => {
    logger.logRequest('GET', '/api/search?api_key=secret&q=test', 200, 100);
    const requests = logger.getRequestLogs();

    // Should remove query parameters
    expect(requests[0].url).toBe('/api/search');
    expect(requests[0].url).not.toContain('api_key');
  });
});
```

**Example Test: Error Handling**

```typescript
// src/lib/api/__tests__/errors.test.ts
import { describe, it, expect } from 'vitest';
import {
  ApiError,
  NetworkError,
  ValidationError,
  isRetryable,
} from '../errors';

describe('Error Classes', () => {
  it('should mark network errors as retryable', () => {
    const error = new NetworkError('Connection failed');
    expect(error.retryable).toBe(true);
  });

  it('should mark validation errors as non-retryable', () => {
    const error = new ValidationError('Invalid input');
    expect(error.retryable).toBe(false);
  });

  it('should check retryability', () => {
    const networkError = new NetworkError('Failed');
    const clientError = new ValidationError('Invalid');

    expect(isRetryable(networkError)).toBe(true);
    expect(isRetryable(clientError)).toBe(false);
  });
});
```

### E2E Testing Setup

```bash
npm install -D playwright @playwright/test
```

**Example E2E Test**

```typescript
// tests/e2e/search.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Search Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173/');
  });

  test('should search and display results', async ({ page }) => {
    // Fill search input
    const searchInput = page.getByRole('textbox');
    await searchInput.fill('soil carbon data');

    // Click search button
    const searchButton = page.getByRole('button', { name: /search/i });
    await searchButton.click();

    // Wait for results
    await page.waitForSelector('[class*="results"]', { timeout: 10000 });

    // Verify results are displayed
    const results = await page.locator('[class*="dataset-card"]').count();
    expect(results).toBeGreaterThan(0);
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Simulate offline
    await page.context().setOffline(true);

    const searchInput = page.getByRole('textbox');
    await searchInput.fill('test query');
    const searchButton = page.getByRole('button', { name: /search/i });
    await searchButton.click();

    // Should show error message
    await expect(page.getByText(/network error|failed/i)).toBeVisible();

    // Restore connection
    await page.context().setOffline(false);
  });

  test('should debounce suggestions', async ({ page }) => {
    const searchInput = page.getByRole('textbox');

    // Type quickly
    await searchInput.type('soil', { delay: 10 });

    // Wait to ensure debounce completed
    await page.waitForTimeout(400);

    // Suggestions should appear
    const suggestions = page.locator('[class*="suggestion"]');
    const count = await suggestions.count();

    // Should have made only 1 request despite multiple key presses
    expect(count).toBeGreaterThanOrEqual(0); // Depends on API
  });
});
```

### Coverage Targets

| Area | Target |
|------|--------|
| Statements | 80%+ |
| Branches | 75%+ |
| Functions | 80%+ |
| Lines | 80%+ |

---

## Part 2: Security Hardening

### 1. Content Security Policy (CSP)

**Add to `src/app.html`:**

```html
<meta
  http-equiv="Content-Security-Policy"
  content="
    default-src 'self';
    script-src 'self' 'wasm-unsafe-eval';
    style-src 'self' 'unsafe-inline' fonts.googleapis.com;
    font-src 'self' fonts.gstatic.com;
    connect-src 'self' https://api.your-domain.com;
    img-src 'self' data: https:;
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
  "
/>
```

### 2. Security Headers (Backend Configuration)

**Add to backend CORS middleware:**

```python
# src/api/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response
```

### 3. Input Validation

**Enhanced SearchBar validation:**

```typescript
// src/lib/services/validation.service.ts
export class ValidationService {
  static validateSearchQuery(query: string): { valid: boolean; error?: string } {
    if (!query || typeof query !== 'string') {
      return { valid: false, error: 'Query must be a string' };
    }

    const trimmed = query.trim();

    if (trimmed.length === 0) {
      return { valid: false, error: 'Query cannot be empty' };
    }

    if (trimmed.length > 1000) {
      return { valid: false, error: 'Query cannot exceed 1000 characters' };
    }

    // Check for SQL injection patterns (basic)
    if (/['";\\]/g.test(trimmed)) {
      return { valid: false, error: 'Invalid characters in query' };
    }

    return { valid: true };
  }

  static sanitizeQuery(query: string): string {
    return query
      .trim()
      .replace(/\s+/g, ' ')
      .replace(/['"\\]/g, '')
      .slice(0, 1000);
  }
}
```

### 4. API Authentication

**Add token-based auth:**

```typescript
// src/lib/api/auth.ts
export class AuthService {
  private token: string | null = null;
  private tokenExpiry: number | null = null;

  setToken(token: string, expiresIn: number) {
    this.token = token;
    this.tokenExpiry = Date.now() + expiresIn * 1000;
    localStorage.setItem('auth_token', token);
    localStorage.setItem('token_expiry', this.tokenExpiry.toString());
  }

  getToken(): string | null {
    if (this.tokenExpiry && Date.now() > this.tokenExpiry) {
      this.clearToken();
      return null;
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    this.tokenExpiry = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('token_expiry');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
```

**Update HTTP client to add auth headers:**

```typescript
// src/lib/api/handlers.ts
export class RequestHandler {
  static addHeaders(authService?: AuthService): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const token = authService?.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }
}
```

### 5. Secure Log Storage

**Never log sensitive data:**

```typescript
// src/lib/logger.ts - PII redaction
private redactSensitiveData(data: unknown): unknown {
  if (typeof data === 'string') {
    return data
      .replace(/\b\d{3}-\d{2}-\d{4}\b/g, 'XXX-XX-XXXX') // SSN
      .replace(/\b\d{16}\b/g, 'XXXX-XXXX-XXXX-XXXX') // Credit card
      .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '[EMAIL]') // Email
      .replace(/Bearer\s+\S+/i, 'Bearer [TOKEN]'); // Auth tokens
  }

  if (typeof data === 'object' && data !== null) {
    const obj = { ...data } as Record<string, any>;
    const sensitiveKeys = ['password', 'token', 'secret', 'apiKey', 'ssn', 'creditCard'];
    
    for (const key of sensitiveKeys) {
      if (key in obj) {
        obj[key] = '[REDACTED]';
      }
    }
    return obj;
  }

  return data;
}
```

### 6. HTTPS Enforcement

**Add in `src/hooks.server.ts`:**

```typescript
// Force HTTPS in production
export const handle = (async ({ event, resolve }) => {
  if (event.url.protocol === 'http:' && process.env.NODE_ENV === 'production') {
    const httpsUrl = event.url.href.replace('http://', 'https://');
    return new Response(null, {
      status: 301,
      headers: { Location: httpsUrl },
    });
  }

  return resolve(event);
}) satisfies Handle;
```

### 7. Rate Limiting (Frontend)

```typescript
// src/lib/utils/rate-limiter.ts
export class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private readonly windowMs: number = 60 * 1000; // 1 minute
  private readonly maxRequests: number = 10;

  canMakeRequest(key: string): boolean {
    const now = Date.now();
    const timestamps = this.requests.get(key) || [];

    // Remove old timestamps outside window
    const recentRequests = timestamps.filter(ts => now - ts < this.windowMs);

    if (recentRequests.length >= this.maxRequests) {
      return false;
    }

    recentRequests.push(now);
    this.requests.set(key, recentRequests);

    return true;
  }

  getRemainingRequests(key: string): number {
    const timestamps = this.requests.get(key) || [];
    return Math.max(0, this.maxRequests - timestamps.length);
  }
}
```

---

## Part 3: Monitoring & Observability

### Error Tracking (Sentry Integration)

```bash
npm install @sentry/svelte
```

**Initialize in `src/routes/+layout.svelte`:**

```typescript
import * as Sentry from '@sentry/svelte';

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  tracesSampleRate: 0.1,
  beforeSend(event) {
    // Redact sensitive data
    if (event.request?.url) {
      event.request.url = event.request.url.split('?')[0];
    }
    return event;
  },
});
```

### Performance Monitoring

```typescript
// src/lib/utils/performance.ts
export class PerformanceMonitor {
  static trackOperation(label: string, fn: () => Promise<any>) {
    return async () => {
      const start = performance.now();
      try {
        const result = await fn();
        const duration = performance.now() - start;
        logger.info(`${label} completed`, { durationMs: duration });
        return result;
      } catch (error) {
        const duration = performance.now() - start;
        logger.error(`${label} failed`, { durationMs: duration }, error as Error);
        throw error;
      }
    };
  }
}
```

### Analytics

```typescript
// src/lib/services/analytics.service.ts
export class AnalyticsService {
  static trackEvent(event: string, properties?: Record<string, any>) {
    logger.info(`Analytics: ${event}`, properties);

    // Send to external service
    if (import.meta.env.PROD) {
      // fetch('/api/analytics', {
      //   method: 'POST',
      //   body: JSON.stringify({ event, properties, timestamp: new Date() })
      // });
    }
  }

  static trackSearch(query: string, resultCount: number, duration: number) {
    this.trackEvent('search', { query, resultCount, durationMs: duration });
  }

  static trackError(error: Error, context?: Record<string, any>) {
    this.trackEvent('error', { errorMessage: error.message, ...context });
  }
}
```

---

## Part 4: CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/frontend.yml
name: Frontend CI/CD

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend.yml'
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Type check
        run: cd frontend && npm run check

      - name: Lint
        run: cd frontend && npm run lint

      - name: Unit tests
        run: cd frontend && npm run test

      - name: E2E tests
        run: cd frontend && npm run test:e2e

      - name: Build
        run: cd frontend && npm run build

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/coverage-final.json

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to production
        run: |
          # Your deployment script here
          echo "Deploying frontend to production..."
```

---

## Implementation Priority

1. **Phase 1 (Week 1):** Unit tests + error handling
2. **Phase 2 (Week 2):** E2E tests + security headers
3. **Phase 3 (Week 3):** Monitoring + analytics
4. **Phase 4 (Week 4):** Documentation + CI/CD

---

## Success Metrics

- ✅ 80%+ code coverage
- ✅ 0 security vulnerabilities
- ✅ <3s page load time
- ✅ 99.9% uptime
- ✅ < 1% error rate
- ✅ All tests passing in CI/CD

