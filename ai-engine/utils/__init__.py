# Utils package for ModPorter AI Engine

from .vector_db_client import VectorDBClient
from .feature_flags import (
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

_vector_db_client_instance = None

def get_vector_db_client() -> VectorDBClient:
    """
    Returns a shared instance of the VectorDBClient.
    Initializes it if it doesn't exist yet.
    """
    global _vector_db_client_instance
    if _vector_db_client_instance is None:
        _vector_db_client_instance = VectorDBClient()
    return _vector_db_client_instance

# It might also be useful to expose the class directly if users
# want to create instances with custom configurations.
__all__ = [
    "VectorDBClient",
    "get_vector_db_client",
    "FeatureFlag",
    "FeatureFlagManager",
    "FeatureFlagType",
    "FeatureFlags",
    "FeatureFlagNotEnabledError",
    "get_feature_flag_manager",
    "set_feature_flag_manager",
    "is_feature_enabled",
    "feature_flag",
    "require_feature",
    "initialize_default_flags",
    "DEFAULT_FLAGS",
]