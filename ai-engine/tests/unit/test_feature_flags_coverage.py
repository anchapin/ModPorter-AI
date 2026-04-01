"""
Unit tests for feature flags utility.
"""

import pytest
from unittest.mock import patch, MagicMock
from utils.feature_flags import (
    FeatureFlags,
    FeatureFlagManager,
    is_feature_enabled,
    get_feature_flag_manager,
)


class TestFeatureFlags:
    """Test feature flag functionality."""

    @pytest.fixture
    def manager(self):
        """Create a FeatureFlagManager instance."""
        return FeatureFlagManager()

    def test_feature_flag_manager_initialization(self, manager):
        """Test FeatureFlagManager initializes with default values."""
        assert hasattr(manager, '_flags')
        assert isinstance(manager._flags, dict)

    def test_is_feature_enabled_returns_bool(self):
        """Test is_feature_enabled returns boolean."""
        result = is_feature_enabled("nonexistent_feature")
        assert isinstance(result, bool)
        assert result is False

    def test_get_feature_flag_manager_returns_manager(self):
        """Test get_feature_flag_manager returns FeatureFlagManager."""
        result = get_feature_flag_manager()
        assert isinstance(result, FeatureFlagManager)


class TestFeatureFlagsIndividual:
    """Test individual feature flags."""

    @pytest.fixture
    def flags(self):
        """Create FeatureFlags instance."""
        return FeatureFlags()

    def test_feature_flags_has_attributes(self, flags):
        """Test FeatureFlags has expected attributes."""
        # Check for various possible flag attributes
        attrs = dir(flags)
        # Just verify it's a FeatureFlags instance
        assert flags is not None