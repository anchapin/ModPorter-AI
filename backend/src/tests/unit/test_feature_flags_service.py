"""
Unit tests for feature_flags service.

Tests FeatureFlag, FeatureFlagManager, and helper functions.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from services.feature_flags import (
    FeatureFlag,
    FeatureFlagType,
    FeatureFlagManager,
    get_feature_flag_manager,
    set_feature_flag_manager,
    is_feature_enabled,
    feature_flag,
    require_feature,
    FeatureFlagNotEnabledError,
)


@pytest.fixture
def clean_manager():
    """Reset manager before and after test."""
    original = get_feature_flag_manager()
    set_feature_flag_manager(FeatureFlagManager())
    yield
    set_feature_flag_manager(original)


class TestFeatureFlagType:
    def test_feature_flag_type_values(self):
        assert FeatureFlagType.BOOLEAN.value == "boolean"
        assert FeatureFlagType.PERCENTAGE.value == "percentage"
        assert FeatureFlagType.VARIANT.value == "variant"


class TestFeatureFlag:
    def test_feature_flag_init_boolean(self):
        flag = FeatureFlag(
            name="test_flag", flag_type=FeatureFlagType.BOOLEAN, default_value=True, enabled=True
        )
        assert flag.name == "test_flag"
        assert flag.flag_type == FeatureFlagType.BOOLEAN
        assert flag.default_value is True

    def test_feature_flag_init_percentage(self):
        flag = FeatureFlag(name="rollout", flag_type=FeatureFlagType.PERCENTAGE, percentage=50.0)
        assert flag.percentage == 50.0

    def test_feature_flag_init_variant(self):
        variants = {"control": 0.5, "treatment": 0.5}
        flag = FeatureFlag(name="variant", flag_type=FeatureFlagType.VARIANT, variants=variants)
        assert flag.variants == variants

    def test_to_dict(self):
        flag = FeatureFlag(name="test", enabled=True)
        data = flag.to_dict()
        assert data["name"] == "test"
        assert data["enabled"] is True

    def test_from_dict(self):
        data = {"name": "test", "flag_type": "boolean", "enabled": True}
        flag = FeatureFlag.from_dict(data)
        assert flag.name == "test"
        assert flag.flag_type == FeatureFlagType.BOOLEAN


class TestFeatureFlagManager:
    @pytest.fixture
    def manager(self):
        return FeatureFlagManager()

    def test_manager_init(self, manager):
        assert isinstance(manager._flags, dict)

    def test_register_flag(self, manager):
        # Use name string, not FeatureFlag object
        manager.register_flag(name="new_feature", enabled=True)
        assert "new_feature" in manager._flags

    def test_get_flag(self, manager):
        manager.register_flag(name="test", enabled=True)
        assert manager.get_flag("test") is not None
        assert manager.get_flag("test").name == "test"

    def test_get_flag_not_found(self, manager):
        assert manager.get_flag("nonexistent") is None

    def test_is_enabled(self, manager):
        manager.register_flag(name="test", enabled=True)
        assert manager.is_enabled("test") is True

    def test_enable(self, manager):
        manager.register_flag(name="test", enabled=False)
        manager.enable("test")
        assert manager.is_enabled("test") is True

    def test_disable(self, manager):
        manager.register_flag(name="test", enabled=True)
        manager.disable("test")
        assert manager.is_enabled("test") is False

    def test_unregister_flag(self, manager):
        manager.register_flag(name="test")
        manager.unregister_flag("test")
        assert "test" not in manager._flags

    def test_list_flags(self, manager):
        manager.register_flag(name="flag1")
        manager.register_flag(name="flag2")
        flags = manager.list_flags()
        assert len(flags) == 2


class TestIsFeatureEnabled:
    def test_is_feature_enabled_with_manager(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(name="test_feature", enabled=True)
        assert is_feature_enabled("test_feature") is True

    def test_is_feature_enabled_not_found(self, clean_manager):
        assert is_feature_enabled("nonexistent") is False

    def test_is_feature_enabled_disabled(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(name="off_feature", enabled=False)
        assert is_feature_enabled("off_feature") is False


class TestFeatureFlagDecorator:
    def test_decorator_enabled(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(name="decorator_test", enabled=True)

        @feature_flag("decorator_test")
        def test_func():
            return "executed"

        assert test_func() == "executed"

    def test_decorator_disabled(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(name="disabled_decorator", enabled=False)

        @feature_flag("disabled_decorator")
        def test_func():
            return "executed"

        assert test_func() is None


class TestRequireFeature:
    def test_require_feature_raises_when_disabled(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(name="required_feature", enabled=False)

        @require_feature("required_feature")
        def test_func():
            return "executed"

        with pytest.raises(FeatureFlagNotEnabledError):
            test_func()

    def test_require_feature_passes_when_enabled(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(name="enabled_required", enabled=True)

        @require_feature("enabled_required")
        def test_func():
            return "executed"

        assert test_func() == "executed"


class TestPercentageFlags:
    def test_percentage_rollout_100(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(
            name="rollout", flag_type=FeatureFlagType.PERCENTAGE, percentage=100.0, enabled=True
        )
        result = manager.is_enabled("rollout", user_id="user1")
        assert result is True

    def test_percentage_rollout_0(self, clean_manager):
        manager = get_feature_flag_manager()
        manager.register_flag(
            name="rollout", flag_type=FeatureFlagType.PERCENTAGE, percentage=0.0, enabled=True
        )
        result = manager.is_enabled("rollout", user_id="user1")
        assert result is False


class TestLoadFromEnv:
    def test_load_from_env_var(self, clean_manager):
        with patch.dict(os.environ, {"FEATURE_FLAG_TEST_FROM_ENV": "true"}):
            m = FeatureFlagManager()
            assert m.is_enabled("test_from_env") is True
