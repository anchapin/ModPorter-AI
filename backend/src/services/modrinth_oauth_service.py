"""
Modrinth OAuth 2.0 Integration Service

Provides OAuth 2.0 authentication and publishing capabilities for Modrinth.
API Documentation: https://docs.modrinth.app/api-v2/
OAuth Documentation: https://docs.modrinth.app/api-v2/#section/Authentication/OAuth2-CodeFlow
"""

import os
import httpx
import secrets
import hashlib
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote
import logging

logger = logging.getLogger(__name__)

# Modrinth OAuth configuration
MODRINTH_CLIENT_ID = os.getenv("MODRINTH_CLIENT_ID", "")
MODRINTH_CLIENT_SECRET = os.getenv("MODRINTH_CLIENT_SECRET", "")
MODRINTH_REDIRECT_URI = os.getenv("MODRINTH_REDIRECT_URI", "http://localhost:8080/api/v1/auth/modrinth/callback")
MODRINTH_API_BASE_URL = "https://api.modrinth.com/v2"
MODRINTH_AUTH_URL = "https://modrinth.com/auth/authorize"
MODRINTH_TOKEN_URL = "https://api.modrinth.com/v2/oauth/token"
MODRINTH_TOKEN_EXCHANGE_URL = "https://modrinth.com/auth/token"

# Scopes needed for OAuth
MODRINTH_SCOPES = [
    "USER_IDENTIFY",
    "USER_EMAIL",
    "PUBLISH_VERSION",
    "EDIT_PROJECT",
]


class ModrinthOAuthService:
    """Service for Modrinth OAuth 2.0 authentication and publishing"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = client_id or MODRINTH_CLIENT_ID
        self.client_secret = client_secret or MODRINTH_CLIENT_SECRET
        self.redirect_uri = redirect_uri or MODRINTH_REDIRECT_URI
        self.base_url = MODRINTH_API_BASE_URL

    def generate_state(self) -> str:
        """Generate a secure random state parameter for OAuth flow"""
        return secrets.token_urlsafe(32)

    def generate_code_verifier(self) -> str:
        """Generate PKCE code verifier"""
        return secrets.token_urlsafe(32)

    def generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        sha256_hash = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")

    def get_authorization_url(
        self,
        state: str,
        code_verifier: str,
    ) -> str:
        """
        Generate the Modrinth OAuth authorization URL

        Args:
            state: Secure random state parameter
            code_verifier: PKCE code verifier for the authorization request

        Returns:
            Authorization URL to redirect user to
        """
        code_challenge = self.generate_code_challenge(code_verifier)
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(MODRINTH_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        
        return f"{MODRINTH_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier used in authorization request

        Returns:
            Dictionary containing access_token, refresh_token, and expires_in
        """
        # Modrinth uses a different token exchange mechanism
        # They use form-urlencoded POST to their auth endpoint
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    MODRINTH_TOKEN_EXCHANGE_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "code_verifier": code_verifier,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth token exchange error: {e}")
                raise

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token

        Args:
            refresh_token: The refresh token from initial OAuth flow

        Returns:
            Dictionary containing new access_token and expires_in
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    MODRINTH_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth token refresh error: {e}")
                raise

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get authenticated user's information

        Args:
            access_token: Valid OAuth access token

        Returns:
            User information dictionary
        """
        endpoint = f"{self.base_url}/user"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth user info error: {e}")
                raise

    async def get_user_projects(
        self,
        access_token: str,
        page: int = 0,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get projects owned by the authenticated user

        Args:
            access_token: Valid OAuth access token
            page: Page number for pagination
            page_size: Number of results per page

        Returns:
            List of project dictionaries
        """
        user_info = await self.get_user_info(access_token)
        user_id = user_info.get("id")

        endpoint = f"{self.base_url}/users/{user_id}/projects"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    params={
                        "page": page,
                        "page_size": page_size,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth user projects error: {e}")
                raise


class ModrinthPublisher:
    """Service for publishing mods to Modrinth"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id or MODRINTH_CLIENT_ID
        self.client_secret = client_secret or MODRINTH_CLIENT_SECRET
        self.base_url = MODRINTH_API_BASE_URL

    async def create_project(
        self,
        access_token: str,
        project_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new project on Modrinth

        Args:
            access_token: Valid OAuth access token with project creation scope
            project_data: Project details including name, slug, summary, description

        Returns:
            Created project information
        """
        endpoint = f"{self.base_url}/projects"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    json=project_data,
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth create project error: {e}")
                raise

    async def update_project(
        self,
        access_token: str,
        project_slug: str,
        project_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing project

        Args:
            access_token: Valid OAuth access token
            project_slug: The project's unique slug
            project_data: Updated project details

        Returns:
            Updated project information
        """
        endpoint = f"{self.base_url}/projects/{project_slug}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    json=project_data,
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth update project error: {e}")
                raise

    async def upload_version(
        self,
        access_token: str,
        project_slug: str,
        version_data: Dict[str, Any],
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Upload a new version/file to a project

        Args:
            access_token: Valid OAuth access token
            project_slug: The project's unique slug
            version_data: Version metadata
            file_path: Path to the file to upload

        Returns:
            Created version information
        """
        endpoint = f"{self.base_url}/projects/{project_slug}/version"

        # Read file and prepare multipart upload
        with open(file_path, "rb") as file:
            file_content = file.read()

        # Prepare the version metadata as JSON
        from io import BytesIO

        files = {
            "file": (os.path.basename(file_path), file_content, "application/zip"),
        }
        data = {
            "data": version_data,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    files=files,
                    data=data,
                    timeout=300.0,  # Longer timeout for file uploads
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth upload version error: {e}")
                raise

    async def publish_version(
        self,
        access_token: str,
        project_slug: str,
        version_id: str,
    ) -> Dict[str, Any]:
        """
        Publish a version (change from draft to published)

        Args:
            access_token: Valid OAuth access token
            project_slug: The project's unique slug
            version_id: The version ID to publish

        Returns:
            Updated version information
        """
        endpoint = f"{self.base_url}/projects/{project_slug}/versions/{version_id}/publish"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth publish version error: {e}")
                raise

    async def delete_version(
        self,
        access_token: str,
        project_slug: str,
        version_id: str,
    ) -> None:
        """
        Delete a version from a project

        Args:
            access_token: Valid OAuth access token
            project_slug: The project's unique slug
            version_id: The version ID to delete
        """
        endpoint = f"{self.base_url}/projects/{project_slug}/versions/{version_id}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth delete version error: {e}")
                raise

    async def get_project_versions(
        self,
        access_token: str,
        project_slug: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all versions of a project

        Args:
            access_token: Valid OAuth access token
            project_slug: The project's unique slug

        Returns:
            List of version dictionaries
        """
        endpoint = f"{self.base_url}/projects/{project_slug}/version"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "User-Agent": "ModPorter-AI/1.0",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Modrinth get versions error: {e}")
                raise


class ModrinthIntegrationError(Exception):
    """Custom exception for Modrinth integration errors"""
    pass


# Singleton instances
modrinth_oauth_service = ModrinthOAuthService()
modrinth_publisher = ModrinthPublisher()
