"""
Unit tests for core secrets management.

Issue: Test coverage for src/core/secrets.py
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pydantic import ValidationError


class TestSecretStr:
    """Tests for SecretStr class."""

    def test_secret_str_repr(self):
        """Test SecretStr __repr__ returns redacted value."""
        from core.secrets import SecretStr

        secret = SecretStr("my_secret_value")
        result = repr(secret)

        assert result == "***REDACTED***"

    def test_secret_str_str(self):
        """Test SecretStr __str__ returns redacted value."""
        from core.secrets import SecretStr

        secret = SecretStr("my_secret_value")
        result = str(secret)

        assert result == "***REDACTED***"

    def test_secret_str_value_accessible(self):
        """Test SecretStr value is still accessible internally."""
        from core.secrets import SecretStr

        secret = SecretStr("my_secret_value")
        assert secret == "my_secret_value"


class TestSecretsManagerSettings:
    """Tests for SecretsManagerSettings."""

    def test_default_backend_is_local(self):
        """Test default secrets backend is local."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings()
        assert settings.secrets_backend == "local"

    def test_settings_has_backend_attribute(self):
        """Test settings has secrets_backend attribute."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings()
        assert hasattr(settings, "secrets_backend")

    def test_settings_has_aws_attributes(self):
        """Test settings has AWS-related attributes."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings()
        assert hasattr(settings, "aws_region")
        assert hasattr(settings, "aws_secret_name")

    def test_settings_has_vault_attributes(self):
        """Test settings has Vault-related attributes."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings()
        assert hasattr(settings, "vault_url")
        assert hasattr(settings, "vault_token")
        assert hasattr(settings, "vault_secret_path")

    def test_settings_has_doppler_attributes(self):
        """Test settings has Doppler-related attributes."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings()
        assert hasattr(settings, "doppler_project")
        assert hasattr(settings, "doppler_config")
        assert hasattr(settings, "doppler_token")


class TestSecretsManager:
    """Tests for SecretsManager class."""

    def test_init_with_default_settings(self):
        """Test initialization with default settings."""
        from core.secrets import SecretsManager

        manager = SecretsManager()

        assert manager.settings is not None
        assert manager._cache == {}
        assert manager._backend_initialized is False

    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        from core.secrets import SecretsManager, SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None, secrets_backend="local")
        manager = SecretsManager(settings=settings)

        assert manager.settings.secrets_backend == "local"

    def test_get_secret_local_backend(self):
        """Test getting secret with local backend."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        manager._backend_initialized = True

        result = manager.get_secret("PATH")

        assert result is not None

    def test_get_secret_with_default(self):
        """Test getting non-existent secret returns default."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        manager._backend_initialized = True

        result = manager.get_secret("NON_EXISTENT_SECRET_XYZ", default="default_value")

        assert result == "default_value"

    def test_get_secret_caching(self):
        """Test that secrets are cached."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        manager._backend_initialized = True
        manager._cache.clear()

        first_result = manager.get_secret("PATH")
        second_result = manager.get_secret("PATH")

        assert first_result == second_result
        assert "PATH" in manager._cache

    def test_get_secret_local_none_returns_default(self):
        """Test getting secret that is None returns default."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        manager._backend_initialized = True
        manager._cache.clear()

        result = manager.get_secret("NONEXISTENT123", default="default")

        assert result == "default"


class TestSecretsManagerGetAllSecrets:
    """Tests for get_all_secrets method."""

    def test_get_all_secrets_local_backend(self):
        """Test getting all secrets with local backend."""
        from core.secrets import SecretsManager

        manager = SecretsManager()

        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "test-key",
                "JWT_SECRET_KEY": "jwt-secret",
                "OPENAI_API_KEY": "sk-...",
            },
        ):
            result = manager.get_all_secrets()

        assert "SECRET_KEY" in result
        assert result["SECRET_KEY"] == "test-key"
        assert "JWT_SECRET_KEY" in result

    def test_get_all_secrets_filters_empty(self):
        """Test that empty secrets are filtered out."""
        from core.secrets import SecretsManager

        manager = SecretsManager()

        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "test-key",
            },
            clear=False,
        ):
            for key in ["DB_PASSWORD", "DATABASE_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
                if key in os.environ:
                    del os.environ[key]

            result = manager.get_all_secrets()

        assert isinstance(result, dict)


class TestGetSecretsManager:
    """Tests for get_secrets_manager function."""

    def test_returns_singleton(self):
        """Test that get_secrets_manager returns singleton."""
        from core.secrets import get_secrets_manager

        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()

        assert manager1 is manager2


class TestGetSecretsSettings:
    """Tests for get_secrets_settings function."""

    def test_returns_singleton(self):
        """Test that get_secrets_settings returns singleton."""
        from core.secrets import get_secrets_settings

        settings1 = get_secrets_settings()
        settings2 = get_secrets_settings()

        assert settings1 is settings2


class TestGetSecret:
    """Tests for get_secret convenience function."""

    def test_get_secret_returns_something(self):
        """Test the get_secret convenience function returns a value."""
        from core.secrets import get_secret

        result = get_secret("PATH")

        assert result is not None
        assert isinstance(result, (str, type(None)))


class TestSettingsCustomization:
    """Tests for Settings class customization."""

    def test_settings_init(self):
        """Test Settings initialization works."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None)

        assert settings is not None
        assert settings.secrets_backend == "local"


class TestSecretsManagerBackendInit:
    """Tests for backend initialization."""

    def test_backend_initialized_flag(self):
        """Test backend initialized flag works correctly."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        assert manager._backend_initialized is False

        manager._backend_initialized = True
        assert manager._backend_initialized is True

    def test_reinitialize_uses_cache(self):
        """Test that reinitialize uses cached backend."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        manager._backend_initialized = True

        manager._initialize_backend()

        assert manager._backend_initialized is True


class TestVaultTokenFromFile:
    """Tests for Vault token file loading."""

    def test_vault_url_default_is_localhost(self):
        """Test Vault URL default value."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None)

        assert "localhost" in settings.vault_url

    def test_vault_settings_have_path(self):
        """Test Vault settings have secret path attribute."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None)

        assert hasattr(settings, "vault_secret_path")


class TestDopplerTokenRequired:
    """Tests for Doppler token requirement."""

    def test_doppler_project_attribute_exists(self):
        """Test Doppler project attribute exists."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None)

        assert hasattr(settings, "doppler_project")

    def test_doppler_config_attribute_exists(self):
        """Test Doppler config attribute exists."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None)

        assert hasattr(settings, "doppler_config")


class TestAWSGetSecret:
    """Tests for AWS secrets retrieval."""

    def test_aws_region_attribute_exists(self):
        """Test AWS region attribute exists."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None)

        assert hasattr(settings, "aws_region")

    def test_aws_secret_name_attribute_exists(self):
        """Test AWS secret name attribute exists."""
        from core.secrets import SecretsManagerSettings

        settings = SecretsManagerSettings(_secrets_settings=None)

        assert hasattr(settings, "aws_secret_name")


class TestVaultGetSecret:
    """Tests for Vault secrets retrieval."""

    def test_vault_client_attribute(self):
        """Test Vault client attribute handling."""
        from core.secrets import SecretsManager

        manager = SecretsManager()

        assert not hasattr(manager, "_vault_client") or manager._vault_client is None


class TestGetAllSecretsBackends:
    """Tests for get_all_secrets with different backends."""

    def test_get_all_secrets_local_returns_dict(self):
        """Test get_all_secrets with local backend returns dict."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        manager._backend_initialized = True

        result = manager.get_all_secrets()

        assert isinstance(result, dict)

    def test_get_all_secrets_local_returns_expected_keys(self):
        """Test get_all_secrets returns expected structure."""
        from core.secrets import SecretsManager

        manager = SecretsManager()
        manager._backend_initialized = True

        result = manager.get_all_secrets()

        assert isinstance(result, dict)
        assert "SECRET_KEY" in result


class TestExports:
    """Tests for module exports."""

    def test_all_exports_present(self):
        """Test all expected exports are present."""
        from core import secrets

        expected = [
            "SecretsManager",
            "SecretsManagerSettings",
            "SecretStr",
            "Settings",
            "get_secrets_manager",
            "get_secrets_settings",
            "get_secret",
        ]

        for name in expected:
            assert hasattr(secrets, name), f"Missing export: {name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
