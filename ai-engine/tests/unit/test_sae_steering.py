"""
Tests for SAE-based feature steering module.
"""

import pytest

from steering.sae.core import (
    SAEDecoder,
    FeatureSteeringConfig,
    SteeringDirection,
    FeatureSteerer,
    FeatureSearchResult,
)


class TestSAEDecoder:
    """Tests for SAEDecoder class."""

    def test_init(self):
        """Test decoder initialization."""
        decoder = SAEDecoder()
        assert decoder.config is not None
        assert not decoder._is_fitted

    def test_fit(self):
        """Test fitting the decoder to activations."""
        decoder = SAEDecoder()
        activations = [
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
            [0.3, 0.4, 0.5, 0.6],
        ]
        decoder.fit(activations)
        assert decoder._is_fitted

    def test_fit_empty(self):
        """Test fitting with empty activations fails."""
        decoder = SAEDecoder()
        with pytest.raises(ValueError, match="at least one activation"):
            decoder.fit([])

    def test_encode(self):
        """Test encoding activations."""
        decoder = SAEDecoder()
        activations = [
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
        ]
        decoder.fit(activations)

        encoded = decoder.encode([0.15, 0.25, 0.35, 0.45])
        assert len(encoded) == 4
        assert all(v >= 0 for v in encoded)

    def test_encode_not_fitted(self):
        """Test encoding before fitting fails."""
        decoder = SAEDecoder()
        with pytest.raises(RuntimeError, match="must be fitted"):
            decoder.encode([0.1, 0.2])

    def test_decode(self):
        """Test decoding features."""
        decoder = SAEDecoder()
        activations = [
            [1.0, 2.0, 3.0, 4.0],
        ]
        decoder.fit(activations)

        features = [0.5, 0.0, 0.0, 0.0]
        decoded = decoder.decode(features)
        assert len(decoded) == 4

    def test_steer(self):
        """Test steering with mask."""
        decoder = SAEDecoder()
        activations = [
            [1.0, 2.0, 3.0, 4.0],
        ]
        decoder.fit(activations)

        steering_mask = {0: 0.0, 1: 0.5}
        steered = decoder.steer([1.0, 2.0, 3.0, 4.0], steering_mask)
        assert len(steered) == 4

    def test_k_sparse(self):
        """Test k-sparse selection in encoder."""
        config = FeatureSteeringConfig(sae_k_factor=2)
        decoder = SAEDecoder(config)
        activations = [
            [1.0, 2.0, 3.0, 4.0],
            [4.0, 3.0, 2.0, 1.0],
        ]
        decoder.fit(activations)

        encoded = decoder.encode([3.0, 1.0, 4.0, 2.0])
        nonzero = [v for v in encoded if v != 0.0]
        assert len(nonzero) <= 2


class TestFeatureSteerer:
    """Tests for FeatureSteerer class."""

    def test_init(self):
        """Test steerer initialization."""
        steerer = FeatureSteerer()
        assert steerer.config is not None
        assert not steerer.is_active()

    def test_set_steering_targets_suppress(self):
        """Test setting suppression targets."""
        steerer = FeatureSteerer()
        steerer.set_steering_targets([0, 1, 2], SteeringDirection.SUPPRESS, strength=1.0)

        assert steerer._is_active
        assert steerer._steering_mask[0] == 0.0
        assert steerer._steering_mask[1] == 0.0
        assert steerer._steering_mask[2] == 0.0

    def test_set_steering_targets_amplify(self):
        """Test setting amplification targets."""
        steerer = FeatureSteerer()
        steerer.set_steering_targets([0, 1], SteeringDirection.AMPLIFY, strength=0.5)

        assert steerer._is_active
        assert steerer._steering_mask[0] == 1.5
        assert steerer._steering_mask[1] == 1.5

    def test_steer_activations(self):
        """Test steering activations."""
        decoder = SAEDecoder()
        decoder.fit([[1.0, 2.0, 3.0]])
        steerer = FeatureSteerer(decoder=decoder)
        steerer.set_steering_targets([0], SteeringDirection.SUPPRESS, strength=1.0)

        activations = [1.0, 2.0, 3.0]
        steered = steerer.steer_activations(activations)
        assert len(steered) == 3

    def test_steer_inactive(self):
        """Test that inactive steerer returns original."""
        decoder = SAEDecoder()
        decoder.fit([[1.0, 2.0, 3.0]])
        steerer = FeatureSteerer(decoder=decoder)
        steerer.set_steering_targets([0], SteeringDirection.SUPPRESS)
        steerer.deactivate()

        activations = [1.0, 2.0, 3.0]
        steered = steerer.steer_activations(activations)
        assert steered == activations

    def test_activate_deactivate(self):
        """Test activate and deactivate."""
        steerer = FeatureSteerer()
        steerer.set_steering_targets([0], SteeringDirection.SUPPRESS)

        steerer.deactivate()
        assert not steerer.is_active()

        steerer.activate()
        assert steerer.is_active()


class TestFeatureSteeringConfig:
    """Tests for FeatureSteeringConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = FeatureSteeringConfig()
        assert config.steering_strength == 1.0
        assert config.feature_threshold == 0.1
        assert config.enable_conditional is True
        assert config.steering_mode == SteeringDirection.SUPPRESS

    def test_custom_config(self):
        """Test custom configuration."""
        config = FeatureSteeringConfig(
            steering_strength=2.0,
            feature_threshold=0.2,
            enable_conditional=False,
        )
        assert config.steering_strength == 2.0
        assert config.feature_threshold == 0.2
        assert config.enable_conditional is False
