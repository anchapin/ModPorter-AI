import pytest
import os
import zipfile
import json
from unittest.mock import MagicMock, patch, mock_open
from services.file_handler import FileHandler, ModLoader, ModMetadata, ValidationResult


@pytest.fixture
def file_handler():
    return FileHandler()


@pytest.mark.asyncio
async def test_validate_jar_file_not_found(file_handler):
    with patch("os.path.exists", return_value=False):
        result = await file_handler.validate_jar("nonexistent.jar")
        assert result.is_valid is False
        assert "File not found" in result.errors[0]


@pytest.mark.asyncio
async def test_validate_jar_empty_file(file_handler):
    with patch("os.path.exists", return_value=True), patch("os.path.getsize", return_value=0):
        result = await file_handler.validate_jar("empty.jar")
        assert result.is_valid is False
        assert "File is empty" in result.errors[0]


@pytest.mark.asyncio
async def test_validate_jar_invalid_zip(file_handler):
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=100),
        patch("zipfile.ZipFile", side_effect=zipfile.BadZipFile),
    ):
        result = await file_handler.validate_jar("invalid.jar")
        assert result.is_valid is False
        assert "Invalid ZIP/JAR file format" in result.errors[0]


@pytest.mark.asyncio
async def test_validate_jar_valid(file_handler):
    mock_zip = MagicMock()
    mock_zip.testzip.return_value = None
    mock_zip.namelist.return_value = ["META-INF/MANIFEST.MF", "some/class.class"]

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=100),
        patch(
            "zipfile.ZipFile", return_value=MagicMock(__enter__=MagicMock(return_value=mock_zip))
        ),
    ):
        result = await file_handler.validate_jar("valid.jar")
        assert result.is_valid is True
        assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_identify_mod_loader_fabric(file_handler):
    mock_zip = MagicMock()
    mock_zip.namelist.return_value = ["fabric.mod.json", "some/class.class"]

    with patch(
        "zipfile.ZipFile", return_value=MagicMock(__enter__=MagicMock(return_value=mock_zip))
    ):
        loader = await file_handler.identify_mod_loader("fabric.jar")
        assert loader == ModLoader.FABRIC


@pytest.mark.asyncio
async def test_identify_mod_loader_forge(file_handler):
    mock_zip = MagicMock()
    mock_zip.namelist.return_value = ["META-INF/mods.toml", "some/class.class"]

    with patch(
        "zipfile.ZipFile", return_value=MagicMock(__enter__=MagicMock(return_value=mock_zip))
    ):
        loader = await file_handler.identify_mod_loader("forge.jar")
        assert loader == ModLoader.FORGE


@pytest.mark.asyncio
async def test_identify_mod_loader_neoforge(file_handler):
    mock_zip = MagicMock()
    mock_zip.namelist.return_value = ["META-INF/neoforge.mods.toml", "some/class.class"]

    with patch(
        "zipfile.ZipFile", return_value=MagicMock(__enter__=MagicMock(return_value=mock_zip))
    ):
        loader = await file_handler.identify_mod_loader("neoforge.jar")
        assert loader == ModLoader.NEOFORGE


@pytest.mark.asyncio
async def test_extract_metadata_fabric(file_handler):
    mock_zip = MagicMock()
    mock_zip.namelist.return_value = ["fabric.mod.json"]
    fabric_data = {
        "id": "test-mod",
        "name": "Test Mod",
        "version": "1.0.0",
        "description": "A test mod",
        "authors": ["Author1"],
        "depends": {"fabricloader": ">=0.14.0"},
    }
    mock_zip.read.return_value = json.dumps(fabric_data).encode("utf-8")

    with patch(
        "zipfile.ZipFile", return_value=MagicMock(__enter__=MagicMock(return_value=mock_zip))
    ):
        metadata = await file_handler.extract_metadata("fabric.jar")
        assert metadata.modid == "test-mod"
        assert metadata.name == "Test Mod"
        assert metadata.version == "1.0.0"
        assert "fabricloader" in metadata.dependencies


@pytest.mark.asyncio
async def test_process_file_success(file_handler):
    job_id = "test-job"
    file_path = "test.jar"

    with (
        patch.object(file_handler, "validate_jar", return_value=ValidationResult(is_valid=True)),
        patch.object(file_handler, "extract_metadata", return_value=ModMetadata(modid="test")),
        patch.object(file_handler, "identify_mod_loader", return_value=ModLoader.FORGE),
        patch.object(file_handler, "virus_scan_placeholder", return_value=True),
    ):
        result = await file_handler.process_file(job_id, file_path)
        assert result.success is True
        assert result.metadata.modid == "test"
        assert result.metadata.mod_loader == ModLoader.FORGE

        status = await file_handler.get_upload_status(job_id)
        assert status["status"] == "completed"
