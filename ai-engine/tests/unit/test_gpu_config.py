"""
Unit tests for GPU Configuration Manager.
"""

import os
from unittest.mock import MagicMock, patch
from utils.gpu_config import GPUConfig, GPUType, get_gpu_config, reinitialize_gpu_config, get_torch_device, get_device_string, get_onnx_providers, optimize_for_inference

class TestGPUConfig:
    def test_get_gpu_type_default(self):
        with patch.dict('os.environ', {}, clear=True):
            config = GPUConfig()
            assert config.gpu_type == GPUType.CPU

    def test_get_gpu_type_nvidia(self):
        with patch.dict('os.environ', {'GPU_TYPE': 'nvidia'}):
            # We need to mock torch.cuda.is_available to avoid fallback to CPU during init
            with patch('torch.cuda.is_available', return_value=True):
                config = GPUConfig()
                assert config.gpu_type == GPUType.NVIDIA

    def test_get_gpu_type_invalid(self):
        with patch.dict('os.environ', {'GPU_TYPE': 'invalid'}):
            config = GPUConfig()
            assert config.gpu_type == GPUType.CPU

    def test_is_gpu_enabled(self):
        with patch.dict('os.environ', {'GPU_ENABLED': 'true'}):
            config = GPUConfig()
            assert config.gpu_enabled is True
        
        with patch.dict('os.environ', {'GPU_ENABLED': 'false'}):
            config = GPUConfig()
            assert config.gpu_enabled is False

    def test_configure_cpu(self):
        config = GPUConfig()
        config._configure_cpu()
        assert config.torch_device == "cpu"
        assert "CPUExecutionProvider" in config.onnx_providers
        assert os.environ["CUDA_VISIBLE_DEVICES"] == ""

    def test_configure_nvidia_success(self):
        config = GPUConfig()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "RTX 3080"
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            config._configure_nvidia()
            assert config.torch_device == "cuda"
            assert "CUDAExecutionProvider" in config.onnx_providers

    def test_configure_nvidia_no_hardware(self):
        config = GPUConfig()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            config._configure_nvidia()
            assert config.torch_device == "cpu" # Fallback

    def test_configure_amd_rocm(self):
        config = GPUConfig()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        
        with patch.dict('sys.modules', {'torch': mock_torch}), \
             patch.object(config, '_is_rocm_available', return_value=True):
            config._configure_amd()
            assert "ROCMExecutionProvider" in config.onnx_providers

    def test_configure_amd_directml(self):
        config = GPUConfig()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        
        with patch.dict('sys.modules', {'torch': mock_torch}), \
             patch.object(config, '_is_rocm_available', return_value=False), \
             patch.object(config, '_is_directml_available', return_value=True):
            config._configure_amd()
            assert "DmlExecutionProvider" in config.onnx_providers

    def test_is_rocm_available(self):
        config = GPUConfig()
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ["ROCMExecutionProvider"]
        with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
            assert config._is_rocm_available() is True

    def test_get_memory_optimization_settings(self):
        config = GPUConfig()
        config.gpu_type = GPUType.NVIDIA
        config.gpu_enabled = True
        settings = config.get_memory_optimization_settings()
        assert settings["torch_compile"] is True
        
        config.gpu_type = GPUType.CPU
        settings = config.get_memory_optimization_settings()
        assert settings["torch_compile"] is False

    def test_validate_configuration_cpu(self):
        config = GPUConfig()
        config.gpu_type = GPUType.CPU
        valid, msg = config.validate_configuration()
        assert valid is True

    def test_validate_configuration_nvidia_fail(self):
        config = GPUConfig()
        config.gpu_type = GPUType.NVIDIA
        config.gpu_enabled = True
        
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            valid, msg = config.validate_configuration()
            assert valid is False
            assert "CUDA not available" in msg

    def test_validate_configuration_nvidia_ort_fail(self):
        config = GPUConfig()
        config.gpu_type = GPUType.NVIDIA
        config.gpu_enabled = True
        
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
        
        with patch.dict('sys.modules', {'torch': mock_torch, 'onnxruntime': mock_ort}):
            valid, msg = config.validate_configuration()
            assert valid is False
            assert "CUDA execution provider not available" in msg

    def test_full_init_nvidia(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "RTX 3080"
        with patch.dict('os.environ', {'GPU_TYPE': 'nvidia', 'GPU_ENABLED': 'true'}), \
             patch.dict('sys.modules', {'torch': mock_torch}):
            config = GPUConfig()
            assert config.gpu_type == GPUType.NVIDIA
            assert config.torch_device == "cuda"

    def test_full_init_amd(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        with patch.dict('os.environ', {'GPU_TYPE': 'amd', 'GPU_ENABLED': 'true'}), \
             patch.dict('sys.modules', {'torch': mock_torch}), \
             patch('utils.gpu_config.GPUConfig._is_rocm_available', return_value=True):
            config = GPUConfig()
            assert config.gpu_type == GPUType.AMD
            assert "ROCMExecutionProvider" in config.onnx_providers

    def test_get_torch_device_object(self):
        config = GPUConfig()
        config.torch_device = "cpu"
        mock_torch = MagicMock()
        with patch.dict('sys.modules', {'torch': mock_torch}):
            config.get_torch_device()
            mock_torch.device.assert_called_with("cpu")

    def test_validate_configuration_amd_success(self):
        config = GPUConfig()
        config.gpu_type = GPUType.AMD
        config.gpu_enabled = True
        mock_torch = MagicMock(); mock_torch.cuda.is_available.return_value = True
        mock_ort = MagicMock(); mock_ort.get_available_providers.return_value = ["ROCMExecutionProvider"]
        with patch.dict('sys.modules', {'torch': mock_torch, 'onnxruntime': mock_ort}):
            valid, msg = config.validate_configuration()
            assert valid is True
            assert "AMD GPU configuration is valid" in msg

class TestGlobalFunctions:
    def test_get_gpu_config(self):
        with patch('utils.gpu_config.GPUConfig') as mock_cls:
            reinitialize_gpu_config()
            get_gpu_config()
            assert mock_cls.called

    def test_convenience_functions(self):
        mock_config = MagicMock()
        mock_config.device = "cuda"
        mock_config.get_onnx_providers.return_value = ["P1"]
        
        with patch('utils.gpu_config._gpu_config', mock_config):
            assert get_device_string() == "cuda"
            assert get_onnx_providers() == ["P1"]
            
            optimize_for_inference()
            assert mock_config.optimize_for_inference.called
            
            get_torch_device()
            assert mock_config.get_torch_device.called
