"""
Unit tests for Feature Flags service.

Issue: #643 - Backend: Implement Rate Limiting Dashboard
"""

import pytest
import tempfile
import json
from unittest.mock import patch, MagicMock
import os

from services.feature_flags import (
    FeatureFlagType,
    FeatureFlag,
    FeatureFlagManager,
    get_feature_flag_manager,
    set_feature_flag_manager,
    is_feature_enabled,
    feature_flag,
    require_feature,
    FeatureFlagNotEnabledError,
    FeatureFlags,
    DEFAULT_FLAGS,
    initialize_default_flags,
)


class TestFeatureFlagType:
    """Tests for FeatureFlagType enum."""

    def test_all_types_exist(self):
        """Test all flag types are defined."""
        assert FeatureFlagType.BOOLEAN.value == "boolean"
        assert FeatureFlagType.PERCENTAGE.value == "percentage"
        assert FeatureFlagType.VARIANT.value == "variant"


class TestFeatureFlag:
    """Tests for FeatureFlag class."""

    def test_creation_defaults(self):
        """Test creating flag with defaults."""
        flag = FeatureFlag(name="test_flag")
        assert flag.name == "test_flag"
        assert flag.flag_type == FeatureFlagType.BOOLEAN
        assert flag.default_value is False
        assert flag.enabled is False
        assert flag.percentage == 0.0
        assert flag.variants == {}

    def test_creation_custom(self):
        """Test creating flag with custom values."""
        flag = FeatureFlag(
            name="custom_flag",
            flag_type=FeatureFlagType.PERCENTAGE,
            default_value=True,
            description="Custom flag",
            enabled=True,
            percentage=50.0,
            variants={"a": 50.0, "b": 50.0},
        )
        assert flag.name == "custom_flag"
        assert flag.flag_type == FeatureFlagType.PERCENTAGE
        assert flag.enabled is True
        assert flag.percentage == 50.0
        assert flag.variants == {"a": 50.0, "b": 50.0}

    def test_to_dict(self):
        """Test converting flag to dictionary."""
        flag = FeatureFlag(
            name="test",
            flag_type=FeatureFlagType.BOOLEAN,
            enabled=True,
            percentage=25.0,
        )
        data = flag.to_dict()
        assert data["name"] == "test"
        assert data["flag_type"] == "boolean"
        assert data["enabled"] is True
        assert data["percentage"] == 25.0

    def test_from_dict(self):
        """Test creating flag from dictionary."""
        data = {
            "name": "from_dict",
            "flag_type": "percentage",
            "enabled": True,
            "percentage": 75.0,
            "description": "Test",
        }
        flag = FeatureFlag.from_dict(data)
        assert flag.name == "from_dict"
        assert flag.flag_type == FeatureFlagType.PERCENTAGE
        assert flag.enabled is True
        assert flag.percentage == 75.0

    def test_from_dict_boolean(self):
        """Test creating flag from dict with boolean type string."""
        data = {"name": "bool_flag", "flag_type": "boolean", "enabled": False}
        flag = FeatureFlag.from_dict(data)
        assert flag.flag_type == FeatureFlagType.BOOLEAN

    def test_repr(self):
        """Test string representation."""
        flag = FeatureFlag(name="repr_test", enabled=True)
        repr_str = repr(flag)
        assert "repr_test" in repr_str
        assert "enabled" in repr_str


class TestFeatureFlagManager:
    """Tests for FeatureFlagManager class."""

    @pytest.fixture
    def manager(self):
        """Create fresh manager instance."""
        return FeatureFlagManager()

    def test_initialization_empty(self, manager):
        """Test manager initializes with no flags."""
        assert len(manager._flags) == 0

    def test_register_flag(self, manager):
        """Test registering a new flag."""
        flag = manager.register_flag("new_flag", description="A new flag")
        assert flag.name == "new_flag"
        assert "new_flag" in manager._flags

    def test_register_flag_overwrites(self, manager):
        """Test registering existing flag overwrites."""
        manager.register_flag("existing", enabled=False)
        manager.register_flag("existing", enabled=True)
        assert manager._flags["existing"].enabled is True

    def test_register_flag_percentage(self, manager):
        """Test registering percentage flag."""
        flag = manager.register_flag(
            "rollout", flag_type=FeatureFlagType.PERCENTAGE, percentage=50.0
        )
        assert flag.flag_type == FeatureFlagType.PERCENTAGE
        assert flag.percentage == 50.0

    def test_register_flag_variant(self, manager):
        """Test registering variant flag."""
        flag = manager.register_flag(
            "variant_flag",
            flag_type=FeatureFlagType.VARIANT,
            variants={"control": 50.0, "treatment": 50.0},
        )
        assert flag.flag_type == FeatureFlagType.VARIANT
        assert "control" in flag.variants

    def test_unregister_flag(self, manager):
        """Test unregistering a flag."""
        manager.register_flag("to_remove")
        result = manager.unregister_flag("to_remove")
        assert result is True
        assert "to_remove" not in manager._flags

    def test_unregister_nonexistent(self, manager):
        """Test unregistering nonexistent flag returns False."""
        result = manager.unregister_flag("nonexistent")
        assert result is False

    def test_get_flag(self, manager):
        """Test getting a flag."""
        manager.register_flag("get_test", enabled=True)
        flag = manager.get_flag("get_test")
        assert flag is not None
        assert flag.name == "get_test"

    def test_get_flag_nonexistent(self, manager):
        """Test getting nonexistent flag returns None."""
        flag = manager.get_flag("nonexistent")
        assert flag is None

    def test_is_enabled_boolean_true(self, manager):
        """Test checking enabled boolean flag."""
        manager.register_flag("enabled_flag", enabled=True)
        assert manager.is_enabled("enabled_flag") is True

    def test_is_enabled_boolean_false(self, manager):
        """Test checking disabled boolean flag."""
        manager.register_flag("disabled_flag", enabled=False)
        assert manager.is_enabled("disabled_flag") is False

    def test_is_enabled_nonexistent(self, manager):
        """Test checking nonexistent flag returns False."""
        result = manager.is_enabled("nonexistent")
        assert result is False

    def test_is_enabled_percentage_disabled(self, manager):
        """Test percentage flag returns False when disabled."""
        manager.register_flag(
            "pct_disabled",
            flag_type=FeatureFlagType.PERCENTAGE,
            enabled=False,
            percentage=100.0,
        )
        assert manager.is_enabled("pct_disabled") is False

    def test_is_enabled_percentage_rollout(self, manager):
        """Test percentage flag with rollout."""
        manager.register_flag(
            "pct_rollout",
            flag_type=FeatureFlagType.PERCENTAGE,
            enabled=True,
            percentage=100.0,
        )
        result = manager.is_enabled("pct_rollout", user_id="user123")
        assert result is True

    def test_is_enabled_variant_warning(self, manager):
        """Test is_enabled warns for variant flags."""
        manager.register_flag(
            "variant_check",
            flag_type=FeatureFlagType.VARIANT,
            enabled=True,
            variants={"a": 50.0, "b": 50.0},
        )
        result = manager.is_enabled("variant_check")
        assert result is True

    def test_get_variant(self, manager):
        """Test getting variant."""
        manager.register_flag(
            "variant_flag",
            flag_type=FeatureFlagType.VARIANT,
            enabled=True,
            variants={"control": 50.0, "treatment": 50.0},
        )
        variant = manager.get_variant("variant_flag", user_id="user1")
        assert variant in ("control", "treatment")

    def test_get_variant_consistent_per_user(self, manager):
        """Test variant is consistent for same user."""
        manager.register_flag(
            "consistent",
            flag_type=FeatureFlagType.VARIANT,
            enabled=True,
            variants={"a": 50.0, "b": 50.0},
        )
        v1 = manager.get_variant("consistent", user_id="same_user")
        v2 = manager.get_variant("consistent", user_id="same_user")
        assert v1 == v2

    def test_get_variant_disabled(self, manager):
        """Test get_variant returns None for disabled flag."""
        manager.register_flag(
            "variant_disabled",
            flag_type=FeatureFlagType.VARIANT,
            enabled=False,
            variants={"a": 50.0, "b": 50.0},
        )
        result = manager.get_variant("variant_disabled")
        assert result is None

    def test_get_variant_nonexistent(self, manager):
        """Test get_variant returns None for nonexistent flag."""
        result = manager.get_variant("nonexistent")
        assert result is None

    def test_enable(self, manager):
        """Test enabling a flag."""
        manager.register_flag("to_enable")
        result = manager.enable("to_enable")
        assert result is True
        assert manager._flags["to_enable"].enabled is True

    def test_enable_nonexistent(self, manager):
        """Test enabling nonexistent flag returns False."""
        result = manager.enable("nonexistent")
        assert result is False

    def test_disable(self, manager):
        """Test disabling a flag."""
        manager.register_flag("to_disable", enabled=True)
        result = manager.disable("to_disable")
        assert result is True
        assert manager._flags["to_disable"].enabled is False

    def test_disable_nonexistent(self, manager):
        """Test disabling nonexistent flag returns False."""
        result = manager.disable("nonexistent")
        assert result is False

    def test_set_percentage(self, manager):
        """Test setting percentage."""
        manager.register_flag("pct", flag_type=FeatureFlagType.PERCENTAGE, percentage=0.0)
        result = manager.set_percentage("pct", 75.0)
        assert result is True
        assert manager._flags["pct"].percentage == 75.0

    def test_set_percentage_clamps_values(self, manager):
        """Test percentage is clamped to 0-100."""
        manager.register_flag("clamp", flag_type=FeatureFlagType.PERCENTAGE, percentage=50.0)

        manager.set_percentage("clamp", 150.0)
        assert manager._flags["clamp"].percentage == 100.0

        manager.set_percentage("clamp", -50.0)
        assert manager._flags["clamp"].percentage == 0.0

    def test_set_percentage_wrong_type(self, manager):
        """Test set_percentage fails for wrong type."""
        manager.register_flag("wrong_type", flag_type=FeatureFlagType.BOOLEAN)
        result = manager.set_percentage("wrong_type", 50.0)
        assert result is False

    def test_set_user_context(self, manager):
        """Test setting user context."""
        manager.set_user_context("user123")
        assert manager._user_id == "user123"

    def test_list_flags(self, manager):
        """Test listing all flags."""
        manager.register_flag("flag1")
        manager.register_flag("flag2")
        flags = manager.list_flags()
        assert len(flags) == 2
        assert "flag1" in flags
        assert "flag2" in flags

    def test_list_flags_returns_copy(self, manager):
        """Test list_flags returns a copy."""
        manager.register_flag("original")
        flags = manager.list_flags()
        flags["new_key"] = None
        assert "new_key" not in manager._flags

    def test_get_all_enabled(self, manager):
        """Test getting all enabled flag names."""
        manager.register_flag("enabled1", enabled=True)
        manager.register_flag("enabled2", enabled=True)
        manager.register_flag("disabled", enabled=False)
        enabled = manager.get_all_enabled()
        assert "enabled1" in enabled
        assert "enabled2" in enabled
        assert "disabled" not in enabled

    def test_export_config(self, manager):
        """Test exporting configuration."""
        manager.register_flag("export_test", enabled=True)
        config = manager.export_config()
        assert "feature_flags" in config
        assert "export_test" in config["feature_flags"]

    def test_save_config(self, manager):
        """Test saving configuration to file."""
        manager.register_flag("save_test", enabled=True)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = manager.save_config(temp_path)
            assert result is True
            with open(temp_path) as f:
                loaded = json.load(f)
            assert "feature_flags" in loaded
        finally:
            os.unlink(temp_path)

    def test_save_config_no_path(self, manager):
        """Test save_config fails without path."""
        result = manager.save_config()
        assert result is False

    def test_load_from_file(self):
        """Test loading flags from JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "feature_flags": {
                        "from_file": {"name": "from_file", "enabled": True, "flag_type": "boolean"}
                    }
                },
                f,
            )
            temp_path = f.name

        try:
            manager = FeatureFlagManager(config_file=temp_path)
            assert "from_file" in manager._flags
        finally:
            os.unlink(temp_path)

    def test_load_from_file_not_found(self):
        """Test loading from nonexistent file."""
        manager = FeatureFlagManager(config_file="/nonexistent/path.json")
        assert len(manager._flags) == 0

    def test_load_from_env(self):
        """Test loading flags from environment."""
        with patch.dict(os.environ, {"FEATURE_FLAG_TEST_ENV": "true"}):
            manager = FeatureFlagManager()
            assert "test_env" in manager._flags
            assert manager._flags["test_env"].enabled is True

    def test_compute_percentage_hash(self, manager):
        """Test percentage hash computation."""
        hash1 = manager._compute_percentage_hash("flag", "user1")
        hash2 = manager._compute_percentage_hash("flag", "user1")
        assert hash1 == hash2

        hash3 = manager._compute_percentage_hash("flag", "user2")
        assert hash1 != hash3

    def test_compute_percentage_hash_no_user(self, manager):
        """Test hash without user ID."""
        hash1 = manager._compute_percentage_hash("flag")
        hash2 = manager._compute_percentage_hash("flag")
        assert hash1 == hash2


class TestGlobalFunctions:
    """Tests for global functions."""

    def setup_method(self):
        """Reset global manager before each test."""
        from services import feature_flags

        feature_flags._default_manager = None

    def test_get_feature_flag_manager_creates(self):
        """Test get creates manager if none exists."""
        manager = get_feature_flag_manager()
        assert isinstance(manager, FeatureFlagManager)

    def test_get_feature_flag_manager_singleton(self):
        """Test get returns same instance."""
        m1 = get_feature_flag_manager()
        m2 = get_feature_flag_manager()
        assert m1 is m2

    def test_set_feature_flag_manager(self):
        """Test setting global manager."""
        new_manager = FeatureFlagManager()
        new_manager.register_flag("set_test", enabled=True)
        set_feature_flag_manager(new_manager)
        assert get_feature_flag_manager() is new_manager

    def test_is_feature_enabled(self):
        """Test is_feature_enabled convenience function."""
        manager = get_feature_flag_manager()
        manager.register_flag("convenience_test", enabled=True)
        assert is_feature_enabled("convenience_test") is True


class TestFeatureFlagDecorator:
    """Tests for feature flag decorators."""

    def setup_method(self):
        """Reset global manager before each test."""
        from services import feature_flags

        feature_flags._default_manager = None

    def test_feature_flag_decorator_enabled(self):
        """Test decorator allows execution when enabled."""
        manager = get_feature_flag_manager()
        manager.register_flag("decorated_enabled", enabled=True)

        @feature_flag("decorated_enabled")
        def decorated_func():
            return "executed"

        result = decorated_func()
        assert result == "executed"

    def test_feature_flag_decorator_disabled(self):
        """Test decorator returns None when disabled."""
        manager = get_feature_flag_manager()
        manager.register_flag("decorated_disabled", enabled=False)

        @feature_flag("decorated_disabled")
        def decorated_func():
            return "executed"

        result = decorated_func()
        assert result is None

    def test_feature_flag_decorator_passes_args(self):
        """Test decorator passes through function arguments."""
        manager = get_feature_flag_manager()
        manager.register_flag("decorated_args", enabled=True)

        @feature_flag("decorated_args")
        def decorated_func(a, b, c=None):
            return a + b

        result = decorated_func(1, 2, c=3)
        assert result == 3

    def test_require_feature_enabled(self):
        """Test require_feature allows when enabled."""
        manager = get_feature_flag_manager()
        manager.register_flag("required_enabled", enabled=True)

        @require_feature("required_enabled")
        def required_func():
            return "executed"

        result = required_func()
        assert result == "executed"

    def test_require_feature_disabled_raises(self):
        """Test require_feature raises when disabled."""
        manager = get_feature_flag_manager()
        manager.register_flag("required_disabled", enabled=False)

        @require_feature("required_disabled")
        def required_func():
            return "executed"

        with pytest.raises(FeatureFlagNotEnabledError):
            required_func()


class TestFeatureFlags:
    """Tests for FeatureFlags constants."""

    def test_all_flags_defined(self):
        """Test all expected flags are defined."""
        assert FeatureFlags.WEBSOCKET_API == "websocket_api"
        assert FeatureFlags.CACHE_ENABLED == "cache_enabled"
        assert FeatureFlags.RATE_LIMITING == "rate_limiting"
        assert FeatureFlags.ADVANCED_ANALYTICS == "advanced_analytics"
        assert FeatureFlags.EXPERIMENTAL_CONVERSION == "experimental_conversion"
        assert FeatureFlags.REAL_TIME_REPORTING == "real_time_reporting"
        assert FeatureFlags.ENHANCED_PARSING == "enhanced_parsing"
        assert FeatureFlags.NEW_CONVERSION_ENGINE == "new_conversion_engine"
        assert FeatureFlags.FAILURE_ANALYSIS == "failure_analysis"


class TestDefaultFlags:
    """Tests for default flags."""

    def test_default_flags_structure(self):
        """Test default flags have correct structure."""
        assert "websocket_api" in DEFAULT_FLAGS
        assert "cache_enabled" in DEFAULT_FLAGS
        assert DEFAULT_FLAGS["websocket_api"]["flag_type"] == "boolean"

    def test_initialize_default_flags(self):
        """Test initializing default flags."""
        manager = initialize_default_flags()
        assert "websocket_api" in manager._flags
        assert "cache_enabled" in manager._flags
        assert manager._flags["websocket_api"].enabled is True

    def test_initialize_existing_manager(self):
        """Test initializing existing manager."""
        existing = FeatureFlagManager()
        existing.register_flag("custom", enabled=True)
        result = initialize_default_flags(existing)
        assert result is existing
        assert "websocket_api" in result._flags
        assert "custom" in result._flags


class TestEdgeCases:
    """Tests for edge cases."""

    def test_get_variant_empty_variants(self):
        """Test get_variant with empty variants dict."""
        manager = FeatureFlagManager()
        manager.register_flag(
            "empty_vars", flag_type=FeatureFlagType.VARIANT, enabled=True, variants={}
        )
        result = manager.get_variant("empty_vars")
        assert result is None

    def test_percentage_hash_different_flags(self):
        """Test hash differs between flag names."""
        manager = FeatureFlagManager()
        hash1 = manager._compute_percentage_hash("flag_a", "user1")
        hash2 = manager._compute_percentage_hash("flag_b", "user1")
        assert hash1 != hash2
