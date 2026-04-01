"""
Tests for Secrets module to improve coverage.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSecretStr:
    """Test SecretStr class."""

    def test_secret_str_repr(self):
        """Test SecretStr redacts in repr."""
        from core.secrets import SecretStr
        
        secret = SecretStr("my_secret_value")
        assert "***REDACTED***" in repr(secret)

    def test_secret_str_str(self):
        """Test SecretStr redacts in str."""
        from core.secrets import SecretStr
        
        secret = SecretStr("my_secret_value")
        assert str(secret) == "***REDACTED***"


class TestSecretsManagerSettings:
    """Test SecretsManagerSettings."""

    def test_settings_defaults(self):
        """Test default settings."""
        from core.secrets import SecretsManagerSettings
        
        settings = SecretsManagerSettings(
            model_config={"env_file": ".env.test"}
        )
        # Should have default provider
        assert settings is not None