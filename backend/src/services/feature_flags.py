"""
Feature Flag Infrastructure for dynamic feature toggling.

This module provides a feature flag system that allows dynamic enabling/disabling
of features at runtime. Supports boolean flags, percentage rollouts, and
environment-based configuration.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Callable
from enum import Enum
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class FeatureFlagType(str, Enum):
    """Types of feature flags supported."""

    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    VARIANT = "variant"


class FeatureFlag:
    """
    Represents a single feature flag with its configuration.

    Attributes:
        name: Unique identifier for the feature flag
        flag_type: Type of the flag (BOOLEAN, PERCENTAGE, or VARIANT)
        default_value: Default value when flag is not set
        description: Human-readable description of the flag
        enabled: Whether the flag is currently enabled
        percentage: Percentage value for rollout flags (0-100)
        variants: Dictionary of variant name to weight for variant flags
    """

    def __init__(
        self,
        name: str,
        flag_type: FeatureFlagType = FeatureFlagType.BOOLEAN,
        default_value: Any = False,
        description: str = "",
        enabled: bool = False,
        percentage: float = 0.0,
        variants: Optional[Dict[str, float]] = None,
    ):
        self.name = name
        self.flag_type = flag_type
        self.default_value = default_value
        self.description = description
        self.enabled = enabled
        self.percentage = percentage
        self.variants = variants or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert flag to dictionary representation."""
        return {
            "name": self.name,
            "flag_type": (
                self.flag_type.value if isinstance(self.flag_type, Enum) else self.flag_type
            ),
            "default_value": self.default_value,
            "description": self.description,
            "enabled": self.enabled,
            "percentage": self.percentage,
            "variants": self.variants,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureFlag":
        """Create flag from dictionary representation."""
        flag_type = data.get("flag_type", "boolean")
        if isinstance(flag_type, str):
            flag_type = FeatureFlagType(flag_type)
        return cls(
            name=data["name"],
            flag_type=flag_type,
            default_value=data.get("default_value", False),
            description=data.get("description", ""),
            enabled=data.get("enabled", False),
            percentage=data.get("percentage", 0.0),
            variants=data.get("variants", {}),
        )

    def __repr__(self) -> str:
        return f"FeatureFlag(name={self.name}, enabled={self.enabled}, type={self.flag_type.value if isinstance(self.flag_type, Enum) else self.flag_type})"


class FeatureFlagManager:
    """
    Central manager for feature flags.

    Provides methods to register, check, enable, and disable feature flags.
    Supports loading configuration from environment variables and JSON files.

    Example:
        >>> manager = FeatureFlagManager()
        >>> manager.register_flag("new_dashboard", description="New dashboard UI")
        >>> if manager.is_enabled("new_dashboard"):
        ...     # Show new dashboard
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the feature flag manager.

        Args:
            config_file: Optional path to JSON configuration file
        """
        self._flags: Dict[str, FeatureFlag] = {}
        self._config_file = config_file
        self._user_id: Optional[str] = None

        # Load initial configuration
        self._load_from_env()
        if config_file:
            self._load_from_file(config_file)

    def _load_from_env(self) -> None:
        """Load feature flags from environment variables."""
        prefix = "FEATURE_FLAG_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                flag_name = key[len(prefix) :].lower()
                is_enabled = value.lower() in ("true", "1", "yes", "on")
                self.register_flag(
                    name=flag_name,
                    flag_type=FeatureFlagType.BOOLEAN,
                    enabled=is_enabled,
                    description=f"Loaded from environment variable {key}",
                )
                logger.debug(f"Loaded feature flag '{flag_name}' from environment: {is_enabled}")

        legacy_flags = {
            "FEATURE_USER_ACCOUNTS": "user_accounts",
            "FEATURE_PREMIUM_FEATURES": "premium_features",
            "FEATURE_API_KEYS": "api_keys",
        }
        for env_var, flag_name in legacy_flags.items():
            if env_var in os.environ:
                is_enabled = os.environ[env_var].lower() in ("true", "1", "yes", "on")
                if flag_name not in self._flags:
                    self.register_flag(
                        name=flag_name,
                        flag_type=FeatureFlagType.BOOLEAN,
                        enabled=is_enabled,
                        description=f"Loaded from {env_var}",
                    )
                    logger.debug(f"Loaded feature flag '{flag_name}' from {env_var}: {is_enabled}")

    def _load_from_file(self, config_file: str) -> None:
        """Load feature flags from a JSON configuration file."""
        try:
            with open(config_file, "r") as f:
                config = json.load(f)

            flags_data = config.get("feature_flags", {})
            for flag_name, flag_data in flags_data.items():
                flag_data["name"] = flag_name
                flag = FeatureFlag.from_dict(flag_data)
                self._flags[flag_name] = flag
                logger.debug(f"Loaded feature flag '{flag_name}' from config file")

        except FileNotFoundError:
            logger.warning(f"Feature flag config file not found: {config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing feature flag config file: {e}")

    def _compute_percentage_hash(self, flag_name: str, user_id: Optional[str] = None) -> float:
        """
        Compute a deterministic hash for percentage-based flags.

        Uses the flag name and optional user ID to create a consistent
        hash that stays stable across requests for the same user.
        """
        if user_id:
            hash_input = f"{flag_name}:{user_id}"
        else:
            hash_input = flag_name

        hash_bytes = hashlib.md5(hash_input.encode()).digest()
        return (int.from_bytes(hash_bytes[:2], "big") % 10000) / 100

    def register_flag(
        self,
        name: str,
        flag_type: FeatureFlagType = FeatureFlagType.BOOLEAN,
        default_value: Any = False,
        description: str = "",
        enabled: bool = False,
        percentage: float = 0.0,
        variants: Optional[Dict[str, float]] = None,
    ) -> FeatureFlag:
        """
        Register a new feature flag.

        Args:
            name: Unique identifier for the flag
            flag_type: Type of the flag
            default_value: Default value when not enabled
            description: Human-readable description
            enabled: Initial enabled state
            percentage: For PERCENTAGE type flags, the rollout percentage (0-100)
            variants: For VARIANT type flags, mapping of variant names to weights

        Returns:
            The created FeatureFlag instance
        """
        if name in self._flags:
            logger.warning(f"Feature flag '{name}' already exists. Updating...")

        flag = FeatureFlag(
            name=name,
            flag_type=flag_type,
            default_value=default_value,
            description=description,
            enabled=enabled,
            percentage=percentage,
            variants=variants,
        )
        self._flags[name] = flag
        logger.debug(f"Registered feature flag: {flag}")
        return flag

    def unregister_flag(self, name: str) -> bool:
        """
        Remove a feature flag.

        Args:
            name: Name of the flag to remove

        Returns:
            True if flag was removed, False if it didn't exist
        """
        if name in self._flags:
            del self._flags[name]
            logger.debug(f"Unregistered feature flag: {name}")
            return True
        return False

    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """
        Get a feature flag by name.

        Args:
            name: Name of the flag to retrieve

        Returns:
            The FeatureFlag instance or None if not found
        """
        return self._flags.get(name)

    def is_enabled(self, name: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled.

        For BOOLEAN flags, returns the enabled state.
        For PERCENTAGE flags, returns True if the user falls within the percentage.
        For VARIANT flags, use get_variant() instead.

        Args:
            name: Name of the flag to check
            user_id: Optional user ID for percentage-based rollouts

        Returns:
            True if the feature is enabled for the user
        """
        flag = self._flags.get(name)

        if flag is None:
            logger.warning(f"Feature flag '{name}' not found. Returning default: False")
            return False

        if flag.flag_type == FeatureFlagType.BOOLEAN:
            return flag.enabled

        elif flag.flag_type == FeatureFlagType.PERCENTAGE:
            if not flag.enabled:
                return False
            rollout_percentage = flag.percentage
            hash_value = self._compute_percentage_hash(name, user_id or self._user_id)
            return hash_value < rollout_percentage

        elif flag.flag_type == FeatureFlagType.VARIANT:
            logger.warning(f"Use get_variant() for VARIANT type flags, not is_enabled()")
            return flag.enabled

        return flag.enabled

    def get_variant(self, name: str, user_id: Optional[str] = None) -> Optional[str]:
        """
        Get the variant for a VARIANT type feature flag.

        Args:
            name: Name of the flag
            user_id: Optional user ID for consistent variant assignment

        Returns:
            The variant name that's active for this user, or None if not enabled
        """
        flag = self._flags.get(name)

        if flag is None or flag.flag_type != FeatureFlagType.VARIANT:
            return None

        if not flag.enabled:
            return None

        # Compute deterministic variant based on user
        hash_value = self._compute_percentage_hash(name, user_id or self._user_id)

        # Map hash to variant based on weights
        cumulative = 0.0
        for variant_name, weight in flag.variants.items():
            cumulative += weight
            if hash_value < cumulative:
                return variant_name

        # Return last variant if hash exceeds all weights
        return list(flag.variants.keys())[-1] if flag.variants else None

    def enable(self, name: str) -> bool:
        """
        Enable a feature flag.

        Args:
            name: Name of the flag to enable

        Returns:
            True if flag was enabled, False if not found
        """
        flag = self._flags.get(name)
        if flag:
            flag.enabled = True
            logger.info(f"Enabled feature flag: {name}")
            return True
        logger.warning(f"Cannot enable flag '{name}': not found")
        return False

    def disable(self, name: str) -> bool:
        """
        Disable a feature flag.

        Args:
            name: Name of the flag to disable

        Returns:
            True if flag was disabled, False if not found
        """
        flag = self._flags.get(name)
        if flag:
            flag.enabled = False
            logger.info(f"Disabled feature flag: {name}")
            return True
        logger.warning(f"Cannot disable flag '{name}': not found")
        return False

    def set_percentage(self, name: str, percentage: float) -> bool:
        """
        Set the rollout percentage for a PERCENTAGE type flag.

        Args:
            name: Name of the flag
            percentage: Rollout percentage (0-100)

        Returns:
            True if percentage was set, False if flag not found or wrong type
        """
        flag = self._flags.get(name)
        if flag and flag.flag_type == FeatureFlagType.PERCENTAGE:
            flag.percentage = max(0.0, min(100.0, percentage))
            logger.info(f"Set feature flag '{name}' percentage to {flag.percentage}%")
            return True
        logger.warning(f"Cannot set percentage for flag '{name}': not found or wrong type")
        return False

    def set_user_context(self, user_id: Optional[str]) -> None:
        """
        Set the user context for percentage-based rollouts.

        Args:
            user_id: The user ID to use for consistent rollout decisions
        """
        self._user_id = user_id

    def list_flags(self) -> Dict[str, FeatureFlag]:
        """
        Get all registered feature flags.

        Returns:
            Dictionary mapping flag names to FeatureFlag instances
        """
        return self._flags.copy()

    def get_all_enabled(self) -> list[str]:
        """
        Get a list of all enabled feature flag names.

        Returns:
            List of enabled flag names
        """
        return [name for name, flag in self._flags.items() if flag.enabled]

    def export_config(self) -> Dict[str, Any]:
        """
        Export all flags as a configuration dictionary.

        Returns:
            Dictionary containing all feature flag configurations
        """
        return {"feature_flags": {name: flag.to_dict() for name, flag in self._flags.items()}}

    def save_config(self, config_file: Optional[str] = None) -> bool:
        """
        Save current flag configuration to a JSON file.

        Args:
            config_file: Path to save to (uses instance config_file if not provided)

        Returns:
            True if configuration was saved successfully
        """
        file_path = config_file or self._config_file
        if not file_path:
            logger.error("No config file path specified")
            return False

        try:
            with open(file_path, "w") as f:
                json.dump(self.export_config(), f, indent=2)
            logger.info(f"Saved feature flag configuration to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving feature flag config: {e}")
            return False


# Global instance for easy access
_default_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """
    Get the global feature flag manager instance.

    Creates a new instance if one doesn't exist.

    Returns:
        The global FeatureFlagManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = FeatureFlagManager()
        initialize_default_flags(_default_manager)
    return _default_manager


def set_feature_flag_manager(manager: FeatureFlagManager) -> None:
    """
    Set the global feature flag manager instance.

    Args:
        manager: The FeatureFlagManager instance to use globally
    """
    global _default_manager
    _default_manager = manager


def is_feature_enabled(name: str, user_id: Optional[str] = None) -> bool:
    """
    Convenience function to check if a feature is enabled.

    Args:
        name: Name of the feature flag
        user_id: Optional user ID for percentage rollouts

    Returns:
        True if the feature is enabled
    """
    return get_feature_flag_manager().is_enabled(name, user_id)


def feature_flag(name: str, default: bool = False):
    """
    Decorator to conditionally enable functionality based on a feature flag.

    Args:
        name: Name of the feature flag to check
        default: Default value if flag is not found

    Example:
        @feature_flag("new_processing_engine")
        def process_data(data):
            # This only runs if the flag is enabled
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_feature_enabled(name):
                return func(*args, **kwargs)
            else:
                logger.debug(f"Feature '{name}' is disabled, skipping {func.__name__}")
                return None

        return wrapper

    return decorator


def require_feature(name: str):
    """
    Decorator that raises an exception if a feature flag is not enabled.

    Args:
        name: Name of the required feature flag

    Example:
        @require_feature("advanced_analytics")
        def get_analytics():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_feature_enabled(name):
                raise FeatureFlagNotEnabledError(f"Feature '{name}' is not enabled")
            return func(*args, **kwargs)

        return wrapper

    return decorator


class FeatureFlagNotEnabledError(Exception):
    """Exception raised when a required feature flag is not enabled."""

    pass


# Predefined feature flags for common use cases
class FeatureFlags:
    """Predefined feature flag names for the application."""

    # Backend flags
    WEBSOCKET_API = "websocket_api"
    CACHE_ENABLED = "cache_enabled"
    RATE_LIMITING = "rate_limiting"
    ADVANCED_ANALYTICS = "advanced_analytics"
    EXPERIMENTAL_CONVERSION = "experimental_conversion"
    REAL_TIME_REPORTING = "real_time_reporting"

    # Conversion service flags
    ENHANCED_PARSING = "enhanced_parsing"
    NEW_CONVERSION_ENGINE = "new_conversion_engine"
    FAILURE_ANALYSIS = "failure_analysis"


# Default configuration with common feature flags
DEFAULT_FLAGS = {
    "websocket_api": {
        "flag_type": "boolean",
        "enabled": True,
        "description": "Enable WebSocket API for real-time updates",
    },
    "cache_enabled": {
        "flag_type": "boolean",
        "enabled": True,
        "description": "Enable response caching",
    },
    "rate_limiting": {
        "flag_type": "boolean",
        "enabled": True,
        "description": "Enable API rate limiting",
    },
    "advanced_analytics": {
        "flag_type": "boolean",
        "enabled": False,
        "description": "Enable advanced analytics features",
    },
    "experimental_conversion": {
        "flag_type": "percentage",
        "enabled": True,
        "percentage": 10.0,
        "description": "Gradual rollout of experimental conversion engine",
    },
    "real_time_reporting": {
        "flag_type": "boolean",
        "enabled": False,
        "description": "Enable real-time reporting features",
    },
    "enhanced_parsing": {
        "flag_type": "boolean",
        "enabled": True,
        "description": "Enable enhanced modpack parsing",
    },
    "failure_analysis": {
        "flag_type": "percentage",
        "enabled": True,
        "percentage": 5.0,
        "description": "Gradual rollout of failure analysis features",
    },
    "user_accounts": {
        "flag_type": "boolean",
        "enabled": False,
        "description": "Enable user registration and login (FEATURE_USER_ACCOUNTS)",
    },
    "premium_features": {
        "flag_type": "boolean",
        "enabled": False,
        "description": "Enable premium features including billing (FEATURE_PREMIUM_FEATURES)",
    },
    "api_keys": {
        "flag_type": "boolean",
        "enabled": False,
        "description": "Enable API key generation and management (FEATURE_API_KEYS)",
    },
    "byok_enabled": {
        "flag_type": "boolean",
        "enabled": False,
        "description": "Enable BYOK (Bring Your Own Key) functionality for users to supply their own LLM API keys",
    },
    "payg_credits": {
        "flag_type": "boolean",
        "enabled": False,
        "description": "Enable PAYG credit pack purchases",
    },
}


def initialize_default_flags(
    manager: Optional[FeatureFlagManager] = None,
) -> FeatureFlagManager:
    """
    Initialize the feature flag manager with default flags.

    Args:
        manager: Optional existing manager to initialize

    Returns:
        The initialized FeatureFlagManager
    """
    if manager is None:
        manager = get_feature_flag_manager()

    for flag_name, flag_config in DEFAULT_FLAGS.items():
        flag_type = flag_config.get("flag_type", "boolean")
        if isinstance(flag_type, str):
            flag_type = FeatureFlagType(flag_type)
        manager.register_flag(
            name=flag_name,
            flag_type=flag_type,
            enabled=flag_config.get("enabled", False),
            percentage=flag_config.get("percentage", 0.0),
            description=flag_config.get("description", ""),
        )

    return manager
