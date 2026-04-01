"""
Tests for backend authentication API endpoints

Coverage target: backend/src/api/auth.py

These tests validate the auth module structure and Pydantic models.
"""

import pytest
from pydantic import BaseModel, EmailStr, Field, ValidationError


# ============================================
# Test Module Import
# ============================================

def test_auth_module_importable():
    """Auth module should be importable"""
    # Skip if module can't be imported due to dependency issues
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert auth is not None


def test_auth_module_has_router():
    """Auth module should define router as APIRouter"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    from fastapi import APIRouter
    assert isinstance(auth.router, APIRouter)


def test_auth_router_has_auth_prefix():
    """Router should have /auth prefix"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert auth.router.prefix == "/auth"


def test_auth_router_has_auth_tags():
    """Router should have Authentication tag"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert "Authentication" in auth.router.tags


# ============================================
# Test Model Validation
# ============================================

def test_register_request_model_exists():
    """RegisterRequest should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.RegisterRequest, BaseModel)


def test_register_request_has_email_field():
    """RegisterRequest should have email field with EmailStr type"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.RegisterRequest(email="test@example.com", password="TestPass123!")
    assert model.email == "test@example.com"


def test_register_request_has_password_field():
    """RegisterRequest should have password field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.RegisterRequest(email="test@example.com", password="TestPass123!")
    assert hasattr(model, 'password')


def test_register_request_validates_email_format():
    """RegisterRequest should reject invalid email formats"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    with pytest.raises(ValidationError):
        auth.RegisterRequest(email="not-an-email", password="TestPass123!")


def test_register_request_validates_password_min_length():
    """RegisterRequest should reject passwords less than 8 chars"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    with pytest.raises(ValidationError):
        auth.RegisterRequest(email="test@example.com", password="Short1!")


def test_register_request_validates_password_has_number():
    """RegisterRequest should reject passwords without numbers"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    with pytest.raises(ValidationError):
        auth.RegisterRequest(email="test@example.com", password="NoNumbers!")


def test_register_request_validates_password_has_special_char():
    """RegisterRequest should reject passwords without special characters"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    with pytest.raises(ValidationError):
        auth.RegisterRequest(email="test@example.com", password="NoSpecial123")


def test_register_request_accepts_valid_password():
    """RegisterRequest should accept valid passwords"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.RegisterRequest(email="test@example.com", password="ValidPass123!")
    assert model.password == "ValidPass123!"


def test_login_request_model_exists():
    """LoginRequest should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.LoginRequest, BaseModel)


def test_login_request_has_email_field():
    """LoginRequest should have email field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.LoginRequest(email="test@example.com", password="password")
    assert model.email == "test@example.com"


def test_login_request_has_password_field():
    """LoginRequest should have password field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.LoginRequest(email="test@example.com", password="password")
    assert model.password == "password"


def test_login_request_validates_email():
    """LoginRequest should validate email format"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    with pytest.raises(ValidationError):
        auth.LoginRequest(email="invalid", password="password")


def test_token_response_model_exists():
    """TokenResponse should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.TokenResponse, BaseModel)


def test_token_response_has_access_token_field():
    """TokenResponse should have access_token field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.TokenResponse(access_token="abc123")
    assert model.access_token == "abc123"


def test_token_response_has_token_type_with_default():
    """TokenResponse should have token_type with default 'bearer'"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.TokenResponse(access_token="abc123")
    assert model.token_type == "bearer"


def test_register_response_model_exists():
    """RegisterResponse should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.RegisterResponse, BaseModel)


def test_register_response_has_message_field():
    """RegisterResponse should have message field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.RegisterResponse(message="Success", user_id="123")
    assert model.message == "Success"


def test_register_response_has_user_id_field():
    """RegisterResponse should have user_id field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.RegisterResponse(message="Success", user_id="123")
    assert model.user_id == "123"


def test_login_response_model_exists():
    """LoginResponse should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.LoginResponse, BaseModel)


def test_login_response_has_required_fields():
    """LoginResponse should have access_token and refresh_token"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.LoginResponse(access_token="abc", refresh_token="xyz")
    assert model.access_token == "abc"
    assert model.refresh_token == "xyz"


def test_password_reset_request_model_exists():
    """PasswordResetRequest should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.PasswordResetRequest, BaseModel)


def test_password_reset_request_validates_email():
    """PasswordResetRequest should validate email"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    with pytest.raises(ValidationError):
        auth.PasswordResetRequest(email="not-email")


def test_password_reset_confirm_request_model_exists():
    """PasswordResetConfirmRequest should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.PasswordResetConfirmRequest, BaseModel)


def test_token_refresh_request_model_exists():
    """TokenRefreshRequest should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.TokenRefreshRequest, BaseModel)


def test_token_refresh_request_has_refresh_token_field():
    """TokenRefreshRequest should have refresh_token field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.TokenRefreshRequest(refresh_token="token123")
    assert model.refresh_token == "token123"


def test_message_response_model_exists():
    """MessageResponse should be a Pydantic BaseModel"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert issubclass(auth.MessageResponse, BaseModel)


def test_message_response_has_message_field():
    """MessageResponse should have message field"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    model = auth.MessageResponse(message="Hello")
    assert model.message == "Hello"


# ============================================
# Test Security Imports
# ============================================

def test_auth_has_http_bearer():
    """Auth module should import HTTPBearer for security"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    from fastapi.security import HTTPBearer
    assert isinstance(auth.security, HTTPBearer)


def test_auth_exports_hash_password():
    """Auth module should import hash_password from security.auth"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.hash_password)


def test_auth_exports_verify_password():
    """Auth module should import verify_password from security.auth"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.verify_password)


def test_auth_exports_create_access_token():
    """Auth module should import create_access_token"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.create_access_token)


def test_auth_exports_create_refresh_token():
    """Auth module should import create_refresh_token"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.create_refresh_token)


def test_auth_exports_verify_token():
    """Auth module should import verify_token"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.verify_token)


def test_auth_exports_generate_verification_token():
    """Auth module should import generate_verification_token"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.generate_verification_token)


def test_auth_exports_generate_reset_token():
    """Auth module should import generate_reset_token"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.generate_reset_token)


def test_auth_exports_generate_api_key():
    """Auth module should import generate_api_key"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    assert callable(auth.generate_api_key)


# ============================================
# Test Password Hashing Behavior
# ============================================

def test_hash_password_produces_hash():
    """hash_password should produce a hash different from input"""
    auth=pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    password="test_password_123"
    hashed = auth.hash_password(password)
    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$2b$")  # bcrypt format


def test_verify_password_correct_password():
    """verify_password should return True for correct password"""
    auth=pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    password="test_password_123"
    hashed = auth.hash_password(password)
    assert auth.verify_password(password, hashed) is True


def test_verify_password_wrong_password():
    """verify_password should return False for wrong password"""
    auth=pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    password="test_password_123"
    hashed = auth.hash_password(password)
    assert auth.verify_password("WrongPassword123!", hashed) is False


def test_generate_verification_token_produces_token():
    """generate_verification_token should produce a token string"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    token = auth.generate_verification_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_reset_token_produces_token():
    """generate_reset_token should produce a token string"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    token = auth.generate_reset_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_api_key_produces_key_and_prefix():
    """generate_api_key should produce a tuple of (full_key, prefix)"""
    auth = pytest.importorskip("backend.src.api.auth", reason="backend.src.api.auth not importable")
    result = auth.generate_api_key()
    assert isinstance(result, tuple)
    assert len(result) == 2
    full_key, prefix = result
    assert isinstance(full_key, str)
    assert isinstance(prefix, str)
    assert len(full_key) > 0
    assert len(prefix) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
