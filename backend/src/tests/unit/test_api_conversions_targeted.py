import pytest
import json
import uuid
import os
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["DISABLE_REDIS"] = "true"
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-12345678901234567890"

from api.conversions import router, ConversionOptions
from api._authz import get_current_user

_TEST_USER_ID = "11111111-1111-4111-a111-111111111111"


def _mock_user():
    user = MagicMock()
    user.id = _TEST_USER_ID
    return user


class TestConversionsAPITargeted:
    def test_list_conversions(self):
        test_app = FastAPI()
        test_app.include_router(router)
        test_app.dependency_overrides[get_current_user] = lambda: _mock_user()

        mock_get_db = MagicMock()
        mock_get_db.return_value = AsyncMock()

        mock_crud = MagicMock()
        from types import SimpleNamespace

        mock_job = SimpleNamespace(
            id=uuid.uuid4(),
            status="completed",
            progress=SimpleNamespace(progress=100),
            message="Done",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            original_filename="test.jar",
            input_data={"original_filename": "test.jar"},
            error_message=None,
        )
        mock_job.user_id = _TEST_USER_ID  # issue #1417: pass ownership check
        mock_crud.list_jobs = AsyncMock(return_value=([mock_job], 1))
        mock_crud.count_jobs = AsyncMock(return_value=1)

        with patch("api.conversions.get_db", mock_get_db), patch("api.conversions.crud", mock_crud):
            with TestClient(test_app) as client:
                response = client.get("/api/v1/conversions")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["conversions"]) == 1
            assert data["conversions"][0]["conversion_id"] == str(mock_job.id)

    def test_get_conversion_success(self):
        test_app = FastAPI()
        test_app.include_router(router)
        test_app.dependency_overrides[get_current_user] = lambda: _mock_user()

        mock_get_db = MagicMock()
        mock_get_db.return_value = AsyncMock()

        conversion_id = str(uuid.uuid4())
        from types import SimpleNamespace

        mock_job = SimpleNamespace(
            id=conversion_id,
            status="processing",
            progress=SimpleNamespace(progress=45),
            message="Converting assets...",
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            original_filename="test.jar",
            input_data={"original_filename": "test.jar"},
            error_message=None,
        )

        mock_job.user_id = _TEST_USER_ID  # issue #1417: pass ownership check

        mock_crud = MagicMock()
        mock_crud.get_job = AsyncMock(return_value=mock_job)

        with patch("api.conversions.get_db", mock_get_db), patch("api.conversions.crud", mock_crud):
            with TestClient(test_app) as client:
                response = client.get(f"/api/v1/conversions/{conversion_id}")

            assert response.status_code == 200
            assert response.json()["conversion_id"] == conversion_id
            assert response.json()["status"] == "processing"
            assert response.json()["progress"] == 45

    def test_get_conversion_not_found(self):
        test_app = FastAPI()
        test_app.include_router(router)
        test_app.dependency_overrides[get_current_user] = lambda: _mock_user()

        mock_get_db = MagicMock()
        mock_get_db.return_value = AsyncMock()

        mock_crud = MagicMock()
        mock_crud.get_job = AsyncMock(return_value=None)

        conversion_id = str(uuid.uuid4())

        with patch("api.conversions.get_db", mock_get_db), patch("api.conversions.crud", mock_crud):
            with TestClient(test_app) as client:
                response = client.get(f"/api/v1/conversions/{conversion_id}")

            assert response.status_code == 404

    def test_sanitize_filename(self):
        from api.conversions import sanitize_filename

        assert sanitize_filename("test.jar") == "test.jar"
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("test space.jar") == "testspace.jar"
        assert sanitize_filename(".hidden") == "file.hidden"
        assert sanitize_filename("") == "uploaded_file"

    def test_validate_file_type(self):
        from api.conversions import validate_file_type

        is_valid, _ = validate_file_type("test.jar")
        assert is_valid is True
        is_valid, _ = validate_file_type("test.zip")
        assert is_valid is True
        is_valid, _ = validate_file_type("test.txt")
        assert is_valid is False

    def test_conversion_options_defaults(self):
        from api.conversions import ConversionOptions

        opts = ConversionOptions()
        assert opts.assumptions == "conservative"
        assert opts.target_version == "1.20.0"
        assert opts.notify_on_completion is True

    def test_conversion_options_custom(self):
        from api.conversions import ConversionOptions

        opts = ConversionOptions(
            assumptions="aggressive",
            target_version="1.21.0",
            notify_on_completion=False,
        )
        assert opts.assumptions == "aggressive"
        assert opts.target_version == "1.21.0"
        assert opts.notify_on_completion is False

    def test_conversion_options_invalid_assumptions(self):
        from api.conversions import ConversionOptions
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ConversionOptions(assumptions="invalid")
