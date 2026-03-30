import pytest
from unittest.mock import MagicMock, patch
from services.email_service import SendGridEmailService, EmailMessage, get_email_service

@pytest.fixture
def email_service():
    return SendGridEmailService(api_key="test-key")

@pytest.mark.asyncio
async def test_send_email_no_client(email_service):
    # Test when sendgrid is not installed or api key missing
    with patch.object(email_service, "_get_client", return_value=None):
        msg = EmailMessage(
            to="test@example.com",
            subject="Test",
            template="welcome",
            context={"user_name": "Test User"}
        )
        result = await email_service.send(msg)
        assert result is True # Returns True because it logs only

@pytest.mark.asyncio
async def test_send_email_success(email_service):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_client.send.return_value = mock_response
    
    # Mock sys.modules to prevent ImportError
    mock_sendgrid = MagicMock()
    mock_mail_module = MagicMock()
    
    with patch.dict("sys.modules", {
        "sendgrid": mock_sendgrid,
        "sendgrid.helpers": MagicMock(),
        "sendgrid.helpers.mail": mock_mail_module
    }):
        with patch.object(email_service, "_get_client", return_value=mock_client):
            msg = EmailMessage(
                to="test@example.com",
                subject="Test",
                template="welcome",
                context={"user_name": "Test User"}
            )
            result = await email_service.send(msg)
            assert result is True
            mock_client.send.assert_called_once()

def test_render_template_welcome(email_service):
    content = email_service._render_template("welcome", {"user_name": "Alex"})
    assert "Welcome to ModPorter AI, Alex!" in content

def test_render_template_verification(email_service):
    content = email_service._render_template("email_verification", {
        "verification_url": "http://example.com/verify",
        "expiry_hours": 24
    })
    assert "http://example.com/verify" in content
    assert "24 hours" in content

def test_render_template_unknown(email_service):
    content = email_service._render_template("nonexistent", {})
    assert "Unknown template" in content

def test_get_email_service():
    with patch.dict("os.environ", {"SENDGRID_API_KEY": "env-key"}):
        service = get_email_service()
        assert service.api_key == "env-key"
