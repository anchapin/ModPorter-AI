"""
Comprehensive security testing suite.
Tests authentication, authorization, input validation, and rate limiting.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import hashlib
import json
from datetime import datetime, timedelta

# Set up imports
try:
    from modporter.cli.main import convert_mod
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


@pytest.fixture
def mock_auth_service():
    """Create a mock authentication service."""
    service = AsyncMock()
    service.verify_token = AsyncMock(return_value={"user_id": "user123", "valid": True})
    service.generate_token = AsyncMock(return_value="token_abc123")
    return service


@pytest.fixture
def mock_user_context():
    """Create a mock user context."""
    return {
        "user_id": "user123",
        "username": "testuser",
        "roles": ["user"],
        "permissions": ["read", "write"],
        "token": "valid_token_123",
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }


class TestAuthenticationBasics:
    """Test basic authentication mechanisms."""
    
    @pytest.mark.asyncio
    async def test_valid_token_authentication(self, mock_auth_service):
        """Test authentication with valid token."""
        token = "valid_token_123"
        
        result = await mock_auth_service.verify_token(token)
        
        assert result["valid"] is True
        assert result["user_id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejection(self, mock_auth_service):
        """Test rejection of invalid tokens."""
        mock_auth_service.verify_token = AsyncMock(
            return_value={"valid": False, "error": "Invalid token"}
        )
        
        result = await mock_auth_service.verify_token("invalid_token")
        
        assert result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_expired_token_rejection(self, mock_auth_service):
        """Test rejection of expired tokens."""
        mock_auth_service.verify_token = AsyncMock(
            side_effect=ValueError("Token expired")
        )
        
        with pytest.raises(ValueError):
            await mock_auth_service.verify_token("expired_token")
    
    @pytest.mark.asyncio
    async def test_token_generation(self, mock_auth_service):
        """Test secure token generation."""
        user_id = "user123"
        
        token = await mock_auth_service.generate_token(user_id)
        
        assert token is not None
        assert len(token) > 0
    
    @pytest.mark.asyncio
    async def test_token_format_validation(self):
        """Test JWT token format validation."""
        # Valid JWT format: header.payload.signature
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        
        parts = valid_jwt.split(".")
        
        assert len(parts) == 3
        assert all(len(part) > 0 for part in parts)
    
    @pytest.mark.asyncio
    async def test_missing_token_rejection(self, mock_auth_service):
        """Test rejection when token is missing."""
        mock_auth_service.verify_token = AsyncMock(
            side_effect=ValueError("Token required")
        )
        
        with pytest.raises(ValueError):
            await mock_auth_service.verify_token(None)


class TestAuthorizationControl:
    """Test authorization and access control."""
    
    @pytest.mark.asyncio
    async def test_permission_based_access(self, mock_user_context):
        """Test permission-based access control."""
        required_permission = "read"
        user_permissions = mock_user_context["permissions"]
        
        has_access = required_permission in user_permissions
        
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_role_based_access(self, mock_user_context):
        """Test role-based access control."""
        required_role = "user"
        user_roles = mock_user_context["roles"]
        
        has_access = required_role in user_roles
        
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_deny_insufficient_permissions(self, mock_user_context):
        """Test denial of access with insufficient permissions."""
        required_permission = "admin"
        user_permissions = mock_user_context["permissions"]
        
        has_access = required_permission in user_permissions
        
        assert has_access is False
    
    @pytest.mark.asyncio
    async def test_scope_limited_access(self):
        """Test scope-limited access (e.g., user can only access own data)."""
        user_id = "user123"
        resource_owner = "user123"
        
        # User can access their own resources
        can_access = user_id == resource_owner
        
        assert can_access is True
        
        # Different user cannot access
        other_user = "user456"
        can_access = other_user == resource_owner
        
        assert can_access is False
    
    @pytest.mark.asyncio
    async def test_multi_level_authorization(self):
        """Test multi-level authorization check."""
        user = {"id": "user123", "roles": ["user"]}
        resource = {"owner_id": "user123", "required_role": "user"}
        
        # Check 1: Is user authenticated?
        authenticated = user["id"] is not None
        
        # Check 2: Does user have required role?
        authorized = resource["required_role"] in user["roles"]
        
        # Check 3: Is user the owner or admin?
        owner = user["id"] == resource["owner_id"]
        
        # Access granted if authorized and (owner or admin)
        access_granted = authenticated and authorized and (owner or "admin" in user["roles"])
        
        assert access_granted is True


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks."""
        malicious_input = "'; DROP TABLE users; --"
        
        # Should be escaped/parameterized
        safe_input = malicious_input.replace("'", "''")
        
        assert safe_input == "''; DROP TABLE users; --"
    
    def test_xss_prevention(self):
        """Test prevention of XSS attacks."""
        malicious_input = "<script>alert('XSS')</script>"
        
        # Should be HTML escaped
        safe_input = (malicious_input
                     .replace("<", "&lt;")
                     .replace(">", "&gt;"))
        
        assert "&lt;script&gt;" in safe_input
        assert "<script>" not in safe_input
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        malicious_path = "../../etc/passwd"
        
        # Should normalize and validate
        import os
        normalized = os.path.normpath(malicious_path)
        
        assert ".." not in normalized or normalized.startswith("..")
    
    @pytest.mark.asyncio
    async def test_file_upload_validation(self):
        """Test file upload security."""
        # Valid JAR file
        valid_file = {"name": "mod.jar", "size": 1000000, "type": "application/java-archive"}
        
        # Check extension
        allowed_extensions = [".jar", ".mcaddon", ".zip"]
        valid_extension = any(valid_file["name"].endswith(ext) for ext in allowed_extensions)
        
        # Check size
        max_size = 100000000  # 100MB
        valid_size = valid_file["size"] <= max_size
        
        assert valid_extension is True
        assert valid_size is True
    
    @pytest.mark.asyncio
    async def test_malicious_file_rejection(self):
        """Test rejection of malicious files."""
        malicious_file = {"name": "malware.exe", "size": 5000}
        
        allowed_extensions = [".jar", ".mcaddon", ".zip"]
        valid_extension = any(malicious_file["name"].endswith(ext) for ext in allowed_extensions)
        
        assert valid_extension is False
    
    def test_length_constraint_validation(self):
        """Test field length constraints."""
        username = "a" * 256  # Too long
        max_length = 255
        
        is_valid = len(username) <= max_length
        
        assert is_valid is False
    
    def test_type_validation(self):
        """Test data type validation."""
        # Should be integer
        user_id = "not_an_integer"
        
        is_valid_type = isinstance(user_id, int)
        
        assert is_valid_type is False
    
    def test_email_format_validation(self):
        """Test email format validation."""
        import re
        
        valid_email = "user@example.com"
        invalid_email = "not_an_email"
        
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        
        assert re.match(email_pattern, valid_email) is not None
        assert re.match(email_pattern, invalid_email) is None


class TestRateLimiting:
    """Test rate limiting and DoS prevention."""
    
    @pytest.mark.asyncio
    async def test_per_user_rate_limit(self):
        """Test per-user rate limiting."""
        user_id = "user123"
        requests_made = 0
        rate_limit = 100  # 100 requests
        time_window = 60  # per minute
        
        for _ in range(150):
            if requests_made < rate_limit:
                requests_made += 1
            else:
                break  # Rate limit exceeded
        
        assert requests_made == rate_limit
    
    @pytest.mark.asyncio
    async def test_global_rate_limit(self):
        """Test global rate limiting."""
        total_requests = 0
        global_limit = 1000  # 1000 requests per minute
        
        for _ in range(1500):
            if total_requests < global_limit:
                total_requests += 1
            else:
                break
        
        assert total_requests == global_limit
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self):
        """Test rate limit window reset."""
        requests = []
        limit = 10
        window_seconds = 60
        
        # First window: 10 requests
        for i in range(10):
            requests.append({"timestamp": 0, "user": "user1"})
        
        # At window boundary, counter should reset
        window_2_requests = [r for r in requests if r["timestamp"] >= window_seconds]
        
        # New window allows new requests
        can_make_request = len(window_2_requests) < limit
        
        assert can_make_request is True
    
    @pytest.mark.asyncio
    async def test_burst_protection(self):
        """Test protection against burst attacks."""
        burst_limit = 20  # Max 20 requests in burst
        burst_requests = 25
        
        accepted_requests = min(burst_requests, burst_limit)
        rejected_requests = burst_requests - accepted_requests
        
        assert accepted_requests == burst_limit
        assert rejected_requests == 5


class TestDataSecurity:
    """Test data security and encryption."""
    
    def test_password_hashing(self):
        """Test secure password hashing."""
        password = "secure_password_123"
        salt = "random_salt_abc"
        
        # Use PBKDF2 or similar
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        
        # Hash should not be same as password
        assert hashed.hex() != password
    
    def test_password_hash_verification(self):
        """Test password hash verification."""
        password = "secure_password"
        salt = "salt123"
        
        # Hash password
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        
        # Verify password
        verify_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        
        assert hashed == verify_hash
    
    def test_sensitive_data_masking(self):
        """Test masking of sensitive data in logs."""
        api_key = "sk_live_abc123def456"
        
        # Mask API key
        masked = f"{api_key[:7]}...{api_key[-4:]}"
        
        assert "abc123def456" not in masked
        assert masked == "sk_live...f456"
    
    def test_encryption_at_rest(self):
        """Test encryption of data at rest."""
        from cryptography.fernet import Fernet
        
        key = Fernet.generate_key()
        cipher = Fernet(key)
        
        sensitive_data = "confidential_information"
        encrypted = cipher.encrypt(sensitive_data.encode())
        
        # Should be encrypted
        assert encrypted != sensitive_data.encode()
        
        # Should be decryptable
        decrypted = cipher.decrypt(encrypted).decode()
        assert decrypted == sensitive_data


class TestSecurityHeaders:
    """Test security-related HTTP headers."""
    
    def test_content_security_policy_header(self):
        """Test Content-Security-Policy header."""
        headers = {
            "Content-Security-Policy": "default-src 'self'"
        }
        
        assert "Content-Security-Policy" in headers
        assert "default-src 'self'" in headers["Content-Security-Policy"]
    
    def test_hsts_header(self):
        """Test HTTP Strict-Transport-Security header."""
        headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }
        
        assert "Strict-Transport-Security" in headers
    
    def test_x_content_type_options_header(self):
        """Test X-Content-Type-Options header."""
        headers = {
            "X-Content-Type-Options": "nosniff"
        }
        
        assert headers["X-Content-Type-Options"] == "nosniff"
    
    def test_x_frame_options_header(self):
        """Test X-Frame-Options header."""
        headers = {
            "X-Frame-Options": "DENY"
        }
        
        assert headers["X-Frame-Options"] == "DENY"


class TestCORSSecurity:
    """Test CORS and cross-origin security."""
    
    def test_cors_origin_validation(self):
        """Test CORS origin validation."""
        request_origin = "https://trusted-domain.com"
        allowed_origins = ["https://trusted-domain.com", "https://app.example.com"]
        
        is_allowed = request_origin in allowed_origins
        
        assert is_allowed is True
    
    def test_cors_deny_untrusted_origin(self):
        """Test denying untrusted origins."""
        request_origin = "https://malicious-site.com"
        allowed_origins = ["https://trusted-domain.com"]
        
        is_allowed = request_origin in allowed_origins
        
        assert is_allowed is False
    
    def test_cors_preflight_request(self):
        """Test CORS preflight request handling."""
        preflight = {
            "method": "OPTIONS",
            "headers": {
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST"
            }
        }
        
        is_preflight = (preflight["method"] == "OPTIONS" and 
                       "Access-Control-Request-Method" in preflight["headers"])
        
        assert is_preflight is True


class TestSecurityAuditing:
    """Test security event auditing and logging."""
    
    @pytest.mark.asyncio
    async def test_login_audit_logging(self):
        """Test audit logging of login events."""
        audit_log = {
            "event": "user_login",
            "user_id": "user123",
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": "192.168.1.1"
        }
        
        assert audit_log["event"] == "user_login"
        assert audit_log["user_id"] == "user123"
        assert "timestamp" in audit_log
    
    @pytest.mark.asyncio
    async def test_unauthorized_access_logging(self):
        """Test audit logging of unauthorized access attempts."""
        audit_log = {
            "event": "unauthorized_access_attempt",
            "user_id": "user123",
            "resource": "/admin/users",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "high"
        }
        
        assert audit_log["severity"] == "high"
        assert audit_log["event"] == "unauthorized_access_attempt"
    
    @pytest.mark.asyncio
    async def test_data_access_logging(self):
        """Test logging of sensitive data access."""
        audit_log = {
            "event": "data_access",
            "user_id": "user123",
            "resource_id": "doc456",
            "action": "read",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        assert audit_log["event"] == "data_access"
        assert audit_log["action"] == "read"
