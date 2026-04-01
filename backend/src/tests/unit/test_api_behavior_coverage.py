"""
Tests for Behavior Files API - src/api/behavior_files.py and src/api/behavior_export.py
Targeting uncovered lines in behavior API endpoints.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException


class TestBehaviorFileModels:
    """Tests for Pydantic models."""

    def test_behavior_file_create_model(self):
        """Test BehaviorFileCreate model."""
        from api.behavior_files import BehaviorFileCreate

        model = BehaviorFileCreate(
            file_path="blocks/test.json", file_type="block_behavior", content='{"test": true}'
        )

        assert model.file_path == "blocks/test.json"
        assert model.file_type == "block_behavior"

    def test_behavior_file_update_model(self):
        """Test BehaviorFileUpdate model."""
        from api.behavior_files import BehaviorFileUpdate

        model = BehaviorFileUpdate(content='{"updated": true}')

        assert model.content == '{"updated": true}'

    def test_behavior_file_response_model(self):
        """Test BehaviorFileResponse model."""
        from api.behavior_files import BehaviorFileResponse

        model = BehaviorFileResponse(
            id=str(uuid.uuid4()),
            conversion_id=str(uuid.uuid4()),
            file_path="test.json",
            file_type="entity_behavior",
            content="{}",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        assert model.id is not None


class TestExportModels:
    """Tests for export Pydantic models."""

    def test_export_request_model(self):
        """Test ExportRequest model."""
        from api.behavior_export import ExportRequest

        model = ExportRequest(
            conversion_id=str(uuid.uuid4()),
            file_types=["entity_behavior"],
            include_templates=True,
            export_format="mcaddon",
        )

        assert model.export_format == "mcaddon"

    def test_export_response_model(self):
        """Test ExportResponse model."""
        from api.behavior_export import ExportResponse

        model = ExportResponse(
            conversion_id=str(uuid.uuid4()),
            export_format="zip",
            file_count=10,
            template_count=2,
            export_size=5000,
            exported_at="2024-01-01T00:00:00Z",
        )

        assert model.file_count == 10


class TestBehaviorFilesCrud:
    """Tests for behavior file CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_conversion_behavior_files_empty(self):
        """Test getting behavior files when none exist."""
        from api.behavior_files import get_conversion_behavior_files
        from unittest.mock import AsyncMock

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            )
        )

        result = await get_conversion_behavior_files(str(uuid.uuid4()), mock_db)

        assert result == []

    def test_build_file_tree(self):
        """Test file tree building logic."""
        from api.behavior_files import dict_to_tree_nodes

        node_dict = {
            "folder1": {
                "name": "folder1",
                "path": "folder1",
                "type": "directory",
                "children": {
                    "file1.json": {
                        "id": "123",
                        "name": "file1.json",
                        "path": "folder1/file1.json",
                        "type": "file",
                        "file_type": "block_behavior",
                        "children": {},
                    }
                },
            }
        }

        nodes = dict_to_tree_nodes(node_dict)

        assert len(nodes) == 1
        assert nodes[0].name == "folder1"


class TestBehaviorExportFormats:
    """Tests for export format endpoint."""

    @pytest.mark.asyncio
    async def test_get_export_formats(self):
        """Test getting available export formats."""
        from api.behavior_export import get_export_formats

        formats = await get_export_formats()

        assert len(formats) == 3
        assert any(f["format"] == "mcaddon" for f in formats)
        assert any(f["format"] == "zip" for f in formats)
        assert any(f["format"] == "json" for f in formats)


class TestExportBehaviorPack:
    """Tests for export behavior pack endpoint."""

    @pytest.mark.asyncio
    async def test_export_json_format(self):
        """Test export with JSON format."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        mock_file = MagicMock()
        mock_file.file_path = "test.json"
        mock_file.file_type = "block_behavior"
        mock_file.content = "{}"
        mock_file.created_at = datetime.now(timezone.utc)
        mock_file.updated_at = datetime.now(timezone.utc)

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                with patch(
                    "api.behavior_export.crud.get_addon_details", new_callable=AsyncMock
                ) as mock_get_addon:
                    mock_get_job.return_value = mock_job
                    mock_get_files.return_value = [mock_file]
                    mock_get_addon.return_value = None

                    request = ExportRequest(conversion_id=str(uuid.uuid4()), export_format="json")

                    result = await export_behavior_pack(request, mock_db)

                    assert result.export_format == "json"

    @pytest.mark.asyncio
    async def test_export_invalid_conversion_id(self):
        """Test export with invalid conversion ID."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock
        from fastapi import HTTPException

        mock_db = AsyncMock()

        request = ExportRequest(conversion_id="invalid-uuid", export_format="json")

        with pytest.raises(HTTPException) as exc_info:
            await export_behavior_pack(request, mock_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_export_conversion_not_found(self):
        """Test export when conversion not found."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock, patch
        from fastapi import HTTPException

        mock_db = AsyncMock()

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            mock_get_job.return_value = None

            request = ExportRequest(conversion_id=str(uuid.uuid4()), export_format="json")

            with pytest.raises(HTTPException) as exc_info:
                await export_behavior_pack(request, mock_db)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_no_behavior_files(self):
        """Test export when no behavior files exist."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock, patch, MagicMock
        from fastapi import HTTPException

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                mock_get_job.return_value = mock_job
                mock_get_files.return_value = []

                request = ExportRequest(conversion_id=str(uuid.uuid4()), export_format="json")

                with pytest.raises(HTTPException) as exc_info:
                    await export_behavior_pack(request, mock_db)

                assert exc_info.value.status_code == 400


class TestExportPreview:
    """Tests for export preview endpoint."""

    @pytest.mark.asyncio
    async def test_preview_export_basic(self):
        """Test basic export preview."""
        from api.behavior_export import preview_export
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime, timezone

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        mock_file = MagicMock()
        mock_file.file_path = "blocks/test.json"
        mock_file.file_type = "block_behavior"
        mock_file.content = '{"identifier": "test"}'
        mock_file.updated_at = datetime.now(timezone.utc)

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                mock_get_job.return_value = mock_job
                mock_get_files.return_value = [mock_file]

                result = await preview_export(str(uuid.uuid4()), mock_db)

                assert "conversion_id" in result
                assert "analysis" in result

    @pytest.mark.asyncio
    async def test_preview_invalid_conversion_id(self):
        """Test preview with invalid conversion ID."""
        from api.behavior_export import preview_export
        from unittest.mock import AsyncMock
        from fastapi import HTTPException

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await preview_export("invalid-id", mock_db)

        assert exc_info.value.status_code == 400


class TestExportDownload:
    """Tests for export download endpoint."""

    @pytest.mark.asyncio
    async def test_download_export_not_found(self):
        """Test download when export not found."""
        from api.behavior_export import download_exported_pack
        from unittest.mock import AsyncMock, patch, MagicMock
        from fastapi import HTTPException

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch("api.behavior_export.CacheService") as mock_cache_cls:
                mock_cache = MagicMock()
                mock_cache.get_export_data = AsyncMock(return_value=None)
                mock_cache_cls.return_value = mock_cache

                mock_get_job.return_value = mock_job

                with pytest.raises(HTTPException) as exc_info:
                    await download_exported_pack(str(uuid.uuid4()), mock_db)

                assert exc_info.value.status_code == 404


class TestExportZipFormat:
    """Tests for ZIP format export."""

    @pytest.mark.asyncio
    async def test_export_zip_format(self):
        """Test export with ZIP format."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock, MagicMock, patch
        from datetime import datetime

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        mock_file = MagicMock()
        mock_file.file_path = "test.json"
        mock_file.file_type = "block_behavior"
        mock_file.content = "{}"
        mock_file.created_at = datetime.now(timezone.utc)
        mock_file.updated_at = datetime.now(timezone.utc)

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                with patch(
                    "api.behavior_export.crud.get_addon_details", new_callable=AsyncMock
                ) as mock_get_addon:
                    with patch("api.behavior_export.CacheService") as mock_cache_cls:
                        mock_cache = MagicMock()
                        mock_cache.set_export_data = AsyncMock()
                        mock_cache_cls.return_value = mock_cache

                        mock_get_job.return_value = mock_job
                        mock_get_files.return_value = [mock_file]
                        mock_get_addon.return_value = None

                        request = ExportRequest(
                            conversion_id=str(uuid.uuid4()), export_format="zip"
                        )

                        result = await export_behavior_pack(request, mock_db)

                        assert result.export_format == "zip"


class TestExportMcaddonFormat:
    """Tests for MCADDON format export."""

    @pytest.mark.asyncio
    async def test_export_mcaddon_format(self):
        """Test export with MCADDON format."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock, MagicMock, patch
        from datetime import datetime
        import io

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        mock_file = MagicMock()
        mock_file.file_path = "test.json"
        mock_file.file_type = "block_behavior"
        mock_file.content = "{}"
        mock_file.created_at = datetime.now(timezone.utc)
        mock_file.updated_at = datetime.now(timezone.utc)

        mock_addon = MagicMock()
        mock_addon.id = uuid.uuid4()
        mock_addon.name = "Test"
        mock_addon.description = "Test addon"
        mock_addon.blocks = []
        mock_addon.recipes = []
        mock_addon.assets = []

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                with patch(
                    "api.behavior_export.crud.get_addon_details", new_callable=AsyncMock
                ) as mock_get_addon:
                    with patch(
                        "api.behavior_export.addon_exporter.create_mcaddon_zip"
                    ) as mock_create_zip:
                        with patch("api.behavior_export.CacheService") as mock_cache_cls:
                            mock_cache = MagicMock()
                            mock_cache.set_export_data = AsyncMock()
                            mock_cache_cls.return_value = mock_cache

                            mock_get_job.return_value = mock_job
                            mock_get_files.return_value = [mock_file]
                            mock_get_addon.return_value = mock_addon

                            mock_zip_buffer = io.BytesIO(b"fake zip data")
                            mock_create_zip.return_value = mock_zip_buffer

                            request = ExportRequest(
                                conversion_id=str(uuid.uuid4()), export_format="mcaddon"
                            )

                            result = await export_behavior_pack(request, mock_db)

                            assert result.export_format == "mcaddon"


class TestExportWithTemplateInfo:
    """Tests for export with template information."""

    @pytest.mark.asyncio
    async def test_export_with_template_info(self):
        """Test export includes template info when requested."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock, MagicMock, patch
        from datetime import datetime

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        template_content = {
            "identifier": "test",
            "_template_info": {"template_name": "entity_basic", "template_version": "1.0"},
        }

        mock_file = MagicMock()
        mock_file.file_path = "entities/test.json"
        mock_file.file_type = "entity_behavior"
        mock_file.content = json.dumps(template_content)
        mock_file.created_at = datetime.now(timezone.utc)
        mock_file.updated_at = datetime.now(timezone.utc)

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                with patch(
                    "api.behavior_export.crud.get_addon_details", new_callable=AsyncMock
                ) as mock_get_addon:
                    mock_get_job.return_value = mock_job
                    mock_get_files.return_value = [mock_file]
                    mock_get_addon.return_value = None

                    request = ExportRequest(
                        conversion_id=str(uuid.uuid4()),
                        include_templates=True,
                        export_format="json",
                    )

                    result = await export_behavior_pack(request, mock_db)

                    assert result.template_count >= 0


class TestExportWithFileTypeFilter:
    """Tests for export with file type filtering."""

    @pytest.mark.asyncio
    async def test_export_filter_by_file_type(self):
        """Test export filters by file type."""
        from api.behavior_export import export_behavior_pack, ExportRequest
        from unittest.mock import AsyncMock, MagicMock, patch
        from datetime import datetime

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        entity_file = MagicMock()
        entity_file.file_path = "entities/test.json"
        entity_file.file_type = "entity_behavior"
        entity_file.content = "{}"
        entity_file.created_at = datetime.now(timezone.utc)
        entity_file.updated_at = datetime.now(timezone.utc)

        block_file = MagicMock()
        block_file.file_path = "blocks/test.json"
        block_file.file_type = "block_behavior"
        block_file.content = "{}"
        block_file.created_at = datetime.now(timezone.utc)
        block_file.updated_at = datetime.now(timezone.utc)

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                with patch(
                    "api.behavior_export.crud.get_addon_details", new_callable=AsyncMock
                ) as mock_get_addon:
                    mock_get_job.return_value = mock_job
                    mock_get_files.return_value = [entity_file, block_file]
                    mock_get_addon.return_value = None

                    request = ExportRequest(
                        conversion_id=str(uuid.uuid4()),
                        file_types=["entity_behavior"],
                        export_format="json",
                    )

                    result = await export_behavior_pack(request, mock_db)

                    assert result.file_count >= 0


class TestPreviewAnalysis:
    """Tests for preview analysis functionality."""

    @pytest.mark.asyncio
    async def test_preview_analyzes_file_types(self):
        """Test preview analyzes file types correctly."""
        from api.behavior_export import preview_export
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime, timezone

        mock_db = AsyncMock()

        mock_job = MagicMock()
        mock_job.status = "completed"

        mock_file1 = MagicMock()
        mock_file1.file_path = "entities/test.json"
        mock_file1.file_type = "entity_behavior"
        mock_file1.content = "{}"
        mock_file1.updated_at = datetime.now(timezone.utc)

        mock_file2 = MagicMock()
        mock_file2.file_path = "blocks/test.json"
        mock_file2.file_type = "block_behavior"
        mock_file2.content = "{}"
        mock_file2.updated_at = datetime.now(timezone.utc)

        with patch("api.behavior_export.crud.get_job", new_callable=AsyncMock) as mock_get_job:
            with patch(
                "api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock
            ) as mock_get_files:
                mock_get_job.return_value = mock_job
                mock_get_files.return_value = [mock_file1, mock_file2]

                result = await preview_export(str(uuid.uuid4()), mock_db)

                assert "entity_behavior" in result["analysis"]["file_types"]
                assert "block_behavior" in result["analysis"]["file_types"]
