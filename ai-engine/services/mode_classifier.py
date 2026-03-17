"""
Mode Classification System for Minecraft Mod Conversion

Classifies mods into 4 conversion modes:
- Simple: 99% automation, basic blocks/items
- Standard: 95% automation, entities/recipes
- Complex: 85% automation, multiblock/machines
- Expert: 70% automation, dimensions/worldgen
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import zipfile
import os

logger = logging.getLogger(__name__)


class ConversionMode:
    """Conversion mode constants."""

    SIMPLE = "Simple"
    STANDARD = "Standard"
    COMPLEX = "Complex"
    EXPERT = "Expert"


@dataclass
class ModFeatures:
    """Features extracted from a mod for classification."""

    # Basic counts
    class_count: int = 0
    method_count: int = 0
    field_count: int = 0

    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    dependency_count: int = 0

    # Assets
    texture_count: int = 0
    model_count: int = 0
    sound_count: int = 0
    asset_count: int = 0

    # Complex features (boolean flags)
    has_entities: bool = False
    has_multiblock: bool = False
    has_machines: bool = False
    has_custom_ai: bool = False
    has_dimension: bool = False
    has_biome: bool = False
    has_worldgen: bool = False
    has_gui: bool = False
    has_recipes: bool = False
    has_achievements: bool = False

    # Detected complex features
    complex_features: List[str] = field(default_factory=list)
    unknown_features: List[str] = field(default_factory=list)

    # Calculated metrics
    complexity_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_count": self.class_count,
            "dependency_count": self.dependency_count,
            "asset_count": self.asset_count,
            "complex_features": self.complex_features,
            "complexity_score": self.complexity_score,
        }


@dataclass
class ClassificationResult:
    """Result of mode classification."""

    mode: str
    confidence: float  # 0.0 to 1.0
    reason: str
    features: Optional[ModFeatures] = None
    automation_target: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "confidence": self.confidence,
            "reason": self.reason,
            "automation_target": self.automation_target,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


# Classification rules configuration
CLASSIFICATION_RULES = {
    ConversionMode.SIMPLE: {
        "class_count_range": (1, 5),
        "dependency_range": (0, 2),
        "complex_features": [],
        "automation_target": 0.99,
        "description": "Basic mod with simple blocks or items",
    },
    ConversionMode.STANDARD: {
        "class_count_range": (5, 20),
        "dependency_range": (2, 5),
        "complex_features": ["entity", "recipe", "gui", "achievement"],
        "automation_target": 0.95,
        "description": "Standard mod with entities or recipes",
    },
    ConversionMode.COMPLEX: {
        "class_count_range": (20, 50),
        "dependency_range": (5, 10),
        "complex_features": ["multiblock", "machine", "custom_ai"],
        "automation_target": 0.85,
        "description": "Complex mod with multiblock structures or machines",
    },
    ConversionMode.EXPERT: {
        "class_count_range": (50, None),  # No upper limit
        "dependency_range": (10, None),
        "complex_features": ["dimension", "biome", "worldgen"],
        "automation_target": 0.70,
        "description": "Expert mod with dimensions or custom worldgen",
    },
}

# Feature detection patterns
FEATURE_PATTERNS = {
    "multiblock": [
        "IMultiBlock",
        "MultiBlockPart",
        "TileEntityMultiBlock",
        "multiblock",
    ],
    "machine": ["TileEntity", "BlockEntity", "IMachine", "EnergyTile"],
    "custom_ai": ["Goal", "Task", "AI", "PathNavigate"],
    "dimension": ["DimensionType", "WorldProvider", "DimensionRegistry"],
    "biome": ["Biome", "BiomeBuilder", "BiomeRegistry"],
    "worldgen": ["WorldGenerator", "ChunkGenerator", "TerrainGen"],
    "entity": ["Entity", "LivingEntity", "MobEntity", "IEntity"],
    "gui": ["GuiScreen", "ContainerScreen", "IGuiHandler"],
    "recipe": ["IRecipe", "RecipeRegistry", "Crafting"],
}


class ModeClassifier:
    """
    Classifies Minecraft mods into conversion modes.

    Usage:
        classifier = ModeClassifier()
        result = classifier.classify_mod("/path/to/mod.jar")
        print(f"Mode: {result.mode}, Confidence: {result.confidence:.0%}")
    """

    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        logger.info("ModeClassifier initialized")

    def classify_mod(self, mod_path: str) -> ClassificationResult:
        """
        Classify a mod into a conversion mode.

        Args:
            mod_path: Path to mod JAR file or directory

        Returns:
            ClassificationResult with mode, confidence, and recommendations
        """
        logger.info(f"Classifying mod: {mod_path}")

        # Extract features
        features = self.feature_extractor.extract_features(mod_path)

        # Classify based on features
        result = self._classify_by_features(features)
        result.features = features

        # Add recommendations
        result.recommendations = self._generate_recommendations(result)

        logger.info(
            f"Classification result: {result.mode} (confidence: {result.confidence:.0%})"
        )

        return result

    def _classify_by_features(self, features: ModFeatures) -> ClassificationResult:
        """Classify mod based on extracted features."""

        # Check for expert features first (highest priority)
        set(FEATURE_PATTERNS.keys()) & set(features.complex_features)
        if any(
            f in features.complex_features
            for f in CLASSIFICATION_RULES[ConversionMode.EXPERT]["complex_features"]
        ):
            return ClassificationResult(
                mode=ConversionMode.EXPERT,
                confidence=self._calculate_confidence(features, ConversionMode.EXPERT),
                reason="Expert-level features detected (dimension/worldgen/biome)",
                automation_target=CLASSIFICATION_RULES[ConversionMode.EXPERT][
                    "automation_target"
                ],
            )

        # Check for complex features
        if any(
            f in features.complex_features
            for f in CLASSIFICATION_RULES[ConversionMode.COMPLEX]["complex_features"]
        ):
            return ClassificationResult(
                mode=ConversionMode.COMPLEX,
                confidence=self._calculate_confidence(features, ConversionMode.COMPLEX),
                reason="Complex features detected (multiblock/machine/custom AI)",
                automation_target=CLASSIFICATION_RULES[ConversionMode.COMPLEX][
                    "automation_target"
                ],
            )

        # Check for standard features
        if any(
            f in features.complex_features
            for f in CLASSIFICATION_RULES[ConversionMode.STANDARD]["complex_features"]
        ):
            return ClassificationResult(
                mode=ConversionMode.STANDARD,
                confidence=self._calculate_confidence(
                    features, ConversionMode.STANDARD
                ),
                reason="Standard features detected (entities/recipes)",
                automation_target=CLASSIFICATION_RULES[ConversionMode.STANDARD][
                    "automation_target"
                ],
            )

        # Check class count and dependencies
        class_count = features.class_count
        dep_count = features.dependency_count

        # Standard range check
        if (
            CLASSIFICATION_RULES[ConversionMode.STANDARD]["class_count_range"][0]
            <= class_count
            <= CLASSIFICATION_RULES[ConversionMode.STANDARD]["class_count_range"][1]
        ):
            return ClassificationResult(
                mode=ConversionMode.STANDARD,
                confidence=self._calculate_confidence(
                    features, ConversionMode.STANDARD
                ),
                reason=f"Standard complexity ({class_count} classes, {dep_count} dependencies)",
                automation_target=CLASSIFICATION_RULES[ConversionMode.STANDARD][
                    "automation_target"
                ],
            )

        # Complex range check (high class count without complex features)
        if (
            class_count
            > CLASSIFICATION_RULES[ConversionMode.STANDARD]["class_count_range"][1]
        ):
            return ClassificationResult(
                mode=ConversionMode.COMPLEX,
                confidence=self._calculate_confidence(features, ConversionMode.COMPLEX),
                reason=f"High complexity ({class_count} classes)",
                automation_target=CLASSIFICATION_RULES[ConversionMode.COMPLEX][
                    "automation_target"
                ],
            )

        # Default to Simple
        return ClassificationResult(
            mode=ConversionMode.SIMPLE,
            confidence=self._calculate_confidence(features, ConversionMode.SIMPLE),
            reason="Basic mod structure",
            automation_target=CLASSIFICATION_RULES[ConversionMode.SIMPLE][
                "automation_target"
            ],
        )

    def _calculate_confidence(self, features: ModFeatures, mode: str) -> float:
        """Calculate classification confidence score (0.0 to 1.0)."""
        confidence = 1.0
        rules = CLASSIFICATION_RULES[mode]

        # Check class count fit
        class_range = rules["class_count_range"]
        if class_range[0] and class_range[1]:
            midpoint = (class_range[0] + class_range[1]) / 2
            range_size = class_range[1] - class_range[0]
            distance = abs(features.class_count - midpoint)
            # Reduce confidence for being far from midpoint
            confidence -= (distance / range_size) * 0.2
        elif class_range[0] and features.class_count < class_range[0]:
            confidence -= 0.3

        # Check dependency fit
        dep_range = rules["dependency_range"]
        if dep_range[0] and dep_range[1]:
            if not (dep_range[0] <= features.dependency_count <= dep_range[1]):
                confidence -= 0.1

        # Reduce confidence for missing information
        if features.class_count == 0:
            confidence -= 0.3
        if features.dependency_count == 0 and features.class_count > 0:
            confidence -= 0.1

        # Reduce confidence for unknown features
        unknown_count = len(features.unknown_features)
        confidence -= unknown_count * 0.05

        # Ensure confidence is in valid range
        return max(0.0, min(1.0, confidence))

    def _generate_recommendations(self, result: ClassificationResult) -> List[str]:
        """Generate recommendations based on classification."""
        recommendations = []

        if result.confidence < 0.7:
            recommendations.append("Low confidence - manual review recommended")

        if result.mode == ConversionMode.EXPERT:
            recommendations.append("Expert mode: Expect significant manual work")
            recommendations.append("Consider breaking into smaller components")

        if result.mode == ConversionMode.COMPLEX:
            recommendations.append("Complex mode: Review multiblock/machine patterns")

        if result.features:
            if result.features.has_custom_ai:
                recommendations.append(
                    "Custom AI detected: Review behavior tree conversion"
                )
            if result.features.has_multiblock:
                recommendations.append(
                    "Multi-block detected: Verify structure validation"
                )

        return recommendations


class FeatureExtractor:
    """Extracts features from Minecraft mods for classification."""

    def __init__(self):
        logger.debug("FeatureExtractor initialized")

    def extract_features(self, mod_path: str) -> ModFeatures:
        """
        Extract all features from a mod.

        Args:
            mod_path: Path to mod JAR file or directory

        Returns:
            ModFeatures with all extracted features
        """
        features = ModFeatures()

        if mod_path.endswith((".jar", ".zip")):
            self._extract_from_jar(mod_path, features)
        elif os.path.isdir(mod_path):
            self._extract_from_directory(mod_path, features)
        else:
            logger.warning(f"Unknown mod format: {mod_path}")

        # Calculate complexity score
        features.complexity_score = self._calculate_complexity(features)

        return features

    def _extract_from_jar(self, jar_path: str, features: ModFeatures):
        """Extract features from JAR file."""
        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                file_list = jar.namelist()

                # Count Java classes
                java_files = [f for f in file_list if f.endswith(".java")]
                class_files = [f for f in file_list if f.endswith(".class")]
                features.class_count = len(class_files)

                # Analyze Java files if available
                for java_file in java_files[:50]:  # Limit for performance
                    try:
                        content = jar.read(java_file).decode("utf-8", errors="ignore")
                        self._analyze_java_content(content, features)
                    except Exception:
                        pass

                # Count assets
                features.texture_count = len(
                    [f for f in file_list if "/textures/" in f and f.endswith(".png")]
                )
                features.model_count = len(
                    [f for f in file_list if "/models/" in f and f.endswith(".json")]
                )
                features.sound_count = len(
                    [f for f in file_list if "/sounds/" in f and f.endswith(".ogg")]
                )
                features.asset_count = (
                    features.texture_count + features.model_count + features.sound_count
                )

                # Count dependencies from metadata
                features.dependencies = self._extract_dependencies_from_jar(
                    jar, file_list
                )
                features.dependency_count = len(features.dependencies)

        except Exception as e:
            logger.error(f"Error extracting from JAR {jar_path}: {e}")

    def _extract_from_directory(self, dir_path: str, features: ModFeatures):
        """Extract features from directory."""
        root = Path(dir_path)

        # Count Java files
        java_files = list(root.rglob("*.java"))
        class_files = list(root.rglob("*.class"))
        features.class_count = len(class_files)

        # Analyze Java content
        for java_file in java_files[:50]:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
                self._analyze_java_content(content, features)
            except Exception:
                pass

        # Count assets
        features.texture_count = len(list(root.rglob("**/textures/**/*.png")))
        features.model_count = len(list(root.rglob("**/models/**/*.json")))
        features.sound_count = len(list(root.rglob("**/sounds/**/*.ogg")))
        features.asset_count = (
            features.texture_count + features.model_count + features.sound_count
        )

        # Extract dependencies
        features.dependencies = self._extract_dependencies_from_dir(root)
        features.dependency_count = len(features.dependencies)

    def _analyze_java_content(self, content: str, features: ModFeatures):
        """Analyze Java file content for features."""
        # Count methods and fields
        features.method_count += content.count("(") - content.count("import")
        features.field_count += content.count(";") - content.count("import")

        # Detect complex features
        for feature_name, patterns in FEATURE_PATTERNS.items():
            for pattern in patterns:
                if pattern in content:
                    if feature_name not in features.complex_features:
                        features.complex_features.append(feature_name)

                        # Set boolean flags
                        setattr(features, f"has_{feature_name}", True)
                    break

    def _extract_dependencies_from_jar(
        self, jar: zipfile.ZipFile, file_list: List[str]
    ) -> List[str]:
        """Extract dependencies from JAR metadata."""
        dependencies = []

        # Check fabric.mod.json
        if "fabric.mod.json" in file_list:
            try:
                import json

                content = jar.read("fabric.mod.json").decode("utf-8")
                data = json.loads(content)
                deps = data.get("depends", {})
                dependencies.extend(deps.keys())
            except Exception:
                pass

        # Check mods.toml
        for f in file_list:
            if f.endswith("mods.toml"):
                try:
                    content = jar.read(f).decode("utf-8")
                    # Simple parsing for dependency strings
                    if "modId=" in content:
                        for line in content.split("\n"):
                            if "modId=" in line:
                                mod_id = line.split("=")[1].strip('"')
                                dependencies.append(mod_id)
                except Exception:
                    pass

        return list(set(dependencies))

    def _extract_dependencies_from_dir(self, root: Path) -> List[str]:
        """Extract dependencies from directory metadata."""
        dependencies = []

        # Check fabric.mod.json
        fabric_mod = root / "fabric.mod.json"
        if fabric_mod.exists():
            try:
                import json

                data = json.loads(fabric_mod.read_text())
                deps = data.get("depends", {})
                dependencies.extend(deps.keys())
            except Exception:
                pass

        return list(set(dependencies))

    def _calculate_complexity(self, features: ModFeatures) -> float:
        """Calculate overall complexity score (0.0 to 1.0)."""
        score = 0.0

        # Class count contribution (0-0.4)
        if features.class_count > 0:
            class_score = min(features.class_count / 100, 1.0) * 0.4
            score += class_score

        # Dependency contribution (0-0.2)
        if features.dependency_count > 0:
            dep_score = min(features.dependency_count / 20, 1.0) * 0.2
            score += dep_score

        # Complex features contribution (0-0.4)
        complex_count = len(features.complex_features)
        if complex_count > 0:
            feature_score = min(complex_count / 5, 1.0) * 0.4
            score += feature_score

        return min(1.0, score)


# Convenience functions
def classify_mod(mod_path: str) -> ClassificationResult:
    """
    Classify a mod into a conversion mode.

    Args:
        mod_path: Path to mod JAR file or directory

    Returns:
        ClassificationResult with mode and confidence
    """
    classifier = ModeClassifier()
    return classifier.classify_mod(mod_path)


def get_mode_info(mode: str) -> Dict[str, Any]:
    """
    Get information about a conversion mode.

    Args:
        mode: Mode name (Simple/Standard/Complex/Expert)

    Returns:
        Dictionary with mode information
    """
    if mode not in CLASSIFICATION_RULES:
        return {"error": f"Unknown mode: {mode}"}

    rules = CLASSIFICATION_RULES[mode]
    return {
        "mode": mode,
        "description": rules["description"],
        "automation_target": rules["automation_target"],
        "class_count_range": rules["class_count_range"],
        "dependency_range": rules["dependency_range"],
        "complex_features": rules["complex_features"],
    }


def get_all_modes() -> List[Dict[str, Any]]:
    """Get information about all conversion modes."""
    return [
        get_mode_info(mode)
        for mode in [
            ConversionMode.SIMPLE,
            ConversionMode.STANDARD,
            ConversionMode.COMPLEX,
            ConversionMode.EXPERT,
        ]
    ]
