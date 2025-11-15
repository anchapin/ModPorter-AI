

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_behavior_file():
    return AsyncMock(
        id=uuid.uuid4(),
        conversion_id=uuid.uuid4(),
        file_path="entities/player.json",
        file_type="entity_behavior",
        content='{"format_version": "1.16.0"}',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
@patch("src.api.behavior_files.crud", new_callable=AsyncMock)
async def test_get_conversion_behavior_files_tree(mock_crud, mock_behavior_file):
    """
    Tests getting the behavior file tree for a conversion.
    """
    mock_crud.get_job.return_value = AsyncMock(id=mock_behavior_file.conversion_id)
    mock_crud.get_behavior_files_by_conversion.return_value = [
        mock_behavior_file,
        AsyncMock(
            id=uuid.uuid4(),
            conversion_id=mock_behavior_file.conversion_id,
            file_path="entities/creeper.json",
            file_type="entity_behavior",
            content="{}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        AsyncMock(
            id=uuid.uuid4(),
            conversion_id=mock_behavior_file.conversion_id,
            file_path="recipes/new_recipe.json",
            file_type="recipe",
            content="{}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]

    response = client.get(
        f"/api/v1/conversions/{mock_behavior_file.conversion_id}/behaviors"
    )

    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 2  # entities and recipes folders
    entities_folder = next(item for item in json_response if item["name"] == "entities")
    assert entities_folder["type"] == "directory"
    assert len(entities_folder["children"]) == 2
    player_file = next(
        item for item in entities_folder["children"] if item["name"] == "player.json"
    )
    assert player_file["type"] == "file"
    assert player_file["file_type"] == "entity_behavior"


@pytest.mark.asyncio
@patch("src.api.behavior_files.crud", new_callable=AsyncMock)
async def test_get_behavior_file_success(mock_crud, mock_behavior_file):
    """
    Tests getting a single behavior file by ID.
    """
    mock_crud.get_behavior_file.return_value = mock_behavior_file

    response = client.get(f"/api/v1/behaviors/{mock_behavior_file.id}")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["id"] == str(mock_behavior_file.id)
    assert json_response["content"] == mock_behavior_file.content


@pytest.mark.asyncio
@patch("src.api.behavior_files.crud", new_callable=AsyncMock)
async def test_get_behavior_file_not_found(mock_crud):
    """
    Tests getting a single behavior file that does not exist.
    """
    mock_crud.get_behavior_file.return_value = None
    file_id = uuid.uuid4()

    response = client.get(f"/api/v1/behaviors/{file_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
@patch("src.api.behavior_files.crud", new_callable=AsyncMock)
async def test_update_behavior_file_success(mock_crud, mock_behavior_file):
    """
    Tests updating the content of a behavior file.
    """
    updated_content = '{"format_version": "1.17.0"}'
    mock_behavior_file.content = updated_content
    mock_crud.get_behavior_file.return_value = mock_behavior_file
    mock_crud.update_behavior_file_content.return_value = mock_behavior_file

    update_data = {"content": updated_content}
    response = client.put(f"/api/v1/behaviors/{mock_behavior_file.id}", json=update_data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["content"] == updated_content


@pytest.mark.asyncio
@patch("src.api.behavior_files.crud", new_callable=AsyncMock)
async def test_create_behavior_file_success(mock_crud, mock_behavior_file):
    """
    Tests creating a new behavior file.
    """
    mock_crud.get_job.return_value = AsyncMock(id=mock_behavior_file.conversion_id)
    mock_crud.create_behavior_file.return_value = mock_behavior_file

    create_data = {
        "file_path": "entities/zombie.json",
        "file_type": "entity_behavior",
        "content": "{}",
    }
    response = client.post(
        f"/api/v1/conversions/{mock_behavior_file.conversion_id}/behaviors",
        json=create_data,
    )

    assert response.status_code == 201
    json_response = response.json()
    assert json_response["id"] == str(mock_behavior_file.id)


@pytest.mark.asyncio
@patch("src.api.behavior_files.crud", new_callable=AsyncMock)
async def test_delete_behavior_file_success(mock_crud, mock_behavior_file):
    """
    Tests deleting a behavior file.
    """
    mock_crud.delete_behavior_file.return_value = True

    response = client.delete(f"/api/v1/behaviors/{mock_behavior_file.id}")

    assert response.status_code == 204


@pytest.mark.asyncio
@patch("src.api.behavior_files.crud", new_callable=AsyncMock)
async def test_get_behavior_files_by_type_success(mock_crud, mock_behavior_file):
    """
    Tests getting behavior files by type.
    """
    mock_crud.get_job.return_value = AsyncMock(id=mock_behavior_file.conversion_id)
    mock_crud.get_behavior_files_by_type.return_value = [mock_behavior_file]

    response = client.get(
        f"/api/v1/conversions/{mock_behavior_file.conversion_id}/behaviors/types/entity_behavior"
    )

    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 1
    assert json_response[0]["id"] == str(mock_behavior_file.id)
    assert json_response[0]["file_type"] == "entity_behavior"
