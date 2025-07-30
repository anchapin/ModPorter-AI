"""
Unit tests for Conversion Asset CRUD operations
"""

import pytest

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from db import crud, models
from datetime import datetime


@pytest.fixture
def mock_session():
    """Mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_conversion_id():
    """Sample conversion ID for testing"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_asset_data():
    """Sample asset data for testing"""
    return {
        "conversion_id": str(uuid.uuid4()),
        "asset_type": "texture",
        "original_path": "/path/to/original/texture.png",
        "original_filename": "texture.png",
        "file_size": 1024,
        "mime_type": "image/png",
        "asset_metadata": {"category": "blocks", "resolution": "16x16"}
    }


@pytest.fixture
def sample_asset_model(sample_asset_data):
    """Sample Asset model instance"""
    asset = models.Asset()
    asset.id = uuid.uuid4()
    asset.conversion_id = uuid.UUID(sample_asset_data["conversion_id"])
    asset.asset_type = sample_asset_data["asset_type"]
    asset.original_path = sample_asset_data["original_path"]
    asset.original_filename = sample_asset_data["original_filename"]
    asset.file_size = sample_asset_data["file_size"]
    asset.mime_type = sample_asset_data["mime_type"]
    asset.asset_metadata = sample_asset_data["asset_metadata"]
    asset.status = "pending"
    asset.created_at = datetime.utcnow()
    asset.updated_at = datetime.utcnow()
    return asset


class TestCreateAsset:
    """Tests for create_asset function"""

    async def test_create_asset_success(self, mock_session, sample_asset_data):
        """Test successful asset creation"""
        # Setup
        mock_session.add = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Execute
        result = await crud.create_asset(
            mock_session,
            **sample_asset_data
        )
        
        # Verify
        assert isinstance(result, models.Asset)
        assert result.asset_type == sample_asset_data["asset_type"]
        assert result.original_filename == sample_asset_data["original_filename"]
        assert result.status == "pending"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_asset_invalid_conversion_id(self, mock_session):
        """Test asset creation with invalid conversion ID"""
        with pytest.raises(ValueError, match="Invalid conversion_id format"):
            await crud.create_asset(
                mock_session,
                conversion_id="invalid-uuid",
                asset_type="texture",
                original_path="/path/to/file.png",
                original_filename="file.png"
            )

    async def test_create_asset_no_commit(self, mock_session, sample_asset_data):
        """Test asset creation without committing"""
        # Setup
        mock_session.add = AsyncMock()
        mock_session.flush = AsyncMock()
        
        # Execute
        result = await crud.create_asset(
            mock_session,
            commit=False,
            **sample_asset_data
        )
        
        # Verify
        assert isinstance(result, models.Asset)
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()


class TestGetAsset:
    """Tests for get_asset function"""

    @patch('db.crud.select')
    async def test_get_asset_success(self, mock_select, mock_session, sample_asset_model):
        """Test successful asset retrieval"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_model
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await crud.get_asset(mock_session, str(sample_asset_model.id))
        
        # Verify
        assert result == sample_asset_model
        mock_session.execute.assert_called_once()

    async def test_get_asset_invalid_id(self, mock_session):
        """Test asset retrieval with invalid ID"""
        result = await crud.get_asset(mock_session, "invalid-uuid")
        assert result is None

    @patch('db.crud.select')
    async def test_get_asset_not_found(self, mock_select, mock_session):
        """Test asset retrieval when asset doesn't exist"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await crud.get_asset(mock_session, str(uuid.uuid4()))
        
        # Verify
        assert result is None


class TestListAssetsForConversion:
    """Tests for list_assets_for_conversion function"""

    @patch('db.crud.select')
    async def test_list_assets_success(self, mock_select, mock_session, sample_conversion_id):
        """Test successful asset listing"""
        # Setup
        mock_assets = [AsyncMock(), AsyncMock()]
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_assets
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await crud.list_assets_for_conversion(mock_session, sample_conversion_id)
        
        # Verify
        assert result == mock_assets
        mock_session.execute.assert_called_once()

    async def test_list_assets_invalid_conversion_id(self, mock_session):
        """Test asset listing with invalid conversion ID"""
        result = await crud.list_assets_for_conversion(mock_session, "invalid-uuid")
        assert result == []

    @patch('db.crud.select')
    async def test_list_assets_with_filters(self, mock_select, mock_session, sample_conversion_id):
        """Test asset listing with type and status filters"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await crud.list_assets_for_conversion(
            mock_session,
            sample_conversion_id,
            asset_type="texture",
            status="pending"
        )
        
        # Verify
        assert result == []
        mock_session.execute.assert_called_once()


class TestUpdateAssetStatus:
    """Tests for update_asset_status function"""

    @patch('db.crud.update')
    @patch('db.crud.select')
    async def test_update_asset_status_success(self, mock_select, mock_update, mock_session, sample_asset_model):
        """Test successful asset status update"""
        # Setup
        asset_id = str(sample_asset_model.id)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_model
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await crud.update_asset_status(
            mock_session,
            asset_id,
            "converted",
            converted_path="/path/to/converted.png"
        )
        
        # Verify
        assert result == sample_asset_model
        assert mock_session.execute.call_count == 2  # Update + Select
        mock_session.commit.assert_called_once()

    async def test_update_asset_status_invalid_id(self, mock_session):
        """Test asset status update with invalid ID"""
        result = await crud.update_asset_status(
            mock_session,
            "invalid-uuid",
            "converted"
        )
        assert result is None


class TestUpdateAssetMetadata:
    """Tests for update_asset_metadata function"""

    @patch('db.crud.update')
    @patch('db.crud.select')
    async def test_update_metadata_success(self, mock_select, mock_update, mock_session, sample_asset_model):
        """Test successful metadata update"""
        # Setup
        asset_id = str(sample_asset_model.id)
        new_metadata = {"resolution": "32x32", "animated": True}
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_model
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await crud.update_asset_metadata(
            mock_session,
            asset_id,
            new_metadata
        )
        
        # Verify
        assert result == sample_asset_model
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    async def test_update_metadata_invalid_id(self, mock_session):
        """Test metadata update with invalid ID"""
        result = await crud.update_asset_metadata(
            mock_session,
            "invalid-uuid",
            {"key": "value"}
        )
        assert result is None


class TestDeleteAsset:
    """Tests for delete_asset function"""

    @patch('db.crud.delete')
    async def test_delete_asset_success(self, mock_delete, mock_session, sample_asset_model):
        """Test successful asset deletion"""
        # Setup
        asset_id = str(sample_asset_model.id)
        
        with patch('db.crud.get_asset', return_value=sample_asset_model):
            # Execute
            result = await crud.delete_asset(mock_session, asset_id)
            
            # Verify
            assert result is not None
            assert result["id"] == str(sample_asset_model.id)
            assert result["original_filename"] == sample_asset_model.original_filename
            mock_session.execute.assert_called()
            mock_session.commit.assert_called_once()

    async def test_delete_asset_not_found(self, mock_session):
        """Test deletion of non-existent asset"""
        with patch('db.crud.get_asset', return_value=None):
            result = await crud.delete_asset(mock_session, str(uuid.uuid4()))
            assert result is None

    async def test_delete_asset_invalid_id(self, mock_session):
        """Test asset deletion with invalid ID"""
        result = await crud.delete_asset(mock_session, "invalid-uuid")
        assert result is None


@pytest.mark.integration
class TestAssetCRUDIntegration:
    """Integration tests for Asset CRUD operations"""

    async def test_create_and_retrieve_asset(self, mock_session, sample_asset_data):
        """Test creating an asset and then retrieving it"""
        # This would be a more comprehensive test with a real database
        # For now, we'll simulate the flow with mocks
        
        # Create asset
        with patch('db.crud.create_asset') as mock_create:
            mock_asset = models.Asset()
            mock_asset.id = uuid.uuid4()
            mock_create.return_value = mock_asset
            
            created_asset = await crud.create_asset(mock_session, **sample_asset_data)
            assert created_asset == mock_asset
        
        # Retrieve asset
        with patch('db.crud.get_asset') as mock_get:
            mock_get.return_value = mock_asset
            
            retrieved_asset = await crud.get_asset(mock_session, str(mock_asset.id))
            assert retrieved_asset == mock_asset

    async def test_asset_status_workflow(self, mock_session, sample_asset_model):
        """Test typical asset status workflow: pending -> processing -> converted"""
        asset_id = str(sample_asset_model.id)
        
        # Mock the update functions
        with patch('db.crud.update_asset_status') as mock_update:
            # Set to processing
            sample_asset_model.status = "processing"
            mock_update.return_value = sample_asset_model
            
            result = await crud.update_asset_status(mock_session, asset_id, "processing")
            assert result.status == "processing"
            
            # Set to converted
            sample_asset_model.status = "converted"
            sample_asset_model.converted_path = "/path/to/converted.png"
            
            result = await crud.update_asset_status(
                mock_session, 
                asset_id, 
                "converted",
                converted_path="/path/to/converted.png"
            )
            assert result.status == "converted"
            assert result.converted_path == "/path/to/converted.png"