# Multi-stage Dockerfile with GPU type selection
# Build args: GPU_TYPE=nvidia|amd|cpu (default: cpu)
ARG GPU_TYPE=cpu

# ========================================
# NVIDIA GPU Stage
# ========================================
FROM nvidia/cuda:12.4-devel-ubuntu22.04 AS builder-nvidia

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
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir .[gpu-nvidia]

# ========================================
# AMD GPU Stage
# ========================================
FROM ubuntu:22.04 AS builder-amd

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

# Create virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install ROCm (minimal)
RUN wget -q -O /tmp/rocm.gpg.key https://repo.radeon.com/rocm/rocm.gpg.key && \
    gpg --dearmor < /tmp/rocm.gpg.key > /usr/share/keyrings/rocm-archive-keyring.gpg && \
    echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/rocm-archive-keyring.gpg] https://repo.radeon.com/rocm/apt/6.0/ jammy main' > /etc/apt/sources.list.d/rocm.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends rocm-libs hip-runtime-amd && \
    rm -rf /var/lib/apt/lists/* /tmp/rocm.gpg.key

# Copy project files
COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir .[gpu-amd]

# ========================================
# CPU-only Stage
# ========================================
FROM python:3.11-slim AS builder-cpu

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir .[cpu-only] --extra-index-url https://download.pytorch.org/whl/cpu

# ========================================
# Final Runtime Stages
# ========================================

# NVIDIA Runtime
FROM nvidia/cuda:12.4-runtime-ubuntu22.04 AS runtime-nvidia
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder-nvidia /opt/venv /opt/venv
ENV NVIDIA_VISIBLE_DEVICES=all
ENV GPU_TYPE=nvidia
ENV GPU_ENABLED=true

# AMD Runtime  
FROM ubuntu:22.04 AS runtime-amd
COPY --from=builder-amd /usr/share/keyrings/rocm-archive-keyring.gpg /usr/share/keyrings/rocm-archive-keyring.gpg
COPY --from=builder-amd /etc/apt/sources.list.d/rocm.list /etc/apt/sources.list.d/rocm.list
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    curl \
    ffmpeg \
    rocm-libs hip-runtime-amd \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder-amd /opt/venv /opt/venv
ENV ROCm_VISIBLE_DEVICES=all
ENV HIP_VISIBLE_DEVICES=0
ENV GPU_TYPE=amd
ENV GPU_ENABLED=true

# CPU Runtime
FROM python:3.11-slim AS runtime-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder-cpu /opt/venv /opt/venv
ENV GPU_TYPE=cpu
ENV GPU_ENABLED=false

# ========================================
# Final Selection Stage
# ========================================
FROM runtime-${GPU_TYPE} AS final

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"

# Create user and directories
RUN adduser --disabled-password --gecos '' appuser
RUN mkdir -p /app/models /app/cache

# Copy source code with correct permissions
COPY --chown=appuser:appuser . /app/
USER appuser

# Verify GPU setup based on type
ARG GPU_TYPE=cpu
RUN if [ "$GPU_TYPE" = "nvidia" ]; then \
        python -c "import torch; print(f'NVIDIA CUDA available: {torch.cuda.is_available()}')"; \
    elif [ "$GPU_TYPE" = "amd" ]; then \
        python -c "import torch; print(f'AMD ROCm available: {torch.cuda.is_available()}')"; \
    else \
        python -c "import torch; print(f'CPU device: {torch.device(\"cpu\")}')"; \
    fi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

EXPOSE 8001

# Use modern uvicorn settings
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--access-log"]