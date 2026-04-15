"""
Unit tests for core.startup_validation module.

Covers: placeholder detection, required-secret validation,
CORS checks, and environment-gated fail-fast behavior.
"""

import pytest
from unittest.mock import patch


class TestIsPlaceholder:
    def test_detects_change_this(self):
        from core.startup_validation import _is_placeholder

        assert _is_placeholder("change-this-secret") is True

    def test_detects_your_prefix(self):
        from core.startup_validation import _is_placeholder

        assert _is_placeholder("your-openai-api-key") is True

    def test_detects_changeme(self):
        from core.startup_validation import _is_placeholder

        assert _is_placeholder("changeme") is True

    def test_detects_placeholder_word(self):
        from core.startup_validation import _is_placeholder

        assert _is_placeholder("placeholder-value") is True

    def test_real_value_not_placeholder(self):
        from core.startup_validation import _is_placeholder

        assert _is_placeholder("a3Kx9qZ2LmN8pR4sT6wY1cV5jH0dF7bE") is False

    def test_empty_string_not_placeholder(self):
        from core.startup_validation import _is_placeholder

        assert _is_placeholder("") is False


class TestCheckSecretStrength:
    def test_short_secret_key_flagged(self):
        from core.startup_validation import _check_secret_strength

        issues = _check_secret_strength("SECRET_KEY", "short")
        assert len(issues) == 1
        assert "too short" in issues[0]

    def test_short_jwt_key_flagged(self):
        from core.startup_validation import _check_secret_strength

        issues = _check_secret_strength("JWT_SECRET_KEY", "tooShort12345")
        assert len(issues) == 1

    def test_long_enough_secret_passes(self):
        from core.startup_validation import _check_secret_strength

        issues = _check_secret_strength("SECRET_KEY", "a" * 32)
        assert issues == []

    def test_other_key_not_checked_for_length(self):
        from core.startup_validation import _check_secret_strength

        issues = _check_secret_strength("DB_PASSWORD", "short")
        assert issues == []


class TestValidateSecrets:
    def _base_env(self):
        return {
            "SECRET_KEY": "a3Kx9qZ2LmN8pR4sT6wY1cV5jH0dF7bE12",
            "JWT_SECRET_KEY": "b4Ly0rA3MnO9qS5tU7xZ2dW6kI1eG8cH34",
            "DB_PASSWORD": "securepassword123",
            "DATABASE_URL": "postgresql+asyncpg://postgres:securepassword123@db:5432/modporter",
            "CORS_ORIGINS": "https://modporter.ai,https://www.modporter.ai",
            "ENVIRONMENT": "production",
        }

    def test_passes_with_valid_production_secrets(self):
        from core.startup_validation import validate_secrets

        with patch.dict("os.environ", self._base_env(), clear=False):
            validate_secrets(environment="production")

    def test_fails_in_production_with_missing_secret_key(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env.pop("SECRET_KEY", None)
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="SECRET_KEY"):
                validate_secrets(environment="production")

    def test_fails_in_production_with_placeholder_jwt_secret(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env["JWT_SECRET_KEY"] = "change-this-jwt-secret-production-key"
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
                validate_secrets(environment="production")

    def test_fails_in_production_with_placeholder_secret_key(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env["SECRET_KEY"] = "change-this-super-secret-production-key-123456789"
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="SECRET_KEY"):
                validate_secrets(environment="production")

    def test_warns_but_does_not_raise_in_development(self):
        from core.startup_validation import validate_secrets

        env = {
            "SECRET_KEY": "change-this",
            "CORS_ORIGINS": "http://localhost:3000",
        }
        with patch.dict("os.environ", env, clear=True):
            validate_secrets(environment="development")

    def test_fails_in_production_with_wildcard_cors(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env["CORS_ORIGINS"] = "*"
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="CORS_ORIGINS"):
                validate_secrets(environment="production")

    def test_fails_in_production_with_empty_cors(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env.pop("CORS_ORIGINS", None)
        env.pop("ALLOWED_ORIGINS", None)
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="CORS_ORIGINS"):
                validate_secrets(environment="production")

    def test_staging_also_enforces_secrets(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env["SECRET_KEY"] = "change-this"
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError):
                validate_secrets(environment="staging")

    def test_allowed_origins_fallback_accepted(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env.pop("CORS_ORIGINS", None)
        env["ALLOWED_ORIGINS"] = "https://modporter.ai"
        with patch.dict("os.environ", env, clear=False):
            validate_secrets(environment="production")

    def test_error_message_includes_setup_hint(self):
        from core.startup_validation import validate_secrets

        env = self._base_env()
        env["SECRET_KEY"] = "change-this"
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="fly secrets set"):
                validate_secrets(environment="production")
