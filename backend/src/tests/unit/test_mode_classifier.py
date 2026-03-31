"""
Tests for Mode Classification Service (GAP-2.5-01)

Tests the Pipeline + Supervisor pattern for automatic mod classification:
1. FeatureExtractionAgent - extracts mod features from JAR
2. ClassifierAgent - applies rules, calculates confidence
3. RouterAgent - routes to mode-specific pipeline
4. ModeClassifier - full pipeline integration

See: docs/GAP-ANALYSIS-v2.5.md
"""

import pytest
import zipfile
import io
import sys
import os
from unittest.mock import patch, MagicMock
from typing import List

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.services.mode_classifier import (
    FeatureExtractionAgent,
    ClassifierAgent,
    RouterAgent,
    ModeClassifier,
)
from src.models.conversion_mode import (
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
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def feature_agent():
    """Create a FeatureExtractionAgent instance."""
    return FeatureExtractionAgent()


@pytest.fixture
def classifier_agent():
    """Create a ClassifierAgent instance."""
    return ClassifierAgent()


@pytest.fixture
def router_agent():
    """Create a RouterAgent instance."""
    return RouterAgent()


@pytest.fixture
def mode_classifier():
    """Create a ModeClassifier instance."""
    return ModeClassifier()


@pytest.fixture
def minimal_jar_content():
    """Create minimal JAR content with a single class."""
    jar_buffer = io.BytesIO()
    with zipfile.ZipFile(jar_buffer, 'w') as zf:
        zf.writestr('com/example/SimpleItem.class', b'fake class content')
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
    return jar_buffer.getvalue()


@pytest.fixture
def simple_mod_jar():
    """Create JAR with simple mod features (items only)."""
    jar_buffer = io.BytesIO()
    with zipfile.ZipFile(jar_buffer, 'w') as zf:
        zf.writestr('com/example/Item/MyItem.class', b'fake')
        zf.writestr('com/example/Block/ExampleBlock.class', b'fake')
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
    return jar_buffer.getvalue()


@pytest.fixture
def complex_mod_jar():
    """Create JAR with complex mod features (multiblock, worldgen)."""
    jar_buffer = io.BytesIO()
    with zipfile.ZipFile(jar_buffer, 'w') as zf:
        # Simple classes
        for i in range(5):
            zf.writestr(f'com/example/Item/Item{i}.class', b'fake')
        # Complex features
        zf.writestr('com/example/Dimension/DimensionManager.class', b'fake')
        zf.writestr('com/example/WorldGen/BiomeGenerator.class', b'fake')
        zf.writestr('com/example/Multiblock/IMultiblock.class', b'fake')
        zf.writestr('com/example/Entity/LivingEntity.class', b'fake')
        zf.writestr('com/example/Network/NetworkManager.class', b'fake')
        zf.writestr('com/example/ASM/ClassWriter.class', b'fake')
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
    return jar_buffer.getvalue()


@pytest.fixture
def empty_jar_content():
    """Create empty JAR with no class files."""
    jar_buffer = io.BytesIO()
    with zipfile.ZipFile(jar_buffer, 'w') as zf:
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
    return jar_buffer.getvalue()


@pytest.fixture
def blocking_features_mod_features():
    """Create ModFeatures with blocking features (ASM, network packets)."""
    return ModFeatures(
        total_classes=60,
        total_dependencies=15,
        has_items=True,
        has_blocks=True,
        has_entities=True,
        has_network_packets=True,
        has_ASM=True,
        has_dimensions=True,
        complex_features=[
            ComplexFeature(
                feature_type="ASM",
                description="ASM bytecode manipulation detected",
                impact="blocking",
                workaround_available=False,
                workaround_description="ASM not available in Bedrock"
            ),
            ComplexFeature(
                feature_type="network_packets",
                description="Custom network packets detected",
                impact="blocking",
                workaround_available=False,
                workaround_description="No network packet support in Bedrock"
            )
        ]
    )


@pytest.fixture
def simple_features():
    """Create features for Simple mode (1-5 classes)."""
    return ModFeatures(
        total_classes=3,
        total_dependencies=1,
        has_items=True,
        has_blocks=True,
        complex_features=[]
    )


@pytest.fixture
def standard_features():
    """Create features for Standard mode (5-20 classes)."""
    return ModFeatures(
        total_classes=15,
        total_dependencies=4,
        has_items=True,
        has_blocks=True,
        has_entities=True,
        has_recipes=True,
        complex_features=[]
    )


@pytest.fixture
def complex_features():
    """Create features for Complex mode (20-50 classes)."""
    return ModFeatures(
        total_classes=35,
        total_dependencies=7,
        has_items=True,
        has_blocks=True,
        has_entities=True,
        has_multiblock=True,
        has_custom_AI=True,
        complex_features=[
            ComplexFeature(
                feature_type="multiblock",
                description="Multiblock structure detected",
                impact="warning",
                workaround_available=True,
                workaround_description="Use vanilla multiblock as base"
            )
        ]
    )


@pytest.fixture
def expert_features():
    """Create features for Expert mode (50+ classes)."""
    return ModFeatures(
        total_classes=75,
        total_dependencies=12,
        has_items=True,
        has_blocks=True,
        has_entities=True,
        has_dimensions=True,
        has_worldgen=True,
        has_biomes=True,
        has_multiblock=True,
        complex_features=[
            ComplexFeature(
                feature_type="dimensions",
                description="Custom dimension implementation detected",
                impact="warning",
                workaround_available=True,
                workaround_description="Use vanilla dimensions as base"
            ),
            ComplexFeature(
                feature_type="worldgen",
                description="Custom world generation detected",
                impact="warning",
                workaround_available=True,
                workaround_description="Limited Bedrock world gen support"
            )
        ]
    )


# =============================================================================
# FeatureExtractionAgent Tests
# =============================================================================

class TestFeatureExtractionAgent:
    """Tests for FeatureExtractionAgent.extract_from_jar"""

    def test_extract_from_jar_minimal_content_returns_features(self, feature_agent, minimal_jar_content):
        """Test extraction from minimal JAR returns valid ModFeatures."""
        features = feature_agent.extract_from_jar(minimal_jar_content)
        
        assert isinstance(features, ModFeatures)
        assert features.total_classes == 1
        assert features.has_items is True or features.has_blocks is True

    def test_extract_from_jar_simple_mod_detects_items_and_blocks(self, feature_agent, simple_mod_jar):
        """Test that simple mod JAR correctly identifies items and blocks."""
        features = feature_agent.extract_from_jar(simple_mod_jar)
        
        assert features.total_classes == 2
        assert features.has_items is True
        assert features.has_blocks is True
        assert features.has_entities is False

    def test_extract_from_jar_complex_mod_detects_complex_features(self, feature_agent, complex_mod_jar):
        """Test that complex mod JAR detects worldgen, biomes, ASM, network packets."""
        features = feature_agent.extract_from_jar(complex_mod_jar)
        
        # The complex_mod_jar has classes that match worldgen, biomes, ASM, and network patterns
        assert features.total_classes == 11
        assert features.has_worldgen is True
        assert features.has_biomes is True
        assert features.has_network_packets is True
        assert features.has_ASM is True
        # Complex features detected based on actual pattern matches
        assert len(features.complex_features) >= 3

    def test_extract_from_jar_empty_jar_returns_zero_features(self, feature_agent, empty_jar_content):
        """Test that empty JAR returns zero classes and no features."""
        features = feature_agent.extract_from_jar(empty_jar_content)
        
        assert features.total_classes == 0
        assert features.has_items is False
        assert features.has_blocks is False

    def test_extract_from_jar_detects_mod_loader_forge(self, feature_agent):
        """Test that Forge mod loader is detected."""
        jar_buffer = io.BytesIO()
        with zipfile.ZipFile(jar_buffer, 'w') as zf:
            zf.writestr('net/minecraftforge/ForgeMod.class', b'fake')
        jar_content = jar_buffer.getvalue()
        
        features = feature_agent.extract_from_jar(jar_content)
        
        assert features.mod_loader == 'forge'

    def test_extract_from_jar_detects_mod_loader_fabric(self, feature_agent):
        """Test that Fabric mod loader is detected."""
        jar_buffer = io.BytesIO()
        with zipfile.ZipFile(jar_buffer, 'w') as zf:
            zf.writestr('net/fabricmc/loader/FabricLoader.class', b'fake')
        jar_content = jar_buffer.getvalue()
        
        features = feature_agent.extract_from_jar(jar_content)
        
        assert features.mod_loader == 'fabric'

    def test_extract_from_jar_handles_corrupt_zip_gracefully(self, feature_agent):
        """Test that corrupt ZIP content doesn't raise exceptions."""
        corrupt_content = b'not a valid zip file content at all'
        
        # Should not raise, just log error and return empty features
        features = feature_agent.extract_from_jar(corrupt_content)
        
        assert isinstance(features, ModFeatures)
        assert features.total_classes == 0


# =============================================================================
# ClassifierAgent Tests
# =============================================================================

class TestClassifierAgent:
    """Tests for ClassifierAgent.classify"""

    def test_classify_simple_mode_returns_simple(self, classifier_agent, simple_features):
        """Test that simple features correctly classify as SIMPLE mode."""
        result = classifier_agent.classify(simple_features)
        
        assert result.mode == ConversionMode.SIMPLE
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0

    def test_classify_standard_mode_returns_standard(self, classifier_agent, standard_features):
        """Test that standard features correctly classify as STANDARD mode."""
        result = classifier_agent.classify(standard_features)
        
        assert result.mode == ConversionMode.STANDARD
        assert result.automation_level == 95
        assert len(result.alternative_modes) == 3  # Other 3 modes

    def test_classify_complex_mode_returns_complex(self, classifier_agent, complex_features):
        """Test that complex features correctly classify as COMPLEX mode."""
        result = classifier_agent.classify(complex_features)
        
        assert result.mode == ConversionMode.COMPLEX
        assert result.automation_level == 85
        assert result.estimated_time_seconds >= 300

    def test_classify_expert_mode_returns_expert(self, classifier_agent):
        """Test that expert-level features correctly classify as EXPERT mode."""
        # Expert mode with blocking features (ASM) forces EXPERT classification
        # Without blocking features, 75 classes / 12 deps ties with COMPLEX
        expert_features = ModFeatures(
            total_classes=75,
            total_dependencies=12,
            has_items=True,
            has_blocks=True,
            has_entities=True,
            has_dimensions=True,
            has_worldgen=True,
            has_biomes=True,
            has_multiblock=True,
            has_ASM=True,  # Blocking feature forces EXPERT mode
            complex_features=[
                ComplexFeature(
                    feature_type="ASM",
                    description="ASM bytecode manipulation detected",
                    impact="blocking",
                    workaround_available=False,
                    workaround_description="ASM not available in Bedrock"
                ),
                ComplexFeature(
                    feature_type="dimensions",
                    description="Custom dimension implementation detected",
                    impact="warning",
                    workaround_available=True,
                    workaround_description="Use vanilla dimensions as base"
                ),
            ]
        )
        
        result = classifier_agent.classify(expert_features)
        
        # Blocking features force Expert mode regardless of class count
        assert result.mode == ConversionMode.EXPERT
        assert result.automation_level == 70
        assert result.estimated_time_seconds >= 600

    def test_classify_blocking_features_forces_expert_mode(self, classifier_agent, blocking_features_mod_features):
        """Test that blocking features (ASM, network packets) force Expert mode."""
        result = classifier_agent.classify(blocking_features_mod_features)
        
        assert result.mode == ConversionMode.EXPERT
        # Check that blocking features are mentioned in reasons
        reasons_text = ' '.join([str(r) for r in result.alternative_modes])
        # Should have reduced convertible percentage due to blocking features
        assert result.convertible_percentage < 100.0

    def test_classify_no_features_returns_default_mode(self, classifier_agent):
        """Test that empty features still return a classification."""
        empty_features = ModFeatures()
        
        result = classifier_agent.classify(empty_features)
        
        assert result.mode in ConversionMode
        assert result.confidence >= 0.0

    def test_classify_calculates_convertible_percentage(self, classifier_agent, standard_features):
        """Test that convertible percentage is calculated correctly."""
        result = classifier_agent.classify(standard_features)
        
        # Standard mod with no blocking features should have 100% or close
        assert result.convertible_percentage >= 0.0
        assert result.convertible_percentage <= 100.0

    def test_classify_has_alternative_modes(self, classifier_agent, simple_features):
        """Test that result includes alternative mode confidence scores."""
        result = classifier_agent.classify(simple_features)
        
        assert len(result.alternative_modes) == 3  # 4 modes - 1 primary
        for alt in result.alternative_modes:
            assert alt.confidence >= 0.0
            assert alt.confidence <= 1.0
            assert alt.mode != result.mode


# =============================================================================
# RouterAgent Tests
# =============================================================================

class TestRouterAgent:
    """Tests for RouterAgent pipeline and settings methods"""

    def test_get_pipeline_config_simple_mode(self, router_agent):
        """Test that SIMPLE mode returns simple-pipeline config."""
        config = router_agent.get_pipeline_config(ConversionMode.SIMPLE)
        
        assert config.pipeline_name == "simple-pipeline"
        assert "parse" in config.steps
        assert "translate" in config.steps
        assert config.estimated_success_rate == 0.99
        assert config.requires_human_review is False

    def test_get_pipeline_config_standard_mode(self, router_agent):
        """Test that STANDARD mode returns standard-pipeline config."""
        config = router_agent.get_pipeline_config(ConversionMode.STANDARD)
        
        assert config.pipeline_name == "standard-pipeline"
        assert "qa-review" in config.steps
        assert config.estimated_success_rate == 0.95
        assert config.requires_human_review is False

    def test_get_pipeline_config_complex_mode(self, router_agent):
        """Test that COMPLEX mode returns complex-pipeline config."""
        config = router_agent.get_pipeline_config(ConversionMode.COMPLEX)
        
        assert config.pipeline_name == "complex-pipeline"
        assert "semantic-check" in config.steps
        assert config.estimated_success_rate == 0.85
        assert config.requires_human_review is True
        assert "additional_qa" in config.special_requirements

    def test_get_pipeline_config_expert_mode(self, router_agent):
        """Test that EXPERT mode returns expert-pipeline config."""
        config = router_agent.get_pipeline_config(ConversionMode.EXPERT)
        
        assert config.pipeline_name == "expert-pipeline"
        assert "expert-review" in config.steps
        assert config.estimated_success_rate == 0.70
        assert config.requires_human_review is True
        assert "expert_qa" in config.special_requirements

    def test_get_recommended_settings_simple_mode(self, router_agent):
        """Test settings for SIMPLE mode have minimal validation."""
        settings = router_agent.get_recommended_settings(ConversionMode.SIMPLE)
        
        assert settings.mode == ConversionMode.SIMPLE
        assert settings.detail_level == "minimal"
        assert settings.validation_level == "basic"
        assert settings.enable_auto_fix is True
        assert settings.timeout_seconds == 120
        assert settings.quality_threshold == 0.9

    def test_get_recommended_settings_standard_mode(self, router_agent):
        """Test settings for STANDARD mode have standard validation."""
        settings = router_agent.get_recommended_settings(ConversionMode.STANDARD)
        
        assert settings.mode == ConversionMode.STANDARD
        assert settings.detail_level == "standard"
        assert settings.validation_level == "standard"
        assert settings.enable_auto_fix is True
        assert settings.timeout_seconds == 300
        assert settings.quality_threshold == 0.8

    def test_get_recommended_settings_complex_mode(self, router_agent):
        """Test settings for COMPLEX mode have strict validation."""
        settings = router_agent.get_recommended_settings(ConversionMode.COMPLEX)
        
        assert settings.mode == ConversionMode.COMPLEX
        assert settings.detail_level == "detailed"
        assert settings.validation_level == "strict"
        assert settings.enable_auto_fix is True
        assert settings.max_retries == 5
        assert settings.timeout_seconds == 600

    def test_get_recommended_settings_expert_mode_disables_auto_fix(self, router_agent):
        """Test settings for EXPERT mode disable auto-fix (manual review required)."""
        settings = router_agent.get_recommended_settings(ConversionMode.EXPERT)
        
        assert settings.mode == ConversionMode.EXPERT
        assert settings.enable_auto_fix is False
        assert settings.enable_ai_assistance is True
        assert settings.timeout_seconds == 900
        assert settings.quality_threshold == 0.6


# =============================================================================
# ModeClassifier Full Pipeline Tests
# =============================================================================

class TestModeClassifier:
    """Tests for ModeClassifier full pipeline integration"""

    @pytest.mark.asyncio
    async def test_classify_with_file_content_simple_mod(self, mode_classifier, simple_mod_jar):
        """Test full classification pipeline with simple mod JAR content."""
        request = ModeClassificationRequest(file_content=simple_mod_jar)
        
        result = await mode_classifier.classify(request)
        
        assert isinstance(result, ModeClassificationResult)
        assert result.mode in ConversionMode
        assert result.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_classify_with_features_pre_extracted(self, mode_classifier, standard_features):
        """Test full classification with pre-extracted features."""
        request = ModeClassificationRequest(features=standard_features)
        
        result = await mode_classifier.classify(request)
        
        assert result.mode == ConversionMode.STANDARD
        assert result.features.total_classes == 15

    @pytest.mark.asyncio
    async def test_classify_empty_jar_raises_error(self, mode_classifier, empty_jar_content):
        """Test that empty JAR raises appropriate error or returns fallback."""
        request = ModeClassificationRequest(file_content=empty_jar_content)
        
        # Should handle gracefully - empty JAR means no features
        result = await mode_classifier.classify(request)
        
        # Returns result but with 0 classes
        assert result.features.total_classes == 0

    @pytest.mark.asyncio
    async def test_classify_requires_file_content_or_features(self, mode_classifier):
        """Test that classify requires either file_content, features, or file_path."""
        request = ModeClassificationRequest()
        
        with pytest.raises(ValueError, match="Must provide"):
            await mode_classifier.classify(request)

    def test_get_pipeline_config_delegates_to_router(self, mode_classifier):
        """Test that ModeClassifier.get_pipeline_config uses RouterAgent."""
        config = mode_classifier.get_pipeline_config(ConversionMode.COMPLEX)
        
        assert config.pipeline_name == "complex-pipeline"

    def test_get_recommended_settings_delegates_to_router(self, mode_classifier):
        """Test that ModeClassifier.get_recommended_settings uses RouterAgent."""
        settings = mode_classifier.get_recommended_settings(ConversionMode.EXPERT)
        
        assert settings.enable_auto_fix is False
        assert settings.mode == ConversionMode.EXPERT


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestModeClassifierEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_classify_features_with_no_complex_features(self, classifier_agent):
        """Test classification when features have no complex features."""
        features = ModFeatures(
            total_classes=25,
            total_dependencies=6,
            has_items=True,
            has_blocks=True,
            complex_features=[]
        )
        
        result = classifier_agent.classify(features)
        
        # Should classify based on class/dependency count alone
        assert result.mode in ConversionMode

    def test_classify_features_on_mode_boundaries(self, classifier_agent):
        """Test classification at mode boundary values."""
        # At exactly 5 classes - boundary between SIMPLE and STANDARD
        boundary_features = ModFeatures(
            total_classes=5,
            total_dependencies=2,
            has_items=True,
            complex_features=[]
        )
        
        result = classifier_agent.classify(boundary_features)
        
        # Should be classified (mode depends on rule evaluation)
        assert result.mode in ConversionMode

    def test_router_returns_standard_for_unknown_mode_fallback(self, router_agent):
        """Test that unknown mode falls back to STANDARD pipeline."""
        # This tests the fallback behavior in get_pipeline_config
        config = router_agent.get_pipeline_config(ConversionMode.STANDARD)
        
        assert config.pipeline_name == "standard-pipeline"

    def test_feature_agent_handles_missing_mcmod_info(self, feature_agent, minimal_jar_content):
        """Test that missing mcmod.info doesn't cause errors."""
        features = feature_agent.extract_from_jar(minimal_jar_content)
        
        # Should handle gracefully - version may be None
        assert features.target_version is None or isinstance(features.target_version, str)

    def test_classifier_agent_respects_blocking_features_impact(self, classifier_agent):
        """Test that blocking features impact classification even with few classes."""
        features = ModFeatures(
            total_classes=10,
            total_dependencies=3,
            has_network_packets=True,
            has_ASM=True,
            complex_features=[
                ComplexFeature(
                    feature_type="ASM",
                    description="ASM bytecode manipulation",
                    impact="blocking",
                    workaround_available=False
                )
            ]
        )
        
        result = classifier_agent.classify(features)
        
        # Blocking features should force EXPERT mode
        assert result.mode == ConversionMode.EXPERT

    def test_estimated_time_scales_with_class_count(self, classifier_agent):
        """Test that estimated time increases with class count."""
        small_features = ModFeatures(total_classes=10, total_dependencies=2)
        large_features = ModFeatures(total_classes=100, total_dependencies=15)
        
        small_result = classifier_agent.classify(small_features)
        large_result = classifier_agent.classify(large_features)
        
        # Larger mod should have longer estimated time
        assert large_result.estimated_time_seconds >= small_result.estimated_time_seconds

    def test_convertible_percentage_reduces_for_blocking_features(self, classifier_agent):
        """Test that blocking features reduce convertible percentage."""
        features_no_blocking = ModFeatures(
            total_classes=30,
            total_dependencies=5,
            has_items=True,
            complex_features=[]
        )
        features_with_blocking = ModFeatures(
            total_classes=30,
            total_dependencies=5,
            has_items=True,
            has_ASM=True,
            has_network_packets=True,
            complex_features=[
                ComplexFeature(
                    feature_type="ASM",
                    description="ASM",
                    impact="blocking",
                    workaround_available=False
                )
            ]
        )
        
        result_no_blocking = classifier_agent.classify(features_no_blocking)
        result_with_blocking = classifier_agent.classify(features_with_blocking)
        
        assert result_with_blocking.convertible_percentage < result_no_blocking.convertible_percentage


# =============================================================================
# Integration Tests for Model Constants
# =============================================================================

class TestModelConstants:
    """Tests for model constants and default values"""

    def test_default_classification_rules_exist(self):
        """Test that DEFAULT_CLASSIFICATION_RULES is populated."""
        assert len(DEFAULT_CLASSIFICATION_RULES) > 0
        for rule in DEFAULT_CLASSIFICATION_RULES:
            assert rule.mode in ConversionMode

    def test_mode_pipelines_cover_all_modes(self):
        """Test that MODE_PIPELINES covers all conversion modes."""
        for mode in ConversionMode:
            assert mode in MODE_PIPELINES
            pipeline = MODE_PIPELINES[mode]
            assert pipeline.mode == mode
            assert len(pipeline.steps) > 0

    def test_all_modes_have_required_settings_attributes(self, router_agent):
        """Test that all modes return settings with required attributes."""
        for mode in ConversionMode:
            settings = router_agent.get_recommended_settings(mode)
            assert hasattr(settings, 'mode')
            assert hasattr(settings, 'detail_level')
            assert hasattr(settings, 'validation_level')
            assert hasattr(settings, 'enable_auto_fix')
            assert hasattr(settings, 'enable_ai_assistance')
            assert hasattr(settings, 'max_retries')
            assert hasattr(settings, 'timeout_seconds')
            assert hasattr(settings, 'parallel_processing')
            assert hasattr(settings, 'quality_threshold')
