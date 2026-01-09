# Frontend Logging Implementation Guide

## 🎯 What's Changed

The frontend now has **production-ready structured logging** that automatically tracks all HTTP requests, application events, and errors.

### Issues Fixed
1. ✅ **Frontend logs now visible** - Logger displays to console during development
2. ✅ **Automatic request tracking** - All fetch requests are intercepted and logged
3. ✅ **Singleton pattern** - Logger properly initialized on app startup
4. ✅ **Development-only logging** - Console output disabled in production builds

---

## 🚀 How It Works

### Automatic Initialization

The logger is **automatically initialized** in `+layout.svelte`:

```svelte
<script lang="ts">
  import { initializeLogger } from '$lib/container';
  import { enableDebugConsole } from '$lib/debug-console';

  // Initializes logger and sets up fetch interceptor
  $effect.pre(() => {
    initializeLogger();
    enableDebugConsole();
  });
</script>
```

### What Gets Logged

#### 1. **Application Events** (Manual)
```typescript
import { logger } from '$lib';

// Log different levels
logger.debug('Details', { userId: '123' });
logger.info('User searched', { query: 'water' });
logger.warn('Deprecated API', { endpoint: '/old' });
logger.error('Failed to load', { status: 500 });
```

#### 2. **HTTP Requests** (Automatic)
Every fetch request is automatically intercepted and logged:

```
✓ GET http://localhost:8000/api/search (200) [156ms]
✓ POST http://localhost:8000/api/chat (200) [234ms]
✗ GET http://localhost:8000/api/datasets (500) [45ms]
```

---

## 🔍 Accessing Logs in Development

### Method 1: Browser Console (Automatic)
Open DevTools (F12) → Console. You'll see:

```
🚀 CEH Dataset Discovery - Debug Console
Logs will be displayed below...
💡 Pro Tip: Type __LOGGER__.display() to see all logs...

📋 Application Logs
[INFO] 12:34:56 Frontend logger initialized...
[INFO] 12:34:57 Search started...

🌐 HTTP Requests
✓ GET 200 http://localhost:8000/api/search (156ms)
✓ POST 200 http://localhost:8000/api/chat (234ms)

📊 Statistics
│ Total Logs      │ 45    │
│ Total Requests  │ 12    │
```

### Method 2: Direct Console Commands
```javascript
// View all logs
__LOGGER__.logs()

// View all requests
__LOGGER__.requests()

// Refresh display
__LOGGER__.display()

// Download logs as JSON
__LOGGER__.export()

// Clear logs
__LOGGER__.clear()

// View request statistics
__LOGGER__.showRequestStats()
```

### Method 3: Download Logs
```javascript
import { downloadLogs } from '$lib/debug-console';

// Downloads all logs as JSON file
downloadLogs();
```

---

## 📊 Backend Logging (Already Configured)

The backend has comprehensive structured logging with:

- **Trace IDs**: Correlation IDs for request tracking
- **Structured format**: Timestamp, level, module, message
- **Request logging**: All HTTP requests logged with duration
- **Error tracking**: Full exception details with stack traces
- **Log rotation**: 10MB max per file, 5 backup files

Current logs shown in your backend log output:
```
2026-01-07T12:51:54.554740Z | c6911abcee3a58ff | INFO | src.services.embeddings.vector_store:170 | ✓ Datasets collection ready
2026-01-07T12:52:28.902725Z | ca42e8781e5e7c1b | INFO | src.repositories.unit_of_work:102 | Unit of Work started
```

### Fix Applied
✅ **OpenTelemetry UNAVAILABLE error** - Set `JAEGER_ENABLED=false` in `.env` to disable Jaeger tracing when not deployed

---

## 🏗️ For Production

### 1. Disable Console Logging
The logger automatically detects production build (`import.meta.env.PROD`):
- ✅ Console logging **automatically disabled** in production
- ✅ Logs still stored in memory for export if needed
- ✅ No console spam, clean production experience

### 2. Export Logs for Monitoring
```typescript
// Periodically export logs to your monitoring service
setInterval(() => {
  const logs = logger.exportLogs();
  // Send to monitoring service (Sentry, DataDog, etc.)
  fetch('/api/logs', { method: 'POST', body: JSON.stringify(logs) });
}, 30000); // Every 30 seconds
```

### 3. Send to Centralized Logging Service
```typescript
import { logger } from '$lib';

// In +layout.svelte or a hook
async function sendLogsToService() {
  const logs = logger.exportLogs();
  
  await fetch('https://your-logging-service.com/api/logs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      appVersion: '1.0.0',
      environment: 'production',
      logs: logs.logs,
      requestLogs: logs.requestLogs,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    })
  });
}

// Call periodically
setInterval(sendLogsToService, 60000);
```

### 4. Monitor Request Performance
```typescript
import { showRequestStats } from '$lib/debug-console';

// Get aggregated request stats
const stats = logger.getRequestLogs().reduce((acc, req) => {
  // Group by method/endpoint
  const key = `${req.method} ${req.url}`;
  if (!acc[key]) acc[key] = { count: 0, total: 0 };
  acc[key].count++;
  acc[key].total += req.duration;
  return acc;
}, {});
```

---

## 📋 Logger API Reference

### Methods

```typescript
// Logging
logger.debug(message, context?)
logger.info(message, context?)
logger.warn(message, context?)
logger.error(message, context?, error?)

// Manual request tracking
logger.trackRequest({ method, url, status, duration, error? })

// Data access
logger.getLogs()           // All app logs
logger.getRequestLogs()    // All HTTP requests
logger.exportLogs()        // Export as JSON
logger.clearLogs()         // Clear memory

// Initialization
initializeLogger()         // Setup logger and fetch interceptor
enableDebugConsole()       // Enable console display
```

### Log Entry Format

```typescript
interface LogEntry {
  timestamp: string;        // ISO 8601 timestamp
  level: LogLevel;          // 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'
  message: string;          // Log message
  context?: Record<string, any>; // Additional data
  error?: Error;            // Error object if applicable
}

interface RequestLog {
  timestamp: string;
  method: string;           // 'GET', 'POST', etc.
  url: string;              // Full URL
  status?: number;          // HTTP status code
  duration: number;         // Duration in ms
  error?: string;           // Error message if failed
}
```

---

## 🎯 Development Workflow

1. **Open DevTools** (F12 or Cmd+Option+I)
2. **Go to Console tab**
3. **Watch logs appear automatically**:
   - Application events
   - HTTP requests with timing
   - Errors with stack traces
4. **Use `__LOGGER__` commands** for deep inspection
5. **Check Network tab** for detailed request/response bodies

---

## 🐛 Debugging Tips

### See All Recent Logs
```javascript
__LOGGER__.display()
```

### Find Slow Requests
```javascript
__LOGGER__.requests()
  .filter(r => r.duration > 1000)
  .sort((a, b) => b.duration - a.duration)
```

### Check for Errors
```javascript
__LOGGER__.requests()
  .filter(r => r.error || r.status >= 400)
```

### Monitor Performance
```javascript
__LOGGER__.showRequestStats()
```

### Export for Analysis
```javascript
const logs = __LOGGER__.export();
console.save(logs);  // If console.save is available
```

---

## ✅ Verification Checklist

- ✅ Frontend logger initializes on app startup
- ✅ All fetch requests are automatically logged
- ✅ Console shows formatted logs in development
- ✅ Logger unavailable in production builds
- ✅ Backend logs show healthy operation
- ✅ OpenTelemetry errors disabled (JAEGER_ENABLED=false)
- ✅ Logs stored in memory (configurable: 1000 max entries)
- ✅ Request tracking includes timing and status

---

## 🚀 Next Steps

1. **Monitor requests** - Check console as you use the app
2. **Add custom logging** - Call `logger.info()` in your components
3. **Set up production export** - Send logs to monitoring service
4. **Alert on errors** - Create handlers for failed requests
5. **Performance tracking** - Monitor request durations over time

---

## 📞 Support

**Still no logs showing?**
1. Open DevTools (F12)
2. Type: `__LOGGER__.logs()` - should return array
3. Type: `__LOGGER__.requests()` - should show HTTP requests
4. Check Network tab in DevTools for actual requests

If empty, frontend logger may not be initialized. Verify `+layout.svelte` has `initializeLogger()` call.
