"""
Diffusion Model LoRA for Minecraft Texture Pair Conversion

This module provides AI-powered texture conversion using fine-tuned diffusion models
(FLUX or Stable Diffusion) with LoRA adapters specifically trained on Minecraft
texture pairs for Java → Bedrock conversion.

Use Cases:
1. Texture format conversion - Java textures → Bedrock-compatible textures
2. Texture upscaling - upscale pixel art while maintaining art style
3. Missing texture generation - generate new textures in the same style
4. Style transfer - adapt textures to match Bedrock's rendering pipeline
5. Texture variant generation - create Bedrock-specific texture variants
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class DiffusionModelType(Enum):
    FLUX_KONTEXT = "flux_kontext"
    STABLE_DIFFUSION_3_5 = "stable_diffusion_3_5"
    SD_XL_LORA = "sd_xl_lora"


class TextureConversionMode(Enum):
    FORMAT_CONVERSION = "format_conversion"
    UPSCALING = "upscaling"
    STYLE_TRANSFER = "style_transfer"
    VARIANT_GENERATION = "variant_generation"
    MISSING_TEXTURE = "missing_texture"


class QualityMetric(Enum):
    SSIM = "ssim"
    LPIPS = "lpips"
    PIXEL_MATCH = "pixel_match"


@dataclass
class LoRATrainingConfig:
    model_type: DiffusionModelType = DiffusionModelType.STABLE_DIFFUSION_3_5
    lora_rank: int = 16
    lora_alpha: int = 16
    learning_rate: float = 1e-4
    batch_size: int = 4
    epochs: int = 10
    resolution: Tuple[int, int] = (64, 64)
    guidance_scale: float = 7.5
    num_inference_steps: int = 30


@dataclass
class TextureConversionConfig:
    mode: TextureConversionMode = TextureConversionMode.FORMAT_CONVERSION
    target_resolution: Optional[Tuple[int, int]] = None
    apply_alpha_premultiply: bool = True
    preserve_animations: bool = True
    style_strength: float = 0.7
    quality_threshold: float = 0.85
    use_batch_processing: bool = True
    batch_size: int = 8
    fallback_to_standard: bool = True
    cache_predictions: bool = True


@dataclass
class TexturePair:
    java_path: str
    bedrock_path: str
    texture_type: str
    resolution: Tuple[int, int]
    is_animated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionResult:
    success: bool
    original_path: str
    converted_path: Optional[str]
    quality_score: Optional[float]
    metrics: Dict[str, float] = field(default_factory=dict)
    used_ai: bool = False
    fallback_used: bool = False
    error: Optional[str] = None
    conversion_time_seconds: float = 0.0


class MinecraftTextureLoRA:
    """
    Diffusion Model LoRA wrapper for Minecraft texture conversion.

    This class manages the loading and inference of LoRA-adapted diffusion models
    specifically fine-tuned for Minecraft pixel art texture conversion.
    """

    _instance = None

    def __init__(
        self,
        config: Optional[TextureConversionConfig] = None,
        lora_config: Optional[LoRATrainingConfig] = None,
    ):
        self.config = config or TextureConversionConfig()
        self.lora_config = lora_config or LoRATrainingConfig()
        self._model = None
        self._processor = None
        self._is_available = False
        self._cache_dir = Path.home() / ".cache" / "portkit" / "lora"
        self._prediction_cache: Dict[str, np.ndarray] = {}

    @classmethod
    def get_instance(cls) -> "MinecraftTextureLoRA":
        """Get singleton instance of MinecraftTextureLoRA"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)"""
        cls._instance = None

    def initialize(self, model_path: Optional[str] = None) -> bool:
        """
        Initialize the diffusion model and LoRA weights.

        Args:
            model_path: Optional path to custom LoRA weights

        Returns:
            True if initialization succeeded, False otherwise
        """
        if self._is_available:
            return True

        try:
            self._initialize_diffusion_model(model_path)
            self._is_available = True
            logger.info("MinecraftTextureLoRA initialized successfully")
            return True
        except ImportError as e:
            logger.warning(f"Diffusion model dependencies not available: {e}")
            logger.info("Falling back to standard texture conversion")
            self._is_available = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize MinecraftTextureLoRA: {e}")
            self._is_available = False
            return False

    def _initialize_diffusion_model(self, model_path: Optional[str] = None):
        """Initialize the underlying diffusion model."""
        try:
            import torch
            from diffusers import StableDiffusionImg2ImgPipeline

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device for diffusion model: {device}")

            base_model = "stabilityai/stable-diffusion-xl-base-1.0"
            if model_path is None:
                model_path = self._get_default_lora_path()

            if model_path and Path(model_path).exists():
                logger.info(f"Loading LoRA weights from: {model_path}")
                pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
                    base_model,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                )
                pipe = self._load_lora_weights(pipe, model_path)
            else:
                logger.info("No LoRA weights found, using base SDXL model")
                pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
                    base_model,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                )

            pipe = pipe.to(device)
            pipe.enable_attention_slicing() if device == "cuda" else None

            self._model = pipe
            self._device = device

        except ImportError as e:
            raise ImportError(
                f"Required packages for diffusion model not installed: {e}. "
                "Install with: pip install torch diffusers transformers accelerate"
            ) from e

    def _load_lora_weights(self, pipe, lora_path: str):
        """Load LoRA weights into the pipeline."""
        try:
            from peft import PeftModel

            pipe.unet = PeftModel.from_pretrained(pipe.unet, lora_path)
            return pipe
        except Exception as e:
            logger.warning(f"Could not load LoRA weights: {e}. Using base model.")
            return pipe

    def _get_default_lora_path(self) -> Optional[str]:
        """Get the default LoRA weights path if available."""
        default_path = self._cache_dir / "minecraft_texture_lora"
        if default_path.exists():
            return str(default_path)
        return None

    def is_available(self) -> bool:
        """Check if the diffusion model is available for inference."""
        return self._is_available and self._model is not None

    def convert_texture(
        self,
        java_texture: Image.Image,
        target_mode: TextureConversionMode,
        original_path: str,
    ) -> ConversionResult:
        """
        Convert a Java texture to Bedrock format using AI-powered conversion.

        Args:
            java_texture: PIL Image of the Java texture
            target_mode: The conversion mode to use
            original_path: Path to the original texture (for reference)

        Returns:
            ConversionResult with the converted texture and quality metrics
        """
        import time

        start_time = time.time()

        if not self.is_available():
            return ConversionResult(
                success=False,
                original_path=original_path,
                converted_path=None,
                quality_score=None,
                fallback_used=True,
                error="Diffusion model not available",
                conversion_time_seconds=time.time() - start_time,
            )

        cache_key = f"{original_path}_{target_mode.value}"
        if self.config.cache_predictions and cache_key in self._prediction_cache:
            logger.debug(f"Using cached prediction for {original_path}")
            cached_image = Image.fromarray(self._prediction_cache[cache_key])
            return self._finalize_conversion(
                cached_image,
                original_path,
                java_texture,
                time.time() - start_time,
            )

        try:
            converted_image = self._run_diffusion_conversion(java_texture, target_mode)

            if self.config.cache_predictions:
                self._prediction_cache[cache_key] = np.array(converted_image)

            return self._finalize_conversion(
                converted_image,
                original_path,
                java_texture,
                time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Diffusion conversion failed for {original_path}: {e}")
            return ConversionResult(
                success=False,
                original_path=original_path,
                converted_path=None,
                quality_score=None,
                used_ai=True,
                error=str(e),
                conversion_time_seconds=time.time() - start_time,
            )

    def _run_diffusion_conversion(
        self,
        java_texture: Image.Image,
        target_mode: TextureConversionMode,
    ) -> Image.Image:
        """Run the actual diffusion model inference."""
        if not self._model:
            raise RuntimeError("Model not initialized")

        prompt = self._build_conversion_prompt(java_texture, target_mode)
        negative_prompt = self._build_negative_prompt()

        init_image = self._preprocess_for_diffusion(java_texture)

        result = self._model(
            prompt=prompt,
            image=init_image,
            strength=self._get_strength_for_mode(target_mode),
            guidance_scale=self.lora_config.guidance_scale,
            num_inference_steps=self.lora_config.num_inference_steps,
            negative_prompt=negative_prompt,
        )

        return result.images[0]

    def _preprocess_for_diffusion(self, image: Image.Image) -> Image.Image:
        """Preprocess image for diffusion model input."""
        target_size = self.lora_config.resolution

        if image.size != target_size:
            image = image.resize(target_size, Image.Resampling.LANCZOS)

        if image.mode != "RGB":
            image = image.convert("RGB")

        return image

    def _build_conversion_prompt(self, texture: Image.Image, mode: TextureConversionMode) -> str:
        """Build the conversion prompt based on texture characteristics."""
        width, height = texture.size
        base_prompt = (
            "Minecraft pixel art texture, "
            f"{width}x{height} pixels, "
            "blocky pixelated style, "
            "no smoothing, "
            "crisp edges, "
            "video game art"
        )

        mode_prompts = {
            TextureConversionMode.FORMAT_CONVERSION: (
                "Convert Java Edition texture to Bedrock Edition format, "
                "preserve exact pixel art style, "
                "proper alpha channel handling"
            ),
            TextureConversionMode.UPSCALING: (
                "Upscale pixel art texture, "
                "maintain blocky pixelated aesthetic, "
                "4x resolution increase, "
                "preserve original art style exactly"
            ),
            TextureConversionMode.STYLE_TRANSFER: (
                "Adapt texture to Bedrock Edition rendering style, "
                "match Bedrock color palette slightly, "
                "preserve original design"
            ),
            TextureConversionMode.VARIANT_GENERATION: (
                "Generate Bedrock Edition variant, "
                "create alternative texture version, "
                "same subject, different style interpretation"
            ),
            TextureConversionMode.MISSING_TEXTURE: (
                "Generate missing Bedrock Edition texture, "
                "match existing texture pack style, "
                "create cohesive texture"
            ),
        }

        return f"{base_prompt}, {mode_prompts.get(mode, '')}"

    def _build_negative_prompt(self) -> str:
        """Build negative prompt to avoid unwanted artifacts."""
        return (
            "blurry, fuzzy, smoothed, anti-aliased, "
            "photorealistic, photograph, 3d render, "
            "deformed, distorted, artifacts, noise"
        )

    def _get_strength_for_mode(self, mode: TextureConversionMode) -> float:
        """Get diffusion strength parameter for the conversion mode."""
        strength_map = {
            TextureConversionMode.FORMAT_CONVERSION: 0.2,
            TextureConversionMode.STYLE_TRANSFER: 0.4,
            TextureConversionMode.UPSCALING: 0.3,
            TextureConversionMode.VARIANT_GENERATION: 0.6,
            TextureConversionMode.MISSING_TEXTURE: 0.7,
        }
        return strength_map.get(mode, 0.5)

    def _finalize_conversion(
        self,
        converted_image: Image.Image,
        original_path: str,
        java_texture: Image.Image,
        conversion_time: float,
    ) -> ConversionResult:
        """Finalize conversion and compute quality metrics."""
        quality_score, metrics = self._compute_quality_metrics(converted_image, java_texture)

        should_keep = (
            quality_score is None
            or quality_score >= self.config.quality_threshold
            or not self.config.fallback_to_standard
        )

        return ConversionResult(
            success=True,
            original_path=original_path,
            converted_path=None,
            quality_score=quality_score,
            metrics=metrics,
            used_ai=True,
            fallback_used=not should_keep,
            conversion_time_seconds=conversion_time,
        )

    def _compute_quality_metrics(
        self, converted: Image.Image, original: Image.Image
    ) -> Tuple[Optional[float], Dict[str, float]]:
        """Compute quality metrics between converted and original textures."""
        metrics: Dict[str, float] = {}

        try:
            from skimage.metrics import structural_similarity as ssim
            import cv2

            orig_array = np.array(original.convert("RGB"))
            conv_array = np.array(converted.convert("RGB"))

            if orig_array.shape != conv_array.shape:
                conv_array = cv2.resize(conv_array, (orig_array.shape[1], orig_array.shape[0]))

            ssim_score = ssim(orig_array, conv_array, channel_axis=2, data_range=255)
            metrics[QualityMetric.SSIM.value] = float(ssim_score)

            pixel_match = np.mean(orig_array == conv_array)
            metrics[QualityMetric.PIXEL_MATCH.value] = float(pixel_match)

            try:
                import torch
                from torchvision import transforms
                from lpips import LPIPS

                lpips_model = LPIPS(net="alex")
                lpips_model.eval()

                transform = transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                )

                def preprocess(img_array):
                    tensor = torch.from_numpy(img_array).float().permute(2, 0, 1) / 255.0
                    tensor = transform(tensor).unsqueeze(0)
                    return tensor

                orig_t = preprocess(orig_array)
                conv_t = preprocess(conv_array)

                with torch.no_grad():
                    lpips_score = lpips_model(orig_t, conv_t).item()

                metrics[QualityMetric.LPIPS.value] = float(lpips_score)
            except ImportError:
                pass

            overall_score = metrics.get(QualityMetric.SSIM.value, 0.0)
            return overall_score, metrics

        except Exception as e:
            logger.warning(f"Could not compute quality metrics: {e}")
            return None, metrics

    def clear_cache(self):
        """Clear the prediction cache."""
        self._prediction_cache.clear()
        logger.info("Prediction cache cleared")


class TextureConversionPipeline:
    """
    Main pipeline that orchestrates AI-powered texture conversion
    with fallback to standard conversion methods.
    """

    def __init__(
        self,
        lora_config: Optional[LoRATrainingConfig] = None,
        conversion_config: Optional[TextureConversionConfig] = None,
    ):
        self.lora = MinecraftTextureLoRA.get_instance()
        self.lora.lora_config = lora_config or LoRATrainingConfig()
        self.lora.config = conversion_config or TextureConversionConfig()
        self._standard_converter = None

    def initialize(self, model_path: Optional[str] = None) -> bool:
        """
        Initialize the conversion pipeline.

        Args:
            model_path: Optional path to custom LoRA weights

        Returns:
            True if initialization succeeded
        """
        return self.lora.initialize(model_path)

    def is_ai_available(self) -> bool:
        """Check if AI-powered conversion is available."""
        return self.lora.is_available()

    def convert_batch(
        self,
        textures: List[Dict],
        output_dir: Path,
        conversion_mode: TextureConversionMode = TextureConversionMode.FORMAT_CONVERSION,
    ) -> List[ConversionResult]:
        """
        Convert a batch of textures with AI-powered conversion.

        Args:
            textures: List of texture dicts with 'path', 'type', 'usage' keys
            output_dir: Output directory for converted textures
            conversion_mode: The conversion mode to use

        Returns:
            List of ConversionResult objects
        """
        results = []

        if self.lora.config.use_batch_processing and self.is_ai_available():
            results = self._convert_batch_ai(textures, output_dir, conversion_mode)
        else:
            results = self._convert_batch_standard(textures, output_dir)

        return results

    def _convert_batch_ai(
        self,
        textures: List[Dict],
        output_dir: Path,
        conversion_mode: TextureConversionMode,
    ) -> List[ConversionResult]:
        """Convert textures using AI model."""
        results = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        batch_size = self.lora.config.batch_size

        for i in range(0, len(textures), batch_size):
            batch = textures[i : i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}, size: {len(batch)}")

            for texture_data in batch:
                texture_path = texture_data.get("path", "")
                texture_type = texture_data.get("usage", "block")

                try:
                    java_texture = Image.open(texture_path)
                    result = self.lora.convert_texture(java_texture, conversion_mode, texture_path)

                    if result.success and not result.fallback_used:
                        converted_image = self._get_converted_image(texture_path, conversion_mode)
                        if converted_image:
                            output_path = self._get_output_path(
                                output_dir, texture_path, texture_type
                            )
                            converted_image.save(output_path, "PNG", optimize=True)
                            result.converted_path = str(output_path)

                    if result.fallback_used and self.lora.config.fallback_to_standard:
                        fallback_result = self._fallback_conversion(
                            texture_path, texture_type, output_dir
                        )
                        results.append(fallback_result)
                    else:
                        results.append(result)

                except Exception as e:
                    logger.error(f"Error converting {texture_path}: {e}")
                    results.append(
                        ConversionResult(
                            success=False,
                            original_path=texture_path,
                            converted_path=None,
                            quality_score=None,
                            error=str(e),
                        )
                    )

        return results

    def _convert_batch_standard(
        self, textures: List[Dict], output_dir: Path
    ) -> List[ConversionResult]:
        """Convert textures using standard (non-AI) methods."""
        results = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for texture_data in textures:
            texture_path = texture_data.get("path", "")
            texture_type = texture_data.get("usage", "block")
            metadata = texture_data.get("metadata", {})

            try:
                if self._standard_converter is None:
                    self._standard_converter = self._get_standard_converter()

                result = self._standard_converter(texture_path, metadata, texture_type, output_dir)

                if result.get("success"):
                    results.append(
                        ConversionResult(
                            success=True,
                            original_path=texture_path,
                            converted_path=result.get("converted_path"),
                            quality_score=None,
                            fallback_used=True,
                            metrics={},
                        )
                    )
                else:
                    results.append(
                        ConversionResult(
                            success=False,
                            original_path=texture_path,
                            converted_path=None,
                            quality_score=None,
                            fallback_used=True,
                            error=result.get("error", "Unknown error"),
                        )
                    )
            except Exception as e:
                logger.error(f"Standard conversion error for {texture_path}: {e}")
                results.append(
                    ConversionResult(
                        success=False,
                        original_path=texture_path,
                        converted_path=None,
                        quality_score=None,
                        fallback_used=True,
                        error=str(e),
                    )
                )

        return results

    def _fallback_conversion(
        self, texture_path: str, texture_type: str, output_dir: Path
    ) -> ConversionResult:
        """Perform fallback standard conversion when AI fails."""
        return self._convert_batch_standard(
            [{"path": texture_path, "usage": texture_type}], output_dir
        )[0]

    def _get_standard_converter(self):
        """Get the standard texture converter function."""
        from agents.texture_converter import _convert_single_texture

        return _convert_single_texture

    def _get_converted_image(
        self, texture_path: str, mode: TextureConversionMode
    ) -> Optional[Image.Image]:
        """Get the converted image from cache or regenerate."""
        cache_key = f"{texture_path}_{mode.value}"
        if cache_key in self.lora._prediction_cache:
            return Image.fromarray(self.lora._prediction_cache[cache_key])
        return None

    def _get_output_path(self, output_dir: Path, original_path: str, texture_type: str) -> Path:
        """Generate the output path for a converted texture."""
        base_name = Path(original_path).stem
        subdir = texture_type if texture_type else "other"
        return output_dir / "textures" / f"{subdir}s" / f"{base_name}.png"


def compute_ssim(img1: Image.Image, img2: Image.Image) -> float:
    """Compute SSIM between two images."""
    from skimage.metrics import structural_similarity as ssim
    import cv2

    arr1 = np.array(img1.convert("RGB"))
    arr2 = np.array(img2.convert("RGB"))

    if arr1.shape != arr2.shape:
        arr2 = cv2.resize(arr2, (arr1.shape[1], arr1.shape[0]))

    return float(ssim(arr1, arr2, channel_axis=2, data_range=255))


def compute_lpips(img1: Image.Image, img2: Image.Image) -> float:
    """Compute LPIPS perceptual similarity between two images."""
    try:
        import torch
        from torchvision import transforms
        from lpips import LPIPS

        lpips_model = LPIPS(net="alex")
        lpips_model.eval()

        transform = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

        def preprocess(img_array):
            tensor = torch.from_numpy(img_array).float().permute(2, 0, 1) / 255.0
            return transform(tensor).unsqueeze(0)

        arr1 = np.array(img1.convert("RGB"))
        arr2 = np.array(img2.convert("RGB"))

        orig_t = preprocess(arr1)
        conv_t = preprocess(arr2)

        with torch.no_grad():
            score = lpips_model(orig_t, conv_t).item()

        return float(score)
    except ImportError:
        logger.warning("LPIPS not available, install with: pip install lpips")
        return 0.0


@dataclass
class DatasetEntry:
    java_texture_path: str
    bedrock_texture_path: str
    texture_category: str
    resolution: Tuple[int, int]
    is_animated: bool = False


class TexturePairDataset:
    """
    Dataset class for Minecraft texture pairs used in LoRA training.
    """

    def __init__(self, dataset_path: Optional[str] = None):
        self.dataset_path = dataset_path or self._get_default_dataset_path()
        self._entries: List[DatasetEntry] = []

    def _get_default_dataset_path(self) -> str:
        """Get the default dataset path."""
        return str(Path(__file__).parent.parent.parent / "training_data" / "texture_pairs")

    def load(self) -> int:
        """
        Load texture pairs from the dataset directory.

        Returns:
            Number of texture pairs loaded
        """
        if not Path(self.dataset_path).exists():
            logger.warning(f"Dataset path does not exist: {self.dataset_path}")
            return 0

        java_dir = Path(self.dataset_path) / "java"
        bedrock_dir = Path(self.dataset_path) / "bedrock"

        if not java_dir.exists() or not bedrock_dir.exists():
            logger.warning(f"Dataset directories not found: {java_dir}, {bedrock_dir}")
            return 0

        categories = ["blocks", "items", "entities", "particles", "ui"]
        count = 0

        for category in categories:
            java_cat_dir = java_dir / category
            if not java_cat_dir.exists():
                continue

            for texture_file in java_cat_dir.glob("*.png"):
                stem = texture_file.stem
                bedrock_path = bedrock_dir / category / f"{stem}.png"

                if bedrock_path.exists():
                    try:
                        with Image.open(texture_file) as img:
                            resolution = img.size
                            is_animated = self._check_animated(texture_file)

                        self._entries.append(
                            DatasetEntry(
                                java_texture_path=str(texture_file),
                                bedrock_texture_path=str(bedrock_path),
                                texture_category=category,
                                resolution=resolution,
                                is_animated=is_animated,
                            )
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Could not load texture pair {stem}: {e}")

        logger.info(f"Loaded {count} texture pairs from dataset")
        return count

    def _check_animated(self, texture_path: Path) -> bool:
        """Check if a texture is animated (has .mcmeta file)."""
        mcmeta_path = texture_path.with_suffix(".png.mcmeta")
        if not mcmeta_path.exists():
            return False

        try:
            with open(mcmeta_path) as f:
                data = json.load(f)
                return "animation" in data
        except Exception:
            return False

    def get_entries(self) -> List[DatasetEntry]:
        """Get all dataset entries."""
        return self._entries.copy()

    def filter_by_resolution(self, min_res: int = 16, max_res: int = 64) -> List[DatasetEntry]:
        """Filter entries by resolution range."""
        return [
            e
            for e in self._entries
            if min_res <= e.resolution[0] <= max_res and min_res <= e.resolution[1] <= max_res
        ]

    def filter_by_category(self, category: str) -> List[DatasetEntry]:
        """Filter entries by texture category."""
        return [e for e in self._entries if e.texture_category == category]


def prepare_training_dataset(
    output_path: str,
    min_pairs: int = 1000,
    categories: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Prepare a training dataset from Java/Bedrock texture pairs.

    Args:
        output_path: Path to save the prepared dataset
        min_pairs: Minimum number of pairs to collect
        categories: List of categories to include

    Returns:
        Summary dict with counts per category
    """
    categories = categories or ["blocks", "items", "entities", "particles", "ui"]
    dataset = TexturePairDataset()
    dataset.load()

    summary = {}
    for cat in categories:
        entries = dataset.filter_by_category(cat)
        summary[cat] = len(entries)

    logger.info(f"Dataset summary: {summary}")
    return summary
