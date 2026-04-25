"""
Unit tests for Addon CRUD operations: update_addon_details, create_addon_asset_from_local_path
"""

import os
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud, models

pytestmark = pytest.mark.asyncio


class FakeAddonData:
    def __init__(
        self,
        name="Test Addon",
        description="A test addon",
        user_id="user-1",
        blocks=None,
        recipes=None,
    ):
        self.name = name
        self.description = description
        self.user_id = user_id
        self.blocks = blocks or []
        self.recipes = recipes or []


class FakeBlockData:
    def __init__(self, identifier="test:block", properties=None, behavior=None):
        self.identifier = identifier
        self.properties = properties or {}
        self.behavior = behavior


class FakeBehaviorData:
    def __init__(self, data=None):
        self.data = data or {"components": {}}


class FakeRecipeData:
    def __init__(self, data=None):
        self.data = data or {"type": "crafting"}


def _make_mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _make_addon_model(addon_id=None, name="Existing Addon", blocks=None, recipes=None):
    addon = models.Addon()
    addon.id = addon_id or uuid.uuid4()
    addon.name = name
    addon.description = "existing desc"
    addon.user_id = "user-1"
    addon.blocks = blocks or []
    addon.recipes = recipes or []
    return addon


class TestUpdateAddonDetails:
    async def test_create_new_addon_when_not_found(self):
        session = _make_mock_session()
        addon_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        addon_data = FakeAddonData(name="New Addon", description="brand new")

        result = await crud.update_addon_details(session, str(addon_id), addon_data)

        session.add.assert_called()
        session.commit.assert_called_once()
        assert result.name == "New Addon"

    async def test_update_existing_addon(self):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        existing = _make_addon_model(addon_id, name="Old Name")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute = AsyncMock(return_value=mock_result)

        addon_data = FakeAddonData(name="Updated Name")

        result = await crud.update_addon_details(session, str(addon_id), addon_data)

        assert result.name == "Updated Name"
        session.commit.assert_called_once()

    async def test_with_blocks_and_behavior(self):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        existing = _make_addon_model(addon_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute = AsyncMock(return_value=mock_result)

        behavior = FakeBehaviorData(data={"events": {"on_step": {}}})
        block = FakeBlockData(identifier="test:custom_block", behavior=behavior)
        addon_data = FakeAddonData(blocks=[block])

        result = await crud.update_addon_details(session, str(addon_id), addon_data)

        session.commit.assert_called_once()

    async def test_with_recipes(self):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        existing = _make_addon_model(addon_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute = AsyncMock(return_value=mock_result)

        recipe = FakeRecipeData(data={"type": "smelting", "input": "cobblestone"})
        addon_data = FakeAddonData(recipes=[recipe])

        result = await crud.update_addon_details(session, str(addon_id), addon_data)

        session.commit.assert_called_once()

    async def test_commit_false_uses_flush(self):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        existing = _make_addon_model(addon_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute = AsyncMock(return_value=mock_result)

        addon_data = FakeAddonData(name="Flushed")
        result = await crud.update_addon_details(session, str(addon_id), addon_data, commit=False)

        session.flush.assert_called()
        session.commit.assert_not_called()

    async def test_rollback_on_commit_failure(self):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        existing = _make_addon_model(addon_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock(side_effect=Exception("db error"))

        addon_data = FakeAddonData()
        with pytest.raises(Exception, match="db error"):
            await crud.update_addon_details(session, str(addon_id), addon_data)

        session.rollback.assert_called_once()

    async def test_clears_existing_blocks_and_recipes(self):
        session = _make_mock_session()
        addon_id = uuid.uuid4()

        existing_block = MagicMock()
        existing_recipe = MagicMock()
        existing = _make_addon_model(addon_id, blocks=[existing_block], recipes=[existing_recipe])

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute = AsyncMock(return_value=mock_result)

        addon_data = FakeAddonData(blocks=[], recipes=[])
        await crud.update_addon_details(session, str(addon_id), addon_data)

        assert session.delete.call_count == 2


class TestCreateAddonAssetFromLocalPath:
    @patch("db.crud.create_addon_asset")
    async def test_with_relative_path(self, mock_create):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        mock_asset = MagicMock()
        mock_create.return_value = mock_asset

        result = await crud.create_addon_asset_from_local_path(
            session,
            addon_id=str(addon_id),
            source_file_path="textures/block.png",
            asset_type="texture",
            original_filename="block.png",
        )

        mock_create.assert_called_once_with(
            session,
            addon_id=str(addon_id),
            asset_type="texture",
            file_path="textures/block.png",
            original_filename="block.png",
            commit=True,
        )
        assert result == mock_asset

    @patch("db.crud.create_addon_asset")
    async def test_with_absolute_path(self, mock_create):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        mock_asset = MagicMock()
        mock_create.return_value = mock_asset

        abs_path = os.path.join(crud.BASE_ASSET_PATH, "sounds", "click.ogg")
        result = await crud.create_addon_asset_from_local_path(
            session,
            addon_id=str(addon_id),
            source_file_path=abs_path,
            asset_type="sound",
            original_filename="click.ogg",
        )

        call_args = mock_create.call_args
        assert not os.path.isabs(call_args.kwargs["file_path"])

    @patch("db.crud.create_addon_asset")
    async def test_commit_false(self, mock_create):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        mock_asset = MagicMock()
        mock_create.return_value = mock_asset

        await crud.create_addon_asset_from_local_path(
            session,
            addon_id=str(addon_id),
            source_file_path="models/item.json",
            asset_type="model",
            original_filename="item.json",
            commit=False,
        )

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["commit"] is False

    @patch("db.crud.create_addon_asset")
    async def test_uuid_object_addon_id(self, mock_create):
        session = _make_mock_session()
        addon_id = uuid.uuid4()
        mock_asset = MagicMock()
        mock_create.return_value = mock_asset

        await crud.create_addon_asset_from_local_path(
            session,
            addon_id=addon_id,
            source_file_path="scripts/main.js",
            asset_type="script",
            original_filename="main.js",
        )

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["addon_id"] == str(addon_id)
