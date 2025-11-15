
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.src.api.behavior_templates import router, TEMPLATE_CATEGORIES
import uuid
from datetime import datetime

client = TestClient(router)

@pytest.fixture
def mock_db_session():
    with patch('backend.src.api.behavior_templates.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        yield mock_db

def test_get_template_categories():
    response = client.get("/templates/categories")
    assert response.status_code == 200
    assert response.json() == [category.dict() for category in TEMPLATE_CATEGORIES]

@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_templates')
def test_get_behavior_templates(mock_get_templates, mock_db_session):
    mock_template = MagicMock()
    mock_template.id = uuid.uuid4()
    mock_template.name = "Test Template"
    mock_template.description = "A test template"
    mock_template.category = "block_behavior"
    mock_template.template_type = "simple_block"
    mock_template.template_data = {}
    mock_template.tags = ["test"]
    mock_template.is_public = True
    mock_template.version = "1.0.0"
    mock_template.created_by = None
    mock_template.created_at = datetime.utcnow()
    mock_template.updated_at = datetime.utcnow()

    mock_get_templates.return_value = [mock_template]

    response = client.get("/templates")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test Template"
    mock_get_templates.assert_called_once()

@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')
def test_get_behavior_template(mock_get_template, mock_db_session):
    template_id = uuid.uuid4()
    mock_template = MagicMock()
    mock_template.id = template_id
    mock_template.name = "Test Template"
    mock_template.description = "A test template"
    mock_template.category = "block_behavior"
    mock_template.template_type = "simple_block"
    mock_template.template_data = {}
    mock_template.tags = ["test"]
    mock_template.is_public = True
    mock_template.version = "1.0.0"
    mock_template.created_by = None
    mock_template.created_at = datetime.utcnow()
    mock_template.updated_at = datetime.utcnow()

    mock_get_template.return_value = mock_template

    response = client.get(f"/templates/{template_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Test Template"
    mock_get_template.assert_called_once_with(mock_db_session, str(template_id))

@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')
def test_get_behavior_template_not_found(mock_get_template, mock_db_session):
    template_id = uuid.uuid4()
    mock_get_template.return_value = None

    response = client.get(f"/templates/{template_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Template not found"}
    mock_get_template.assert_called_once_with(mock_db_session, str(template_id))

def test_get_behavior_template_invalid_id(mock_db_session):
    response = client.get("/templates/invalid-id")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid template ID format"}

@patch('backend.src.api.behavior_templates.behavior_templates_crud.create_behavior_template')
def test_create_behavior_template(mock_create_template, mock_db_session):
    template_data = {
        "name": "New Template",
        "description": "A new test template",
        "category": "block_behavior",
        "template_type": "custom_block",
        "template_data": {"key": "value"},
        "tags": ["new", "test"],
        "is_public": False,
        "version": "1.0.0"
    }

    mock_template = MagicMock()
    mock_template.id = uuid.uuid4()
    mock_template.name = template_data["name"]
    mock_template.description = template_data["description"]
    mock_template.category = template_data["category"]
    mock_template.template_type = template_data["template_type"]
    mock_template.template_data = template_data["template_data"]
    mock_template.tags = template_data["tags"]
    mock_template.is_public = template_data["is_public"]
    mock_template.version = template_data["version"]
    mock_template.created_by = None
    mock_template.created_at = datetime.utcnow()
    mock_template.updated_at = datetime.utcnow()

    mock_create_template.return_value = mock_template

    response = client.post("/templates", json=template_data)

    assert response.status_code == 201
    assert response.json()["name"] == "New Template"
    mock_create_template.assert_called_once()



def test_create_behavior_template_invalid_category(mock_db_session):

    template_data = {

        "name": "New Template",

        "description": "A new test template",

        "category": "invalid_category",

        "template_type": "custom_block",

        "template_data": {"key": "value"},

        "tags": ["new", "test"],

        "is_public": False,

        "version": "1.0.0"

    }



    response = client.post("/templates", json=template_data)



    assert response.status_code == 400

    valid_categories = [cat.name for cat in TEMPLATE_CATEGORIES]

    assert response.json() == {"detail": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}



@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')

@patch('backend.src.api.behavior_templates.behavior_templates_crud.update_behavior_template')

def test_update_behavior_template(mock_update_template, mock_get_template, mock_db_session):

    template_id = uuid.uuid4()

    update_data = {"name": "Updated Name"}



    mock_get_template.return_value = True  # Simulate template exists



    mock_template = MagicMock()

    mock_template.id = template_id

    mock_template.name = "Updated Name"

    mock_template.description = "A test template"

    mock_template.category = "block_behavior"

    mock_template.template_type = "simple_block"

    mock_template.template_data = {}

    mock_template.tags = ["test"]

    mock_template.is_public = True

    mock_template.version = "1.0.0"

    mock_template.created_by = None

    mock_template.created_at = datetime.utcnow()

    mock_template.updated_at = datetime.utcnow()



    mock_update_template.return_value = mock_template



    response = client.put(f"/templates/{template_id}", json=update_data)



    assert response.status_code == 200

    assert response.json()["name"] == "Updated Name"

    mock_get_template.assert_called_once_with(mock_db_session, str(template_id))

    mock_update_template.assert_called_once()



@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')

def test_update_behavior_template_not_found(mock_get_template, mock_db_session):

    template_id = uuid.uuid4()

    update_data = {"name": "Updated Name"}



    mock_get_template.return_value = None



    response = client.put(f"/templates/{template_id}", json=update_data)



    assert response.status_code == 404

    assert response.json() == {"detail": "Template not found"}

    mock_get_template.assert_called_once_with(mock_db_session, str(template_id))







@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')



def test_update_behavior_template_invalid_category(mock_get_template, mock_db_session):



    template_id = uuid.uuid4()



    update_data = {"category": "invalid_category"}







    mock_get_template.return_value = True







    response = client.put(f"/templates/{template_id}", json=update_data)







    assert response.status_code == 400



    valid_categories = [cat.name for cat in TEMPLATE_CATEGORIES]



    assert response.json() == {"detail": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}







@patch('backend.src.api.behavior_templates.behavior_templates_crud.delete_behavior_template')



def test_delete_behavior_template(mock_delete_template, mock_db_session):



    template_id = uuid.uuid4()



    mock_delete_template.return_value = True







    response = client.delete(f"/templates/{template_id}")







    assert response.status_code == 204



    mock_delete_template.assert_called_once_with(mock_db_session, str(template_id))















@patch('backend.src.api.behavior_templates.behavior_templates_crud.delete_behavior_template')







def test_delete_behavior_template_not_found(mock_delete_template, mock_db_session):







    template_id = uuid.uuid4()







    mock_delete_template.return_value = False















    response = client.delete(f"/templates/{template_id}")















    assert response.status_code == 404







    assert response.json() == {"detail": "Template not found"}







    mock_delete_template.assert_called_once_with(mock_db_session, str(template_id))















@patch('backend.src.api.behavior_templates.behavior_templates_crud.apply_behavior_template')







@patch('backend.src.api.behavior_templates.crud.get_job')







@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')







def test_apply_behavior_template(mock_get_template, mock_get_job, mock_apply_template, mock_db_session):







    template_id = uuid.uuid4()







    conversion_id = uuid.uuid4()















    mock_get_template.return_value = True







    mock_get_job.return_value = True







    mock_apply_template.return_value = {







        "content": {"key": "value"},







        "file_path": "path/to/file.json",







        "file_type": "json"







    }















    response = client.get(f"/templates/{template_id}/apply?conversion_id={conversion_id}")















    assert response.status_code == 200







    assert response.json()["template_id"] == str(template_id)







    mock_get_template.assert_called_once_with(mock_db_session, str(template_id))







    mock_get_job.assert_called_once_with(mock_db_session, str(conversion_id))







    mock_apply_template.assert_called_once()















@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')







def test_apply_behavior_template_not_found(mock_get_template, mock_db_session):







    template_id = uuid.uuid4()







    conversion_id = uuid.uuid4()















    mock_get_template.return_value = None















    response = client.get(f"/templates/{template_id}/apply?conversion_id={conversion_id}")















    assert response.status_code == 404







    assert response.json() == {"detail": "Template not found"}







    mock_get_template.assert_called_once_with(mock_db_session, str(template_id))































@patch('backend.src.api.behavior_templates.crud.get_job')















@patch('backend.src.api.behavior_templates.behavior_templates_crud.get_behavior_template')















def test_apply_behavior_template_conversion_not_found(mock_get_template, mock_get_job, mock_db_session):















    template_id = uuid.uuid4()















    conversion_id = uuid.uuid4()































    mock_get_template.return_value = True















    mock_get_job.return_value = None































    response = client.get(f"/templates/{template_id}/apply?conversion_id={conversion_id}")































    assert response.status_code == 404















    assert response.json() == {"detail": "Conversion not found"}















    mock_get_template.assert_called_once_with(mock_db_session, str(template_id))















    mock_get_job.assert_called_once_with(mock_db_session, str(conversion_id))































def test_get_predefined_templates():















    response = client.get("/templates/predefined")















    assert response.status_code == 200















    assert len(response.json()) == 3















    assert response.json()[0]["name"] == "Simple Custom Block"
