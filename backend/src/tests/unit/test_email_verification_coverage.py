"""
Tests for Email Verification API to improve coverage.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from pydantic import ValidationError


class TestEmailVerificationModels:
    """Test email verification models."""

    def test_register_with_verification_request_valid(self):
        """Test valid registration request."""
        from api.email_verification import RegisterWithVerificationRequest
        
        request = RegisterWithVerificationRequest(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        assert request.email == "test@example.com"
        assert request.password == "SecurePass123!"

    def test_register_with_verification_request_invalid_email(self):
        """Test invalid email in registration request."""
        from api.email_verification import RegisterWithVerificationRequest
        
        with pytest.raises(ValidationError):
            RegisterWithVerificationRequest(
                email="not-an-email",
                password="SecurePass123!"
            )

    def test_resend_verification_request_valid(self):
        """Test valid resend verification request."""
        from api.email_verification import ResendVerificationRequest
        
        request = ResendVerificationRequest(email="test@example.com")
        
        assert request.email == "test@example.com"


class TestEmailVerificationResponseModels:
    """Test response models."""

    def test_register_response(self):
        """Test registration response model."""
        from api.email_verification import RegisterWithVerificationResponse
        
        response = RegisterWithVerificationResponse(
            message="Test message",
            user_id="123"
        )
        
        assert response.message == "Test message"
        assert response.user_id == "123"

    def test_resend_response(self):
        """Test resend response model."""
        from api.email_verification import ResendVerificationResponse
        
        response = ResendVerificationResponse(message="Email sent")
        
        assert response.message == "Email sent"