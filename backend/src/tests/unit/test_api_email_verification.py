"""
Tests for Email Verification API - src/api/email_verification.py
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


class TestRegisterWithVerificationRequest:
    """Tests for RegisterWithVerificationRequest model."""

    def test_valid_registration_request(self):
        """Test valid registration with email verification request."""
        from api.email_verification import RegisterWithVerificationRequest
        
        request = RegisterWithVerificationRequest(
            email="test@example.com",
            password="SecurePass123!"
        )
        assert request.email == "test@example.com"
        assert request.password == "SecurePass123!"

    def test_invalid_email_format(self):
        """Test invalid email format."""
        from api.email_verification import RegisterWithVerificationRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            RegisterWithVerificationRequest(email="invalid-email", password="pass")


class TestResendVerificationRequest:
    """Tests for ResendVerificationRequest model."""

    def test_valid_resend_request(self):
        """Test valid resend verification request."""
        from api.email_verification import ResendVerificationRequest
        
        request = ResendVerificationRequest(email="test@example.com")
        assert request.email == "test@example.com"

    def test_invalid_resend_email(self):
        """Test invalid email for resend."""
        from api.email_verification import ResendVerificationRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ResendVerificationRequest(email="not-an-email")


class TestResponseModels:
    """Tests for response models."""

    def test_registration_response(self):
        """Test registration response model."""
        from api.email_verification import RegisterWithVerificationResponse
        
        response = RegisterWithVerificationResponse(
            message="Verification email sent",
            user_id="user-123"
        )
        assert response.user_id == "user-123"
        assert "Verification" in response.message

    def test_resend_response(self):
        """Test resend verification response model."""
        from api.email_verification import ResendVerificationResponse
        
        response = ResendVerificationResponse(
            message="Verification email resent"
        )
        assert "Verification" in response.message