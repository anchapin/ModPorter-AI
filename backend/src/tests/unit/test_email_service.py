import pytest
from unittest.mock import MagicMock, patch
from services.email_service import ResendEmailService, EmailMessage, get_email_service


@pytest.fixture
def email_service():
    return ResendEmailService(api_key="test-key")


@pytest.mark.asyncio
async def test_send_email_no_client(email_service):
    with patch.object(email_service, "_get_client", return_value=None):
        msg = EmailMessage(
            to="test@example.com",
            subject="Test",
            template="welcome",
            context={"user_name": "Test User"},
        )
        result = await email_service.send(msg)
        assert result is True


@pytest.mark.asyncio
async def test_send_email_success(email_service):
    mock_response = {"id": "test-email-id"}
    mock_emails = MagicMock()
    mock_emails.send.return_value = mock_response

    with patch.object(email_service, "_get_client", return_value=True):
        with patch.dict("sys.modules", {"resend": MagicMock(Emails=mock_emails)}):
            msg = EmailMessage(
                to="test@example.com",
                subject="Test",
                template="welcome",
                context={"user_name": "Test User"},
            )
            result = await email_service.send(msg)
            assert result is True
            mock_emails.send.assert_called_once()


def test_render_template_welcome(email_service):
    plain_text, html_content = email_service._render_template("welcome", {"user_name": "Alex"})
    assert "Welcome to Portkit, Alex!" in plain_text


def test_render_template_verification(email_service):
    plain_text, html_content = email_service._render_template(
        "email_verification", {"verification_url": "http://example.com/verify", "expiry_hours": 24}
    )
    assert "http://example.com/verify" in plain_text
    assert "24 hours" in plain_text


def test_render_template_unknown(email_service):
    plain_text, html_content = email_service._render_template("nonexistent", {})
    assert "Unknown template" in plain_text


def test_get_email_service():
    import services.email_service as email_service_module

    email_service_module._email_service = None
    with patch.dict("os.environ", {"RESEND_API_KEY": "env-key"}):
        service = get_email_service()
        assert service.api_key == "env-key"
