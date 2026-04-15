"""
Startup secrets validation for ModPorter-AI.

Validates that all required secrets are set and not using placeholder values
before the application starts. Fails fast in production to prevent insecure deployments.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)

PLACEHOLDER_PATTERNS = [
    "change-this",
    "change_this",
    "your-",
    "your_",
    "CHANGE_THIS",
    "CHANGE-THIS",
    "YOUR_",
    "YOUR-",
    "placeholder",
    "example",
    "test-secret",
    "test_secret",
    "secret-key-here",
    "secret_key_here",
    "changeme",
    "TODO",
    "FIXME",
]

REQUIRED_SECRETS: List[str] = [
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "DB_PASSWORD",
    "DATABASE_URL",
]

OPTIONAL_BUT_CHECKED_SECRETS: List[str] = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GRAFANA_ADMIN_PASSWORD",
]


def _is_placeholder(value: str) -> bool:
    """Return True if value looks like a placeholder that was never replaced."""
    lower = value.lower()
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.lower() in lower:
            return True
    return False


def _check_secret_strength(key: str, value: str) -> List[str]:
    """Return a list of warnings for a given secret value."""
    issues = []
    if key in ("SECRET_KEY", "JWT_SECRET_KEY") and len(value) < 32:
        issues.append(
            f"{key} is too short ({len(value)} chars). Use at least 32 chars "
            f"(generate with: openssl rand -base64 32)"
        )
    return issues


def validate_secrets(environment: str = "production") -> None:
    """
    Validate that all required secrets are set and not placeholders.

    In production, any missing or placeholder secret causes a hard failure (raises).
    In development/testing, issues are logged as warnings only.

    Args:
        environment: The runtime environment (production/staging/development/testing)

    Raises:
        ValueError: If any required secret is missing or a placeholder in production.
    """
    is_production = environment in ("production", "staging")
    errors: List[str] = []
    warnings: List[str] = []

    for key in REQUIRED_SECRETS:
        value = os.getenv(key, "")
        if not value:
            msg = f"Required secret '{key}' is not set."
            if is_production:
                errors.append(msg)
            else:
                warnings.append(msg)
            continue

        if _is_placeholder(value):
            msg = (
                f"Secret '{key}' contains a placeholder value. "
                f"Set a real value via 'fly secrets set {key}=...' before deploying."
            )
            if is_production:
                errors.append(msg)
            else:
                warnings.append(msg)
            continue

        strength_issues = _check_secret_strength(key, value)
        for issue in strength_issues:
            if is_production:
                errors.append(issue)
            else:
                warnings.append(issue)

    for key in OPTIONAL_BUT_CHECKED_SECRETS:
        value = os.getenv(key, "")
        if value and _is_placeholder(value):
            msg = f"Optional secret '{key}' contains a placeholder value and will not function correctly."
            warnings.append(msg)

    cors_origins = os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS", "")
    if is_production:
        if not cors_origins or cors_origins.strip() == "*":
            errors.append(
                "CORS_ORIGINS must be explicitly set to production domain(s) "
                "(e.g., https://modporter.ai,https://www.modporter.ai). "
                "Wildcard '*' is not allowed in production."
            )
        elif "localhost" in cors_origins and is_production:
            warnings.append(
                "CORS_ORIGINS includes 'localhost' — ensure this is intentional for production."
            )

    def _sanitize_for_log(msg: str) -> str:
        for key in REQUIRED_SECRETS + OPTIONAL_BUT_CHECKED_SECRETS:
            msg = msg.replace(f"'{key}'", "'[REDACTED]'")
        return msg

    def _log_warn(msg_text: str) -> None:
        logger.warning(msg_text)

    prefix = "[startup-validation] "
    for msg in warnings:
        _log_warn(prefix + _sanitize_for_log(msg))

    if errors:
        error_block = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(
            f"Application startup blocked — {len(errors)} secret(s) failed validation "
            f"for environment '{environment}':\n{error_block}\n\n"
            f"Set secrets via Fly.io: fly secrets set KEY=value\n"
            f"See scripts/setup-fly-secrets.sh for full setup instructions."
        )

    logger.info(
        f"[startup-validation] All required secrets validated successfully "
        f"(environment={environment})."
    )
