"""
OAuth Service for Portkit

Provides OAuth2 authentication for Discord, GitHub, and Google.
Issue #980: Add OAuth login (Discord, GitHub, Google)
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

import httpx

from core.secrets import get_secret

logger = logging.getLogger(__name__)

FRONTEND_URL = get_secret("FRONTEND_URL") or "https://portkit.cloud"
API_BASE_URL = get_secret("API_BASE_URL") or "https://portkit.cloud"

DISCORD_SCOPES = ["identify", "email"]
GITHUB_SCOPES = ["read:user", "user:email"]
GOOGLE_SCOPES = ["openid", "email", "profile"]


@dataclass
class OAuthUserInfo:
    """OAuth user information returned by provider."""

    provider: str
    provider_user_id: str
    email: Optional[str]
    username: Optional[str]
    access_token: str
    refresh_token: Optional[str]
    expires_at: Optional[datetime]


class DiscordOAuthService:
    """Discord OAuth2 service."""

    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Get Discord authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(DISCORD_SCOPES),
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.BASE_URL}/oauth2/authorize?{query}"

    async def exchange_code(self, code: str) -> OAuthUserInfo:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            data = response.json()

            access_token = data["access_token"]
            refresh_token = data.get("refresh_token")
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=data.get("expires_in", 3600)
            )

            user_info = await self._get_user_info(access_token)

            return OAuthUserInfo(
                provider="discord",
                provider_user_id=user_info["id"],
                email=user_info.get("email"),
                username=user_info.get("username"),
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Discord."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()


class GitHubOAuthService:
    """GitHub OAuth2 service."""

    BASE_URL = "https://api.github.com"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Get GitHub authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(GITHUB_SCOPES),
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://github.com/login/oauth/authorize?{query}"

    async def exchange_code(self, code: str) -> OAuthUserInfo:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            access_token = data["access_token"]
            refresh_token = data.get("refresh_token")
            expires_at = None

            user_info = await self._get_user_info(access_token)
            emails = await self._get_emails(access_token)

            primary_email = next(
                (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                user_info.get("email"),
            )

            return OAuthUserInfo(
                provider="github",
                provider_user_id=str(user_info["id"]),
                email=primary_email or user_info.get("email"),
                username=user_info.get("login"),
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from GitHub."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def _get_emails(self, access_token: str) -> list:
        """Get user emails from GitHub."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/user/emails",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()


class GoogleOAuthService:
    """Google OAuth2 service."""

    BASE_URL = "https://oauth2.googleapis.com"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Get Google authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.BASE_URL}/auth?{query}"

    async def exchange_code(self, code: str) -> OAuthUserInfo:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            data = response.json()

            access_token = data["access_token"]
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            user_info = await self._get_user_info(access_token)

            return OAuthUserInfo(
                provider="google",
                provider_user_id=user_info["sub"],
                email=user_info.get("email"),
                username=user_info.get("name"),
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.USERINFO_URL}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()


class OAuthService:
    """OAuth service factory and manager."""

    def __init__(self):
        self.discord: Optional[DiscordOAuthService] = None
        self.github: Optional[GitHubOAuthService] = None
        self.google: Optional[GoogleOAuthService] = None
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize OAuth providers from environment variables."""
        discord_client_id = get_secret("DISCORD_CLIENT_ID")
        discord_client_secret = get_secret("DISCORD_CLIENT_SECRET")
        discord_redirect_uri = (
            get_secret("DISCORD_REDIRECT_URI")
            or f"{API_BASE_URL}/api/v1/auth/oauth/discord/callback"
        )

        if discord_client_id and discord_client_secret:
            self.discord = DiscordOAuthService(
                discord_client_id, discord_client_secret, discord_redirect_uri
            )
            logger.info("Discord OAuth initialized")

        github_client_id = get_secret("GITHUB_CLIENT_ID")
        github_client_secret = get_secret("GITHUB_CLIENT_SECRET")
        github_redirect_uri = (
            get_secret("GITHUB_REDIRECT_URI") or f"{API_BASE_URL}/api/v1/auth/oauth/github/callback"
        )

        if github_client_id and github_client_secret:
            self.github = GitHubOAuthService(
                github_client_id, github_client_secret, github_redirect_uri
            )
            logger.info("GitHub OAuth initialized")

        google_client_id = get_secret("GOOGLE_CLIENT_ID")
        google_client_secret = get_secret("GOOGLE_CLIENT_SECRET")
        google_redirect_uri = (
            get_secret("GOOGLE_REDIRECT_URI") or f"{API_BASE_URL}/api/v1/auth/oauth/google/callback"
        )

        if google_client_id and google_client_secret:
            self.google = GoogleOAuthService(
                google_client_id, google_client_secret, google_redirect_uri
            )
            logger.info("Google OAuth initialized")

    def get_provider(self, provider: str) -> Optional[object]:
        """Get OAuth provider by name."""
        providers = {
            "discord": self.discord,
            "github": self.github,
            "google": self.google,
        }
        return providers.get(provider.lower())

    def is_provider_enabled(self, provider: str) -> bool:
        """Check if OAuth provider is enabled."""
        return self.get_provider(provider) is not None


# Used for OAuth CSRF state - cryptographically secure, not a password
def generate_oauth_state() -> str:
    """Generate secure state parameter for OAuth flow."""
    return secrets.token_urlsafe(32)


oauth_service = OAuthService()
