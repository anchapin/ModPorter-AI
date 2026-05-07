#!/bin/bash
# RunPod container entrypoint: download model, then start FastAPI server.
set -e

MODEL_REPO="alexchapin/portkit-7b"
MODEL_REVISION="${MODEL_REVISION:-main}"
MODEL_DIR="/model_cache/portkit_7b"

echo "[entrypoint] Downloading ${MODEL_REPO} to ${MODEL_DIR}..."
mkdir -p "${MODEL_DIR}"

# Download only if directory is empty (resume support)
if [ -z "$(ls -A "${MODEL_DIR}" 2>/dev/null)" ]; then
    python -c "
import os
os.makedirs('${MODEL_DIR}', exist_ok=True)
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='${MODEL_REPO}',
    revision='${MODEL_REVISION}',
    local_dir='${MODEL_DIR}',
    token=os.getenv('HF_TOKEN'),
    enable_hf_transfer=True,
)
print('[entrypoint] Download complete.')
"
else
    echo "[entrypoint] Model already cached, skipping download."
fi

echo "[entrypoint] Starting inference server..."
exec "$@"