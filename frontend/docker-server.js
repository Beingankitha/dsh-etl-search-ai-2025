import { createServer } from 'http';
import { readFileSync } from 'fs';
import { extname } from 'path';
import { Server } from './.svelte-kit/output/server/index.js';
import { manifest } from './.svelte-kit/output/server/manifest.js';

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';

const server = new Server(manifest);

// Initialize the server
await server.init({
  env: process.env,
  read: null
});

// MIME type mappings
const mimeTypes = {
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.html': 'text/html',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject'
};

// Create HTTP server
const httpServer = createServer(async (req, res) => {
  try {
    // Try to serve static files first (for CSS, JS, images, fonts)
    if (req.url.startsWith('/static/') || req.url.match(/\.(css|js|jpg|jpeg|png|gif|svg|woff|woff2|ttf|eot)$/)) {
      try {
        const filePath = req.url.startsWith('/static/') 
          ? `.${req.url}` 
          : `./.svelte-kit/output/client${req.url}`;
        
        const content = readFileSync(filePath);
        const ext = extname(filePath).toLowerCase();
        const mimeType = mimeTypes[ext] || 'application/octet-stream';
        
        res.writeHead(200, { 'Content-Type': mimeType });
        res.end(content);
        return;
      } catch (e) {
        // Fall through to SvelteKit handler if static file not found
      }
    }
    
    // Route to SvelteKit for dynamic pages
    const response = await server.respond(
      new Request(`http://${req.headers.host || 'localhost'}${req.url}`, {
        method: req.method,
        headers: req.headers
      }),
      {
        getClientAddress() {
          return req.socket.remoteAddress;
        }
      }
    );

    // Write status and headers
    res.writeHead(response.status, Object.fromEntries(response.headers));
    
    // Write body
    if (response.body) {
      const buffer = await response.arrayBuffer();
      res.end(Buffer.from(buffer));
    } else {
      res.end();
    }
  } catch (err) {
    console.error('Error handling request:', err);
    if (!res.headersSent) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
    }
    res.end('Internal Server Error');
  }
});

httpServer.listen(PORT, HOST, () => {
  console.log(`Server listening on http://${HOST}:${PORT}`);
});

