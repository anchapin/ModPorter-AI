# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app/
COPY requirements-dev.txt /app/

# Install core dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# Conditionally install development dependencies
ARG INSTALL_DEV_DEPS=false
RUN if [ "$INSTALL_DEV_DEPS" = "true" ] ; then \
    pip install --no-cache-dir -r requirements-dev.txt ; \
fi

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN adduser --disabled-password --gecos '' appuser
# Create directories for models and cache
# These directories are part of the application structure, so they should be created after COPY . .
RUN mkdir -p /app/models /app/cache

# Copy source code after user creation with correct permissions
COPY --chown=appuser:appuser . /app/
USER appuser

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

EXPOSE 8001

# Use modern uvicorn settings
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--access-log"]