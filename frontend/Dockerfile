# Build stage
FROM node:22 AS builder

WORKDIR /app/frontend

# Copy package files
COPY package*.json ./

# Clean install - rebuild node_modules for Linux environment
RUN rm -rf node_modules package-lock.json
RUN npm install

# Copy source code
COPY . .

# Build the SvelteKit app
RUN npm run build

# Runtime stage
FROM node:22-alpine

WORKDIR /app/frontend

# Copy built app from builder
COPY --from=builder /app/frontend/.svelte-kit ./.svelte-kit
COPY --from=builder /app/frontend/node_modules ./node_modules
COPY --from=builder /app/frontend/static ./static
COPY package.json ./
COPY docker-server.js ./

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# Run the server
CMD ["node", "docker-server.js"]
