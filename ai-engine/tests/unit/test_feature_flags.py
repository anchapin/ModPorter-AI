"""
Unit tests for feature flag infrastructure.
"""

import pytest
import tempfile
import os
import sys
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    FeatureFlagType,
    FeatureFlags,
    FeatureFlagNotEnabledError,
    get_feature_flag_manager,
    set_feature_flag_manager,
    is_feature_enabled,
    feature_flag,
    require_feature,
    initialize_default_flags,
    DEFAULT_FLAGS,
)


class TestFeatureFlag:
    """Tests for the FeatureFlag class."""

    def test_create_boolean_flag(self):
        """Test creating a boolean feature flag."""
        flag = FeatureFlag(
            name="test_flag",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
            description="Test flag",
        )
        assert flag.name == "test_flag"
        assert flag.flag_type == FeatureFlagType.BOOLEAN
        assert flag.enabled is True
        assert flag.description == "Test flag"

    def test_create_percentage_flag(self):
        """Test creating a percentage rollout flag."""
        flag = FeatureFlag(
            name="rollout_flag", flag_type=FeatureFlagType.PERCENTAGE, enabled=True, percentage=25.0
        )
        assert flag.name == "rollout_flag"
        assert flag.flag_type == FeatureFlagType.PERCENTAGE
        assert flag.enabled is True
        assert flag.percentage == 25.0

    def test_create_variant_flag(self):
        """Test creating a variant flag."""
        variants = {"control": 50.0, "treatment": 50.0}
        flag = FeatureFlag(
            name="variant_flag", flag_type=FeatureFlagType.VARIANT, enabled=True, variants=variants
        )
        assert flag.name == "variant_flag"
        assert flag.flag_type == FeatureFlagType.VARIANT
        assert flag.variants == variants

    def test_to_dict(self):
        """Test converting flag to dictionary."""
        flag = FeatureFlag(
            name="test_flag",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
            description="Test flag",
        )
        data = flag.to_dict()
        assert data["name"] == "test_flag"
        assert data["flag_type"] == "boolean"
        assert data["enabled"] is True
        assert data["description"] == "Test flag"

    def test_from_dict(self):
        """Test creating flag from dictionary."""
        data = {
            "name": "test_flag",
            "flag_type": "boolean",
            "enabled": True,
            "description": "Test flag",
        }
        flag = FeatureFlag.from_dict(data)
        assert flag.name == "test_flag"
        assert flag.flag_type == FeatureFlagType.BOOLEAN
        assert flag.enabled is True


class TestFeatureFlagManager:
    """Tests for the FeatureFlagManager class."""

    def test_create_manager(self):
        """Test creating a feature flag manager."""
        manager = FeatureFlagManager()
        assert manager is not None
        assert len(manager.list_flags()) == 0

    def test_register_flag(self):
        """Test registering a new flag."""
        manager = FeatureFlagManager()
        flag = manager.register_flag(
            name="test_flag",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
            description="Test flag",
        )
        assert flag is not None
        assert flag.name == "test_flag"

        retrieved = manager.get_flag("test_flag")
        assert retrieved is not None
        assert retrieved.name == "test_flag"

    def test_register_duplicate_flag(self):
        """Test registering a duplicate flag updates it."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", enabled=True)
        manager.register_flag("test_flag", enabled=False)

        flag = manager.get_flag("test_flag")
        assert flag.enabled is False

    def test_enable_flag(self):
        """Test enabling a flag."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", enabled=False)

        result = manager.enable("test_flag")
        assert result is True
        assert manager.get_flag("test_flag").enabled is True

    def test_disable_flag(self):
        """Test disabling a flag."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", enabled=True)

        result = manager.disable("test_flag")
        assert result is True
        assert manager.get_flag("test_flag").enabled is False

    def test_enable_nonexistent_flag(self):
        """Test enabling a non-existent flag returns False."""
        manager = FeatureFlagManager()
        result = manager.enable("nonexistent")
        assert result is False

    def test_is_enabled_boolean(self):
        """Test checking if boolean flag is enabled."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", flag_type=FeatureFlagType.BOOLEAN, enabled=True)

        assert manager.is_enabled("test_flag") is True

    def test_is_enabled_disabled(self):
        """Test checking if disabled flag returns False."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", flag_type=FeatureFlagType.BOOLEAN, enabled=False)

        assert manager.is_enabled("test_flag") is False

    def test_is_enabled_nonexistent(self):
        """Test checking non-existent flag returns False."""
        manager = FeatureFlagManager()
        assert manager.is_enabled("nonexistent") is False

    def test_percentage_rollout_100_percent(self):
        """Test 100% rollout includes all users."""
        manager = FeatureFlagManager()
        manager.register_flag(
            "rollout_flag", flag_type=FeatureFlagType.PERCENTAGE, enabled=True, percentage=100.0
        )

        for i in range(10):
            assert manager.is_enabled("rollout_flag", user_id=f"user_{i}") is True

    def test_percentage_rollout_0_percent(self):
        """Test 0% rollout excludes all users."""
        manager = FeatureFlagManager()
        manager.register_flag(
            "rollout_flag", flag_type=FeatureFlagType.PERCENTAGE, enabled=True, percentage=0.0
        )

        for i in range(10):
            assert manager.is_enabled("rollout_flag", user_id=f"user_{i}") is False

    def test_percentage_rollout_consistent(self):
        """Test percentage rollout is consistent for same user."""
        manager = FeatureFlagManager()
        manager.register_flag(
            "rollout_flag", flag_type=FeatureFlagType.PERCENTAGE, enabled=True, percentage=50.0
        )

        # Same user should always get same result
        result1 = manager.is_enabled("rollout_flag", user_id="user_1")
        result2 = manager.is_enabled("rollout_flag", user_id="user_1")
        assert result1 == result2

    def test_variant_flag(self):
        """Test variant flag returns correct variant."""
        manager = FeatureFlagManager()
        manager.register_flag(
            "variant_flag",
            flag_type=FeatureFlagType.VARIANT,
            enabled=True,
            variants={"control": 50.0, "treatment": 50.0},
        )

        variant = manager.get_variant("variant_flag", user_id="user_1")
        assert variant in ["control", "treatment"]

    def test_variant_flag_disabled(self):
        """Test variant flag returns None when disabled."""
        manager = FeatureFlagManager()
        manager.register_flag(
            "variant_flag",
            flag_type=FeatureFlagType.VARIANT,
            enabled=False,
            variants={"control": 50.0, "treatment": 50.0},
        )

        variant = manager.get_variant("variant_flag", user_id="user_1")
        assert variant is None

    def test_set_percentage(self):
        """Test setting rollout percentage."""
        manager = FeatureFlagManager()
        manager.register_flag(
            "rollout_flag", flag_type=FeatureFlagType.PERCENTAGE, enabled=True, percentage=0.0
        )

        result = manager.set_percentage("rollout_flag", 50.0)
        assert result is True
        assert manager.get_flag("rollout_flag").percentage == 50.0

    def test_set_percentage_invalid_flag_type(self):
        """Test setting percentage on non-percentage flag returns False."""
        manager = FeatureFlagManager()
        manager.register_flag("bool_flag", flag_type=FeatureFlagType.BOOLEAN)

        result = manager.set_percentage("bool_flag", 50.0)
        assert result is False

    def test_unregister_flag(self):
        """Test unregistering a flag."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", enabled=True)

        result = manager.unregister_flag("test_flag")
        assert result is True
        assert manager.get_flag("test_flag") is None

    def test_unregister_nonexistent_flag(self):
        """Test unregistering non-existent flag returns False."""
        manager = FeatureFlagManager()
        result = manager.unregister_flag("nonexistent")
        assert result is False

    def test_list_flags(self):
        """Test listing all flags."""
        manager = FeatureFlagManager()
        manager.register_flag("flag1")
        manager.register_flag("flag2")

        flags = manager.list_flags()
        assert len(flags) == 2
        assert "flag1" in flags
        assert "flag2" in flags

    def test_get_all_enabled(self):
        """Test getting all enabled flags."""
        manager = FeatureFlagManager()
        manager.register_flag("flag1", enabled=True)
        manager.register_flag("flag2", enabled=False)
        manager.register_flag("flag3", enabled=True)

        enabled = manager.get_all_enabled()
        assert len(enabled) == 2
        assert "flag1" in enabled
        assert "flag3" in enabled

    def test_export_config(self):
        """Test exporting configuration."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", enabled=True, percentage=50.0)

        config = manager.export_config()
        assert "feature_flags" in config
        assert "test_flag" in config["feature_flags"]

    def test_save_and_load_config(self):
        """Test saving and loading configuration from file."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", enabled=True, percentage=50.0)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            manager.save_config(temp_path)

            # Load in new manager
            new_manager = FeatureFlagManager(config_file=temp_path)
            flag = new_manager.get_flag("test_flag")
            assert flag is not None
            assert flag.enabled is True
            assert flag.percentage == 50.0
        finally:
            os.unlink(temp_path)


class TestGlobalManager:
    """Tests for the global feature flag manager."""

    def setUp(self):
        """Reset global manager before each test."""
        global _default_manager
        _default_manager = None

    def tearDown(self):
        """Reset global manager after each test."""
        global _default_manager
        _default_manager = None

    def test_get_default_manager(self):
        """Test getting default manager creates one if needed."""
        manager = get_feature_flag_manager()
        assert manager is not None

    def test_set_custom_manager(self):
        """Test setting a custom manager."""
        custom_manager = FeatureFlagManager()
        custom_manager.register_flag("custom_flag", enabled=True)

        set_feature_flag_manager(custom_manager)

        # Get should return custom manager
        manager = get_feature_flag_manager()
        assert manager is custom_manager
        assert manager.get_flag("custom_flag") is not None

    def test_is_feature_enabled_helper(self):
        """Test the is_feature_enabled convenience function."""
        manager = FeatureFlagManager()
        manager.register_flag("test_flag", enabled=True)
        set_feature_flag_manager(manager)

        assert is_feature_enabled("test_flag") is True
        assert is_feature_enabled("nonexistent") is False


class TestDecorators:
    """Tests for feature flag decorators."""

    def setUp(self):
        """Reset global manager before each test."""
        global _default_manager
        _default_manager = None

    def tearDown(self):
        """Reset global manager after each test."""
        global _default_manager
        _default_manager = None

    def test_feature_flag_decorator_enabled(self):
        """Test feature_flag decorator runs function when enabled."""
        manager = FeatureFlagManager()
        manager.register_flag("test_feature", enabled=True)
        set_feature_flag_manager(manager)

        @feature_flag("test_feature")
        def test_function():
            return "executed"

        result = test_function()
        assert result == "executed"

    def test_feature_flag_decorator_disabled(self):
        """Test feature_flag decorator returns None when disabled."""
        manager = FeatureFlagManager()
        manager.register_flag("test_feature", enabled=False)
        set_feature_flag_manager(manager)

        @feature_flag("test_feature")
        def test_function():
            return "executed"

        result = test_function()
        assert result is None

    def test_require_feature_decorator_enabled(self):
        """Test require_feature decorator runs function when enabled."""
        manager = FeatureFlagManager()
        manager.register_flag("test_feature", enabled=True)
        set_feature_flag_manager(manager)

        @require_feature("test_feature")
        def test_function():
            return "executed"

        result = test_function()
        assert result == "executed"

    def test_require_feature_decorator_disabled(self):
        """Test require_feature decorator raises exception when disabled."""
        manager = FeatureFlagManager()
        manager.register_flag("test_feature", enabled=False)
        set_feature_flag_manager(manager)

        @require_feature("test_feature")
        def test_function():
            return "executed"

        with pytest.raises(FeatureFlagNotEnabledError):
            test_function()


class TestDefaultFlags:
    """Tests for default flags configuration."""

    def test_default_flags_exist(self):
        """Test that DEFAULT_FLAGS is properly defined."""
        assert isinstance(DEFAULT_FLAGS, dict)
        assert len(DEFAULT_FLAGS) > 0

    def test_initialize_default_flags(self):
        """Test initializing default flags."""
        manager = FeatureFlagManager()
        initialize_default_flags(manager)

        for flag_name in DEFAULT_FLAGS.keys():
            flag = manager.get_flag(flag_name)
            assert flag is not None, f"Flag {flag_name} should be registered"


class TestFeatureFlagsEnum:
    """Tests for the FeatureFlags enum class."""

    def test_feature_flags_exist(self):
        """Test that FeatureFlags has expected flags."""
        assert hasattr(FeatureFlags, "WEBSOCKET_API")
        assert hasattr(FeatureFlags, "CACHE_ENABLED")
        assert hasattr(FeatureFlags, "RATE_LIMITING")

    def test_feature_flags_values(self):
        """Test that FeatureFlags values are strings."""
        assert isinstance(FeatureFlags.WEBSOCKET_API, str)
        assert FeatureFlags.WEBSOCKET_API == "websocket_api"


class TestEnvironmentLoading:
    """Tests for loading flags from environment variables."""

    def test_load_from_env(self):
        """Test loading flags from environment variables."""
        with patch.dict(os.environ, {"FEATURE_FLAG_TEST_FLAG": "true"}):
            manager = FeatureFlagManager()
            flag = manager.get_flag("test_flag")
            assert flag is not None
            assert flag.enabled is True

    def test_load_multiple_from_env(self):
        """Test loading multiple flags from environment."""
        env = {
            "FEATURE_FLAG_FLAG_ONE": "true",
            "FEATURE_FLAG_FLAG_TWO": "false",
            "FEATURE_FLAG_FLAG_THREE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            manager = FeatureFlagManager()
            assert manager.get_flag("flag_one").enabled is True
            assert manager.get_flag("flag_two").enabled is False
            assert manager.get_flag("flag_three").enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
