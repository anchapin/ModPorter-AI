import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from db import behavior_templates_crud
from db.models import BehaviorTemplate


class TestBehaviorTemplatesCRUD:
    """Test behavior templates CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_behavior_template_success(self):
        """Test creating a behavior template successfully."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        template_data = {"key": "value"}
        tags = ["tag1", "tag2"]
        created_by = str(uuid.uuid4())

        template = await behavior_templates_crud.create_behavior_template(
            session=mock_session,
            name="Test Template",
            description="Test Description",
            category="recipe",
            template_type="crafting",
            template_data=template_data,
            tags=tags,
            is_public=True,
            version="1.1.0",
            created_by=created_by,
        )

        assert template.name == "Test Template"
        assert template.description == "Test Description"
        assert template.category == "recipe"
        assert template.template_type == "crafting"
        assert template.template_data == template_data
        assert template.tags == tags
        assert template.is_public is True
        assert template.version == "1.1.0"
        assert str(template.created_by) == created_by

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_behavior_template_no_commit(self):
        """Test creating a behavior template without committing."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()

        template = await behavior_templates_crud.create_behavior_template(
            session=mock_session,
            name="Test Template",
            description="Test Description",
            category="recipe",
            template_type="crafting",
            template_data={},
            tags=[],
            commit=False,
        )

        assert template is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_behavior_template_success(self):
        """Test getting a behavior template by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_template = MagicMock(spec=BehaviorTemplate)
        mock_result.scalar_one_or_none.return_value = mock_template
        mock_session.execute.return_value = mock_result

        template_id = str(uuid.uuid4())
        template = await behavior_templates_crud.get_behavior_template(
            session=mock_session, template_id=template_id
        )

        assert template == mock_template
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_behavior_template_invalid_uuid(self):
        """Test getting a behavior template with an invalid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError, match="Invalid template ID format"):
            await behavior_templates_crud.get_behavior_template(
                session=mock_session, template_id="invalid-uuid"
            )

    @pytest.mark.asyncio
    async def test_get_behavior_templates_all_filters(self):
        """Test getting behavior templates with all filters."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_templates = [MagicMock(spec=BehaviorTemplate), MagicMock(spec=BehaviorTemplate)]
        mock_result.scalars.return_value.all.return_value = mock_templates
        mock_session.execute.return_value = mock_result

        templates = await behavior_templates_crud.get_behavior_templates(
            session=mock_session,
            category="recipe",
            template_type="crafting",
            tags=["tag1"],
            search="test",
            is_public=True,
            skip=10,
            limit=20,
        )

        assert templates == mock_templates
        mock_session.execute.assert_called_once()
        # Verify pagination and limit in the query would require more complex mocking
        # or checking the actual statement object

    @pytest.mark.asyncio
    async def test_update_behavior_template_success(self):
        """Test updating a behavior template successfully."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_template = MagicMock(spec=BehaviorTemplate)
        mock_result.scalar_one_or_none.return_value = mock_template
        mock_session.execute.return_value = mock_result

        template_id = str(uuid.uuid4())
        updates = {"name": "Updated Name", "is_public": False}

        template = await behavior_templates_crud.update_behavior_template(
            session=mock_session,
            template_id=template_id,
            updates=updates,
        )

        assert template == mock_template
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_behavior_template_invalid_uuid(self):
        """Test updating a behavior template with an invalid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError, match="Invalid template ID format"):
            await behavior_templates_crud.update_behavior_template(
                session=mock_session, template_id="invalid-uuid", updates={}
            )

    @pytest.mark.asyncio
    async def test_update_behavior_template_no_updates(self):
        """Test updating a behavior template with no valid updates."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_template = MagicMock(spec=BehaviorTemplate)
        mock_result.scalar_one_or_none.return_value = mock_template
        mock_session.execute.return_value = mock_result

        template_id = str(uuid.uuid4())
        # Provide updates that are not in the allowed list
        updates = {"invalid_field": "value"}

        template = await behavior_templates_crud.update_behavior_template(
            session=mock_session,
            template_id=template_id,
            updates=updates,
        )

        assert template == mock_template
        # Should have called get_behavior_template which calls execute
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_behavior_template_success(self):
        """Test deleting a behavior template successfully."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock get_behavior_template to return something (template exists)
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = MagicMock(spec=BehaviorTemplate)

        # Mock delete execute
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        mock_session.execute.side_effect = [mock_get_result, mock_delete_result]

        template_id = str(uuid.uuid4())
        success = await behavior_templates_crud.delete_behavior_template(
            session=mock_session, template_id=template_id
        )

        assert success is True
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_behavior_template_not_found(self):
        """Test deleting a behavior template that doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock get_behavior_template to return None
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_get_result

        template_id = str(uuid.uuid4())
        success = await behavior_templates_crud.delete_behavior_template(
            session=mock_session, template_id=template_id
        )

        assert success is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_behavior_template_invalid_uuid(self):
        """Test deleting a behavior template with an invalid UUID."""
        mock_session = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError, match="Invalid template ID format"):
            await behavior_templates_crud.delete_behavior_template(
                session=mock_session, template_id="invalid-uuid"
            )

    @pytest.mark.asyncio
    async def test_apply_behavior_template_success(self):
        """Test applying a behavior template successfully."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_template = MagicMock(spec=BehaviorTemplate)
        mock_template.id = uuid.uuid4()
        mock_template.name = "Test Template"
        mock_template.version = "1.0.0"
        mock_template.template_type = "crafting"
        mock_template.template_data = {"result": "diamond"}
        mock_template.category = "recipe"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_template
        mock_session.execute.return_value = mock_result

        result = await behavior_templates_crud.apply_behavior_template(
            session=mock_session, template_id=str(mock_template.id), conversion_id="conv-123"
        )

        assert result["content"]["result"] == "diamond"
        assert "_template_info" in result["content"]
        assert result["file_type"] == "recipe"
        assert "generated/crafting_" in result["file_path"]

    @pytest.mark.asyncio
    async def test_apply_behavior_template_not_found(self):
        """Test applying a non-existent behavior template."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Template .* not found"):
            await behavior_templates_crud.apply_behavior_template(
                session=mock_session, template_id=str(uuid.uuid4()), conversion_id="conv-123"
            )
