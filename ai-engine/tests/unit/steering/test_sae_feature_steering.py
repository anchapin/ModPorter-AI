"""
Unit tests for SAE-based feature steering module.

Tests the core functionality of SAEFeatureSteerer and JavaIdiomClassifier.
"""

import pytest
from steering.sae_feature_steering import (
    JavaIdiomClassifier,
    JavaIdiomFeatures,
    SAEFeatureSteerer,
    SteeringConfig,
    create_default_steering_config,
    create_demo_features,
    FeatureVector,
)


class TestSteeringConfig:
    """Tests for SteeringConfig dataclass."""

    def test_default_config(self):
        """Test default steering configuration."""
        config = SteeringConfig()
        assert config.steering_strength == 1.0
        assert config.suppression_threshold == 0.5
        assert config.enable_boost is False
        assert config.conditional_on_context is True

    def test_custom_config(self):
        """Test custom steering configuration."""
        config = SteeringConfig(
            steering_strength=1.5,
            suppression_threshold=0.3,
            enable_boost=True,
            conditional_on_context=False,
        )
        assert config.steering_strength == 1.5
        assert config.suppression_threshold == 0.3
        assert config.enable_boost is True
        assert config.conditional_on_context is False

    def test_create_default_steering_config(self):
        """Test factory function."""
        config = create_default_steering_config()
        assert isinstance(config, SteeringConfig)
        assert config.steering_strength == 1.0


class TestFeatureVector:
    """Tests for FeatureVector dataclass."""

    def test_feature_vector_creation(self):
        """Test basic FeatureVector creation."""
        fv = FeatureVector(
            feature_id="feature_001",
            activation=0.7,
            steering_direction=-1.0,
            description="Test feature",
        )
        assert fv.feature_id == "feature_001"
        assert fv.activation == 0.7
        assert fv.steering_direction == -1.0
        assert fv.examples == []

    def test_feature_vector_with_examples(self):
        """Test FeatureVector with examples."""
        fv = FeatureVector(
            feature_id="feature_002",
            activation=0.5,
            steering_direction=1.0,
            description="With examples",
            examples=["import net.minecraft", "extends Entity"],
        )
        assert len(fv.examples) == 2


class TestJavaIdiomFeatures:
    """Tests for JavaIdiomFeatures dataclass."""

    def test_empty_features(self):
        """Test empty features object."""
        features = JavaIdiomFeatures()
        assert features.forge_api_features == []
        assert features.class_structure_features == []
        assert features.get_all_features() == []

    def test_features_with_data(self):
        """Test features with populated data."""
        features = JavaIdiomFeatures(
            forge_api_features=[
                FeatureVector("f1", 0.7, -1.0),
                FeatureVector("f2", 0.8, -1.0),
            ],
            class_structure_features=[
                FeatureVector("f3", 0.6, -0.8),
            ],
        )
        all_features = features.get_all_features()
        assert len(all_features) == 3

    def test_get_suppression_vector(self):
        """Test suppression vector generation."""
        features = JavaIdiomFeatures(
            forge_api_features=[
                FeatureVector("forge_1", 0.7, -1.0),
            ],
            class_structure_features=[
                FeatureVector("class_1", 0.6, -0.8),
            ],
        )
        suppression = features.get_suppression_vector()
        assert suppression["forge_1"] == 1.0  # negated from -1.0
        assert suppression["class_1"] == 0.8  # negated from -0.8


class TestSAEFeatureSteerer:
    """Tests for SAEFeatureSteerer class."""

    def test_initialization(self):
        """Test steerer initialization."""
        steerer = SAEFeatureSteerer()
        assert steerer.config is not None
        assert steerer.features is not None
        assert steerer._is_initialized is False

    def test_initialize(self):
        """Test steerer initialization method."""
        steerer = SAEFeatureSteerer()
        result = steerer.initialize("7b")
        assert result is True
        assert steerer._is_initialized is True

    def test_initialize_auto(self):
        """Test steerer with auto model size."""
        steerer = SAEFeatureSteerer()
        result = steerer.initialize("auto")
        assert result is True

    def test_apply_steering_uninitialized(self):
        """Test steering on uninitialized steerer returns unchanged."""
        steerer = SAEFeatureSteerer()
        activations = {"feature_001": 0.5, "feature_002": 0.3}
        result = steerer.apply_steering(activations)
        assert result == activations

    def test_apply_steering_with_features(self):
        """Test steering with loaded features."""
        config = SteeringConfig(steering_strength=1.0)
        features = create_demo_features()
        steerer = SAEFeatureSteerer(config=config, features=features)
        steerer.initialize()

        activations = {
            "forge_feature_001": 0.8,
            "class_struct_feature_001": 0.6,
            "other_feature": 0.5,
        }
        result = steerer.apply_steering(activations)

        # Check that features were steered
        assert "forge_feature_001" in result
        assert "other_feature" in result

    def test_should_apply_steering_java_to_bedrock(self):
        """Test conditional steering for Java to Bedrock conversion."""
        steerer = SAEFeatureSteerer()
        steerer.initialize()

        context = {
            "source": "java",
            "target": "bedrock",
            "conversion_type": "java_to_bedrock",
        }
        assert steerer._should_apply_steering(context) is True

    def test_should_not_apply_steering_other_conversions(self):
        """Test steering not applied for non-Java to Bedrock conversions."""
        steerer = SAEFeatureSteerer()
        steerer.initialize()

        context = {"source": "bedrock", "target": "bedrock"}
        assert steerer._should_apply_steering(context) is False

    def test_should_apply_steering_no_context(self):
        """Test steering applied when no context provided."""
        steerer = SAEFeatureSteerer()
        steerer.initialize()

        assert steerer._should_apply_steering(None) is True

    def test_get_steering_report(self):
        """Test steering report generation."""
        config = SteeringConfig()
        features = create_demo_features()
        steerer = SAEFeatureSteerer(config=config, features=features)
        steerer.initialize()

        activations = {
            f"forge_feature_{i:03d}": 0.5 + (i % 10) * 0.05
            for i in range(10)
        }

        report = steerer.get_steering_report(activations)
        assert "total_features_analyzed" in report
        assert "suppressed_count" in report
        assert "timestamp" in report


class TestJavaIdiomClassifier:
    """Tests for JavaIdiomClassifier class."""

    def test_classifier_creation(self):
        """Test classifier instantiation."""
        classifier = JavaIdiomClassifier()
        assert classifier is not None

    def test_classify_java_code(self):
        """Test classification of Java Edition code."""
        classifier = JavaIdiomClassifier()
        java_code = """
        import net.minecraft.entity.Entity;
        import cpw.mods.fml.common.Mod;

        @Mod(modid = "examplemod")
        public class ExampleEntity extends Entity {
            @SubscribeEvent
            public void onPlayerInteract(PlayerInteractEvent event) {
                Capability<IForgePlayer> cap = entity.getCapability(CAPABILITY);
            }
        }
        """
        result = classifier.classify(java_code)
        assert result["java_score"] > result["bedrock_score"]
        assert result["idiom_type"] == "java"
        assert result["is_java_idiomatic"] is True

    def test_classify_bedrock_code(self):
        """Test classification of Bedrock Edition code."""
        classifier = JavaIdiomClassifier()
        bedrock_code = """
        {
            "format_version": "1.19.0",
            "minecraft:client_entity": {
                "description": {
                    "identifier": "example:entity"
                },
                "client": {
                    "model": "example.model"
                }
            }
        }
        """
        result = classifier.classify(bedrock_code)
        assert result["bedrock_score"] > 0
        assert result["idiom_type"] == "bedrock"

    def test_classify_mixed_code(self):
        """Test classification of mixed code."""
        classifier = JavaIdiomClassifier()
        mixed_code = """
        public class Test {
            public static final int ID = 5;
            "minecraft:item": {
                "id": "test:item"
            }
        }
        """
        result = classifier.classify(mixed_code)
        assert "java_score" in result
        assert "bedrock_score" in result

    def test_validate_steering_effect(self):
        """Test steering validation."""
        classifier = JavaIdiomClassifier()
        original = "import net.minecraft.entity.Entity;"
        steered = '"minecraft:entity": { "id": "test" }'

        result = classifier.validate_steering_effect(original, steered)
        assert "steering_effective" in result
        assert "original_classification" in result
        assert "steered_classification" in result


class TestFeatureDiscovery:
    """Tests for feature discovery functionality."""

    def test_discover_java_features(self):
        """Test feature discovery on sample dataset."""
        steerer = SAEFeatureSteerer()
        steerer.initialize()

        activation_dataset = [
            {"code": "import net.minecraft.Entity;", "is_java": True},
            {"code": "extends Item", "is_java": True},
            {"code": "@Mod public class", "is_java": True},
            {"code": "minecraft:entity format_version", "is_java": False},
            {"code": '"client": {}', "is_java": False},
            {"code": "format_version: 1.19", "is_java": False},
        ]

        features = steerer.discover_java_features(activation_dataset, top_k=20)
        assert isinstance(features, JavaIdiomFeatures)
        all_features = features.get_all_features()
        assert len(all_features) <= 20
        assert len(all_features) > 0


class TestDemoFeatures:
    """Tests for demo features creation."""

    def test_create_demo_features(self):
        """Test demo features creation."""
        features = create_demo_features()
        assert len(features.forge_api_features) == 50
        assert len(features.class_structure_features) == 50
        assert len(features.import_features) == 30
        assert len(features.type_pattern_features) == 40

    def test_demo_features_suppression_vector(self):
        """Test demo features suppression vector."""
        features = create_demo_features()
        suppression = features.get_suppression_vector()
        # All demo features should have negative steering direction
        for steering_value in suppression.values():
            assert steering_value > 0  # negated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])