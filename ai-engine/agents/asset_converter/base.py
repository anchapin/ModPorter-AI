"""
Asset Converter Agent - Base module.

Contains the main AssetConverterAgent class and core configuration.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class AssetConverterAgent:
    """
    Asset Converter Agent responsible for converting visual and audio assets
    to Bedrock-compatible formats as specified in PRD Feature 2.
    """

    _instance = None

    def __init__(self):
        from models.smart_assumptions import SmartAssumptionEngine

        self.smart_assumption_engine = SmartAssumptionEngine()

        # Supported asset formats
        self.texture_formats = {
            "input": [".png", ".jpg", ".jpeg", ".tga", ".bmp"],
            "output": ".png",  # Bedrock uses PNG
        }

        self.model_formats = {
            "input": [".obj", ".fbx", ".json"],  # Java mod formats
            "output": ".geo.json",  # Bedrock geometry format
        }

        self.audio_formats = {
            "input": [".ogg", ".wav", ".mp3"],
            "output": ".ogg",  # Bedrock prefers OGG
        }

        # Bedrock asset constraints
        self.texture_constraints = {
            "max_resolution": 1024,  # Max texture size for performance
            "must_be_power_of_2": True,
            "supported_channels": ["rgb", "rgba"],
        }

        self.model_constraints = {
            "max_vertices": 3000,  # Bedrock model complexity limit
            "max_textures": 8,
            "supported_bones": 60,  # Max bones for animated models
        }

        self.audio_constraints = {
            "max_file_size_mb": 10,
            "sample_rates": [22050, 44100],
            "max_duration_seconds": 300,
        }

        # Caching for performance optimization
        self._texture_cache = {}
        self._conversion_cache = {}

    @classmethod
    def get_instance(cls):
        """Get singleton instance of AssetConverterAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tools(self) -> List:
        """Get tools available to this agent"""
        from agents.asset_converter.tools import (
            analyze_assets_tool,
            convert_textures_tool,
            convert_models_tool,
            convert_audio_tool,
            validate_bedrock_assets_tool,
            extract_jar_textures_tool,
            convert_java_texture_path_tool,
            validate_texture_tool,
            generate_fallback_texture_tool,
        )

        return [
            analyze_assets_tool,
            convert_textures_tool,
            convert_models_tool,
            convert_audio_tool,
            validate_bedrock_assets_tool,
            # New tools for Issue #650 - JAR Texture Extraction
            extract_jar_textures_tool,
            convert_java_texture_path_tool,
            validate_texture_tool,
            generate_fallback_texture_tool,
        ]

    def clear_cache(self):
        """Clear the conversion cache"""
        self._conversion_cache.clear()
        logger.info("Cleared asset conversion cache")

    # Utility functions
    def _is_power_of_2(self, n: int) -> bool:
        return n > 0 and (n & (n - 1)) == 0

    def _next_power_of_2(self, n: int) -> int:
        power = 1
        while power < n:
            power *= 2
        return power

    def _previous_power_of_2(self, n: int) -> int:
        if n <= 0:
            return 1
        power = 1
        while (power * 2) <= n:
            power *= 2
        return power
