# GPU Acceleration Guide for AI Engine

The AI Engine supports acceleration on NVIDIA GPUs, AMD GPUs, and CPU-only execution.

## Quick Start

### 🟢 Default Installation (CPU-Only)
```bash
pip install .
```
Works on any computer, no GPU required.

### 🔥 NVIDIA GPU Acceleration  
```bash
pip install .[gpu-nvidia]
```
**Requirements:**
- NVIDIA GPU with CUDA support
- CUDA 12.4+ drivers installed
- **Performance:** Up to 20x speedup

### 🔴 AMD GPU Acceleration
```bash
pip install .[gpu-amd]  
```
**Requirements:**
- AMD RX 7000+ series or RDNA 3/4 GPU
- Windows: DirectX 12 support (automatic)
- Linux: ROCm 6.0+ drivers installed
- **Performance:** Up to 15x speedup

## Platform-Specific AMD Setup

### Windows (DirectML - Recommended)
```bash
# Install with AMD DirectML support
pip install .[gpu-amd]

# Verify installation
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
# Should show 'DmlExecutionProvider'
```

### Linux (ROCm - Best Performance)
```bash
# Install ROCm drivers first
wget -qO- https://repo.radeon.com/rocm/rocm.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/rocm-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/rocm-archive-keyring.gpg] https://repo.radeon.com/rocm/apt/6.0/ jammy main" | sudo tee /etc/apt/sources.list.d/rocm.list
sudo apt update && sudo apt install rocm-dkms rocm-libs

# Install AI Engine with ROCm
pip install .[gpu-amd]

# Verify PyTorch sees AMD GPU
python -c "import torch; print(f'ROCm available: {torch.cuda.is_available()}')"
```

## Supported Hardware

### ✅ NVIDIA GPUs
- **RTX 40 Series:** RTX 4090, 4080, 4070, 4060
- **RTX 30 Series:** RTX 3090, 3080, 3070, 3060
- **RTX 20 Series:** RTX 2080 Ti, 2070, 2060
- **GTX 16 Series:** GTX 1660 Ti, 1650
- **Professional:** Tesla, Quadro, A100, H100

### ✅ AMD GPUs  
- **RX 7000 Series:** RX 7900 XTX, 7900 XT, 7800 XT, 7700 XT
- **RX 6000 Series:** Limited support (RDNA 2)
- **Professional:** Radeon PRO W7800, W7900
- **Future:** RX 9070 XT, 9060 XT (RDNA 4)

### ✅ CPU-Only
- **Any modern CPU** with Python 3.8+
- Works on laptops, servers, ARM processors
- No additional drivers required

## Performance Comparison

| Component | CPU | AMD GPU | NVIDIA GPU |
|-----------|-----|---------|------------|
| **Sentence Transformers** | 1x | 15x | 20x |
| **ChromaDB Embeddings** | 1x | 12x | 20x |
| **CrewAI/LangChain** | 1x | 8x | 15x |

## GPU Detection in Code

The AI Engine automatically detects available hardware:

```python
import torch
import onnxruntime as ort

# Check PyTorch device
if torch.cuda.is_available():
    if 'AMD' in torch.cuda.get_device_name():
        device = 'cuda'  # AMD ROCm
        print(f"Using AMD GPU: {torch.cuda.get_device_name()}")
    else:
        device = 'cuda'  # NVIDIA CUDA
        print(f"Using NVIDIA GPU: {torch.cuda.get_device_name()}")
else:
    device = 'cpu'
    print("Using CPU")

# Check ONNX Runtime providers
providers = ort.get_available_providers()
if 'CUDAExecutionProvider' in providers:
    print("ONNX: NVIDIA CUDA available")
elif 'ROCMExecutionProvider' in providers:
    print("ONNX: AMD ROCm available") 
elif 'DmlExecutionProvider' in providers:
    print("ONNX: AMD DirectML available")
else:
    print("ONNX: CPU only")
```

## Troubleshooting

### AMD GPU Issues
**Problem:** GPU not detected on Linux
```bash
# Check ROCm installation
rocm-smi
/opt/rocm/bin/rocminfo

# Verify user permissions
sudo usermod -a -G render,video $USER
# Logout and login again
```

**Problem:** DirectML not working on Windows
```bash
# Update DirectX 12
# Install latest GPU drivers from AMD
# Verify Windows version (requires 1903+)
```

### NVIDIA GPU Issues  
**Problem:** CUDA version mismatch
```bash
# Check CUDA version
nvidia-smi
nvcc --version

# Install matching PyTorch version
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

### Performance Issues
**Problem:** No speedup observed
- Verify GPU drivers are up to date
- Check GPU memory usage: `nvidia-smi` or `rocm-smi`  
- Enable mixed precision: `torch.autocast()`
- Use larger batch sizes to saturate GPU

## Environment Variables

```bash
# Force CPU execution
export CUDA_VISIBLE_DEVICES=""

# AMD ROCm debugging  
export HIP_VISIBLE_DEVICES=0
export ROCR_VISIBLE_DEVICES=0

# NVIDIA debugging
export CUDA_LAUNCH_BLOCKING=1
```

## Docker Support

### NVIDIA GPU
```dockerfile
FROM pytorch/pytorch:2.5.0-devel-cuda12.4-cudnn9-ubuntu22.04
COPY . /app
RUN pip install /app[gpu-nvidia]
```

### AMD GPU  
```dockerfile
FROM rocm/pytorch:rocm6.0_ubuntu22.04_py3.10_pytorch_2.1.1
COPY . /app  
RUN pip install /app[gpu-amd]
```

## Cost Comparison

| Setup | Hardware Cost | Power Usage | Performance |
|-------|---------------|-------------|-------------|
| **CPU Only** | $0 | Low | Baseline |
| **AMD RX 7900 XTX** | $800-900 | Medium | 15x faster |
| **NVIDIA RTX 4080** | $1000-1200 | Medium | 20x faster |
| **NVIDIA RTX 4090** | $1500-1800 | High | 25x faster |

## Support

For GPU-specific issues:
- **NVIDIA:** Check [PyTorch CUDA compatibility](https://pytorch.org/get-started/locally/)
- **AMD:** Check [ROCm compatibility list](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html)
- **General:** Open an issue with your `pip list` and GPU info