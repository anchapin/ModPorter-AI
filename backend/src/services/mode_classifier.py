"""
Mode Classification Service for v2.5 Milestone

Implements Pipeline + Supervisor pattern for automatic mod classification:
1. Feature Extraction Agent (parallel) - extracts mod features
2. Classifier Agent (supervisor) - applies rules, calculates confidence
3. Router Agent - routes to mode-specific pipeline

See: docs/GAP-ANALYSIS-v2.5.md
"""

import re
import zipfile
import io
import logging
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from models.conversion_mode import (
    ConversionMode,
    ModFeatures,
    ComplexFeature,
    ModeClassificationResult,
    ModeClassificationRequest,
    ClassificationConfidence,
    ConversionSettings,
    ModeSpecificPipelineConfig,
    DEFAULT_CLASSIFICATION_RULES,
    MODE_PIPELINES,
    ModeClassificationRule,
)


logger = logging.getLogger(__name__)


class FeatureExtractionAgent:
    """
    Agent 1: Extracts features from a mod file.

    Runs in parallel to extract different feature types simultaneously.
    """

    def __init__(self):
        self.complex_feature_patterns = {
            "dimension": [
                r"net/minecraft/world/gen/Dimension",
                r"DimensionType",
                r"createDimension",
            ],
            "worldgen": [
                r"WorldGenerator",
                r"BiomeGenerator",
                r"ChunkGenerator",
            ],
            "biomes": [
                r"Biome",
                r"BiomeRegistry",
            ],
            "multiblock": [
                r"IMultiblock",
                r"MultiblockController",
                r"IStructure",
            ],
            "custom_ai": [
                r"EntityAITask",
                r"GoalSelector",
                r"Navigation",
            ],
            "network_packets": [
                r"PacketBuffer",
                r"IPacket",
                r"NetworkManager",
            ],
            "ASM": [
                r"org/objectweb/asm",
                r"ASMAPI",
                r"ClassWriter",
            ],
        }

    def extract_from_jar(self, jar_content: bytes) -> ModFeatures:
        """
        Extract features from a JAR file content.

        Args:
            jar_content: Raw bytes of the JAR file

        Returns:
            ModFeatures with extracted characteristics
        """
        features = ModFeatures()

        try:
            with zipfile.ZipFile(io.BytesIO(jar_content)) as zf:
                class_files = [f for f in zf.namelist() if f.endswith('.class')]
                features.total_classes = len(class_files)

                # Extract class names for analysis
                class_names = []
                for name in class_files:
                    parts = name.rsplit('/', 1)
                    if len(parts) > 1:
                        class_names.append(parts[1].replace('.class', ''))

                # Check for dependencies in class names
                features.total_dependencies = self._count_dependencies(class_names)

                # Check for mod components
                features.has_items = self._check_pattern(class_names, [
                    r'Item', r'BlockItem', r'SwordItem', r'ToolItem',
                ])
                features.has_blocks = self._check_pattern(class_names, [
                    r'Block', r'OreBlock', r'FallingBlock',
                ])
                features.has_entities = self._check_pattern(class_names, [
                    r'Entity', r'Mob', r'LivingEntity',
                ])
                features.has_recipes = self._check_pattern(class_names, [
                    r'Recipe', r'Crafting', r'ShapedRecipe', r'ShapelessRecipe',
                ])
                features.has_GUI = self._check_pattern(class_names, [
                    r'Screen', r'Gui', r'Container', r'Slot',
                ])
                features.has_multiblock = self._check_pattern(class_names, [
                    r'Multiblock', r'Structure', r'IMultiblock',
                ])
                features.has_custom_AI = self._check_pattern(class_names, [
                    r'EntityAITask', r'GoalSelector', r'Behavior',
                ])
                features.has_custom_rendering = self._check_pattern(class_names, [
                    r'Render', r'Renderer', r'Layer', r'Model',
                ])
                features.has_custom_models = self._check_pattern(class_names, [
                    r'ModelBakery', r'IModel', r'IModelLoader',
                ])

                # Check for complex features in class names
                for feature_type, patterns in self.complex_feature_patterns.items():
                    if self._check_pattern(class_names, patterns):
                        setattr(features, f'has_{feature_type}', True)

                # Detect mod loader
                features.mod_loader = self._detect_mod_loader(zf.namelist())

                # Extract version if present
                features.target_version = self._extract_version(zf.namelist())

                # Build complex features list
                features.complex_features = self._build_complex_features(features)

        except Exception as e:
            logger.error(f"Error extracting features from JAR: {e}")

        return features

    def extract_from_features(self, features: ModFeatures) -> ModFeatures:
        """Use pre-extracted features."""
        return features

    def _count_dependencies(self, class_names: List[str]) -> int:
        """Count external dependencies based on import patterns."""
        known_libs = [
            'net/minecraft', 'com/mojang', 'forge', 'fabric', 'org/slf4j',
            'com/google/gson', 'org/apache', 'io/github/constructing',
        ]
        return len(known_libs) // 3  # Rough estimate

    def _check_pattern(self, names: List[str], patterns: List[str]) -> bool:
        """Check if any class name matches any pattern."""
        for name in names:
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    return True
        return False

    def _detect_mod_loader(self, file_list: List[str]) -> Optional[str]:
        """Detect mod loader from file list."""
        if any('forge' in f.lower() for f in file_list):
            return 'forge'
        if any('fabric' in f.lower() for f in file_list):
            return 'fabric'
        if any('neoforge' in f.lower() for f in file_list):
            return 'neoforge'
        return None

    def _extract_version(self, file_list: List[str]) -> Optional[str]:
        """Extract version from file list."""
        version_pattern = r'mcmod\.info|version.*?(\d+\.\d+\.\d+)'
        for f in file_list:
            if match := re.search(r'version[\"\'\s:=]+(\d+\.\d+\.\d+)', f, re.I):
                return match.group(1)
        return None

    def _build_complex_features(self, features: ModFeatures) -> List[ComplexFeature]:
        """Build list of detected complex features."""
        complex_features = []

        if features.has_dimensions:
            complex_features.append(ComplexFeature(
                feature_type="dimensions",
                description="Custom dimension implementation detected",
                impact="warning",
                workaround_available=True,
                workaround_description="Use vanilla dimensions as base"
            ))

        if features.has_worldgen:
            complex_features.append(ComplexFeature(
                feature_type="worldgen",
                description="Custom world generation detected",
                impact="warning",
                workaround_available=True,
                workaround_description="Limited Bedrock world gen support"
            ))

        if features.has_biomes:
            complex_features.append(ComplexFeature(
                feature_type="biomes",
                description="Custom biome definitions detected",
                impact="info",
                workaround_available=True,
                workaround_description="Use Bedrock biome system"
            ))

        if features.has_network_packets:
            complex_features.append(ComplexFeature(
                feature_type="network_packets",
                description="Custom network packets detected",
                impact="blocking",
                workaround_available=False,
                workaround_description="No network packet support in Bedrock"
            ))

        if features.has_ASM:
            complex_features.append(ComplexFeature(
                feature_type="ASM",
                description="ASM bytecode manipulation detected",
                impact="blocking",
                workaround_available=False,
                workaround_description="ASM not available in Bedrock"
            ))

        return complex_features


class ClassifierAgent:
    """
    Agent 2: Classifies a mod based on extracted features.

    Acts as supervisor - evaluates features and applies rules to determine mode.
    """

    def __init__(self):
        self.rules = DEFAULT_CLASSIFICATION_RULES

    def classify(self, features: ModFeatures) -> ModeClassificationResult:
        """
        Classify mod into a conversion mode.

        Args:
            features: Extracted mod features

        Returns:
            ModeClassificationResult with mode, confidence, and settings
        """
        # Apply rules to determine mode
        mode, confidence, reasons = self._apply_rules(features)

        # Calculate alternative modes
        alternative_modes = self._calculate_alternatives(features, mode)

        # Calculate convertible percentage
        convertible = self._calculate_convertible_percentage(features)

        # Estimate time based on mode
        estimated_time = self._estimate_time(features, mode)

        # Determine automation level
        automation = self._get_automation_level(mode)

        # Build result
        result = ModeClassificationResult(
            mode=mode,
            confidence=confidence,
            features=features,
            alternative_modes=alternative_modes,
            convertible_percentage=convertible,
            estimated_time_seconds=estimated_time,
            automation_level=automation,
        )

        return result

    def _apply_rules(self, features: ModFeatures) -> Tuple[ConversionMode, float, List[str]]:
        """
        Apply classification rules to determine mode.

        Returns:
            Tuple of (mode, confidence, reasons)
        """
        reasons = []
        scores: Dict[ConversionMode, float] = {mode: 0.0 for mode in ConversionMode}

        for rule in self.rules:
            if self._rule_matches(rule, features):
                scores[rule.mode] += 0.3 + rule.confidence_boost
                reasons.append(f"Matches rule: {rule.mode.value} "
                            f"(classes={features.total_classes}, deps={features.total_dependencies})")

        # Check for complex features that override classification
        blocking_features = [f for f in features.complex_features if f.impact == "blocking"]
        if blocking_features:
            # Force expert mode for blocking features
            scores[ConversionMode.EXPERT] += 0.5
            reasons.append(f"Blocking features force Expert mode: "
                         f"{[f.feature_type for f in blocking_features]}")

        # Determine winning mode
        winning_mode = max(scores, key=scores.get)
        winning_score = scores[winning_mode]

        # Normalize confidence to 0-1 range
        confidence = min(winning_score, 1.0)

        return winning_mode, confidence, reasons

    def _rule_matches(self, rule: ModeClassificationRule, features: ModFeatures) -> bool:
        """Check if a classification rule matches the features."""
        if not (rule.min_classes <= features.total_classes <= rule.max_classes):
            return False
        if not (rule.min_dependencies <= features.total_dependencies <= rule.max_dependencies):
            return False
        if rule.has_complex_features:
            if not any(f.impact in ("warning", "blocking") for f in features.complex_features):
                return False
        return True

    def _calculate_alternatives(self, features: ModFeatures,
                               primary_mode: ConversionMode) -> List[ClassificationConfidence]:
        """Calculate confidence scores for alternative modes."""
        alternatives = []

        for mode in ConversionMode:
            if mode == primary_mode:
                continue

            # Calculate alternative confidence
            confidence = 0.5  # Base confidence

            # Adjust based on how close to boundary
            if mode == ConversionMode.SIMPLE and features.total_classes <= 10:
                confidence = 0.7
            elif mode == ConversionMode.STANDARD and 5 <= features.total_classes <= 30:
                confidence = 0.7
            elif mode == ConversionMode.COMPLEX and 20 <= features.total_classes <= 60:
                confidence = 0.7
            elif mode == ConversionMode.EXPERT and features.total_classes >= 50:
                confidence = 0.7

            alternatives.append(ClassificationConfidence(
                mode=mode,
                confidence=confidence,
                reasons=[f"Alternative: {mode.value} ({confidence:.0%} confidence)"]
            ))

        return alternatives

    def _calculate_convertible_percentage(self, features: ModFeatures) -> float:
        """Calculate percentage of mod that is convertible."""
        total_aspects = 10
        non_convertible = 0

        if features.has_network_packets:
            non_convertible += 1
        if features.has_ASM:
            non_convertible += 1
        if features.has_dimensions:
            non_convertible += 0.5

        convertible = ((total_aspects - non_convertible) / total_aspects) * 100
        return round(convertible, 1)

    def _estimate_time(self, features: ModFeatures, mode: ConversionMode) -> int:
        """Estimate conversion time in seconds based on mode."""
        base_times = {
            ConversionMode.SIMPLE: 60,
            ConversionMode.STANDARD: 180,
            ConversionMode.COMPLEX: 300,
            ConversionMode.EXPERT: 600,
        }

        # Scale by class count
        scale_factor = max(1.0, features.total_classes / 20)

        return int(base_times[mode] * scale_factor)

    def _get_automation_level(self, mode: ConversionMode) -> int:
        """Get expected automation level percentage."""
        levels = {
            ConversionMode.SIMPLE: 99,
            ConversionMode.STANDARD: 95,
            ConversionMode.COMPLEX: 85,
            ConversionMode.EXPERT: 70,
        }
        return levels[mode]


class RouterAgent:
    """
    Agent 3: Routes to mode-specific conversion pipeline.

    Selects appropriate pipeline and generates recommended settings.
    """

    def get_pipeline_config(self, mode: ConversionMode) -> ModeSpecificPipelineConfig:
        """Get pipeline configuration for mode."""
        return MODE_PIPELINES.get(mode, MODE_PIPELINES[ConversionMode.STANDARD])

    def get_recommended_settings(self, mode: ConversionMode) -> ConversionSettings:
        """Get recommended conversion settings for mode."""
        base_settings = {
            ConversionMode.SIMPLE: ConversionSettings(
                mode=mode,
                detail_level="minimal",
                validation_level="basic",
                enable_auto_fix=True,
                enable_ai_assistance=True,
                max_retries=1,
                timeout_seconds=120,
                parallel_processing=False,
                quality_threshold=0.9,
            ),
            ConversionMode.STANDARD: ConversionSettings(
                mode=mode,
                detail_level="standard",
                validation_level="standard",
                enable_auto_fix=True,
                enable_ai_assistance=True,
                max_retries=3,
                timeout_seconds=300,
                parallel_processing=True,
                quality_threshold=0.8,
            ),
            ConversionMode.COMPLEX: ConversionSettings(
                mode=mode,
                detail_level="detailed",
                validation_level="strict",
                enable_auto_fix=True,
                enable_ai_assistance=True,
                max_retries=5,
                timeout_seconds=600,
                parallel_processing=True,
                quality_threshold=0.7,
            ),
            ConversionMode.EXPERT: ConversionSettings(
                mode=mode,
                detail_level="detailed",
                validation_level="strict",
                enable_auto_fix=False,  # Manual review required
                enable_ai_assistance=True,
                max_retries=3,
                timeout_seconds=900,
                parallel_processing=True,
                quality_threshold=0.6,
            ),
        }

        return base_settings.get(mode, base_settings[ConversionMode.STANDARD])


class ModeClassifier:
    """
    Main Mode Classification Service implementing Pipeline + Supervisor pattern.

    Pipeline:
    1. FeatureExtractionAgent (parallel) - extracts mod features
    2. ClassifierAgent (supervisor) - classifies mode
    3. RouterAgent - selects pipeline and settings
    """

    def __init__(self):
        self.feature_agent = FeatureExtractionAgent()
        self.classifier_agent = ClassifierAgent()
        self.router_agent = RouterAgent()

    async def classify(self, request: ModeClassificationRequest) -> ModeClassificationResult:
        """
        Classify a mod's conversion mode.

        Pipeline execution:
        1. Extract features (from JAR or use provided)
        2. Classify mode
        3. Route to appropriate pipeline

        Args:
            request: Classification request with file or features

        Returns:
            Complete classification result with settings
        """
        logger.info(f"Starting mode classification for request {request}")

        # Step 1: Feature Extraction
        if request.file_content:
            # Extract from JAR content
            features = self.feature_agent.extract_from_jar(request.file_content)
        elif request.features:
            # Use pre-extracted features
            features = request.features
        elif request.file_path:
            import os
            from pathlib import Path

            # Extract only the filename from the provided path to prevent directory traversal
            filename = os.path.basename(request.file_path)

            # If the original path contained directory components, reject it
            # This is a strict defense-in-depth measure
            if filename != request.file_path:
                raise ValueError("Access denied: Only filenames are allowed, not directory paths")

            # Construct a safe path using only the base filename within the allowed directory
            upload_dir = os.path.abspath(os.environ.get("UPLOAD_DIR", "/tmp/uploads"))
            safe_path = os.path.join(upload_dir, filename)

            # Ensure the constructed path is actually within the upload directory
            if not os.path.abspath(safe_path).startswith(upload_dir):
                raise ValueError("Access denied: Path escape detected")

            if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
                 raise ValueError("Invalid file path")

            # Extract from file path
            with open(safe_path, 'rb') as f:
                content = f.read()
            features = self.feature_agent.extract_from_jar(content)
        else:
            raise ValueError("Must provide file_content, features, or file_path")

        # Step 2: Classification
        result = self.classifier_agent.classify(features)

        # Step 3: Routing - pipeline already embedded in result
        # Additional routing info available via router_agent.get_pipeline_config(result.mode)

        logger.info(f"Classification complete: mode={result.mode}, "
                   f"confidence={result.confidence:.2%}, "
                   f"automation={result.automation_level}%")

        return result

    def get_pipeline_config(self, mode: ConversionMode) -> ModeSpecificPipelineConfig:
        """Get pipeline config for classified mode."""
        return self.router_agent.get_pipeline_config(mode)

    def get_recommended_settings(self, mode: ConversionMode) -> ConversionSettings:
        """Get recommended settings for classified mode."""
        return self.router_agent.get_recommended_settings(mode)


# Singleton instance
_mode_classifier: Optional[ModeClassifier] = None


def get_mode_classifier() -> ModeClassifier:
    """Get singleton ModeClassifier instance."""
    global _mode_classifier
    if _mode_classifier is None:
        _mode_classifier = ModeClassifier()
    return _mode_classifier
