"""
Tests for Behavior Files API endpoints - src/api/behavior_files.py
Covers all 6 endpoints with mocked CRUD layer using TestClient.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.behavior_files import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _make_behavior_file(**overrides):
    bf = MagicMock()
    bf.id = overrides.get("id", uuid.uuid4())
    bf.conversion_id = overrides.get("conversion_id", uuid.uuid4())
    bf.file_path = overrides.get("file_path", "entities/test.json")
    bf.file_type = overrides.get("file_type", "entity_behavior")
    bf.content = overrides.get("content", '{"test": true}')
    bf.created_at = overrides.get("created_at", datetime.now(timezone.utc))
    bf.updated_at = overrides.get("updated_at", datetime.now(timezone.utc))
    return bf


VALID_CONV_ID = str(uuid.uuid4())
VALID_FILE_ID = str(uuid.uuid4())


class TestGetConversionBehaviorFiles:
    @patch("api.behavior_files.crud.get_behavior_files_by_conversion", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_get_behavior_files_with_tree(self, mock_get_job, mock_get_files):
        mock_get_job.return_value = MagicMock()
        bf = _make_behavior_file(file_path="entities/zombie.json")
        mock_get_files.return_value = [bf]

        resp = client.get(f"/conversions/{VALID_CONV_ID}/behaviors")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    @patch("api.behavior_files.crud.get_behavior_files_by_conversion", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_get_behavior_files_empty(self, mock_get_job, mock_get_files):
        mock_get_job.return_value = MagicMock()
        mock_get_files.return_value = []

        resp = client.get(f"/conversions/{VALID_CONV_ID}/behaviors")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_behavior_files_invalid_uuid(self):
        resp = client.get("/conversions/not-a-uuid/behaviors")

        assert resp.status_code == 400

    @patch("api.behavior_files.crud.get_behavior_files_by_conversion", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_get_behavior_files_conversion_not_found(self, mock_get_job, mock_get_files):
        mock_get_job.return_value = None

        resp = client.get(f"/conversions/{VALID_CONV_ID}/behaviors")

        assert resp.status_code == 404

    @patch("api.behavior_files.crud.get_behavior_files_by_conversion", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_get_behavior_files_nested_tree(self, mock_get_job, mock_get_files):
        mock_get_job.return_value = MagicMock()
        bf1 = _make_behavior_file(file_path="entities/hostile/zombie.json")
        bf2 = _make_behavior_file(file_path="entities/passive/cow.json")
        mock_get_files.return_value = [bf1, bf2]

        resp = client.get(f"/conversions/{VALID_CONV_ID}/behaviors")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


class TestGetBehaviorFile:
    @patch("api.behavior_files.crud.get_behavior_file", new_callable=AsyncMock)
    def test_get_behavior_file_success(self, mock_get):
        bf = _make_behavior_file()
        mock_get.return_value = bf

        resp = client.get(f"/behaviors/{VALID_FILE_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["file_type"] == "entity_behavior"

    @patch("api.behavior_files.crud.get_behavior_file", new_callable=AsyncMock)
    def test_get_behavior_file_not_found(self, mock_get):
        mock_get.return_value = None

        resp = client.get(f"/behaviors/{VALID_FILE_ID}")

        assert resp.status_code == 404

    def test_get_behavior_file_invalid_uuid(self):
        resp = client.get("/behaviors/not-a-uuid")

        assert resp.status_code == 400


class TestUpdateBehaviorFile:
    @patch("api.behavior_files.crud.update_behavior_file_content", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_behavior_file", new_callable=AsyncMock)
    def test_update_behavior_file_success(self, mock_get, mock_update):
        bf = _make_behavior_file()
        mock_get.return_value = bf
        updated = _make_behavior_file(content='{"updated": true}')
        mock_update.return_value = updated

        resp = client.put(f"/behaviors/{VALID_FILE_ID}", json={"content": '{"updated": true}'})

        assert resp.status_code == 200
        assert resp.json()["content"] == '{"updated": true}'

    @patch("api.behavior_files.crud.get_behavior_file", new_callable=AsyncMock)
    def test_update_behavior_file_not_found(self, mock_get):
        mock_get.return_value = None

        resp = client.put(f"/behaviors/{VALID_FILE_ID}", json={"content": "new"})

        assert resp.status_code == 404

    @patch("api.behavior_files.crud.update_behavior_file_content", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_behavior_file", new_callable=AsyncMock)
    def test_update_behavior_file_update_fails(self, mock_get, mock_update):
        bf = _make_behavior_file()
        mock_get.return_value = bf
        mock_update.return_value = None

        resp = client.put(f"/behaviors/{VALID_FILE_ID}", json={"content": "new"})

        assert resp.status_code == 500

    def test_update_behavior_file_invalid_uuid(self):
        resp = client.put("/behaviors/bad-uuid", json={"content": "x"})

        assert resp.status_code == 400


class TestCreateBehaviorFile:
    @patch("api.behavior_files.crud.create_behavior_file", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_create_behavior_file_success(self, mock_get_job, mock_create):
        mock_get_job.return_value = MagicMock()
        bf = _make_behavior_file(file_path="entities/new.json")
        mock_create.return_value = bf

        resp = client.post(
            f"/conversions/{VALID_CONV_ID}/behaviors",
            json={
                "file_path": "entities/new.json",
                "file_type": "entity_behavior",
                "content": "{}",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["file_path"] == "entities/new.json"

    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_create_behavior_file_conversion_not_found(self, mock_get_job):
        mock_get_job.return_value = None

        resp = client.post(
            f"/conversions/{VALID_CONV_ID}/behaviors",
            json={
                "file_path": "test.json",
                "file_type": "block_behavior",
                "content": "{}",
            },
        )

        assert resp.status_code == 404

    def test_create_behavior_file_invalid_uuid(self):
        resp = client.post(
            "/conversions/bad-uuid/behaviors",
            json={
                "file_path": "test.json",
                "file_type": "block_behavior",
                "content": "{}",
            },
        )

        assert resp.status_code == 400

    @patch("api.behavior_files.crud.create_behavior_file", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_create_behavior_file_value_error(self, mock_get_job, mock_create):
        mock_get_job.return_value = MagicMock()
        mock_create.side_effect = ValueError("bad input")

        resp = client.post(
            f"/conversions/{VALID_CONV_ID}/behaviors",
            json={
                "file_path": "test.json",
                "file_type": "block_behavior",
                "content": "{}",
            },
        )

        assert resp.status_code == 400

    @patch("api.behavior_files.crud.create_behavior_file", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_create_behavior_file_generic_error(self, mock_get_job, mock_create):
        mock_get_job.return_value = MagicMock()
        mock_create.side_effect = Exception("db error")

        resp = client.post(
            f"/conversions/{VALID_CONV_ID}/behaviors",
            json={
                "file_path": "test.json",
                "file_type": "block_behavior",
                "content": "{}",
            },
        )

        assert resp.status_code == 500


class TestDeleteBehaviorFile:
    @patch("api.behavior_files.crud.delete_behavior_file", new_callable=AsyncMock)
    def test_delete_behavior_file_success(self, mock_delete):
        mock_delete.return_value = True

        resp = client.delete(f"/behaviors/{VALID_FILE_ID}")

        assert resp.status_code == 204

    @patch("api.behavior_files.crud.delete_behavior_file", new_callable=AsyncMock)
    def test_delete_behavior_file_not_found(self, mock_delete):
        mock_delete.return_value = False

        resp = client.delete(f"/behaviors/{VALID_FILE_ID}")

        assert resp.status_code == 404

    def test_delete_behavior_file_invalid_uuid(self):
        resp = client.delete("/behaviors/not-a-uuid")

        assert resp.status_code == 400


class TestGetBehaviorFilesByType:
    @patch("api.behavior_files.crud.get_behavior_files_by_type", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_get_by_type_success(self, mock_get_job, mock_get_by_type):
        mock_get_job.return_value = MagicMock()
        bf = _make_behavior_file(file_type="entity_behavior")
        mock_get_by_type.return_value = [bf]

        resp = client.get(f"/conversions/{VALID_CONV_ID}/behaviors/types/entity_behavior")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["file_type"] == "entity_behavior"

    @patch("api.behavior_files.crud.get_behavior_files_by_type", new_callable=AsyncMock)
    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_get_by_type_empty(self, mock_get_job, mock_get_by_type):
        mock_get_job.return_value = MagicMock()
        mock_get_by_type.return_value = []

        resp = client.get(f"/conversions/{VALID_CONV_ID}/behaviors/types/block_behavior")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("api.behavior_files.crud.get_job", new_callable=AsyncMock)
    def test_get_by_type_conversion_not_found(self, mock_get_job):
        mock_get_job.return_value = None

        resp = client.get(f"/conversions/{VALID_CONV_ID}/behaviors/types/entity_behavior")

        assert resp.status_code == 404

    def test_get_by_type_invalid_uuid(self):
        resp = client.get("/conversions/bad-uuid/behaviors/types/entity_behavior")

        assert resp.status_code == 400
