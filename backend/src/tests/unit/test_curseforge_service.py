"""
Unit tests for CurseForgeService

Tests the CurseForge API integration service for mod search and download.

Issue: #483 - Integrate CurseForge/Modrinth API for Direct Import
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx

from services.curseforge_service import (
    CurseForgeService,
    curseforge_service,
    CURSEFORGE_API_BASE_URL,
)


class TestCurseForgeService:
    """Tests for CurseForgeService class."""
    
    def test_init_default(self):
        """Test service initialization with defaults."""
        service = CurseForgeService()
        
        assert service.base_url == CURSEFORGE_API_BASE_URL
        assert service.api_key is not None or service.api_key == ""
    
    def test_init_with_api_key(self):
        """Test service initialization with custom API key."""
        service = CurseForgeService(api_key="test_key_123")
        
        assert service.api_key == "test_key_123"
        assert "x-api-key" in service.headers
        assert service.headers["x-api-key"] == "test_key_123"
    
    def test_headers_without_api_key(self):
        """Test headers without API key."""
        service = CurseForgeService(api_key=None)
        
        assert "Accept" in service.headers
        assert "x-api-key" not in service.headers
    
    @pytest.mark.asyncio
    async def test_search_mods_success(self):
        """Test successful mod search."""
        service = CurseForgeService(api_key="test_key")
        
        mock_response = {
            "data": [
                {
                    "id": 12345,
                    "name": "Test Mod",
                    "summary": "A test mod",
                    "downloadCount": 1000,
                }
            ],
            "pagination": {
                "index": 0,
                "pageSize": 25,
                "resultCount": 1,
            }
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
            assert "data" in result
    
    @pytest.mark.asyncio
    async def test_search_mods_with_filters(self):
        """Test mod search with filters."""
        service = CurseForgeService(api_key="test_key")
        
        mock_response = {
            "data": [],
            "pagination": {"index": 0, "pageSize": 25, "resultCount": 0}
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
                category_id=6,
                sort_order="popularity",
                page_index=0,
                page_size=10
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_mod_info_success(self):
        """Test getting mod info."""
        service = CurseForgeService(api_key="test_key")
        
        mock_response = {
            "data": {
                "id": 12345,
                "name": "Test Mod",
                "summary": "A test mod",
                "downloadCount": 1000,
            }
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
            
            result = await service.get_mod_info(12345)
            
            assert result is not None
            assert result["data"]["id"] == 12345
    
    @pytest.mark.asyncio
    async def test_get_mod_files_success(self):
        """Test getting mod files."""
        service = CurseForgeService(api_key="test_key")
        
        mock_response = {
            "data": [
                {
                    "id": 98765,
                    "displayName": "test-mod-1.0.0.jar",
                    "gameVersion": ["1.20.1"],
                    "downloadCount": 500,
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
            
            result = await service.get_mod_files(12345, game_version="1.20.1")
            
            assert result is not None
            assert "data" in result
    
    @pytest.mark.asyncio
    async def test_get_file_download_url_success(self):
        """Test getting file download URL."""
        service = CurseForgeService(api_key="test_key")
        
        mock_response = {
            "data": "https://edge.forgecdn.net/files/1234/567/test-mod.jar"
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
            
            result = await service.get_file_download_url(12345, 98765)
            
            assert result is not None
            assert "forgecdn.net" in result
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self):
        """Test getting categories."""
        service = CurseForgeService(api_key="test_key")
        
        mock_response = {
            "data": [
                {"id": 6, "name": "World Gen", "classId": 5},
                {"id": 7, "name": "Biomes", "classId": 6},
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
            
            result = await service.get_categories(game_id=432)
            
            assert result is not None
            assert "data" in result
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test API error handling."""
        service = CurseForgeService(api_key="test_key")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock()
            mock_instance.get.side_effect = httpx.HTTPError("API Error")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            with pytest.raises(httpx.HTTPError):
                await service.search_mods("test")


class TestCurseForgeURLParsing:
    """Tests for CurseForge URL parsing."""
    
    def test_parse_standard_url(self):
        """Test parsing standard CurseForge URL."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url(
            "https://www.curseforge.com/minecraft/mods/test-mod"
        )
        
        assert result is not None
        assert result["platform"] == "curseforge"
        assert result["slug"] == "test-mod"
    
    def test_parse_url_without_www(self):
        """Test parsing URL without www."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url(
            "https://curseforge.com/minecraft/mods/another-mod"
        )
        
        assert result is not None
        assert result["slug"] == "another-mod"
    
    def test_parse_url_with_query_params(self):
        """Test parsing URL with query parameters."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url(
            "https://www.curseforge.com/minecraft/mods/test-mod?param=value"
        )
        
        assert result is not None
        assert result["slug"] == "test-mod"
    
    def test_parse_invalid_url(self):
        """Test parsing invalid URL."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url(
            "https://example.com/something/else"
        )
        
        assert result is None
    
    def test_parse_non_curseforge_url(self):
        """Test parsing non-CurseForge URL."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url(
            "https://modrinth.com/mod/test-mod"
        )
        
        assert result is None
    
    def test_parse_url_with_trailing_slash(self):
        """Test parsing URL with trailing slash."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url(
            "https://www.curseforge.com/minecraft/mods/test-mod/"
        )
        
        assert result is not None
        assert result["slug"] == "test-mod"


class TestCurseForgeServiceSingleton:
    """Tests for singleton instance."""
    
    def test_singleton_exists(self):
        """Test that singleton instance exists."""
        assert curseforge_service is not None
        assert isinstance(curseforge_service, CurseForgeService)
    
    def test_singleton_is_consistent(self):
        """Test that singleton is consistent."""
        from services.curseforge_service import curseforge_service as service2
        
        assert curseforge_service is service2


class TestCurseForgeServiceEdgeCases:
    """Tests for edge cases."""
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """Test search with empty query."""
        service = CurseForgeService(api_key="test_key")
        
        mock_response = {"data": [], "pagination": {}}
        
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
    async def test_get_mod_info_nonexistent(self):
        """Test getting info for nonexistent mod."""
        service = CurseForgeService(api_key="test_key")
        
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
                await service.get_mod_info(999999999)
    
    def test_parse_url_empty_string(self):
        """Test parsing empty string."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url("")
        
        assert result is None
    
    def test_parse_url_none(self):
        """Test parsing None."""
        service = CurseForgeService()
        
        result = service.parse_curseforge_url(None)
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])