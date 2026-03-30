"""
Unit tests for Mod Imports API endpoints.

Issue: #643 - Backend: Implement Rate Limiting Dashboard
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.mod_imports import (
    router,
    parse_mod_url,
    transform_curseforge_mod,
    transform_modrinth_mod,
    transform_curseforge_file,
    transform_modrinth_version,
    ModSearchRequest,
    ModInfo,
    ModFile,
    URLParseResult,
)


app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestParseModUrl:
    """Tests for parse_mod_url helper function."""

    def test_parse_curseforge_url(self):
        """Test parsing CurseForge URLs."""
        result = parse_mod_url("https://www.curseforge.com/minecraft/mods/test-mod")
        assert result.platform == "curseforge"
        assert result.slug == "test-mod"
        assert result.is_valid is True
        assert result.error is None

    def test_parse_curseforge_url_without_www(self):
        """Test parsing CurseForge URLs without www."""
        result = parse_mod_url("https://curseforge.com/minecraft/mods/my-mod")
        assert result.platform == "curseforge"
        assert result.slug == "my-mod"
        assert result.is_valid is True

    def test_parse_curseforge_url_http(self):
        """Test parsing CurseForge URLs with HTTP."""
        result = parse_mod_url("http://www.curseforge.com/minecraft/mods/mod-name")
        assert result.platform == "curseforge"
        assert result.slug == "mod-name"
        assert result.is_valid is True

    def test_parse_modrinth_mod_url(self):
        """Test parsing Modrinth mod URLs."""
        result = parse_mod_url("https://modrinth.com/mod/test-mod")
        assert result.platform == "modrinth"
        assert result.slug == "test-mod"
        assert result.is_valid is True

    def test_parse_modrinth_resourcepack_url(self):
        """Test parsing Modrinth resourcepack URLs."""
        result = parse_mod_url("https://modrinth.com/resourcepack/faithful")
        assert result.platform == "modrinth"
        assert result.slug == "faithful"
        assert result.is_valid is True

    def test_parse_modrinth_plugin_url(self):
        """Test parsing Modrinth plugin URLs."""
        result = parse_mod_url("https://modrinth.com/plugin/essentialsx")
        assert result.platform == "modrinth"
        assert result.slug == "essentialsx"
        assert result.is_valid is True

    def test_parse_modrinth_short_url(self):
        """Test parsing Modrinth short URLs."""
        result = parse_mod_url("https://modrinth.com/sodium")
        assert result.platform == "modrinth"
        assert result.slug == "sodium"
        assert result.is_valid is True

    def test_parse_invalid_url(self):
        """Test parsing invalid URLs."""
        result = parse_mod_url("https://example.com/random/page")
        assert result.platform == "unknown"
        assert result.is_valid is False
        assert result.error is not None

    def test_parse_empty_url(self):
        """Test parsing empty URL."""
        result = parse_mod_url("")
        assert result.platform == "unknown"
        assert result.is_valid is False


class TestTransformFunctions:
    """Tests for transform helper functions."""

    def test_transform_curseforge_mod(self):
        """Test transforming CurseForge mod data."""
        data = {
            "data": {
                "id": 12345,
                "name": "Test Mod",
                "summary": "A test mod description",
                "authors": [{"name": "Author1"}, {"name": "Author2"}],
                "downloadCount": 1000,
                "latestFiles": [
                    {
                        "gameVersions": ["1.20.1", "1.19.4"],
                        "modLoaders": ["Forge"],
                    }
                ],
                "logo": {"url": "https://example.com/logo.png"},
                "slug": "test-mod",
                "dateCreated": "2024-01-01",
                "dateModified": "2024-02-01",
            }
        }
        result = transform_curseforge_mod(data)
        assert isinstance(result, ModInfo)
        assert result.platform == "curseforge"
        assert result.mod_id == "12345"
        assert result.name == "Test Mod"
        assert result.description == "A test mod description"
        assert result.author == "Author1, Author2"
        assert result.download_count == 1000

    def test_transform_curseforge_mod_empty_data(self):
        """Test transforming CurseForge mod with empty data."""
        data = {"data": {}}
        result = transform_curseforge_mod(data)
        assert result.platform == "curseforge"
        assert result.name == ""

    def test_transform_modrinth_mod(self):
        """Test transforming Modrinth mod data."""
        data = {
            "id": "abc123",
            "title": "Sodium",
            "description": "A popular optimization mod",
            "author": "embeddedt",
            "downloads": 50000,
            "versions": ["1.20.1", "1.19.2"],
            "categories": ["fabric", "optimization"],
            "icon_url": "https://example.com/icon.png",
            "slug": "sodium",
            "published": "2024-01-01",
            "updated": "2024-02-01",
        }
        result = transform_modrinth_mod(data)
        assert isinstance(result, ModInfo)
        assert result.platform == "modrinth"
        assert result.mod_id == "abc123"
        assert result.name == "Sodium"
        assert result.description == "A popular optimization mod"
        assert result.author == "embeddedt"

    def test_transform_curseforge_file(self):
        """Test transforming CurseForge file data."""
        data = {
            "id": 99999,
            "displayName": "1.0.0",
            "gameVersions": ["1.20.1"],
            "modLoaders": ["Forge"],
            "fileName": "test-mod-1.0.0.jar",
            "fileLength": 1024000,
            "downloadUrl": "https://example.com/download",
            "releaseType": "release",
            "fileDate": "2024-01-01",
        }
        result = transform_curseforge_file(data)
        assert isinstance(result, ModFile)
        assert result.file_id == "99999"
        assert result.version == "1.0.0"
        assert result.file_size == 1024000

    def test_transform_modrinth_version(self):
        """Test transforming Modrinth version data."""
        data = {
            "id": "version123",
            "version_number": "2.0.0",
            "game_versions": ["1.20.1", "1.20.2"],
            "loaders": ["fabric", "quilt"],
            "files": [
                {"filename": "sodium-2.0.0.jar", "size": 2048000, "url": "https://example.com/dl"}
            ],
            "release_type": "release",
            "date_published": "2024-02-01",
        }
        result = transform_modrinth_version(data)
        assert isinstance(result, ModFile)
        assert result.file_id == "version123"
        assert result.version == "2.0.0"
        assert result.file_name == "sodium-2.0.0.jar"


class TestAPIEndpoints:
    """Tests for API endpoints."""

    def test_parse_url_endpoint(self):
        """Test parse-url endpoint."""
        response = client.get("/parse-url?url=https://modrinth.com/mod/sodium")
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "modrinth"
        assert data["slug"] == "sodium"
        assert data["is_valid"] is True

    def test_parse_url_invalid(self):
        """Test parse-url with invalid URL."""
        response = client.get("/parse-url?url=https://invalid.com/page")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False

    @patch("api.mod_imports.curseforge_service.search_mods", new_callable=AsyncMock)
    def test_search_curseforge(self, mock_search):
        """Test search endpoint for CurseForge."""
        mock_search.return_value = {
            "data": [
                {
                    "id": 123,
                    "name": "Test Mod",
                    "summary": "Description",
                    "authors": [{"name": "Author"}],
                    "downloadCount": 100,
                    "latestFiles": [{"gameVersions": [], "modLoaders": []}],
                    "logo": {"url": None},
                    "slug": "test-mod",
                    "dateCreated": None,
                    "dateModified": None,
                }
            ]
        }

        response = client.get("/search?query=test&platform=curseforge")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Test Mod"

    @patch("api.mod_imports.modrinth_service.search_mods", new_callable=AsyncMock)
    def test_search_modrinth(self, mock_search):
        """Test search endpoint for Modrinth."""
        mock_search.return_value = {
            "hits": [
                {
                    "id": "abc",
                    "title": "Sodium",
                    "description": "Optimization mod",
                    "author": "embeddedt",
                    "downloads": 1000,
                    "versions": [],
                    "categories": [],
                    "icon_url": None,
                    "slug": "sodium",
                    "published": None,
                    "updated": None,
                }
            ]
        }

        response = client.get("/search?query=sodium&platform=modrinth")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Sodium"

    def test_search_invalid_platform(self):
        """Test search with invalid platform."""
        response = client.get("/search?query=test&platform=invalid")
        assert response.status_code == 400

    @patch("api.mod_imports.curseforge_service.search_mods", new_callable=AsyncMock)
    def test_search_with_filters(self, mock_search):
        """Test search with version and loader filters."""
        mock_search.return_value = {"data": []}

        response = client.get(
            "/search?query=test&platform=curseforge&game_version=1.20.1&sort_order=downloads"
        )
        assert response.status_code == 200

    @patch("api.mod_imports.curseforge_service.get_mod_info", new_callable=AsyncMock)
    def test_get_mod_info_curseforge(self, mock_get_info):
        """Test get mod info for CurseForge."""
        mock_get_info.return_value = {
            "data": {
                "id": 123,
                "name": "Test Mod",
                "summary": "Description",
                "authors": [{"name": "Author"}],
                "downloadCount": 100,
                "latestFiles": [{"gameVersions": [], "modLoaders": []}],
                "logo": {"url": None},
                "slug": "test-mod",
                "dateCreated": None,
                "dateModified": None,
            }
        }

        response = client.get("/curseforge/mod/123")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Mod"

    @patch("api.mod_imports.modrinth_service.get_project", new_callable=AsyncMock)
    def test_get_mod_info_modrinth(self, mock_get_project):
        """Test get mod info for Modrinth."""
        mock_get_project.return_value = {
            "id": "abc",
            "title": "Sodium",
            "description": "Optimization mod",
            "author": "embeddedt",
            "downloads": 1000,
            "versions": [],
            "categories": [],
            "icon_url": None,
            "slug": "sodium",
            "published": None,
            "updated": None,
        }

        response = client.get("/modrinth/mod/abc")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sodium"

    @patch("api.mod_imports.curseforge_service.get_mod_files", new_callable=AsyncMock)
    def test_get_mod_files_curseforge(self, mock_get_files):
        """Test get mod files for CurseForge."""
        mock_get_files.return_value = {
            "data": [
                {
                    "id": 456,
                    "displayName": "1.0.0",
                    "gameVersions": ["1.20.1"],
                    "modLoaders": ["Forge"],
                    "fileName": "mod-1.0.0.jar",
                    "fileLength": 1024,
                    "downloadUrl": None,
                    "releaseType": "release",
                    "fileDate": "2024-01-01",
                }
            ]
        }

        response = client.get("/curseforge/mod/123/files")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["version"] == "1.0.0"

    @patch("api.mod_imports.modrinth_service.get_project_versions", new_callable=AsyncMock)
    def test_get_mod_files_modrinth(self, mock_get_versions):
        """Test get mod files for Modrinth."""
        mock_get_versions.return_value = [
            {
                "id": "ver123",
                "version_number": "2.0.0",
                "game_versions": ["1.20.1"],
                "loaders": ["fabric"],
                "files": [
                    {"filename": "mod-2.0.0.jar", "size": 2048, "url": "https://example.com/dl"}
                ],
                "release_type": "release",
                "date_published": "2024-01-01",
            }
        ]

        response = client.get("/modrinth/mod/abc/files")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_get_mod_files_with_version_filter(self):
        """Test get mod files with version filter."""
        with patch(
            "api.mod_imports.curseforge_service.get_mod_files", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {"data": []}
            response = client.get("/curseforge/mod/123/files?game_version=1.20.1")
            assert response.status_code == 200

    @patch("api.mod_imports.curseforge_service.get_categories", new_callable=AsyncMock)
    def test_get_categories_curseforge(self, mock_categories):
        """Test get categories for CurseForge."""
        mock_categories.return_value = {"data": [{"id": 1, "name": "Adventure"}]}

        response = client.get("/categories/curseforge")
        assert response.status_code == 200

    @patch("api.mod_imports.modrinth_service.get_categories", new_callable=AsyncMock)
    def test_get_categories_modrinth(self, mock_categories):
        """Test get categories for Modrinth."""
        mock_categories.return_value = [{"name": "adventure", "display_name": "Adventure"}]

        response = client.get("/categories/modrinth")
        assert response.status_code == 200

    def test_get_categories_invalid_platform(self):
        """Test get categories with invalid platform."""
        response = client.get("/categories/invalid")
        assert response.status_code == 400

    @patch("api.mod_imports.modrinth_service.get_loaders", new_callable=AsyncMock)
    def test_get_loaders(self, mock_loaders):
        """Test get loaders endpoint."""
        mock_loaders.return_value = ["fabric", "forge", "quilt"]

        response = client.get("/loaders")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "fabric" in data

    @patch("api.mod_imports.curseforge_service.search_mods", new_callable=AsyncMock)
    @patch("api.mod_imports.curseforge_service.get_mod_info", new_callable=AsyncMock)
    @patch("api.mod_imports.curseforge_service.get_mod_files", new_callable=AsyncMock)
    @patch("api.mod_imports.curseforge_service.get_file_download_url", new_callable=AsyncMock)
    def test_import_mod_success(self, mock_download_url, mock_files, mock_info, mock_search):
        """Test successful mod import."""
        mock_search.return_value = {"data": [{"id": 123, "name": "Test Mod", "slug": "test-mod"}]}
        mock_info.return_value = {
            "data": {
                "id": 123,
                "name": "Test Mod",
                "summary": "Description",
                "authors": [{"name": "Author"}],
                "downloadCount": 100,
                "latestFiles": [{"gameVersions": [], "modLoaders": []}],
                "logo": {"url": None},
                "slug": "test-mod",
                "dateCreated": None,
                "dateModified": None,
            }
        }
        mock_files.return_value = {"data": [{"id": 456, "displayName": "1.0.0"}]}
        mock_download_url.return_value = "https://example.com/download.jar"

        with patch("os.makedirs"), patch("httpx.AsyncClient") as mock_client:
            mock_stream_response = MagicMock()
            mock_stream_response.raise_for_status = MagicMock()
            mock_stream_response.aiter_bytes = MagicMock(return_value=iter([b"data"]))

            mock_stream_context = MagicMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream_response)
            mock_stream_context.__aexit__ = AsyncMock(return_value=None)

            mock_client_instance = MagicMock()
            mock_client_instance.stream = MagicMock(return_value=mock_stream_context)

            async def mock_client_cm(*args, **kwargs):
                return mock_client_instance

            mock_client.side_effect = lambda *args, **kwargs: mock_client_instance
            mock_client_instance.stream.return_value = mock_stream_context

            with patch("builtins.open", MagicMock()):
                response = client.post(
                    "/import", json={"url": "https://curseforge.com/minecraft/mods/test-mod"}
                )

        assert response.status_code == 200

    def test_import_mod_invalid_url(self):
        """Test import with invalid URL."""
        response = client.post("/import", json={"url": "https://invalid.com/page"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert (
            "Unable to parse URL" in data["message"]
            or "not found" in data["message"].lower()
            or "Invalid URL" in data["message"]
        )
