/**
 * Frontend Logging Utility
 * 
 * Provides structured logging for the frontend application with:
 * - Different severity levels (DEBUG, INFO, WARN, ERROR)
 * - Request/response tracking
 * - Persistent storage (IndexedDB for large volumes, console for development)
 * - Batch export functionality
 * - Request tracking with automatic fetch interception
 * 
 * Usage:
 *   import { logger } from '$lib/logger';
 *   
 *   logger.info('Search started', { query: 'earthworm' });
 *   logger.debug('Results received', { count: 10 });
 *   logger.error('API failed', { status: 500, message: 'Server error' });
 *   
 * Export logs:
 *   const logs = logger.exportLogs();
 *   console.log(logs);
 */

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  error?: Error;
}

interface RequestLog {
  timestamp: string;
  method: string;
  url: string;
  status?: number;
  duration: number;
  error?: string;
}

class Logger {
  private static instance: Logger;
  private logs: LogEntry[] = [];
  private requestLogs: RequestLog[] = [];
  private maxLogs = 1000;
  private isDevelopment = !import.meta.env.PROD;
  private dbName = 'ceh_frontend_logs';
  private storeName = 'logs';
  private db: IDBDatabase | null = null;
  private isIndexedDBReady = false;

  /**
   * Get singleton logger instance
   */
  static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  constructor() {
    if (typeof window !== 'undefined') {
      this.initializeIndexedDB();
    }
  }

  /**
   * Initialize IndexedDB for persistent logging
   */
  private initializeIndexedDB() {
    if (!('indexedDB' in window)) {
      console.warn('IndexedDB not supported - logs will only be kept in memory');
      return;
    }

    try {
      const request = indexedDB.open(this.dbName, 1);

      request.onerror = () => {
        console.warn('Failed to open IndexedDB for logging');
      };

      request.onsuccess = () => {
        this.db = request.result;
        this.isIndexedDBReady = true;
        
        // Periodically clean old logs from IndexedDB
        this.cleanOldLogs();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          const store = db.createObjectStore(this.storeName, { keyPath: 'id', autoIncrement: true });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('level', 'level', { unique: false });
        }
      };
    } catch (error) {
      console.warn('Error initializing IndexedDB:', error);
    }
  }

  /**
   * Clean logs older than 7 days from IndexedDB
   */
  private cleanOldLogs() {
    if (!this.db || !this.isIndexedDBReady) return;

    try {
      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const index = store.index('timestamp');

      const range = IDBKeyRange.upperBound(sevenDaysAgo);
      index.openCursor(range).onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          store.delete(cursor.primaryKey);
          cursor.continue();
        }
      };
    } catch (error) {
      console.warn('Error cleaning old logs:', error);
    }
  }

  /**
   * Persist log to IndexedDB
   */
  private persistLog(entry: LogEntry | RequestLog) {
    if (!this.db || !this.isIndexedDBReady) return;

    try {
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      store.add(entry);
    } catch (error) {
      // Silently fail - don't spam console
      if (this.isDevelopment) {
        console.debug('Failed to persist log to IndexedDB:', error);
      }
    }
  }

  /**
   * Log at DEBUG level (most verbose)
   */
  debug(message: string, context?: Record<string, any>) {
    this.log('DEBUG', message, context);
  }

  /**
   * Log at INFO level (normal operations)
   */
  info(message: string, context?: Record<string, any>) {
    this.log('INFO', message, context);
  }

  /**
   * Log at WARN level (warnings)
   */
  warn(message: string, context?: Record<string, any>) {
    this.log('WARN', message, context);
  }

  /**
   * Log at ERROR level (errors)
   */
  error(message: string, context?: Record<string, any>, error?: Error) {
    this.log('ERROR', message, context, error);
  }

  /**
   * Log API request
   */
  logRequest(method: string, url: string, status?: number, duration: number = 0, error?: string) {
    const entry: RequestLog = {
      timestamp: new Date().toISOString(),
      method,
      url: this.sanitizeUrl(url),
      status,
      duration,
      error
    };

    this.requestLogs.push(entry);
    if (this.requestLogs.length > this.maxLogs) {
      this.requestLogs.shift();
    }

    // Persist to IndexedDB
    this.persistLog(entry);

    // Log to console in development
    if (this.isDevelopment) {
      const icon = status && status >= 200 && status < 300 ? '✓' : '✗';
      const timeStr = `${duration}ms`;
      console.log(`${icon} ${method} ${url} (${status}) [${timeStr}]`);
    }
  }

  /**
   * Get all logs (useful for debugging)
   */
  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  /**
   * Get request logs (useful for performance monitoring)
   */
  getRequestLogs(): RequestLog[] {
    return [...this.requestLogs];
  }

  /**
   * Get logs from IndexedDB for specific level
   */
  async getLogsFromDB(level?: LogLevel, limit: number = 500): Promise<any[]> {
    return new Promise((resolve) => {
      if (!this.db || !this.isIndexedDBReady) {
        resolve([]);
        return;
      }

      try {
        const transaction = this.db.transaction([this.storeName], 'readonly');
        const store = transaction.objectStore(this.storeName);
        const logs: any[] = [];

        let cursor;
        if (level) {
          const index = store.index('level');
          cursor = index.openCursor(IDBKeyRange.only(level));
        } else {
          cursor = store.openCursor();
        }

        (cursor as IDBRequest).onsuccess = (event) => {
          const result = (event.target as IDBRequest).result;
          if (result && logs.length < limit) {
            logs.push(result.value);
            result.continue();
          }
        };

        transaction.oncomplete = () => {
          resolve(logs.reverse()); // Most recent first
        };
      } catch (error) {
        console.error('Error retrieving logs from DB:', error);
        resolve([]);
      }
    });
  }

  /**
   * Clear logs (call periodically to prevent memory issues)
   */
  clearLogs() {
    this.logs = [];
    this.requestLogs = [];
  }

  /**
   * Clear all IndexedDB logs
   */
  async clearDBLogs(): Promise<void> {
    return new Promise((resolve) => {
      if (!this.db || !this.isIndexedDBReady) {
        resolve();
        return;
      }

      try {
        const transaction = this.db.transaction([this.storeName], 'readwrite');
        const store = transaction.objectStore(this.storeName);
        store.clear();

        transaction.oncomplete = () => {
          resolve();
        };
      } catch (error) {
        console.error('Error clearing DB logs:', error);
        resolve();
      }
    });
  }

  /**
   * Export logs as JSON (useful for debugging/reporting)
   * Includes both in-memory and persisted logs
   */
  async exportLogs() {
    const dbLogs = await this.getLogsFromDB();
    return {
      logs: this.logs,
      requestLogs: this.requestLogs,
      persistedLogs: dbLogs,
      exportedAt: new Date().toISOString(),
      environment: {
        isDevelopment: this.isDevelopment,
        url: typeof window !== 'undefined' ? window.location.href : 'unknown'
      }
    };
  }

  /**
   * Initialize fetch interceptor for automatic request tracking
   * Call this once during app initialization
   */
  initFetchInterceptor() {
    if (typeof window === 'undefined') return;
    
    const originalFetch = window.fetch;
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const startTime = performance.now();
      const [resource, config] = args;
      const url = typeof resource === 'string' ? resource : (resource instanceof Request ? resource.url : String(resource));
      const method = (config?.method as string) || 'GET';

      try {
        const response = await originalFetch(...args);
        const duration = Math.round(performance.now() - startTime);
        
        this.logRequest(method, url, response.status, duration);

        return response;
      } catch (error) {
        const duration = Math.round(performance.now() - startTime);
        this.logRequest(method, url, undefined, duration, error instanceof Error ? error.message : 'Unknown error');
        throw error;
      }
    };
  }

  /**
   * Internal logging method
   */
  private log(
    level: LogLevel,
    message: string,
    context?: Record<string, any>,
    error?: Error
  ) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      context,
      error
    };

    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    // Persist to IndexedDB
    this.persistLog(entry);

    // Log to browser console with styling
    if (this.isDevelopment) {
      const styles = {
        DEBUG: 'color: #999; font-style: italic',
        INFO: 'color: #0066cc; font-weight: bold',
        WARN: 'color: #ff9900; font-weight: bold',
        ERROR: 'color: #cc0000; font-weight: bold'
      };

      const logFn = {
        DEBUG: console.debug,
        INFO: console.info,
        WARN: console.warn,
        ERROR: console.error
      }[level];

      logFn(
        `%c[${entry.timestamp}] ${level}: ${message}`,
        styles[level],
        context || ''
      );

      if (error) {
        console.error(error);
      }
    }
  }

  /**
   * Remove sensitive data from URLs
   */
  private sanitizeUrl(url: string): string {
    // Remove query parameters that might contain sensitive data
    const sanitized = url.split('?')[0];
    return sanitized;
  }
}

/**
 * Global logger instance
 * Export as singleton to ensure consistent logging across app
 */
export const logger = Logger.getInstance();

/**
 * Initialize frontend logging
 * Call this in app initialization (+layout.svelte or main.ts)
 * 
 * Example:
 *   import { initializeLogger } from '$lib/logger';
 *   initializeLogger();
 */
export function initializeLogger() {
  logger.initFetchInterceptor();
  logger.info('Frontend logger initialized', { 
    environment: import.meta.env.MODE,
    isDevelopment: !import.meta.env.PROD 
  });
}

/**
 * Get current logger for direct access
 */
export function getLogger(): Logger {
  return Logger.getInstance();
}
