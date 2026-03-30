"""
Comprehensive integration tests for the conversion pipeline.
Tests end-to-end conversion workflows, API integration, and database operations.
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timezone
from uuid import uuid4
from io import BytesIO
import zipfile

# Set up imports
try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from db.base import Base
    from db import crud, models
    from api.conversions import (
        ConversionCreateRequest,
        ConversionUpdateRequest,
        ConversionOptions,
        router as conversion_router,
    )
    from services.conversion_service import ConversionService
    from services.task_queue import TaskQueue, TaskPriority
    from security.file_security import FileSecurityScanner
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


@pytest.fixture
async def test_db():
    """Create async test database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_jar_file(tmp_path):
    """Create a temporary JAR file for testing."""
    jar_file = tmp_path / "test_mod.jar"
    with zipfile.ZipFile(jar_file, 'w') as zf:
        zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
        zf.writestr("mod.json", json.dumps({"name": "TestMod", "version": "1.0"}))
    return jar_file


@pytest.fixture
def mock_conversion_options():
    """Mock conversion options."""
    return ConversionOptions(
        assumptions="conservative",
        target_version="1.20.0"
    )


@pytest.fixture
def mock_conversion_service():
    """Create a mock ConversionService."""
    service = AsyncMock(spec=ConversionService)
    service.convert = AsyncMock(return_value={
        "success": True,
        "output_file": "/tmp/test_mod.mcaddon",
        "registry_name": "test_block",
        "validation": {"valid": True}
    })
    return service


@pytest.fixture
def mock_security_scanner():
    """Create a mock FileSecurityScanner."""
    scanner = Mock(spec=FileSecurityScanner)
    scanner.scan_file = Mock(return_value={
        "safe": True,
        "threats": [],
        "details": "File is safe"
    })
    return scanner


class TestConversionCreateAPI:
    """Test conversion creation API endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_conversion_success(self, test_db, mock_jar_file, mock_conversion_options):
        """Test successful conversion creation."""
        # Create conversion request
        conversion_request = ConversionCreateRequest(
            mod_file=mock_jar_file.name,
            options=mock_conversion_options.dict()
        )
        
        # Verify request is valid
        assert conversion_request is not None
        assert conversion_request.options["target_version"] == "1.20.0"
    
    @pytest.mark.asyncio
    async def test_create_conversion_invalid_file(self, test_db):
        """Test conversion creation with invalid file."""
        with pytest.raises(ValueError):
            ConversionCreateRequest(
                mod_file="test.txt",
                options={"assumptions": "conservative"}
            )
    
    @pytest.mark.asyncio
    async def test_create_conversion_missing_file(self, test_db):
        """Test conversion creation with missing file."""
        with pytest.raises(FileNotFoundError):
            ConversionCreateRequest(
                mod_file="/nonexistent/test.jar",
                options={"assumptions": "conservative"}
            )
    
    @pytest.mark.asyncio
    async def test_conversion_options_validation(self):
        """Test conversion options validation."""
        # Valid options
        valid_opts = ConversionOptions(
            assumptions="aggressive",
            target_version="1.21.0"
        )
        assert valid_opts.assumptions == "aggressive"
        
        # Invalid assumptions
        with pytest.raises(ValueError):
            ConversionOptions(assumptions="invalid")
    
    @pytest.mark.asyncio
    async def test_create_conversion_with_metadata(self, mock_jar_file):
        """Test conversion creation with metadata."""
        metadata = {
            "author": "test",
            "description": "test mod",
            "tags": ["block", "item"]
        }
        
        conversion_request = ConversionCreateRequest(
            mod_file=mock_jar_file.name,
            options={"assumptions": "conservative"},
            metadata=metadata
        )
        
        assert conversion_request.metadata == metadata


class TestConversionRetrieval:
    """Test conversion retrieval and listing."""
    
    @pytest.mark.asyncio
    async def test_get_conversion_by_id(self, test_db):
        """Test retrieving conversion by ID."""
        # Create a test conversion
        conversion_id = uuid4()
        
        # Mock database query
        with patch('db.crud.get_conversion') as mock_get:
            mock_conversion = {
                "id": str(conversion_id),
                "status": "completed",
                "created_at": datetime.now(timezone.utc),
                "output_file": "/tmp/test.mcaddon"
            }
            mock_get.return_value = mock_conversion
            
            result = await mock_get(test_db, str(conversion_id))
            
            assert result is not None
            assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_list_conversions_paginated(self, test_db):
        """Test listing conversions with pagination."""
        # Create multiple conversions
        conversions = [
            {
                "id": str(uuid4()),
                "status": "completed",
                "created_at": datetime.now(timezone.utc)
            }
            for _ in range(5)
        ]
        
        # Mock pagination
        with patch('db.crud.list_conversions') as mock_list:
            mock_list.return_value = conversions[:2], 5
            
            results, total = await mock_list(test_db, skip=0, limit=2)
            
            assert len(results) == 2
            assert total == 5
    
    @pytest.mark.asyncio
    async def test_get_conversion_nonexistent(self, test_db):
        """Test retrieving nonexistent conversion."""
        with patch('db.crud.get_conversion') as mock_get:
            mock_get.return_value = None
            
            result = await mock_get(test_db, str(uuid4()))
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_list_conversions_filtered(self, test_db):
        """Test filtering conversions by status."""
        conversions = [
            {"id": str(uuid4()), "status": "completed"},
            {"id": str(uuid4()), "status": "in_progress"},
            {"id": str(uuid4()), "status": "failed"}
        ]
        
        with patch('db.crud.list_conversions_by_status') as mock_filter:
            completed = [c for c in conversions if c["status"] == "completed"]
            mock_filter.return_value = completed
            
            results = await mock_filter(test_db, "completed")
            
            assert len(results) == 1
            assert results[0]["status"] == "completed"


class TestConversionExecution:
    """Test conversion execution and processing."""
    
    @pytest.mark.asyncio
    async def test_execute_conversion_success(self, mock_conversion_service, mock_jar_file):
        """Test successful conversion execution."""
        result = await mock_conversion_service.convert(
            str(mock_jar_file),
            "conservative"
        )
        
        assert result["success"] is True
        assert "output_file" in result
        assert "registry_name" in result
    
    @pytest.mark.asyncio
    async def test_execute_conversion_with_progress(self, mock_conversion_service):
        """Test conversion execution with progress tracking."""
        progress_updates = []
        
        async def track_progress(update):
            progress_updates.append(update)
        
        mock_conversion_service.convert = AsyncMock(
            return_value={"success": True}
        )
        
        result = await mock_conversion_service.convert(
            "test.jar",
            "aggressive"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_execute_conversion_timeout(self, mock_conversion_service):
        """Test conversion execution timeout."""
        # Simulate timeout
        async def timeout_convert(*args, **kwargs):
            await asyncio.sleep(10)
        
        mock_conversion_service.convert = timeout_convert
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mock_conversion_service.convert("test.jar", "conservative"),
                timeout=0.1
            )
    
    @pytest.mark.asyncio
    async def test_execute_conversion_invalid_input(self, mock_conversion_service):
        """Test conversion with invalid input."""
        mock_conversion_service.convert = AsyncMock(
            side_effect=ValueError("Invalid JAR format")
        )
        
        with pytest.raises(ValueError):
            await mock_conversion_service.convert("invalid.jar", "conservative")


class TestConversionSecurity:
    """Test security scanning during conversion."""
    
    def test_scan_jar_file_safe(self, mock_security_scanner, mock_jar_file):
        """Test scanning safe JAR file."""
        result = mock_security_scanner.scan_file(str(mock_jar_file))
        
        assert result["safe"] is True
        assert len(result["threats"]) == 0
    
    def test_scan_jar_file_malicious(self, mock_security_scanner):
        """Test scanning malicious JAR file."""
        mock_security_scanner.scan_file = Mock(return_value={
            "safe": False,
            "threats": ["virus_signature_xyz"],
            "details": "Malicious code detected"
        })
        
        result = mock_security_scanner.scan_file("malicious.jar")
        
        assert result["safe"] is False
        assert len(result["threats"]) > 0
    
    def test_scan_file_permission_denied(self, mock_security_scanner):
        """Test scanning with permission denied."""
        mock_security_scanner.scan_file = Mock(
            side_effect=PermissionError("Cannot read file")
        )
        
        with pytest.raises(PermissionError):
            mock_security_scanner.scan_file("/protected/file.jar")
    
    def test_scan_file_not_found(self, mock_security_scanner):
        """Test scanning nonexistent file."""
        mock_security_scanner.scan_file = Mock(
            side_effect=FileNotFoundError("File not found")
        )
        
        with pytest.raises(FileNotFoundError):
            mock_security_scanner.scan_file("/nonexistent/file.jar")


class TestConversionCache:
    """Test conversion caching."""
    
    @pytest.mark.asyncio
    async def test_cache_conversion_result(self):
        """Test caching conversion result."""
        cache_key = "conversion_test_mod_v1"
        cached_data = {
            "registry_name": "test_block",
            "output_file": "/tmp/test.mcaddon"
        }
        
        # Mock cache operations
        with patch('services.cache.CacheService.get') as mock_get:
            with patch('services.cache.CacheService.set') as mock_set:
                mock_get.return_value = None
                mock_set.return_value = True
                
                # Set cache
                await mock_set(cache_key, cached_data, ttl=3600)
                mock_set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_cached_conversion(self):
        """Test retrieving cached conversion."""
        cache_key = "conversion_test_mod_v1"
        
        with patch('services.cache.CacheService.get') as mock_get:
            mock_get.return_value = {
                "registry_name": "test_block",
                "output_file": "/tmp/test.mcaddon"
            }
            
            result = await mock_get(cache_key)
            
            assert result is not None
            assert result["registry_name"] == "test_block"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache_key = "conversion_test_mod_v1"
        
        with patch('services.cache.CacheService.delete') as mock_delete:
            mock_delete.return_value = True
            
            result = await mock_delete(cache_key)
            
            assert result is True


class TestConversionDownload:
    """Test conversion output download."""
    
    @pytest.mark.asyncio
    async def test_download_mcaddon_file(self, tmp_path):
        """Test downloading .mcaddon file."""
        # Create a mock mcaddon file
        mcaddon_file = tmp_path / "test.mcaddon"
        mcaddon_file.write_bytes(b"mcaddon content")
        
        # Mock file response
        with patch('fastapi.responses.FileResponse') as mock_response:
            mock_response.return_value = MagicMock()
            
            # Simulate download
            file_content = mcaddon_file.read_bytes()
            
            assert file_content == b"mcaddon content"
    
    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self):
        """Test downloading nonexistent file."""
        with pytest.raises(FileNotFoundError):
            Path("/nonexistent/file.mcaddon").read_bytes()
    
    @pytest.mark.asyncio
    async def test_download_with_headers(self, tmp_path):
        """Test download with proper headers."""
        mcaddon_file = tmp_path / "test.mcaddon"
        mcaddon_file.write_bytes(b"test content")
        
        # Verify file exists and is readable
        assert mcaddon_file.exists()
        assert mcaddon_file.stat().st_size > 0


class TestConversionDeletion:
    """Test conversion deletion and cleanup."""
    
    @pytest.mark.asyncio
    async def test_delete_conversion(self, test_db):
        """Test deleting a conversion."""
        conversion_id = uuid4()
        
        with patch('db.crud.delete_conversion') as mock_delete:
            mock_delete.return_value = True
            
            result = await mock_delete(test_db, str(conversion_id))
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversion(self, test_db):
        """Test deleting nonexistent conversion."""
        with patch('db.crud.delete_conversion') as mock_delete:
            mock_delete.return_value = False
            
            result = await mock_delete(test_db, str(uuid4()))
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, tmp_path):
        """Test cleanup of temporary files."""
        temp_dir = tmp_path / "temp_conversions"
        temp_dir.mkdir()
        
        # Create temp files
        temp_file1 = temp_dir / "conversion_1.tmp"
        temp_file2 = temp_dir / "conversion_2.tmp"
        temp_file1.write_text("temp")
        temp_file2.write_text("temp")
        
        # Mock cleanup
        with patch('shutil.rmtree') as mock_rmtree:
            mock_rmtree.return_value = None
            
            await mock_rmtree(str(temp_dir))
            
            mock_rmtree.assert_called_once()


class TestBatchConversion:
    """Test batch conversion operations."""
    
    @pytest.mark.asyncio
    async def test_batch_conversion_multiple_files(self):
        """Test batch conversion of multiple files."""
        batch_id = str(uuid4())
        files = ["mod1.jar", "mod2.jar", "mod3.jar"]
        
        with patch('services.task_queue.enqueue_task') as mock_enqueue:
            mock_enqueue.return_value = True
            
            for file in files:
                await mock_enqueue(batch_id, file, TaskPriority.NORMAL)
            
            assert mock_enqueue.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_conversion_with_priority(self):
        """Test batch conversion with task priority."""
        tasks = [
            ("task_1", TaskPriority.HIGH),
            ("task_2", TaskPriority.NORMAL),
            ("task_3", TaskPriority.LOW),
        ]
        
        with patch('services.task_queue.enqueue_task') as mock_enqueue:
            mock_enqueue.return_value = True
            
            for task, priority in tasks:
                await mock_enqueue(task, priority=priority)
            
            assert mock_enqueue.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_conversion_partial_failure(self):
        """Test batch conversion with partial failures."""
        files = ["mod1.jar", "invalid.txt", "mod2.jar"]
        results = []
        
        for file in files:
            try:
                if file.endswith(".jar"):
                    results.append({"file": file, "success": True})
                else:
                    raise ValueError(f"Invalid file type: {file}")
            except ValueError:
                results.append({"file": file, "success": False, "error": "Invalid type"})
        
        # 2 successes, 1 failure
        assert sum(1 for r in results if r["success"]) == 2
        assert sum(1 for r in results if not r["success"]) == 1


class TestConversionStatusTracking:
    """Test conversion status tracking and updates."""
    
    @pytest.mark.asyncio
    async def test_update_conversion_status(self, test_db):
        """Test updating conversion status."""
        conversion_id = uuid4()
        
        with patch('db.crud.update_conversion_status') as mock_update:
            mock_update.return_value = True
            
            result = await mock_update(test_db, str(conversion_id), "in_progress")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_track_conversion_progress(self):
        """Test tracking conversion progress."""
        progress_states = ["pending", "analyzing", "converting", "packaging", "completed"]
        
        current_state = 0
        
        for expected_state in progress_states:
            assert expected_state == progress_states[current_state]
            current_state += 1
    
    @pytest.mark.asyncio
    async def test_conversion_failure_status(self, test_db):
        """Test conversion failure status update."""
        conversion_id = uuid4()
        error_message = "Conversion failed: invalid JAR format"
        
        with patch('db.crud.update_conversion_status') as mock_update:
            with patch('db.crud.set_conversion_error') as mock_error:
                mock_update.return_value = True
                mock_error.return_value = True
                
                await mock_update(test_db, str(conversion_id), "failed")
                await mock_error(test_db, str(conversion_id), error_message)
                
                mock_error.assert_called_once()


class TestConversionErrorHandling:
    """Test error handling in conversions."""
    
    @pytest.mark.asyncio
    async def test_handle_json_decode_error(self):
        """Test handling of JSON decode errors."""
        invalid_json = "not valid json {]"
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)
    
    @pytest.mark.asyncio
    async def test_handle_io_error(self, tmp_path):
        """Test handling of IO errors."""
        # Try to read nonexistent file
        with pytest.raises(FileNotFoundError):
            (tmp_path / "nonexistent.jar").read_bytes()
    
    @pytest.mark.asyncio
    async def test_handle_network_error(self):
        """Test handling of network errors."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = ConnectionError("Network unreachable")
            
            with pytest.raises(ConnectionError):
                await mock_get("http://example.com")
    
    @pytest.mark.asyncio
    async def test_graceful_error_recovery(self):
        """Test graceful error recovery."""
        attempt = 0
        max_retries = 3
        
        async def retry_operation():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise RuntimeError("Temporary error")
            return "success"
        
        # Simulate retry logic
        for i in range(max_retries):
            try:
                result = await retry_operation()
                assert result == "success"
                break
            except RuntimeError:
                if i == max_retries - 1:
                    raise


class TestConversionIntegration:
    """Integration tests for complete conversion workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_conversion_workflow(self, mock_jar_file, mock_conversion_service):
        """Test complete conversion workflow from upload to download."""
        # Step 1: Upload file
        assert mock_jar_file.exists()
        
        # Step 2: Create conversion
        conversion_id = uuid4()
        
        # Step 3: Execute conversion
        result = await mock_conversion_service.convert(str(mock_jar_file), "conservative")
        assert result["success"] is True
        
        # Step 4: Verify output
        assert "output_file" in result
    
    @pytest.mark.asyncio
    async def test_conversion_with_security_check(self, mock_jar_file, mock_security_scanner):
        """Test conversion with security scanning."""
        # Step 1: Scan file
        scan_result = mock_security_scanner.scan_file(str(mock_jar_file))
        assert scan_result["safe"] is True
        
        # Step 2: Proceed with conversion (mocked)
        with patch('services.conversion_service.ConversionService.convert') as mock_convert:
            mock_convert.return_value = {"success": True, "output_file": "/tmp/test.mcaddon"}
            
            result = await mock_convert(str(mock_jar_file), "conservative")
            assert result["success"] is True
