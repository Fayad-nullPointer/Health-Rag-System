# Dockerfile for Serenity AI
# Multi-stage build for production optimization

# ---- Stage 1: Dependencies ----
FROM oven/bun:1 AS dependencies

WORKDIR /app

# Copy package files
COPY package.json bun.lock ./

# Install all dependencies (including devDependencies needed for build)
RUN bun install --frozen-lockfile

# ---- Stage 2: Builder ----
FROM oven/bun:1 AS builder

WORKDIR /app

# Copy dependencies from the previous stage
COPY --from=dependencies /app/node_modules ./node_modules

# Copy the rest of the application
COPY . .

# Build the application for production
RUN bun run build

# ---- Stage 3: Production Runner ----
FROM oven/bun:1-slim AS runner

WORKDIR /app

# Create a non-root user for security
RUN groupadd --gid 1001 nodejs && \
    useradd --uid 1001 --gid nodejs --create-home appuser

# Copy built application
COPY --from=builder --chown=appuser:nodejs /app/dist ./dist
COPY --from=builder --chown=appuser:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:nodejs /app/package.json ./package.json
COPY --from=builder --chown=appuser:nodejs /app/src ./src
COPY --from=builder --chown=appuser:nodejs /app/vite.config.ts ./vite.config.ts
COPY --from=builder --chown=appuser:nodejs /app/tsconfig.json ./tsconfig.json
COPY --from=builder --chown=appuser:nodejs /app/bunfig.toml ./bunfig.toml
COPY --from=builder --chown=appuser:nodejs /app/components.json ./components.json

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 3000

# Use preview to serve the production build
# For SSR/production serving, TanStack Start can use `bun preview`
CMD ["bun", "run", "preview", "--host", "0.0.0.0", "--port", "3000"]
