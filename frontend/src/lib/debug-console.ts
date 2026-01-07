/**
 * Debug Console for Development
 * 
 * Provides utilities for viewing and managing logs in development mode.
 * Displays application logs, request/response metrics, and provides
 * export functionality for debugging production issues.
 * 
 * Usage (auto-enabled in development):
 *   import { enableDebugConsole } from '$lib/debug-console';
 *   enableDebugConsole();
 * 
 * Console shortcuts (development only):
 *   window.__DEBUG__.getLogs()        // Get all logs
 *   window.__DEBUG__.getRequests()    // Get request logs
 *   window.__DEBUG__.exportLogs()     // Export all logs as JSON
 *   window.__DEBUG__.clearLogs()      // Clear all logs
 */

import { logger, type LogLevel } from './logger';

interface DebugOptions {
  showRequests?: boolean;
  showLogs?: boolean;
  maxDisplayLines?: number;
}

declare global {
  interface Window {
    __DEBUG__: {
      getLogs: () => any[];
      getRequests: () => any[];
      exportLogs: () => Promise<any>;
      clearLogs: () => void;
      clearDBLogs: () => Promise<void>;
      displayLogs: (options?: DebugOptions) => void;
    };
  }
}

/**
 * Color codes for different log levels in console
 */
const LEVEL_COLORS: Record<LogLevel, string> = {
  DEBUG: '#7B68EE',    // Medium purple
  INFO: '#4A90E2',     // Blue
  WARN: '#F5A623',     // Orange
  ERROR: '#D0021B'     // Red
};

const LEVEL_STYLES: Record<LogLevel, string> = {
  DEBUG: 'color: #7B68EE; font-weight: bold',
  INFO: 'color: #4A90E2; font-weight: bold',
  WARN: 'color: #F5A623; font-weight: bold',
  ERROR: 'color: #D0021B; font-weight: bold'
};

/**
 * Display all logs to console (for development debugging)
 */
export function displayLogs(options: DebugOptions = {}) {
  const {
    showRequests = true,
    showLogs = true,
    maxDisplayLines = 100
  } = options;

  const logs = logger.getLogs();
  const requestLogs = logger.getRequestLogs();

  if (showLogs && logs.length > 0) {
    console.group('%c📋 Application Logs', 'font-size: 14px; font-weight: bold; color: #333');
    
    const recentLogs = logs.slice(-maxDisplayLines);
    recentLogs.forEach(log => {
      const style = LEVEL_STYLES[log.level];
      const prefix = `[${log.level}]`;
      const time = new Date(log.timestamp).toLocaleTimeString();
      
      console.log(
        `%c${prefix} %c${time} ${log.message}`,
        style,
        'color: #666; font-size: 0.9em',
        log.context || ''
      );

      if (log.error) {
        console.error(log.error);
      }
    });
    
    console.groupEnd();
  }

  if (showRequests && requestLogs.length > 0) {
    console.group('%c🌐 HTTP Requests', 'font-size: 14px; font-weight: bold; color: #333');
    
    const recentRequests = requestLogs.slice(-maxDisplayLines);
    recentRequests.forEach(req => {
      const statusColor = req.status && req.status >= 200 && req.status < 300 ? '#27AE60' : '#D0021B';
      const statusText = req.status ? `${req.status}` : 'ERROR';
      const icon = req.status && req.status >= 200 && req.status < 300 ? '✓' : '✗';
      
      console.log(
        `%c${icon} ${req.method} %c${statusText} %c${req.url} %c(${req.duration}ms)`,
        'font-weight: bold',
        `color: ${statusColor}; font-weight: bold`,
        'color: #666',
        'color: #999; font-style: italic'
      );

      if (req.error) {
        console.warn(`  Error: ${req.error}`);
      }
    });
    
    console.groupEnd();
  }

  // Summary statistics
  console.group('%c📊 Statistics', 'font-size: 14px; font-weight: bold; color: #333');
  console.table({
    'Total Logs': logs.length,
    'Total Requests': requestLogs.length,
    'Average Request Duration (ms)': requestLogs.length > 0 
      ? Math.round(requestLogs.reduce((sum, r) => sum + r.duration, 0) / requestLogs.length)
      : 0,
    'Failed Requests': requestLogs.filter(r => r.error).length
  });
  console.groupEnd();
}

/**
 * Enable continuous console logging
 * Periodically refreshes the display as new logs come in
 */
export function enableDebugConsole(options: DebugOptions = {}) {
  if (typeof window === 'undefined') return;

  const isDevelopment = !import.meta.env.PROD;
  if (!isDevelopment) {
    console.log('ℹ️ Debug console only enabled in development mode');
    return;
  }

  console.clear();
  console.log(
    '%c🚀 CEH Dataset Discovery - Debug Console',
    'font-size: 16px; font-weight: bold; color: #2E86C1; text-shadow: 2px 2px 4px rgba(0,0,0,0.1)'
  );
  console.log(
    '%cLogs will be displayed below. Use window.__DEBUG__ in console for direct access.',
    'color: #666; font-style: italic'
  );

  // Make logger available globally for debugging
  window.__DEBUG__ = {
    getLogs: () => logger.getLogs(),
    getRequests: () => logger.getRequestLogs(),
    exportLogs: async () => {
      const data = await logger.exportLogs();
      console.log('📊 Logs exported:', data);
      return data;
    },
    clearLogs: () => {
      logger.clearLogs();
      console.log('✓ In-memory logs cleared');
    },
    clearDBLogs: async () => {
      await logger.clearDBLogs();
      console.log('✓ Database logs cleared');
    },
    displayLogs: (opts?: DebugOptions) => displayLogs(opts)
  };

  console.log(
    '%c💡 Debug Commands Available:\n  window.__DEBUG__.getLogs()      - Get all logs\n  window.__DEBUG__.getRequests()   - Get request logs\n  window.__DEBUG__.exportLogs()    - Export all logs\n  window.__DEBUG__.displayLogs()   - Display formatted logs\n  window.__DEBUG__.clearLogs()     - Clear in-memory logs\n  window.__DEBUG__.clearDBLogs()   - Clear database logs',
    'color: #27AE60; font-weight: bold; font-family: monospace'
  );

  // Initial display
  displayLogs(options);
}

/**
 * Export logs as JSON file (for debugging and support)
 */
export async function downloadLogs() {
  const data = await logger.exportLogs();
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  
  link.href = url;
  link.download = `ceh-logs-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  link.click();
  
  URL.revokeObjectURL(url);
  console.log('📥 Logs downloaded successfully');
}

/**
 * Create a formatted console table of requests
 */
export function showRequestStats() {
  const requests = logger.getRequestLogs();
  
  const stats = requests.reduce((acc, req) => {
    const method = req.method;
    if (!acc[method]) {
      acc[method] = {
        count: 0,
        totalTime: 0,
        avgTime: 0,
        minTime: Infinity,
        maxTime: 0,
        errors: 0
      };
    }
    
    acc[method].count++;
    acc[method].totalTime += req.duration;
    acc[method].avgTime = acc[method].totalTime / acc[method].count;
    acc[method].minTime = Math.min(acc[method].minTime, req.duration);
    acc[method].maxTime = Math.max(acc[method].maxTime, req.duration);
    if (req.error) acc[method].errors++;
    
    return acc;
  }, {} as Record<string, any>);

  console.table(stats);
}
