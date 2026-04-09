"""
Unit tests for GPU config utility.
"""

import pytest
from unittest.mock import patch
from utils.gpu_config import (
    GPUConfig,
    GPUType,
    get_gpu_config,
    get_torch_device,
    get_device_string,
)


class TestGPUConfig:
    """Test GPU configuration detection and selection."""

    @pytest.fixture
    def config(self):
        """Create GPUConfig instance with CPU fallback."""
        with patch('torch.cuda.is_available', return_value=False):
            with patch('torch.version.rocm', None):
                return GPUConfig()

    def test_gpu_type_enum_values(self, config):
        """Test GPUType has expected values."""
        assert hasattr(GPUType, 'NVIDIA')
        assert hasattr(GPUType, 'AMD')
        assert hasattr(GPUType, 'CPU')

    def test_config_has_gpu_type(self, config):
        """Test GPUConfig has gpu_type attribute."""
        assert hasattr(config, 'gpu_type')
        assert isinstance(config.gpu_type, GPUType)

    def test_config_has_device(self, config):
        """Test GPUConfig has device attribute."""
        assert hasattr(config, 'device')
        assert isinstance(config.device, str)

    def test_get_gpu_config_returns_config(self):
        """Test get_gpu_config returns GPUConfig."""
        with patch('torch.cuda.is_available', return_value=False):
            result = get_gpu_config()
            assert isinstance(result, GPUConfig)

    def test_get_device_string_returns_string(self):
        """Test get_device_string returns string."""
        result = get_device_string()
        assert isinstance(result, str)

    def test_get_torch_device_returns_device(self):
        """Test get_torch_device returns torch device or None."""
        result = get_torch_device()
        # Returns None when no GPU
        assert result is None or hasattr(result, 'type')