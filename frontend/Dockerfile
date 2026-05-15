# ---------- Build stage ----------
FROM node:20-alpine AS builder

WORKDIR /app

# Pin pnpm to the version that generated the lockfile so that
# --frozen-lockfile cannot drift between local dev and CI.
RUN npm install -g pnpm@10.30.3

# Copy manifest + lockfile first to maximise Docker layer caching:
# dependency install only re-runs when one of these files changes.
COPY package.json pnpm-lock.yaml ./

# Deterministic install. Fails the build if pnpm-lock.yaml is out of
# sync with package.json -- which is the whole point of this fix.
RUN pnpm install --frozen-lockfile

# Now bring in the rest of the source.
COPY . .

# Build-time configuration injected by docker build --build-arg
ARG VITE_API_URL
ARG VITE_API_BASE_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build the application
RUN pnpm run build

# ---------- Production stage ----------
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
