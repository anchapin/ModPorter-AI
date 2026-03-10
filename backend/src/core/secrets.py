"""
Secrets management module for ModPorter-AI.

This module provides a unified secrets management solution using pydantic-settings,
with support for multiple backends:
- AWS Secrets Manager
- HashiCorp Vault
- Doppler
- Local .env files (default)

Based on issue #701 requirements for secrets management.
"""

from typing import Optional, Dict, Any, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import json
import logging

logger = logging.getLogger(__name__)


class SecretStr(str):
    """
    A string type that marks values as sensitive.
    Values will be redacted in logs and console output.
    """

    def __repr__(self) -> str:
        return "***REDACTED***"

    def __str__(self) -> str:
        return "***REDACTED***"


class SecretsManagerSettings(BaseSettings):
    """
    Settings for secrets management configuration.

    Supports multiple backends via SECRETS_BACKEND env var:
    - "aws": AWS Secrets Manager
    - "vault": HashiCorp Vault
    - "doppler": Doppler
    - "local": Local .env files (default)
    """

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
        secrets_dir=os.getenv("SECRETS_DIR", None),
    )

    # Secrets backend configuration
    secrets_backend: Literal["aws", "vault", "doppler", "local"] = Field(
        default="local",
        alias="SECRETS_BACKEND",
        description="Secrets management backend to use",
    )

    # AWS Secrets Manager settings
    aws_region: str = Field(
        default="us-west-2",
        alias="AWS_REGION",
        description="AWS region for Secrets Manager",
    )
    aws_secret_name: str = Field(
        default="modporter/production",
        alias="AWS_SECRET_NAME",
        description="AWS Secrets Manager secret name",
    )

    # HashiCorp Vault settings
    vault_url: str = Field(
        default="http://localhost:8200",
        alias="VAULT_URL",
        description="HashiCorp Vault URL",
    )
    vault_token: Optional[str] = Field(
        default=None,
        alias="VAULT_TOKEN",
        description="HashiCorp Vault token",
    )
    vault_secret_path: str = Field(
        default="secret/data/modporter",
        alias="VAULT_SECRET_PATH",
        description="Vault secret path",
    )

    # Doppler settings
    doppler_project: str = Field(
        default="modporter-ai",
        alias="DOPPLER_PROJECT",
        description="Doppler project name",
    )
    doppler_config: str = Field(
        default="prod",
        alias="DOPPLER_CONFIG",
        description="Doppler config (prod, dev, etc.)",
    )
    doppler_token: Optional[str] = Field(
        default=None,
        alias="DOPPLER_TOKEN",
        description="Doppler service token",
    )


# Singleton instance for secrets settings
_secrets_settings: Optional[SecretsManagerSettings] = None


def get_secrets_settings() -> SecretsManagerSettings:
    """Get or create the secrets manager settings singleton."""
    global _secrets_settings
    if _secrets_settings is None:
        _secrets_settings = SecretsManagerSettings()
    return _secrets_settings


class SecretsManager:
    """
    Unified secrets manager that supports multiple backends.

    Usage:
        manager = SecretsManager()
        secret = manager.get_secret("DATABASE_URL")
    """

    def __init__(self, settings: Optional[SecretsManagerSettings] = None):
        self.settings = settings or get_secrets_settings()
        self._cache: Dict[str, Any] = {}
        self._backend_initialized = False

    def _initialize_backend(self) -> None:
        """Initialize the secrets backend."""
        if self._backend_initialized:
            return

        backend = self.settings.secrets_backend
        logger.info(f"Initializing secrets backend: {backend}")

        if backend == "aws":
            self._init_aws()
        elif backend == "vault":
            self._init_vault()
        elif backend == "doppler":
            self._init_doppler()
        # local backend uses .env files, no initialization needed

        self._backend_initialized = True

    def _init_aws(self) -> None:
        """Initialize AWS Secrets Manager backend."""
        try:
            import boto3

            self._aws_client = boto3.client(
                "secretsmanager",
                region_name=self.settings.aws_region,
            )
            logger.info("AWS Secrets Manager backend initialized")
        except ImportError:
            logger.warning("boto3 not installed, falling back to local secrets")
            self.settings.secrets_backend = "local"
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager: {e}")
            raise

    def _init_vault(self) -> None:
        """Initialize HashiCorp Vault backend."""
        if not self.settings.vault_token:
            # Try to get token from VAULT_TOKEN env var or file
            vault_token_file = os.getenv("VAULT_TOKEN_FILE", "/run/secrets/vault_token")
            if os.path.exists(vault_token_file):
                with open(vault_token_file, "r") as f:
                    self.settings.vault_token = f.read().strip()

        if not self.settings.vault_token:
            raise ValueError("Vault token is required. Set VAULT_TOKEN environment variable.")

        try:
            import hvac

            self._vault_client = hvac.Client(
                url=self.settings.vault_url,
                token=self.settings.vault_token,
            )
            logger.info("HashiCorp Vault backend initialized")
        except ImportError:
            logger.warning("hvac not installed, falling back to local secrets")
            self.settings.secrets_backend = "local"
        except Exception as e:
            logger.error(f"Failed to initialize HashiCorp Vault: {e}")
            raise

    def _init_doppler(self) -> None:
        """Initialize Doppler backend."""
        if not self.settings.doppler_token:
            raise ValueError("Doppler token is required. Set DOPPLER_TOKEN environment variable.")

        try:
            import requests

            self._doppler_headers = {
                "Authorization": f"Bearer {self.settings.doppler_token}",
            }
            logger.info("Doppler backend initialized")
        except ImportError:
            logger.warning("requests not installed, falling back to local secrets")
            self.settings.secrets_backend = "local"
        except Exception as e:
            logger.error(f"Failed to initialize Doppler: {e}")
            raise

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value from the configured backend.

        Args:
            key: The secret key name (e.g., "DATABASE_URL")
            default: Default value if secret not found

        Returns:
            The secret value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Initialize backend if needed
        self._initialize_backend()

        backend = self.settings.secrets_backend
        value = None

        try:
            if backend == "aws":
                value = self._get_aws_secret(key)
            elif backend == "vault":
                value = self._get_vault_secret(key)
            elif backend == "doppler":
                value = self._get_doppler_secret(key)
            else:  # local
                value = os.getenv(key, default)

            # Cache the value
            if value is not None:
                self._cache[key] = value

            return value if value is not None else default

        except Exception as e:
            logger.error(f"Error retrieving secret {key}: {e}")
            return default

    def _get_aws_secret(self, key: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            response = self._aws_client.get_secret_value(SecretId=self.settings.aws_secret_name)
            secret_dict = json.loads(response["SecretString"])
            return secret_dict.get(key)
        except Exception as e:
            logger.error(f"AWS Secrets Manager error for key {key}: {e}")
            return None

    def _get_vault_secret(self, key: str) -> Optional[str]:
        """Get secret from HashiCorp Vault."""
        try:
            response = self._vault_client.secrets.kv.v2.read_secret_version(
                path=self.settings.vault_secret_path
            )
            return response["data"]["data"].get(key)
        except Exception as e:
            logger.error(f"Vault error for key {key}: {e}")
            return None

    def _get_doppler_secret(self, key: str) -> Optional[str]:
        """Get secret from Doppler."""
        try:
            url = (
                f"https://api.doppler.com/v3/configs/secrets/download"
                f"?project={self.settings.doppler_project}"
                f"&config={self.settings.doppler_config}"
                f"&format=json"
            )
            import requests

            response = requests.get(url, headers=self._doppler_headers)
            response.raise_for_status()
            secrets = response.json()
            return secrets.get(key)
        except Exception as e:
            logger.error(f"Doppler error for key {key}: {e}")
            return None

    def get_all_secrets(self) -> Dict[str, str]:
        """
        Get all secrets from the configured backend.

        Returns:
            Dictionary of all secret key-value pairs
        """
        self._initialize_backend()

        backend = self.settings.secrets_backend

        if backend == "aws":
            try:
                response = self._aws_client.get_secret_value(SecretId=self.settings.aws_secret_name)
                return json.loads(response["SecretString"])
            except Exception as e:
                logger.error(f"AWS Secrets Manager error: {e}")
                return {}

        elif backend == "vault":
            try:
                response = self._vault_client.secrets.kv.v2.read_secret_version(
                    path=self.settings.vault_secret_path
                )
                return response["data"]["data"]
            except Exception as e:
                logger.error(f"Vault error: {e}")
                return {}

        elif backend == "doppler":
            try:
                url = (
                    f"https://api.doppler.com/v3/configs/secrets/download"
                    f"?project={self.settings.doppler_project}"
                    f"&config={self.settings.doppler_config}"
                    f"&format=json"
                )
                import requests

                response = requests.get(url, headers=self._doppler_headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Doppler error: {e}")
                return {}

        else:  # local
            # Return all environment variables that are typically secrets
            secret_keys = [
                "SECRET_KEY",
                "JWT_SECRET_KEY",
                "DB_PASSWORD",
                "DATABASE_URL",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "SMTP_PASSWORD",
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "SENTRY_DSN",
                "GRAFANA_ADMIN_PASSWORD",
                "REDIS_URL",
            ]
            return {k: os.getenv(k, "") for k in secret_keys if os.getenv(k)}


# Singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the secrets manager singleton."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


class Settings(BaseSettings):
    """
    Extended settings class with secrets management support.

    This class integrates with the SecretsManager to provide
    secrets from multiple backends while maintaining compatibility
    with the existing .env file approach.
    """

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings: type[BaseSettings],
        init_settings: tuple[str, ...],
        env_settings: tuple[str, ...],
        dotenv_settings: tuple[str, ...],
        file_secret_settings: tuple[str, ...],
    ) -> tuple[Any, ...]:
        """
        Customize sources to check secrets manager first, then environment variables.

        This ensures secrets from AWS/Vault/Doppler take precedence over .env files.
        """
        # First check secrets manager
        secrets_manager = get_secrets_manager()

        # Create a custom source that checks secrets manager
        class SecretsManagerSource:
            def __init__(self):
                self._secrets = secrets_manager.get_all_secrets()

            def __call__(self, field_name: str) -> str | None:
                # Check secrets manager first
                if field_name in self._secrets and self._secrets[field_name]:
                    return self._secrets[field_name]
                # Then check environment
                return os.getenv(field_name)

            def __repr__(self) -> str:
                return "SecretsManagerSource(...)"

        return (
            SecretsManagerSource(),
            *init_settings,
            *env_settings,
            *dotenv_settings,
            *file_secret_settings,
        )


# Convenience function for getting secrets
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a secret value from the configured backend."""
    return get_secrets_manager().get_secret(key, default)


__all__ = [
    "SecretsManager",
    "SecretsManagerSettings",
    "SecretStr",
    "Settings",
    "get_secrets_manager",
    "get_secrets_settings",
    "get_secret",
]
