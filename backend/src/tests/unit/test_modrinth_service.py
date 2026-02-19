"""
Unit tests for ModrinthService

Tests the Modrinth API integration service for mod search and download.

Issue: #483 - Integrate CurseForge/Modrinth API for Direct Import
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx

from services.modrinth_service import (
    ModrinthService,
    modrinth_service,
    MODRINTH_API_BASE_URL,
    MODRINTH_APP_BASE_URL,
)


class TestModrinthService:
    """Tests for ModrinthService class."""
    
    def test_init_default(self):
        """Test service initialization with defaults."""
        service = ModrinthService()
        
        assert service.base_url == MODRINTH_API_BASE_URL
        assert service.token is not None or service.token == ""
    
    def test_init_with_token(self):
        """Test service initialization with custom token."""
        service = ModrinthService(token="test_token_123")
        
        assert service.token == "test_token_123"
        assert "Authorization" in service.headers
        assert service.headers["Authorization"] == "test_token_123"
    
    def test_headers_without_token(self):
        """Test headers without token."""
        service = ModrinthService(token=None)
        
        assert "Accept" in service.headers
        assert "User-Agent" in service.headers
        assert "Authorization" not in service.headers
    
    def test_headers_with_token(self):
        """Test headers with token."""
        service = ModrinthService(token="my_token")
        
        assert "Authorization" in service.headers
        assert service.headers["Authorization"] == "my_token"
    
    @pytest.mark.asyncio
    async def test_search_mods_success(self):
        """Test successful mod search."""
        service = ModrinthService()
        
        mock_response = {
            "hits": [
                {
                    "project_id": "abc123",
                    "title": "Test Mod",
                    "description": "A test mod",
                    "downloads": 1000,
                }
            ],
            "offset": 0,
            "limit": 25,
            "total_hits": 1,
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.search_mods("test mod")
            
            assert result is not None
            assert "hits" in result
    
    @pytest.mark.asyncio
    async def test_search_mods_with_filters(self):
        """Test mod search with filters."""
        service = ModrinthService()
        
        mock_response = {
            "hits": [],
            "offset": 0,
            "limit": 10,
            "total_hits": 0,
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.search_mods(
                query="test",
                game_version="1.20.1",
                loader="fabric",
                sort_order="downloads",
                page=0,
                limit=10
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_project_success(self):
        """Test getting project info."""
        service = ModrinthService()
        
        mock_response = {
            "id": "abc123",
            "slug": "test-mod",
            "title": "Test Mod",
            "description": "A test mod",
            "downloads": 1000,
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_project("abc123")
            
            assert result is not None
            assert result["id"] == "abc123"
    
    @pytest.mark.asyncio
    async def test_get_project_versions_success(self):
        """Test getting project versions."""
        service = ModrinthService()
        
        mock_response = [
            {
                "id": "version1",
                "version_number": "1.0.0",
                "game_versions": ["1.20.1"],
                "loaders": ["fabric"],
            }
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_project_versions("abc123", game_version="1.20.1")
            
            assert result is not None
            assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_get_version_success(self):
        """Test getting version info."""
        service = ModrinthService()
        
        mock_response = {
            "id": "version1",
            "version_number": "1.0.0",
            "game_versions": ["1.20.1"],
            "loaders": ["fabric"],
            "files": [
                {
                    "url": "https://cdn.modrinth.com/test.jar",
                    "hashes": {"sha1": "abc123"},
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_version("version1")
            
            assert result is not None
            assert result["id"] == "version1"
    
    @pytest.mark.asyncio
    async def test_get_file_download_url_success(self):
        """Test getting file download URL."""
        service = ModrinthService()
        
        mock_version_response = {
            "id": "version1",
            "files": [
                {
                    "url": "https://cdn.modrinth.com/test.jar",
                    "hashes": {"sha1": "abc123"},
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_version_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_file_download_url("version1")
            
            assert result is not None
            assert "modrinth.com" in result
    
    @pytest.mark.asyncio
    async def test_get_file_download_url_with_hash(self):
        """Test getting file download URL with hash verification."""
        service = ModrinthService()
        
        mock_version_response = {
            "id": "version1",
            "files": [
                {
                    "url": "https://cdn.modrinth.com/test.jar",
                    "hashes": {"sha1": "abc123"},
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_version_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_file_download_url("version1", file_hash="abc123")
            
            assert result is not None
            assert "modrinth.com" in result
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self):
        """Test getting categories."""
        service = ModrinthService()
        
        mock_response = [
            {"name": "adventure", "project_type": "mod"},
            {"name": "cursed", "project_type": "mod"},
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_categories()
            
            assert result is not None
            assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_loaders_success(self):
        """Test getting loaders."""
        service = ModrinthService()
        
        mock_response = [
            {"name": "fabric"},
            {"name": "forge"},
            {"name": "quilt"},
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_loaders()
            
            assert result is not None
            assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test API error handling."""
        service = ModrinthService()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.side_effect = httpx.HTTPError("API Error")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            with pytest.raises(httpx.HTTPError):
                await service.search_mods("test")


class TestModrinthURLParsing:
    """Tests for Modrinth URL parsing."""
    
    def test_parse_mod_url(self):
        """Test parsing standard Modrinth mod URL."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://modrinth.com/mod/test-mod"
        )
        
        assert result is not None
        assert result["platform"] == "modrinth"
        assert result["slug"] == "test-mod"
        assert result["project_type"] == "mod"
    
    def test_parse_resourcepack_url(self):
        """Test parsing resourcepack URL."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://modrinth.com/resourcepack/test-pack"
        )
        
        assert result is not None
        assert result["slug"] == "test-pack"
        assert result["project_type"] == "resourcepack"
    
    def test_parse_plugin_url(self):
        """Test parsing plugin URL."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://modrinth.com/plugin/test-plugin"
        )
        
        assert result is not None
        assert result["slug"] == "test-plugin"
        assert result["project_type"] == "plugin"
    
    def test_parse_pack_url(self):
        """Test parsing pack URL."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://modrinth.com/pack/test-pack"
        )
        
        assert result is not None
        assert result["slug"] == "test-pack"
        assert result["project_type"] == "pack"
    
    def test_parse_url_with_query_params(self):
        """Test parsing URL with query parameters."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://modrinth.com/mod/test-mod?param=value"
        )
        
        assert result is not None
        assert result["slug"] == "test-mod"
    
    def test_parse_invalid_url(self):
        """Test parsing invalid URL."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://example.com/something/else"
        )
        
        assert result is None
    
    def test_parse_curseforge_url(self):
        """Test parsing CurseForge URL (should return None)."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://curseforge.com/minecraft/mods/test-mod"
        )
        
        assert result is None
    
    def test_parse_url_with_trailing_slash(self):
        """Test parsing URL with trailing slash."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(
            "https://modrinth.com/mod/test-mod/"
        )
        
        assert result is not None
        assert result["slug"] == "test-mod"


class TestModrinthServiceSingleton:
    """Tests for singleton instance."""
    
    def test_singleton_exists(self):
        """Test that singleton instance exists."""
        assert modrinth_service is not None
        assert isinstance(modrinth_service, ModrinthService)
    
    def test_singleton_is_consistent(self):
        """Test that singleton is consistent."""
        from services.modrinth_service import modrinth_service as service2
        
        assert modrinth_service is service2


class TestModrinthServiceEdgeCases:
    """Tests for edge cases."""
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """Test search with empty query."""
        service = ModrinthService()
        
        mock_response = {"hits": [], "offset": 0, "limit": 25, "total_hits": 0}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.search_mods("")
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_project_nonexistent(self):
        """Test getting info for nonexistent project."""
        service = ModrinthService()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=Mock(),
                response=Mock(status_code=404)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            with pytest.raises(httpx.HTTPStatusError):
                await service.get_project("nonexistent-project-id")
    
    @pytest.mark.asyncio
    async def test_get_file_download_url_no_files(self):
        """Test getting download URL when no files available."""
        service = ModrinthService()
        
        mock_version_response = {
            "id": "version1",
            "files": []
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_version_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_file_download_url("version1")
            
            assert result == ""
    
    @pytest.mark.asyncio
    async def test_get_file_download_url_hash_mismatch(self):
        """Test getting download URL when hash doesn't match."""
        service = ModrinthService()
        
        mock_version_response = {
            "id": "version1",
            "files": [
                {
                    "url": "https://cdn.modrinth.com/test.jar",
                    "hashes": {"sha1": "abc123"},
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.return_value = MagicMock(
                json=lambda: mock_version_response,
                raise_for_status=Mock()
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            result = await service.get_file_download_url("version1", file_hash="wrong_hash")
            
            # Should return empty string when hash doesn't match
            assert result == ""
    
    def test_parse_url_empty_string(self):
        """Test parsing empty string."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url("")
        
        assert result is None
    
    def test_parse_url_none(self):
        """Test parsing None."""
        service = ModrinthService()
        
        result = service.parse_modrinth_url(None)
        
        assert result is None


class TestModrinthServiceIntegration:
    """Integration tests for ModrinthService."""
    
    @pytest.mark.asyncio
    async def test_full_search_workflow(self):
        """Test full search workflow."""
        service = ModrinthService()
        
        mock_search_response = {
            "hits": [
                {
                    "project_id": "abc123",
                    "title": "Test Mod",
                    "description": "A test mod",
                    "downloads": 1000,
                }
            ],
            "offset": 0,
            "limit": 25,
            "total_hits": 1,
        }
        
        mock_project_response = {
            "id": "abc123",
            "slug": "test-mod",
            "title": "Test Mod",
            "description": "A test mod",
            "downloads": 1000,
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            
            # Setup multiple responses
            call_count = [0]
            def get_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return MagicMock(
                        json=lambda: mock_search_response,
                        raise_for_status=Mock()
                    )
                else:
                    return MagicMock(
                        json=lambda: mock_project_response,
                        raise_for_status=Mock()
                    )
            
            mock_instance.get = AsyncMock(side_effect=get_side_effect)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            # Search for mods
            search_result = await service.search_mods("test")
            assert search_result["total_hits"] == 1
            
            # Get project details
            project = await service.get_project("abc123")
            assert project["slug"] == "test-mod"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])