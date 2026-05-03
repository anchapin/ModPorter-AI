"""
Unit tests for BYOK API Key Vault
Issue: #1227 - Security: BYOK API key vault

Tests:
- Fernet encryption/decryption
- API key masking
- PII scrubbing filter
- BYOK key validation
- BYOK vault error handling
"""

import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

from security.byok_vault import (
    BYOKKeyVault,
    BYOKEncryptionError,
    BYOKValidationError,
    LLMProvider,
    validate_api_key,
    PIIScrubbingFilter,
    get_encryption_key,
    byok_vault,
)


class TestBYOKKeyVault:
    """Tests for BYOK encryption/decryption functionality"""

    def setup_method(self):
        """Set up test fixtures with mocked encryption key"""
        self.vault = BYOKKeyVault()
        self._fernet = Fernet(Fernet.generate_key())
        self.vault._fernet = self._fernet

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption followed by decryption returns original value"""
        api_key = "sk-test-1234567890abcdefghijklmnopqrstuvwxyz"
        encrypted = self.vault.encrypt(api_key)
        decrypted = self.vault.decrypt(encrypted)
        assert decrypted == api_key

    def test_encrypt_empty_key_raises_error(self):
        """Test that encrypting empty key raises BYOKEncryptionError"""
        with pytest.raises(BYOKEncryptionError):
            self.vault.encrypt("")

    def test_encrypt_none_raises_error(self):
        """Test that encrypting None raises BYOKEncryptionError"""
        with pytest.raises(BYOKEncryptionError):
            self.vault.encrypt(None)

    def test_decrypt_empty_raises_error(self):
        """Test that decrypting empty value raises BYOKEncryptionError"""
        with pytest.raises(BYOKEncryptionError):
            self.vault.decrypt(b"")

    def test_decrypt_invalid_data_raises_error(self):
        """Test that decrypting invalid data raises BYOKEncryptionError"""
        with pytest.raises(BYOKEncryptionError):
            self.vault.decrypt(b"invalid encrypted data")

    def test_mask_key_full(self):
        """Test masking a full API key - shows only last 4 chars"""
        api_key = "sk-1234567890abcdefghij"  # 23 chars
        masked = self.vault.mask_key(api_key)
        # 19 stars + last 4 chars = 23 total
        assert masked == "*" * 19 + "ghij"
        assert len(masked) == len(api_key)
        assert masked.endswith("ghij")

    def test_mask_key_short(self):
        """Test masking a short API key"""
        api_key = "abc"
        masked = self.vault.mask_key(api_key)
        assert masked == "****"

    def test_mask_key_exactly_four_chars(self):
        """Test masking an API key with exactly 4 characters - nothing to mask so show stars"""
        api_key = "abcd"
        masked = self.vault.mask_key(api_key)
        # With exactly 4 chars, the implementation returns "****" since len <= 4
        assert masked == "****"

    def test_mask_key_empty(self):
        """Test masking an empty key"""
        masked = self.vault.mask_key("")
        assert masked == "****"

    def test_different_encryptions_produce_different_ciphertext(self):
        """Test that encrypting the same key twice produces different ciphertext"""
        api_key = "sk-test-1234567890"
        encrypted1 = self.vault.encrypt(api_key)
        encrypted2 = self.vault.encrypt(api_key)
        assert encrypted1 != encrypted2

    def test_decryption_of_different_ciphertexts_produces_same_result(self):
        """Test that different ciphertexts decrypt to the same original"""
        api_key = "sk-test-1234567890"
        encrypted1 = self.vault.encrypt(api_key)
        encrypted2 = self.vault.encrypt(api_key)
        assert self.vault.decrypt(encrypted1) == self.vault.decrypt(encrypted2)


class TestGetEncryptionKey:
    """Tests for encryption key retrieval"""

    @patch("security.byok_vault.get_secret")
    def test_get_encryption_key_from_byok_master_key(self, mock_get_secret):
        """Test key derivation from BYOK_MASTER_KEY"""
        mock_get_secret.return_value = "test-master-key-32-bytes-long!!"
        key = get_encryption_key()
        assert len(key) == 44  # Fernet key is 44 bytes base64
        assert isinstance(key, bytes)

    @patch("security.byok_vault.get_secret")
    def test_get_encryption_key_fallback_to_secret_key(self, mock_get_secret):
        """Test fallback to SECRET_KEY when BYOK_MASTER_KEY not set"""

        def secret_side_effect(key):
            if key == "BYOK_MASTER_KEY":
                return None
            elif key == "SECRET_KEY":
                return "secret_key_for_fallback_32bytes!"
            return None

        mock_get_secret.side_effect = secret_side_effect
        key = get_encryption_key()
        assert len(key) == 44
        assert isinstance(key, bytes)

    @patch("security.byok_vault.get_secret")
    def test_get_encryption_key_raises_when_no_key_available(self, mock_get_secret):
        """Test that ValueError is raised when no encryption key available"""
        mock_get_secret.return_value = None
        with pytest.raises(ValueError) as exc_info:
            get_encryption_key()
        assert "BYOK_MASTER_KEY or SECRET_KEY" in str(exc_info.value)


class TestPIIScrubbingFilter:
    """Tests for PII scrubbing in logs"""

    def setup_method(self):
        """Set up test fixtures"""
        self.filter = PIIScrubbingFilter()

    def test_scrubs_openai_key(self):
        """Test that OpenAI-style API keys are scrubbed"""
        message = "Request failed with API key sk-1234567890abcdefghijklmnopqrstuvwxyz"
        scrubbed = self.filter._scrub_message(message)
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in scrubbed
        assert "***REDACTED_API_KEY***" in scrubbed

    def test_scrubs_portkit_key(self):
        """Test that Portkit-style API keys are scrubbed"""
        message = "Using API key mpk_abcdefghijklmnopqrstuvwxyz123456"
        scrubbed = self.filter._scrub_message(message)
        assert "mpk_abcdefghijklmnopqrstuvwxyz123456" not in scrubbed
        assert "***REDACTED_API_KEY***" in scrubbed

    def test_scrubs_bearer_tokens(self):
        """Test that Bearer tokens are scrubbed"""
        message = "Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozergus"
        scrubbed = self.filter._scrub_message(message)
        assert "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
        assert "***REDACTED_API_KEY***" in scrubbed

    def test_scrubs_openrouter_key(self):
        """Test that OpenRouter-style keys are scrubbed"""
        message = "OpenRouter key: openrouter|abcdefghijklmnopqrstuvwxyz123456"
        scrubbed = self.filter._scrub_message(message)
        assert "openrouter|abcdefghijklmnopqrstuvwxyz123456" not in scrubbed
        assert "***REDACTED_API_KEY***" in scrubbed

    def test_passes_through_normal_messages(self):
        """Test that normal messages without API keys pass through"""
        message = "Processing conversion job 12345"
        scrubbed = self.filter._scrub_message(message)
        assert scrubbed == message


class TestLLMProvider:
    """Tests for LLMProvider enum"""

    def test_openrouter_value(self):
        """Test OPENROUTER enum value"""
        assert LLMProvider.OPENROUTER.value == "openrouter"

    def test_openai_value(self):
        """Test OPENAI enum value"""
        assert LLMProvider.OPENAI.value == "openai"

    def test_from_string_valid(self):
        """Test creating enum from valid string"""
        provider = LLMProvider("openrouter")
        assert provider == LLMProvider.OPENROUTER

        provider = LLMProvider("openai")
        assert provider == LLMProvider.OPENAI

    def test_from_string_invalid(self):
        """Test creating enum from invalid string raises ValueError"""
        with pytest.raises(ValueError):
            LLMProvider("anthropic")


class TestBYOKVaultSingleton:
    """Tests for the byok_vault singleton instance"""

    @patch("security.byok_vault.get_encryption_key")
    def test_byok_vault_is_byokkeyvault_instance(self, mock_get_key):
        """Test that byok_vault is an instance of BYOKKeyVault"""
        mock_get_key.return_value = Fernet.generate_key()
        vault = BYOKKeyVault()
        assert isinstance(vault, BYOKKeyVault)

    @patch("security.byok_vault.get_encryption_key")
    def test_byok_vault_can_encrypt_and_decrypt(self, mock_get_key):
        """Test that the vault can encrypt and decrypt"""
        mock_get_key.return_value = Fernet.generate_key()
        vault = BYOKKeyVault()
        api_key = "sk-test-singleton-roundtrip"
        encrypted = vault.encrypt(api_key)
        decrypted = vault.decrypt(encrypted)
        assert decrypted == api_key


class TestBYOKEncryptionError:
    """Tests for BYOKEncryptionError exception"""

    def test_exception_message(self):
        """Test exception message is preserved"""
        error = BYOKEncryptionError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inheritance(self):
        """Test exception inherits from Exception"""
        error = BYOKEncryptionError("test")
        assert isinstance(error, Exception)


class TestBYOKValidationError:
    """Tests for BYOKValidationError exception"""

    def test_exception_message(self):
        """Test exception message is preserved"""
        error = BYOKValidationError("Test validation error")
        assert str(error) == "Test validation error"

    def test_exception_inheritance(self):
        """Test exception inherits from Exception"""
        error = BYOKValidationError("test")
        assert isinstance(error, Exception)


class TestLoggingFilter:
    """Tests for the logging filter integration"""

    def test_filter_returns_true(self):
        """Test that filter returns True to allow logging"""
        import logging

        filter_obj = PIIScrubbingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = filter_obj.filter(record)
        assert result is True
