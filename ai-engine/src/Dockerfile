# Build stage
FROM ubuntu:22.04 AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    gcc \
    g++ \
    curl \
    wget \
    gnupg \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment to ensure consistent package locations
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install ROCm using modern apt keyring method - minimal installation
RUN wget -q -O /tmp/rocm.gpg.key https://repo.radeon.com/rocm/rocm.gpg.key && \
    gpg --dearmor < /tmp/rocm.gpg.key > /usr/share/keyrings/rocm-archive-keyring.gpg && \
    echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/rocm-archive-keyring.gpg] https://repo.radeon.com/rocm/apt/6.0/ jammy main' > /etc/apt/sources.list.d/rocm.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends --allow-downgrades rocm-libs hip-runtime-amd && \
    rm -rf /var/lib/apt/lists/* /tmp/rocm.gpg.key

# Copy project files needed for installation
COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
# Install all dependencies, including AMD GPU extras, from pyproject.toml
RUN pip install --no-cache-dir .[gpu-amd]

ARG INSTALL_DEV_DEPS=false
RUN if [ "$INSTALL_DEV_DEPS" = "true" ] ; then \
    pip install --no-cache-dir .[dev] ; \
fi

FROM ubuntu:22.04

WORKDIR /app

# Copy ROCm repo config from builder to install runtime libs
COPY --from=builder /usr/share/keyrings/rocm-archive-keyring.gpg /usr/share/keyrings/rocm-archive-keyring.gpg
COPY --from=builder /etc/apt/sources.list.d/rocm.list /etc/apt/sources.list.d/rocm.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    curl \
    ffmpeg \
    rocm-libs hip-runtime-amd \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN adduser --disabled-password --gecos '' appuser
# Create directories for models and cache
# These directories are part of the application structure, so they should be created after COPY . .
RUN mkdir -p /app/models /app/cache

# Copy source code after user creation with correct permissions
COPY --chown=appuser:appuser . /app/
USER appuser

# Verify PyTorch sees AMD GPU (ROCm)
RUN python -c "import torch; print(f'ROCm available: {torch.cuda.is_available()}')"

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

EXPOSE 8001

# Use modern uvicorn settings
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--access-log"]