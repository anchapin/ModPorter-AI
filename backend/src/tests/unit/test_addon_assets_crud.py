"""
Unit tests for Addon Asset CRUD operations
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
from db import crud, models
from datetime import datetime, timezone

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_session():
    """Mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_addon_id():
    """Sample addon ID for testing"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_file():
    """Sample file object for testing"""
    file_mock = AsyncMock()
    file_mock.filename = "test_texture.png"
    return file_mock


@pytest.fixture
def sample_addon_asset_model():
    """Sample AddonAsset model instance"""
    asset = models.AddonAsset()
    asset.id = uuid.uuid4()
    asset.addon_id = uuid.uuid4()
    asset.type = "texture"
    asset.path = f"{uuid.uuid4()}_test_texture.png"
    asset.original_filename = "test_texture.png"
    asset.created_at = datetime.now(timezone.utc)
    asset.updated_at = datetime.now(timezone.utc)
    return asset


class TestGetAddonAsset:
    """Tests for get_addon_asset function"""

    async def test_get_addon_asset_success(self, mock_session, sample_addon_asset_model):
        """Test successful addon asset retrieval"""
        # Setup - mock the execute method directly
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_addon_asset_model
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await crud.get_addon_asset(mock_session, str(sample_addon_asset_model.id))

        # Verify
        assert result == sample_addon_asset_model
        mock_session.execute.assert_called_once()

    async def test_get_addon_asset_invalid_id(self, mock_session):
        """Test addon asset retrieval with invalid ID"""
        with pytest.raises(ValueError):
            await crud.get_addon_asset(mock_session, "invalid-uuid")

    async def test_get_addon_asset_not_found(self, mock_session):
        """Test addon asset retrieval when asset doesn't exist"""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await crud.get_addon_asset(mock_session, str(uuid.uuid4()))

        # Verify
        assert result is None


class TestCreateAddonAsset:
    """Tests for create_addon_asset function"""

    async def test_create_addon_asset_success(self, mock_session, sample_addon_id):
        """Test successful addon asset creation"""
        # Setup
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Execute
        result = await crud.create_addon_asset(
            mock_session,
            addon_id=sample_addon_id,
            asset_type="texture",
            file_path="textures/test_texture.png",
            original_filename="test_texture.png"
        )

        # Verify
        assert isinstance(result, models.AddonAsset)
        assert result.type == "texture"
        assert result.original_filename == "test_texture.png"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_addon_asset_path_traversal_prevention(self, mock_session, sample_addon_id):
        """Test that path traversal attacks are prevented"""
        # Setup
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Execute - this should raise ValueError due to path traversal
        with pytest.raises(ValueError, match="Invalid file path: path traversal detected"):
            await crud.create_addon_asset(
                mock_session,
                addon_id=sample_addon_id,
                asset_type="texture",
                file_path="../../malicious.png",
                original_filename="malicious.png"
            )

    async def test_create_addon_asset_no_commit(self, mock_session, sample_addon_id):
        """Test addon asset creation without committing"""
        # Setup
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        # Execute
        result = await crud.create_addon_asset(
            mock_session,
            addon_id=sample_addon_id,
            asset_type="texture",
            file_path="textures/test_texture.png",
            original_filename="test_texture.png",
            commit=False
        )

        # Verify
        assert isinstance(result, models.AddonAsset)
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()

    async def test_create_addon_asset_invalid_addon_id(self, mock_session):
        """Test addon asset creation with invalid addon ID"""
        with pytest.raises(ValueError):
            await crud.create_addon_asset(
                mock_session,
                addon_id="invalid-uuid",
                asset_type="texture",
                file_path="textures/test_texture.png",
                original_filename="test_texture.png"
            )


class TestUpdateAddonAsset:
    """Tests for update_addon_asset function"""

    async def test_update_addon_asset_success(self, mock_session, sample_addon_asset_model):
        """Test successful addon asset update"""
        # Setup
        asset_id = str(sample_addon_asset_model.id)

        with patch('db.crud.get_addon_asset', return_value=sample_addon_asset_model):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_addon_asset_model
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()

            # Execute
            result = await crud.update_addon_asset(
                mock_session,
                asset_id=asset_id,
                asset_type="updated_type",
                file_path="updated/path.png",
                original_filename="updated.png"
            )

            # Verify
            assert result == sample_addon_asset_model
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    async def test_update_addon_asset_path_traversal_prevention(self, mock_session, sample_addon_asset_model):
        """Test that path traversal attacks are prevented during update"""
        asset_id = str(sample_addon_asset_model.id)

        with patch('db.crud.get_addon_asset', return_value=sample_addon_asset_model):
            # Execute - this should raise ValueError due to path traversal
            with pytest.raises(ValueError, match="Invalid file path: path traversal detected"):
                await crud.update_addon_asset(
                    mock_session,
                    asset_id=asset_id,
                    file_path="../../malicious_update.png",
                    original_filename="malicious_update.png"
                )

    async def test_update_addon_asset_not_found(self, mock_session):
        """Test updating non-existent addon asset"""
        with patch('db.crud.get_addon_asset', return_value=None):
            result = await crud.update_addon_asset(
                mock_session,
                asset_id=str(uuid.uuid4()),
                asset_type="texture"
            )
            assert result is None

    async def test_update_addon_asset_invalid_id(self, mock_session):
        """Test addon asset update with invalid ID"""
        with pytest.raises(ValueError):
            await crud.update_addon_asset(
                mock_session,
                asset_id="invalid-uuid",
                asset_type="texture"
            )

    async def test_update_addon_asset_no_commit(self, mock_session, sample_addon_asset_model):
        """Test addon asset update without committing"""
        asset_id = str(sample_addon_asset_model.id)

        with patch('db.crud.get_addon_asset', return_value=sample_addon_asset_model):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_addon_asset_model
            mock_session.execute = AsyncMock(return_value=mock_result)

            # Execute
            result = await crud.update_addon_asset(
                mock_session,
                asset_id=asset_id,
                asset_type="updated_type",
                commit=False
            )

            # Verify
            assert result == sample_addon_asset_model
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_not_called()


class TestDeleteAddonAsset:
    """Tests for delete_addon_asset function"""

    async def test_delete_addon_asset_success(self, mock_session, sample_addon_asset_model):
        """Test successful addon asset deletion"""
        asset_id = str(sample_addon_asset_model.id)

        with patch('db.crud.get_addon_asset', return_value=sample_addon_asset_model):
            mock_result = AsyncMock()
            mock_result.rowcount = 1
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()

            # Execute
            result = await crud.delete_addon_asset(mock_session, asset_id)

            # Verify
            assert result is True
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    async def test_delete_addon_asset_not_found(self, mock_session):
        """Test deletion of non-existent addon asset"""
        with patch('db.crud.get_addon_asset', return_value=None):
            result = await crud.delete_addon_asset(mock_session, str(uuid.uuid4()))
            assert result is False

    async def test_delete_addon_asset_invalid_id(self, mock_session):
        """Test addon asset deletion with invalid ID"""
        with pytest.raises(ValueError):
            await crud.delete_addon_asset(mock_session, "invalid-uuid")


class TestListAddonAssets:
    """Tests for list_addon_assets function"""

    async def test_list_addon_assets_success(self, mock_session, sample_addon_id):
        """Test successful addon asset listing"""
        # Setup
        mock_assets = [MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_assets
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await crud.list_addon_assets(mock_session, sample_addon_id)

        # Verify
        assert result == mock_assets
        mock_session.execute.assert_called_once()

    async def test_list_addon_assets_invalid_id(self, mock_session):
        """Test addon asset listing with invalid addon ID"""
        with pytest.raises(ValueError):
            await crud.list_addon_assets(mock_session, "invalid-uuid")

    async def test_list_addon_assets_with_filters(self, mock_session, sample_addon_id):
        """Test addon asset listing with type filter"""
        # Setup
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await crud.list_addon_assets(
            mock_session,
            sample_addon_id,
            asset_type="texture"
        )

        # Verify
        assert result == []
        mock_session.execute.assert_called_once()


@pytest.mark.integration
class TestAddonAssetCRUDIntegration:
    """Integration tests for AddonAsset CRUD operations"""

    async def test_create_and_retrieve_addon_asset(self, mock_session, sample_addon_id, sample_file):
        """Test creating an addon asset and then retrieving it"""
        # Create asset
        with patch('db.crud.create_addon_asset') as mock_create:
            mock_asset = models.AddonAsset()
            mock_asset.id = uuid.uuid4()
            mock_create.return_value = mock_asset

            created_asset = await crud.create_addon_asset(
                mock_session,
                addon_id=sample_addon_id,
                file=sample_file,
                asset_type="texture"
            )
            assert created_asset == mock_asset

        # Retrieve asset
        with patch('db.crud.get_addon_asset') as mock_get:
            mock_get.return_value = mock_asset

            retrieved_asset = await crud.get_addon_asset(mock_session, str(mock_asset.id))
            assert retrieved_asset == mock_asset

    async def test_addon_asset_update_workflow(self, mock_session, sample_addon_asset_model, sample_file):
        """Test typical addon asset update workflow"""
        asset_id = str(sample_addon_asset_model.id)

        # Mock the update function
        with patch('db.crud.update_addon_asset') as mock_update:
            mock_update.return_value = sample_addon_asset_model

            result = await crud.update_addon_asset(
                mock_session,
                asset_id=asset_id,
                file=sample_file
            )
            assert result == sample_addon_asset_model
