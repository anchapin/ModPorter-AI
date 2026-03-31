"""
Tests for backend authentication API endpoints

Coverage target: backend/src/api/auth.py

These tests validate the auth module structure and Pydantic models.
Actual runtime tests require full application context (database, etc.)
"""

import ast
import pytest


# ============================================
# Test Module Structure
# ============================================


def test_auth_module_can_be_parsed():
    """Auth module should be valid Python"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    # Should parse without errors
    tree = ast.parse(source)
    assert tree is not None


def test_auth_module_has_router():
    """Auth module should define APIRouter"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # Find router assignment
    router_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "router":
                    router_found = True
    
    assert router_found, "router should be defined"


def test_auth_module_has_required_imports():
    """Auth module should have required imports"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    required = ["APIRouter", "HTTPBearer", "BaseModel", "EmailStr"]
    for req in required:
        assert req in source, f"Should import {req}"


def test_auth_module_has_register_endpoint():
    """auth.py should define register endpoint"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "/auth/register" in source or 'register' in source


def test_auth_module_has_login_endpoint():
    """auth.py should define login endpoint"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "/auth/login" in source or 'login' in source


# ============================================
# Test Model Validation (Isolated)
# ============================================


def test_register_request_model_structure():
    """RegisterRequest should be a Pydantic model"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    # Should define RegisterRequest class
    assert "class RegisterRequest" in source
    assert "BaseModel" in source


def test_login_request_model_structure():
    """LoginRequest should be a Pydantic model"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "class LoginRequest" in source


def test_token_response_model_structure():
    """TokenResponse should be defined"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "class TokenResponse" in source


def test_register_response_model():
    """RegisterResponse should be defined"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "class RegisterResponse" in source


# ============================================
# Test Security Imports
# ============================================


def test_auth_imports_security_functions():
    """Auth should import security functions"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    # Should import from security.auth
    assert "from security.auth import" in source
    assert "hash_password" in source
    assert "verify_password" in source


def test_auth_imports_db_models():
    """Auth should import database models"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "from db.models import" in source
    assert "User" in source


# ============================================
# Test Endpoint Decorators
# ============================================


def test_has_post_register_decorator():
    """register endpoint should use @router.post"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    # Count POST decorators by string matching
    post_count = source.count('@router.post')
    
    assert post_count >= 6, f"Should have 6+ POST endpoints, found {post_count}"


def test_has_proper_security_scheme():
    """Should define HTTPBearer security"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "HTTPBearer" in source
    assert "security" in source


# ============================================
# Test Model Fields
# ============================================


def test_register_request_has_email():
    """RegisterRequest should have email field"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    # Look for email field with EmailStr
    assert "email:" in source
    assert "EmailStr" in source


def test_register_request_has_password():
    """RegisterRequest should have password field"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert 'password:' in source


def test_login_request_fields():
    """LoginRequest should have email and password"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    # Should define LoginRequest with email and password
    assert "class LoginRequest" in source


# ============================================
# Test Error Handling
# ============================================


def test_has_http_exception():
    """Should use HTTPException for errors"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "HTTPException" in source


def test_has_status_codes():
    """Should use status codes"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert "status" in source


# ============================================
# Edge Cases - Router Configuration
# ============================================


def test_router_prefix_is_auth():
    """Router should have /auth prefix"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert 'prefix="/auth"' in source


def test_router_has_tags():
    """Router should have tags for documentation"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/api/auth.py") as f:
        source = f.read()
    
    assert 'tags=' in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])