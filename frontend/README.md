# DSH ETL Search AI - Frontend README

**SvelteKit-based Web Interface for CEH Dataset Discovery**

Interactive UI for searching datasets, viewing metadata, and AI-powered chat interface.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Development](#development)
5. [Building & Deployment](#building--deployment)
6. [Project Structure](#project-structure)
7. [Environment Configuration](#environment-configuration)
8. [Available Scripts](#available-scripts)
9. [API Integration](#api-integration)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env.local

# 3. Start development server
npm run dev

# 4. Open browser
# http://localhost:5173
```

---

## System Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **Node.js** | 16+ (18+ recommended) | LTS versions preferred |
| **npm** | 8+ or yarn/pnpm | Package manager |
| **OS** | macOS, Linux, Windows | WSL2 for Windows |
| **RAM** | 4 GB minimum | 8 GB recommended |
| **Storage** | 2 GB (node_modules) | Plus build artifacts |

### Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest version

---

## Installation

### Step 1: Verify Node.js

```bash
node --version      # v18.x.x or higher
npm --version       # 8.x.x or higher
```

**Install Node.js if needed:**
- macOS: `brew install node@18`
- Linux: `sudo apt-get install nodejs npm`
- Windows: Download from nodejs.org or `winget install OpenJS.NodeJS`

### Step 2: Install Dependencies

```bash
# Navigate to frontend directory
cd frontend

# Install all dependencies - IT would be good to delete package-lock.json to delete and than run below cmd
npm install # npm run --verbose

# check for errors or warnings
npm run check

# Verify installation
npm list | head -20
```

**Dependency Summary:**
- **SvelteKit**: Full-stack framework
- **Vite**: Build tool & dev server
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Bits UI**: Component library
- **Lucide Icons**: Icon library

### Step 3: Environment Configuration

```bash
# Edit configuration
nano .env.local
```

**Default Configuration:**
```env
VITE_API_URL=http://localhost:8000
```

**For Production:**
```env
VITE_API_URL=https://api.yourdomain.com
```

### Step 4: Verify Setup

```bash
# Type checking
npm run check

# Should complete without errors
```

---

## Development

### Start Development Server

```bash
# Terminal 1: Backend (if running locally)
cd backend
uv run python main.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Swagger API: http://localhost:8000/docs
- ReDoc API: http://localhost:8000/redoc

### Dev Server Features

- ✅ Hot module replacement (HMR)
- ✅ Auto-reload on file changes
- ✅ Type checking
- ✅ Source maps for debugging
- ✅ API proxy to backend

### Development Workflow

```bash
# Watch for type errors
npm run check:watch

# In another terminal, run dev server
npm run dev

# Edit files and see changes immediately
# http://localhost:5173
```

### Code Quality

```bash
# Format code with Prettier (if configured)
npm run format

# Lint check (if configured)
npm run lint

# Type checking
npm run check
```

---

## Building & Deployment

### Development Build

```bash
# Create optimized build
npm run build

# Preview build locally
npm run preview

# Access at: http://localhost:4173
```

### Build Output

```
.svelte-kit/output/
├── client/          # Frontend assets
├── server/          # Server-side code
└── static/          # Static files
```

### Production Deployment

**Using Docker:**
```bash
# Build Docker image
docker build -t dsh-frontend:latest .

# Run container
docker run -p 3000:3000 \
  -e VITE_API_URL=https://api.production.com \
  dsh-frontend:latest
```

**Using Node server:**
```bash
# Build
npm run build

# Run with Node
node build/index.js
```

**Environment:**
```env
PORT=3000
ORIGIN=https://yourdomain.com
VITE_API_URL=https://api.yourdomain.com
```

---

## Project Structure

```
frontend/
├── src/
│   ├── routes/                 # SvelteKit pages & routes
│   │   ├── +layout.svelte      # Root layout
│   │   ├── +page.svelte        # Home page
│   │   └── chat/               # Chat page
│   │
│   ├── lib/                    # Reusable components & utilities
│   │   ├── api/                # API client
│   │   │   ├── client.ts       # HTTP client
│   │   │   ├── handlers.ts     # API handlers
│   │   │   └── types.ts        # Type definitions
│   │   │
│   │   ├── components/         # UI components
│   │   │   ├── ui/             # Generic UI components
│   │   │   └── custom/         # Custom business components
│   │   │       ├── SearchBar.svelte
│   │   │       ├── SearchResults.svelte
│   │   │       ├── DatasetCard.svelte
│   │   │       ├── ChatInterface.svelte
│   │   │       └── ChatMessage.svelte
│   │   │
│   │   ├── services/           # Business logic
│   │   │   ├── search.service.ts
│   │   │   ├── chat.service.ts
│   │   │   └── validation.service.ts
│   │   │
│   │   ├── stores/             # Svelte stores
│   │   │   ├── searchStore.ts
│   │   │   ├── chatStore.ts
│   │   │   └── index.ts
│   │   │
│   │   └── utils/              # Utilities
│   │       ├── logger.ts
│   │       ├── validation.ts
│   │       └── utils.ts
│   │
│   ├── app.html                # HTML template
│   ├── app.css                 # Global styles
│   └── app.d.ts                # Type definitions
│
├── static/                     # Static assets
├── .svelte-kit/                # Generated files (build output)
├── vite.config.ts              # Vite configuration
├── svelte.config.js            # SvelteKit configuration
├── tsconfig.json               # TypeScript configuration
├── tailwind.config.ts          # Tailwind CSS config
├── components.json             # Component setup
├── .env.local                  # Environment variables
└── package.json                # Dependencies

```

---

## Environment Configuration

### .env.local Variables

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Optional: Add more as needed
# VITE_APP_NAME=DSH Search
# VITE_DEBUG=false
```

### Environment Access in Code

```typescript
// In any Svelte/TypeScript file
import { env } from '$env/dynamic/public';

const apiUrl = env.VITE_API_URL;  // http://localhost:8000
```

### Development vs Production

**Development (.env.local):**
```env
VITE_API_URL=http://localhost:8000
```

**Production (.env.local):**
```env
VITE_API_URL=https://api.production.com
```

---

## Available Scripts

### Development

| Script | Purpose | Port |
|--------|---------|------|
| `npm run dev` | Start dev server with HMR | 5173 |
| `npm run check` | TypeScript & Svelte checking | - |
| `npm run check:watch` | Watch mode for type checking | - |

### Building

| Script | Purpose | Output |
|--------|---------|--------|
| `npm run build` | Production build | `.svelte-kit/output/` |
| `npm run preview` | Preview production build | 4173 |

### Maintenance

| Script | Purpose |
|--------|---------|
| `npm install` | Install dependencies |
| `npm update` | Update packages |
| `npm audit` | Check vulnerabilities |

### Examples

```bash
# Development workflow
npm run check:watch &
npm run dev

# Build for production
npm run build
npm run preview

# Update dependencies
npm update
npm audit fix

# Full type check before commit
npm run check
```

---


## Troubleshooting

### Node Version Issues

```bash
# Error: Module not found or version mismatch
node --version  # Must be 16+

# Solution: Update Node
brew install node@18    # macOS
nvm install 18          # Using nvm
```

### Dependencies Not Found

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
npm run check
```

### Port 5173 Already in Use

```bash
# Kill process using port
lsof -i :5173           # Find PID
kill -9 <PID>

# Or use different port
npm run dev -- --port 5174
```

### API Connection Failed

```bash
# Check backend is running
curl http://localhost:8000/docs

# Verify .env.local
cat .env.local

# Check network tab in DevTools (F12)
```

### Build Fails

```bash
# Type checking first
npm run check

# Clear cache
rm -rf .svelte-kit
npm run prepare

# Rebuild
npm run build
```

### Hot Reload Not Working

```bash
# Solution 1: Restart dev server
npm run dev

# Solution 2: Check for file watcher limits (Linux)
cat /proc/sys/fs/inotify/max_user_watches
# If too low, increase: sudo sysctl fs.inotify.max_user_watches=524288

# Solution 3: Disable HMR temporarily
npm run dev -- --no-hmr
```

### TypeScript Errors

```bash
# Full type check
npm run check

# Fix issues
npm run prepare    # Regenerate types

# Try building
npm run build
```

### Component Import Issues

```bash
# Ensure path aliases work
# tsconfig.json should have:
{
  "compilerOptions": {
    "paths": {
      "$lib/*": ["./src/lib/*"],
      "$routes/*": ["./src/routes/*"]
    }
  }
}
```

---

## Key Technologies

### Framework
- **SvelteKit**: Full-stack web framework
- **Svelte 5**: Reactive UI components

### Styling
- **Tailwind CSS 4**: Utility-first CSS
- **Tailwind Variants**: Dynamic classes
- **Bits UI**: Accessible components

### Development
- **Vite**: Build tool (3x faster)
- **TypeScript**: Type safety
- **Lucide Icons**: Icon library


## Docker Deployment

### Build Docker Image

```bash
docker build -f Dockerfile -t dsh-frontend:latest .
```

### Run Container

```bash
docker run -d \
  -p 3000:3000 \
  -e VITE_API_URL=https://api.example.com \
  --name frontend \
  dsh-frontend:latest
```

### Docker Compose

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
```

---

## Common Commands Reference

```bash
# Setup
npm install                    # Install dependencies
npm run check                  # Type checking

# Development
npm run dev                    # Start dev server
npm run check:watch          # Watch type errors

# Production
npm run build                 # Build for production
npm run preview               # Preview build
docker build -t frontend .    # Build Docker image

# Maintenance
npm update                    # Update packages
npm audit                     # Check security
npm audit fix                 # Fix vulnerabilities
```

---

## File Descriptions

| File | Purpose |
|------|---------|
| `src/routes/` | Page components (auto-routed) |
| `src/lib/api/` | API client & error handling |
| `src/lib/components/` | Reusable UI components |
| `src/lib/services/` | Business logic & API calls |
| `src/lib/stores/` | Reactive state management |
| `vite.config.ts` | Build & dev server config |
| `svelte.config.js` | SvelteKit framework config |
| `tsconfig.json` | TypeScript configuration |
| `tailwind.config.ts` | Tailwind CSS settings |
| `.env.local` | Environment variables |

---

## Support & Resources

- **SvelteKit Docs**: https://svelte.dev/docs/kit
- **Vite Guide**: https://vitejs.dev
- **Tailwind CSS**: https://tailwindcss.com
- **TypeScript**: https://www.typescriptlang.org

---

**Last Updated:** January 9, 2025  
**Version:** 1.0  

For issues or questions, refer to the main project README or development team.
