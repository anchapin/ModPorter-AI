"""
GPU Configuration Manager for AI Engine
Automatically detects and configures GPU settings based on GPU_TYPE environment variable.
"""

import os
from typing import Dict, Any, Tuple
from enum import Enum


class GPUType(Enum):
    """Supported GPU types."""
    NVIDIA = "nvidia"
    AMD = "amd"
    CPU = "cpu"


class GPUConfig:
    """
    GPU Configuration Manager that handles automatic detection and configuration
    of GPU settings based on environment variables and hardware availability.
    """
    
    def __init__(self):
        self.gpu_type = self._get_gpu_type()
        self.gpu_enabled = self._is_gpu_enabled()
        self.device = self._get_device()
        self.torch_device = None
        self.onnx_providers = []
        
        # Initialize GPU configuration
        self._initialize_gpu_config()
    
    def _get_gpu_type(self) -> GPUType:
        """Get GPU type from environment variable."""
        gpu_type_str = os.getenv("GPU_TYPE", "cpu").lower().strip()
        
        try:
            return GPUType(gpu_type_str)
        except ValueError:
            print(f"Warning: Invalid GPU_TYPE '{gpu_type_str}', defaulting to CPU")
            return GPUType.CPU
    
    def _is_gpu_enabled(self) -> bool:
        """Check if GPU is enabled via environment variable."""
        gpu_enabled = os.getenv("GPU_ENABLED", "false").lower().strip()
        return gpu_enabled in ("true", "1", "yes", "on")
    
    def _get_device(self) -> str:
        """Get the appropriate device string based on GPU type."""
        if self.gpu_type == GPUType.CPU or not self.gpu_enabled:
            return "cpu"
        else:
            return "cuda"  # Both NVIDIA and AMD use 'cuda' in PyTorch
    
    def _initialize_gpu_config(self):
        """Initialize GPU configuration based on detected type."""
        if self.gpu_type == GPUType.CPU:
            self._configure_cpu()
        elif self.gpu_type == GPUType.NVIDIA:
            self._configure_nvidia()
        elif self.gpu_type == GPUType.AMD:
            self._configure_amd()
    
    def _configure_cpu(self):
        """Configure for CPU-only execution."""
        self.torch_device = "cpu"
        self.onnx_providers = ["CPUExecutionProvider"]
        
        # Force CPU execution for PyTorch
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        
        print("GPU Config: Using CPU-only execution")
    
    def _configure_nvidia(self):
        """Configure for NVIDIA GPU execution."""
        try:
            import torch
            
            if torch.cuda.is_available():
                self.torch_device = "cuda"
                self.onnx_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                
                # Get GPU info
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                
                print(f"GPU Config: Using NVIDIA GPU - {gpu_name} ({gpu_count} device(s))")
                
                # Set environment variables for optimal NVIDIA performance
                os.environ.setdefault("CUDA_LAUNCH_BLOCKING", "0")
                
            else:
                print("Warning: NVIDIA GPU not detected, falling back to CPU")
                self._configure_cpu()
                
        except ImportError:
            print("Warning: PyTorch not available, falling back to CPU")
            self._configure_cpu()
        except Exception as e:
            print(f"Warning: NVIDIA GPU configuration failed: {e}, falling back to CPU")
            self._configure_cpu()
    
    def _configure_amd(self):
        """Configure for AMD GPU execution."""
        try:
            import torch
            
            if torch.cuda.is_available():
                self.torch_device = "cuda"
                
                # Check for ROCm or DirectML
                if self._is_rocm_available():
                    self.onnx_providers = ["ROCMExecutionProvider", "CPUExecutionProvider"]
                    print("GPU Config: Using AMD GPU with ROCm")
                    
                    # Set ROCm environment variables
                    os.environ.setdefault("HIP_VISIBLE_DEVICES", "0")
                    os.environ.setdefault("ROCR_VISIBLE_DEVICES", "0")
                    
                elif self._is_directml_available():
                    self.onnx_providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
                    print("GPU Config: Using AMD GPU with DirectML")
                    
                else:
                    print("Warning: AMD GPU detected but no ROCm/DirectML, using CUDA fallback")
                    self.onnx_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                
                # Get GPU info if available
                try:
                    gpu_count = torch.cuda.device_count()
                    gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown AMD GPU"
                    print(f"GPU Config: AMD GPU - {gpu_name} ({gpu_count} device(s))")
                except:
                    print("GPU Config: AMD GPU detected (device info unavailable)")
                    
            else:
                print("Warning: AMD GPU not detected, falling back to CPU")
                self._configure_cpu()
                
        except ImportError:
            print("Warning: PyTorch not available, falling back to CPU")
            self._configure_cpu()
        except Exception as e:
            print(f"Warning: AMD GPU configuration failed: {e}, falling back to CPU")
            self._configure_cpu()
    
    def _is_rocm_available(self) -> bool:
        """Check if ROCm is available."""
        try:
            import onnxruntime as ort
            return "ROCMExecutionProvider" in ort.get_available_providers()
        except (ImportError, Exception):
            return False
    
    def _is_directml_available(self) -> bool:
        """Check if DirectML is available."""
        try:
            import onnxruntime as ort
            return "DmlExecutionProvider" in ort.get_available_providers()
        except (ImportError, Exception):
            return False
    
    def get_torch_device(self):
        """Get the PyTorch device object."""
        if self.torch_device is None:
            return None
            
        try:
            import torch
            return torch.device(self.torch_device)
        except ImportError:
            return None
    
    def get_sentence_transformers_device(self) -> str:
        """Get device string for sentence-transformers library."""
        return self.torch_device or "cpu"
    
    def get_onnx_providers(self) -> list:
        """Get ONNX Runtime execution providers in priority order."""
        return self.onnx_providers.copy()
    
    def get_memory_optimization_settings(self) -> Dict[str, Any]:
        """Get memory optimization settings based on GPU type."""
        settings = {
            "torch_compile": False,
            "mixed_precision": False,
            "memory_efficient_attention": False,
            "gradient_checkpointing": False,
        }
        
        if self.gpu_type != GPUType.CPU and self.gpu_enabled:
            settings.update({
                "torch_compile": True,
                "mixed_precision": True,
                "memory_efficient_attention": True,
                "gradient_checkpointing": True,
            })
        
        return settings
    
    def optimize_for_inference(self):
        """Apply inference-specific optimizations."""
        if self.gpu_type == GPUType.CPU:
            # CPU optimizations
            os.environ.setdefault("OMP_NUM_THREADS", str(os.cpu_count()))
            os.environ.setdefault("MKL_NUM_THREADS", str(os.cpu_count()))
            
        elif self.gpu_type == GPUType.NVIDIA:
            # NVIDIA optimizations
            try:
                import torch
                if torch.cuda.is_available():
                    torch.backends.cudnn.benchmark = True
                    torch.backends.cudnn.enabled = True
            except:
                pass
                
        elif self.gpu_type == GPUType.AMD:
            # AMD optimizations
            try:
                import torch
                if torch.cuda.is_available():
                    # Enable tensor fusion for AMD
                    torch.backends.cudnn.enabled = True
            except:
                pass
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current GPU configuration."""
        return {
            "gpu_type": self.gpu_type.value,
            "gpu_enabled": self.gpu_enabled,
            "device": self.device,
            "torch_device": self.torch_device,
            "onnx_providers": self.onnx_providers,
            "memory_optimizations": self.get_memory_optimization_settings(),
        }
    
    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate the current GPU configuration."""
        try:
            if self.gpu_type == GPUType.CPU:
                return True, "CPU configuration is valid"
            
            import torch
            if not torch.cuda.is_available() and self.gpu_enabled:
                return False, f"GPU enabled but PyTorch CUDA not available for {self.gpu_type.value}"
            
            if self.gpu_type == GPUType.NVIDIA:
                try:
                    import onnxruntime as ort
                    if "CUDAExecutionProvider" not in ort.get_available_providers():
                        return False, "NVIDIA GPU selected but CUDA execution provider not available"
                except ImportError:
                    pass  # ONNX Runtime not required for validation
            
            elif self.gpu_type == GPUType.AMD:
                try:
                    import onnxruntime as ort
                    providers = ort.get_available_providers()
                    if not any(p in providers for p in ["ROCMExecutionProvider", "DmlExecutionProvider"]):
                        return False, "AMD GPU selected but no ROCm/DirectML execution provider available"
                except ImportError:
                    pass  # ONNX Runtime not required for validation
            
            return True, f"{self.gpu_type.value.upper()} GPU configuration is valid"
            
        except Exception as e:
            return False, f"Configuration validation failed: {str(e)}"


# Global GPU configuration instance
_gpu_config = None


def get_gpu_config() -> GPUConfig:
    """Get the global GPU configuration instance."""
    global _gpu_config
    if _gpu_config is None:
        _gpu_config = GPUConfig()
    return _gpu_config


def reinitialize_gpu_config() -> GPUConfig:
    """Reinitialize GPU configuration (useful for testing or config changes)."""
    global _gpu_config
    _gpu_config = GPUConfig()
    return _gpu_config


# Convenience functions for common use cases
def get_torch_device():
    """Get the PyTorch device for the current GPU configuration."""
    return get_gpu_config().get_torch_device()


def get_device_string() -> str:
    """Get the device string (e.g., 'cuda', 'cpu') for the current configuration."""
    return get_gpu_config().device


def get_onnx_providers() -> list:
    """Get ONNX Runtime execution providers for the current configuration."""
    return get_gpu_config().get_onnx_providers()


def optimize_for_inference():
    """Apply inference optimizations for the current GPU configuration."""
    get_gpu_config().optimize_for_inference()


def print_gpu_info():
    """Print GPU configuration information."""
    config = get_gpu_config()
    print("=" * 50)
    print("GPU Configuration Summary")
    print("=" * 50)
    
    summary = config.get_config_summary()
    for key, value in summary.items():
        print(f"{key:20}: {value}")
    
    # Validation
    is_valid, message = config.validate_configuration()
    status = "✓" if is_valid else "✗"
    print(f"{'validation':20}: {status} {message}")
    
    print("=" * 50)


if __name__ == "__main__":
    # Display GPU configuration when run directly
    print_gpu_info()