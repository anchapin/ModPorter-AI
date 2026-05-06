"""
Unit tests for Diffusion Model LoRA texture conversion module.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image
import numpy as np


class TestMinecraftTextureLoRA:
    """Tests for MinecraftTextureLoRA class."""

    def setup_method(self):
        """Set up test fixtures."""
        from agents.texture_converter.diffusion_lora import MinecraftTextureLoRA

        MinecraftTextureLoRA.reset_instance()

    def test_singleton_pattern(self):
        """Test that MinecraftTextureLoRA follows singleton pattern."""
        from agents.texture_converter.diffusion_lora import MinecraftTextureLoRA

        instance1 = MinecraftTextureLoRA.get_instance()
        instance2 = MinecraftTextureLoRA.get_instance()

        assert instance1 is instance2

    def test_initialization_without_model(self):
        """Test initialization when no model is available."""
        from agents.texture_converter.diffusion_lora import MinecraftTextureLoRA

        lora = MinecraftTextureLoRA.get_instance()
        result = lora.initialize(model_path="/nonexistent/path")

        assert result is False
        assert lora.is_available() is False

    def test_initialization_with_mock_model(self):
        """Test initialization with mocked model."""
        from agents.texture_converter.diffusion_lora import MinecraftTextureLoRA

        lora = MinecraftTextureLoRA.get_instance()

        with patch.object(lora, "_initialize_diffusion_model"):
            lora._is_available = True
            lora._model = MagicMock()

            assert lora.is_available() is True

    def test_is_available_defaults_false(self):
        """Test that is_available defaults to False when not initialized."""
        from agents.texture_converter.diffusion_lora import MinecraftTextureLoRA

        lora = MinecraftTextureLoRA()
        assert lora.is_available() is False

    def test_texture_conversion_when_unavailable(self):
        """Test texture conversion fails gracefully when model unavailable."""
        from agents.texture_converter.diffusion_lora import (
            MinecraftTextureLoRA,
            TextureConversionMode,
        )

        lora = MinecraftTextureLoRA.get_instance()
        texture = Image.new("RGBA", (16, 16), (128, 128, 128, 255))

        result = lora.convert_texture(
            texture,
            TextureConversionMode.FORMAT_CONVERSION,
            "test_texture.png",
        )

        assert result.success is False
        assert result.fallback_used is True
        assert "not available" in result.error.lower()


class TestTextureConversionConfig:
    """Tests for TextureConversionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from agents.texture_converter.diffusion_lora import (
            TextureConversionConfig,
            TextureConversionMode,
        )

        config = TextureConversionConfig()

        assert config.mode == TextureConversionMode.FORMAT_CONVERSION
        assert config.target_resolution is None
        assert config.apply_alpha_premultiply is True
        assert config.preserve_animations is True
        assert config.style_strength == 0.7
        assert config.quality_threshold == 0.85
        assert config.use_batch_processing is True
        assert config.batch_size == 8
        assert config.fallback_to_standard is True
        assert config.cache_predictions is True

    def test_custom_values(self):
        """Test custom configuration values."""
        from agents.texture_converter.diffusion_lora import (
            TextureConversionConfig,
            TextureConversionMode,
        )

        config = TextureConversionConfig(
            mode=TextureConversionMode.UPSCALING,
            target_resolution=(64, 64),
            quality_threshold=0.9,
            batch_size=4,
        )

        assert config.mode == TextureConversionMode.UPSCALING
        assert config.target_resolution == (64, 64)
        assert config.quality_threshold == 0.9
        assert config.batch_size == 4


class TestLoRATrainingConfig:
    """Tests for LoRATrainingConfig dataclass."""

    def test_default_values(self):
        """Test default training configuration."""
        from agents.texture_converter.diffusion_lora import (
            LoRATrainingConfig,
            DiffusionModelType,
        )

        config = LoRATrainingConfig()

        assert config.model_type == DiffusionModelType.STABLE_DIFFUSION_3_5
        assert config.lora_rank == 16
        assert config.lora_alpha == 16
        assert config.learning_rate == 1e-4
        assert config.batch_size == 4
        assert config.epochs == 10
        assert config.resolution == (64, 64)
        assert config.guidance_scale == 7.5
        assert config.num_inference_steps == 30

    def test_custom_model_type(self):
        """Test custom model type configuration."""
        from agents.texture_converter.diffusion_lora import (
            LoRATrainingConfig,
            DiffusionModelType,
        )

        config = LoRATrainingConfig(model_type=DiffusionModelType.FLUX_KONTEXT)

        assert config.model_type == DiffusionModelType.FLUX_KONTEXT


class TestDiffusionModelType:
    """Tests for DiffusionModelType enum."""

    def test_model_types(self):
        """Test all model types are defined."""
        from agents.texture_converter.diffusion_lora import DiffusionModelType

        assert DiffusionModelType.FLUX_KONTEXT.value == "flux_kontext"
        assert DiffusionModelType.STABLE_DIFFUSION_3_5.value == "stable_diffusion_3_5"
        assert DiffusionModelType.SD_XL_LORA.value == "sd_xl_lora"


class TestTextureConversionMode:
    """Tests for TextureConversionMode enum."""

    def test_conversion_modes(self):
        """Test all conversion modes are defined."""
        from agents.texture_converter.diffusion_lora import TextureConversionMode

        assert TextureConversionMode.FORMAT_CONVERSION.value == "format_conversion"
        assert TextureConversionMode.UPSCALING.value == "upscaling"
        assert TextureConversionMode.STYLE_TRANSFER.value == "style_transfer"
        assert TextureConversionMode.VARIANT_GENERATION.value == "variant_generation"
        assert TextureConversionMode.MISSING_TEXTURE.value == "missing_texture"


class TestTexturePair:
    """Tests for TexturePair dataclass."""

    def test_creation(self):
        """Test TexturePair creation."""
        from agents.texture_converter.diffusion_lora import TexturePair

        pair = TexturePair(
            java_path="/path/to/java/texture.png",
            bedrock_path="/path/to/bedrock/texture.png",
            texture_type="blocks",
            resolution=(16, 16),
        )

        assert pair.java_path == "/path/to/java/texture.png"
        assert pair.bedrock_path == "/path/to/bedrock/texture.png"
        assert pair.texture_type == "blocks"
        assert pair.resolution == (16, 16)
        assert pair.is_animated is False

    def test_with_animation(self):
        """Test TexturePair with animation."""
        from agents.texture_converter.diffusion_lora import TexturePair

        pair = TexturePair(
            java_path="/path/to/java/texture.png",
            bedrock_path="/path/to/bedrock/texture.png",
            texture_type="blocks",
            resolution=(16, 16),
            is_animated=True,
        )

        assert pair.is_animated is True


class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_successful_conversion(self):
        """Test successful conversion result."""
        from agents.texture_converter.diffusion_lora import ConversionResult

        result = ConversionResult(
            success=True,
            original_path="/path/to/original.png",
            converted_path="/path/to/converted.png",
            quality_score=0.92,
            used_ai=True,
        )

        assert result.success is True
        assert result.converted_path == "/path/to/converted.png"
        assert result.quality_score == 0.92
        assert result.used_ai is True
        assert result.fallback_used is False

    def test_failed_conversion(self):
        """Test failed conversion result."""
        from agents.texture_converter.diffusion_lora import ConversionResult

        result = ConversionResult(
            success=False,
            original_path="/path/to/original.png",
            converted_path=None,
            quality_score=None,
            error="Model not available",
        )

        assert result.success is False
        assert result.error == "Model not available"

    def test_fallback_conversion(self):
        """Test conversion result when fallback was used."""
        from agents.texture_converter.diffusion_lora import ConversionResult

        result = ConversionResult(
            success=True,
            original_path="/path/to/original.png",
            converted_path="/path/to/fallback.png",
            quality_score=None,
            used_ai=False,
            fallback_used=True,
        )

        assert result.success is True
        assert result.fallback_used is True


class TestTextureConversionPipeline:
    """Tests for TextureConversionPipeline class."""

    def test_initialization(self):
        """Test pipeline initialization."""
        from agents.texture_converter.diffusion_lora import (
            TextureConversionPipeline,
            MinecraftTextureLoRA,
        )

        pipeline = TextureConversionPipeline()

        assert pipeline.lora is not None
        assert isinstance(pipeline.lora, MinecraftTextureLoRA)

    def test_ai_not_available_initially(self):
        """Test that AI is not available initially."""
        from agents.texture_converter.diffusion_lora import TextureConversionPipeline

        pipeline = TextureConversionPipeline()

        assert pipeline.is_ai_available() is False

    def test_convert_batch_standard_fallback(self):
        """Test batch conversion falls back to standard when AI unavailable."""
        from agents.texture_converter.diffusion_lora import (
            TextureConversionPipeline,
            TextureConversionMode,
        )

        pipeline = TextureConversionPipeline()

        with tempfile.TemporaryDirectory() as tmpdir:
            textures = [
                {"path": str(tmpdir) + "/texture1.png", "usage": "block"},
            ]

            with patch.object(pipeline.lora, "is_available", return_value=False):
                results = pipeline.convert_batch(
                    textures,
                    Path(tmpdir),
                    TextureConversionMode.FORMAT_CONVERSION,
                )

            assert len(results) == 1


class TestTexturePairDataset:
    """Tests for TexturePairDataset class."""

    def test_creation(self):
        """Test dataset creation."""
        from agents.texture_converter.diffusion_lora import TexturePairDataset

        dataset = TexturePairDataset()

        assert dataset.dataset_path is not None
        assert len(dataset.get_entries()) == 0

    def test_filter_by_resolution(self):
        """Test filtering by resolution."""
        from agents.texture_converter.diffusion_lora import (
            TexturePairDataset,
            DatasetEntry,
        )

        dataset = TexturePairDataset()
        dataset._entries = [
            DatasetEntry(
                java_texture_path="/path/java.png",
                bedrock_texture_path="/path/bedrock.png",
                texture_category="blocks",
                resolution=(16, 16),
            ),
            DatasetEntry(
                java_texture_path="/path/java2.png",
                bedrock_texture_path="/path/bedrock2.png",
                texture_category="blocks",
                resolution=(32, 32),
            ),
        ]

        filtered = dataset.filter_by_resolution(min_res=16, max_res=16)

        assert len(filtered) == 1
        assert filtered[0].resolution == (16, 16)

    def test_filter_by_category(self):
        """Test filtering by category."""
        from agents.texture_converter.diffusion_lora import (
            TexturePairDataset,
            DatasetEntry,
        )

        dataset = TexturePairDataset()
        dataset._entries = [
            DatasetEntry(
                java_texture_path="/path/java.png",
                bedrock_texture_path="/path/bedrock.png",
                texture_category="blocks",
                resolution=(16, 16),
            ),
            DatasetEntry(
                java_texture_path="/path/java_item.png",
                bedrock_texture_path="/path/bedrock_item.png",
                texture_category="items",
                resolution=(16, 16),
            ),
        ]

        filtered = dataset.filter_by_category("items")

        assert len(filtered) == 1
        assert filtered[0].texture_category == "items"


class TestComputeSSIM:
    """Tests for compute_ssim function."""

    def test_identical_images(self):
        """Test SSIM of identical images."""
        pytest.importorskip("skimage")
        from agents.texture_converter.diffusion_lora import compute_ssim

        img1 = Image.new("RGB", (16, 16), (128, 128, 128))
        img2 = Image.new("RGB", (16, 16), (128, 128, 128))

        score = compute_ssim(img1, img2)

        assert score == pytest.approx(1.0, rel=0.01)

    def test_different_images(self):
        """Test SSIM of different images."""
        pytest.importorskip("skimage")
        from agents.texture_converter.diffusion_lora import compute_ssim

        img1 = Image.new("RGB", (16, 16), (128, 128, 128))
        img2 = Image.new("RGB", (16, 16), (255, 255, 255))

        score = compute_ssim(img1, img2)

        assert 0.0 <= score <= 1.0
        assert score < 1.0


class TestPrepareTrainingDataset:
    """Tests for prepare_training_dataset function."""

    def test_returns_summary(self):
        """Test that function returns summary dict."""
        from agents.texture_converter.diffusion_lora import prepare_training_dataset

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = prepare_training_dataset(
                output_path=tmpdir,
                min_pairs=100,
                categories=["blocks"],
            )

            assert isinstance(summary, dict)
            assert "blocks" in summary


class TestPromptBuilding:
    """Tests for prompt building methods."""

    def test_build_conversion_prompt(self):
        """Test building conversion prompt."""
        from agents.texture_converter.diffusion_lora import (
            MinecraftTextureLoRA,
            TextureConversionMode,
        )

        lora = MinecraftTextureLoRA()
        img = Image.new("RGB", (16, 16))

        prompt = lora._build_conversion_prompt(img, TextureConversionMode.FORMAT_CONVERSION)

        assert "Minecraft pixel art" in prompt
        assert "16x16" in prompt
        assert "blocky pixelated" in prompt

    def test_build_negative_prompt(self):
        """Test building negative prompt."""
        from agents.texture_converter.diffusion_lora import MinecraftTextureLoRA

        lora = MinecraftTextureLoRA()

        neg_prompt = lora._build_negative_prompt()

        assert "blurry" in neg_prompt
        assert "photorealistic" in neg_prompt

    def test_get_strength_for_mode(self):
        """Test getting strength for different modes."""
        from agents.texture_converter.diffusion_lora import (
            MinecraftTextureLoRA,
            TextureConversionMode,
        )

        lora = MinecraftTextureLoRA()

        format_strength = lora._get_strength_for_mode(TextureConversionMode.FORMAT_CONVERSION)
        upscale_strength = lora._get_strength_for_mode(TextureConversionMode.UPSCALING)
        missing_strength = lora._get_strength_for_mode(TextureConversionMode.MISSING_TEXTURE)

        assert 0.0 <= format_strength <= 1.0
        assert 0.0 <= upscale_strength <= 1.0
        assert 0.0 <= missing_strength <= 1.0
        assert format_strength < missing_strength


class TestCacheOperations:
    """Tests for cache operations."""

    def test_clear_cache(self):
        """Test clearing prediction cache."""
        from agents.texture_converter.diffusion_lora import MinecraftTextureLoRA

        lora = MinecraftTextureLoRA.get_instance()
        lora._prediction_cache["test_key"] = np.zeros((16, 16, 3), dtype=np.uint8)

        assert len(lora._prediction_cache) == 1

        lora.clear_cache()

        assert len(lora._prediction_cache) == 0


class TestImagePreprocessing:
    """Tests for image preprocessing."""

    def test_preprocess_for_diffusion(self):
        """Test preprocessing image for diffusion."""
        from agents.texture_converter.diffusion_lora import (
            MinecraftTextureLoRA,
            LoRATrainingConfig,
        )

        lora = MinecraftTextureLoRA()
        lora.lora_config = LoRATrainingConfig(resolution=(64, 64))

        img = Image.new("RGBA", (16, 16), (128, 128, 128, 255))
        processed = lora._preprocess_for_diffusion(img)

        assert processed.size == (64, 64)
        assert processed.mode == "RGB"

    def test_preprocess_respects_mode(self):
        """Test preprocessing respects target resolution."""
        from agents.texture_converter.diffusion_lora import (
            MinecraftTextureLoRA,
            LoRATrainingConfig,
        )

        lora = MinecraftTextureLoRA()
        lora.lora_config = LoRATrainingConfig(resolution=(32, 32))

        img = Image.new("RGB", (32, 32), (128, 128, 128))
        processed = lora._preprocess_for_diffusion(img)

        assert processed.size == (32, 32)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
