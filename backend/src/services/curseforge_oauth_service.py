"""
CurseForge OAuth Integration Service

Provides OAuth authentication and publishing capabilities for CurseForge.
API Documentation: https://curseforge.atlassian.net/wiki/spaces/CURSE/pages/2924450435/The+CurseForge+API
OAuth Documentation: https://curseforge.atlassian.net/wiki/spaces/CURSE/pages/2924450437/OAuth+20
"""

import os
import httpx
import secrets
import hashlib
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

# CurseForge OAuth configuration
CURSEFORGE_CLIENT_ID = os.getenv("CURSEFORGE_CLIENT_ID", "")
CURSEFORGE_CLIENT_SECRET = os.getenv("CURSEFORGE_CLIENT_SECRET", "")
CURSEFORGE_REDIRECT_URI = os.getenv("CURSEFORGE_REDIRECT_URI", "http://localhost:8080/api/v1/auth/curseforge/callback")
CURSEFORGE_API_BASE_URL = "https://api.curseforge.com/v1"
CURSEFORGE_AUTH_URL = "https://oauth.curseforge.com/oauth/authorize"
CURSEFORGE_TOKEN_URL = "https://oauth.curseforge.com/oauth/token"

# Scopes needed for OAuth
CURSEFORGE_SCOPES = [
    "account.read",
    "project.read",
    "project.upload",
    "project.write",
]


class CurseForgeOAuthService:
    """Service for CurseForge OAuth 2.0 authentication"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = client_id or CURSEFORGE_CLIENT_ID
        self.client_secret = client_secret or CURSEFORGE_CLIENT_SECRET
        self.redirect_uri = redirect_uri or CURSEFORGE_REDIRECT_URI
        self.base_url = CURSEFORGE_API_BASE_URL

    def generate_state(self) -> str:
        """Generate a secure random state parameter for OAuth flow"""
        return secrets.token_urlsafe(32)

    def generate_code_verifier(self) -> str:
        """Generate PKCE code verifier"""
        # CurseForge requires 43-128 characters
        return secrets.token_urlsafe(48)

    def generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier (S256 method)"""
        sha256_hash = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")

    def get_authorization_url(
        self,
        state: str,
        code_verifier: str,
    ) -> str:
        """
        Generate the CurseForge OAuth authorization URL

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
            "scope": " ".join(CURSEFORGE_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        
        return f"{CURSEFORGE_AUTH_URL}?{urlencode(params)}"

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
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    CURSEFORGE_TOKEN_URL,
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
                        "Accept": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"CurseForge token exchange error: {e}")
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
                    CURSEFORGE_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"CurseForge token refresh error: {e}")
                raise

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get authenticated user's information

        Args:
            access_token: Valid OAuth access token

        Returns:
            User information dictionary
        """
        endpoint = f"{self.base_url}/account"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", {})
            except httpx.HTTPError as e:
                logger.error(f"CurseForge user info error: {e}")
                raise

    async def get_user_projects(
        self,
        access_token: str,
    ) -> List[Dict[str, Any]]:
        """
        Get projects owned by the authenticated user

        Args:
            access_token: Valid OAuth access token

        Returns:
            List of project dictionaries
        """
        # Get user's mods/projects
        endpoint = f"{self.base_url}/user/mods"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                logger.error(f"CurseForge user projects error: {e}")
                raise


class CurseForgePublisher:
    """Service for publishing mods to CurseForge"""

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        # CurseForge requires both API key and OAuth for publishing
        self.api_key = api_key or os.getenv("CURSEFORGE_API_KEY", "")
        self.base_url = CURSEFORGE_API_BASE_URL
        self.game_id = 432  # Minecraft

    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get common headers for API requests"""
        return {
            "Authorization": f"Bearer {access_token}",
            "x-api-key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def get_game_versions(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get available Minecraft game versions

        Args:
            access_token: Valid OAuth access token

        Returns:
            List of game version dictionaries
        """
        endpoint = f"{self.base_url}/games/{self.game_id}/versions"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(access_token),
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                logger.error(f"CurseForge get game versions error: {e}")
                raise

    async def get_categories(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get available mod categories

        Args:
            access_token: Valid OAuth access token

        Returns:
            List of category dictionaries
        """
        endpoint = f"{self.base_url}/categories"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(access_token),
                    params={"gameId": self.game_id},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                logger.error(f"CurseForge get categories error: {e}")
                raise

    async def create_project(
        self,
        access_token: str,
        project_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new project on CurseForge

        Note: CurseForge requires manual project creation through their website
        for most mod categories. This endpoint may have limited functionality.

        Args:
            access_token: Valid OAuth access token
            project_data: Project details

        Returns:
            Created project information
        """
        endpoint = f"{self.base_url}/projects"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    endpoint,
                    headers=self._get_headers(access_token),
                    json={
                        **project_data,
                        "gameId": self.game_id,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", {})
            except httpx.HTTPError as e:
                logger.error(f"CurseForge create project error: {e}")
                raise

    async def update_project(
        self,
        access_token: str,
        project_id: int,
        project_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing project

        Args:
            access_token: Valid OAuth access token
            project_id: The CurseForge project ID
            project_data: Updated project details

        Returns:
            Updated project information
        """
        endpoint = f"{self.base_url}/projects/{project_id}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    endpoint,
                    headers=self._get_headers(access_token),
                    json=project_data,
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", {})
            except httpx.HTTPError as e:
                logger.error(f"CurseForge update project error: {e}")
                raise

    async def upload_file(
        self,
        access_token: str,
        project_id: int,
        file_data: Dict[str, Any],
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Upload a new file/version to a project

        Args:
            access_token: Valid OAuth access token
            project_id: The CurseForge project ID
            file_data: File metadata
            file_path: Path to the file to upload

        Returns:
            Uploaded file information
        """
        endpoint = f"{self.base_url}/projects/{project_id}/upload-file"

        # Prepare multipart upload
        from io import BytesIO

        with open(file_path, "rb") as file:
            file_content = file.read()

        files = {
            "file": (os.path.basename(file_path), file_content, "application/zip"),
        }
        data = {
            "metadata": file_data,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "x-api-key": self.api_key,
                    },
                    files=files,
                    data=data,
                    timeout=300.0,  # Longer timeout for file uploads
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", {})
            except httpx.HTTPError as e:
                logger.error(f"CurseForge upload file error: {e}")
                raise

    async def get_project_files(
        self,
        access_token: str,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get all files/versions of a project

        Args:
            access_token: Valid OAuth access token
            project_id: The CurseForge project ID

        Returns:
            List of file dictionaries
        """
        endpoint = f"{self.base_url}/projects/{project_id}/files"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(access_token),
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                logger.error(f"CurseForge get files error: {e}")
                raise

    async def delete_file(
        self,
        access_token: str,
        project_id: int,
        file_id: int,
    ) -> None:
        """
        Delete a file from a project

        Args:
            access_token: Valid OAuth access token
            project_id: The CurseForge project ID
            file_id: The file ID to delete
        """
        endpoint = f"{self.base_url}/projects/{project_id}/files/{file_id}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    endpoint,
                    headers=self._get_headers(access_token),
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"CurseForge delete file error: {e}")
                raise


class CurseForgeIntegrationError(Exception):
    """Custom exception for CurseForge integration errors"""
    pass


# Singleton instances
curseforge_oauth_service = CurseForgeOAuthService()
curseforge_publisher = CurseForgePublisher()
