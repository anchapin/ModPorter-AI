"""
Core module for ModPorter-AI backend.

This module contains core functionality including:
- Secrets management
"""

from .secrets import (
    SecretsManager,
    SecretsManagerSettings,
    SecretStr,
    Settings,
    get_secrets_manager,
    get_secrets_settings,
    get_secret,
)

__all__ = [
    "SecretsManager",
    "SecretsManagerSettings",
    "SecretStr",
    "Settings",
    "get_secrets_manager",
    "get_secrets_settings",
    "get_secret",
]
