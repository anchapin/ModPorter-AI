"""
Authorization tests for the behavior_templates API (issue #1417).

Behavior templates use a ``created_by`` field. Public templates
(``is_public=True``) are visible to any authenticated user, but private
templates are only visible to their creator. Mutating endpoints (update,
delete) require ownership and return 404 when the template does not exist
or belongs to another user.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.behavior_templates import router
from api._authz import get_current_user
from db.base import get_db


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = str(uuid.uuid4())
    return user


def _make_template(*, created_by: str | None, is_public: bool = False) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.name = "test-template"
    t.description = "desc"
    t.category = "block_behavior"
    t.template_type = "simple_block"
    t.template_data = {"a": 1}
    t.tags = []
    t.is_public = is_public
    t.version = "1.0.0"
    t.created_by = created_by
    t.created_at = datetime.now()
    t.updated_at = datetime.now()
    return t


def _build_client(current_user, *, template=None, monkeypatch):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    from api import behavior_templates as bt_mod

    monkeypatch.setattr(
        bt_mod.behavior_templates_crud,
        "get_behavior_template",
        AsyncMock(return_value=template),
        raising=True,
    )
    monkeypatch.setattr(
        bt_mod.behavior_templates_crud,
        "delete_behavior_template",
        AsyncMock(return_value=True),
        raising=True,
    )

    return TestClient(app)


class TestBehaviorTemplatesAuthorization:
    def test_get_private_template_404_when_other_user(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        template = _make_template(created_by=str(owner.id), is_public=False)
        client = _build_client(attacker, template=template, monkeypatch=monkeypatch)

        response = client.get(f"/templates/{template.id}")

        assert response.status_code == 404, (
            "Private templates owned by other users must be invisible (404)"
        )

    def test_get_public_template_visible_to_other_user(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        template = _make_template(created_by=str(owner.id), is_public=True)
        client = _build_client(attacker, template=template, monkeypatch=monkeypatch)

        response = client.get(f"/templates/{template.id}")

        assert response.status_code == 200

    def test_delete_template_404_when_other_user(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        template = _make_template(created_by=str(owner.id), is_public=True)
        client = _build_client(attacker, template=template, monkeypatch=monkeypatch)

        response = client.delete(f"/templates/{template.id}")

        # Even though the template is public, only the owner can delete it.
        assert response.status_code == 404

    def test_delete_template_succeeds_for_owner(self, monkeypatch):
        owner = _make_user()
        template = _make_template(created_by=str(owner.id), is_public=False)
        client = _build_client(owner, template=template, monkeypatch=monkeypatch)

        response = client.delete(f"/templates/{template.id}")

        assert response.status_code == 204
