"""
Tests for ClientIPExtractor

Issue: #1534 - security(backend): validate X-Forwarded-For against trusted proxy allowlist
"""

import pytest
from unittest.mock import MagicMock
from fastapi import Request

from security.client_ip import ClientIPExtractor, get_client_ip


class TestClientIPExtractor:
    """Tests for secure client IP extraction with trusted proxy validation."""

    def test_no_trusted_proxies_ignores_forwarded(self):
        """When no trusted proxies configured, X-Forwarded-For is ignored."""
        extractor = ClientIPExtractor(trusted_proxies=[])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client.host = "1.2.3.4"

        # Should return direct client IP since no proxies are trusted
        ip = extractor.get_client_ip(mock_request)
        assert ip == "1.2.3.4"

    def test_trusted_proxy_accepts_forwarded(self):
        """When direct client is trusted proxy, X-Forwarded-For is used."""
        extractor = ClientIPExtractor(trusted_proxies=["1.2.3.4"])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client.host = "1.2.3.4"

        # Should return the first IP from X-Forwarded-For
        ip = extractor.get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_cidr_range_trusted(self):
        """CIDR ranges in allowlist are properly validated."""
        extractor = ClientIPExtractor(trusted_proxies=["10.0.0.0/8"])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client.host = "10.0.0.1"  # In 10.0.0.0/8 range

        ip = extractor.get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_cidr_range_not_trusted(self):
        """IP outside CIDR range is not trusted."""
        extractor = ClientIPExtractor(trusted_proxies=["10.0.0.0/8"])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client.host = "203.0.113.1"  # Not in 10.0.0.0/8

        ip = extractor.get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_multiple_trusted_proxies(self):
        """Multiple trusted proxies are all accepted."""
        extractor = ClientIPExtractor(trusted_proxies=["1.1.1.1", "2.2.2.2", "3.3.3.3"])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1"}
        mock_request.client.host = "2.2.2.2"

        ip = extractor.get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_no_forwarded_header_uses_direct(self):
        """When no X-Forwarded-For, falls back to direct client IP."""
        extractor = ClientIPExtractor(trusted_proxies=["1.2.3.4"])

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "1.2.3.4"

        ip = extractor.get_client_ip(mock_request)
        assert ip == "1.2.3.4"

    def test_no_client_returns_unknown(self):
        """When no client info, returns 'unknown'."""
        extractor = ClientIPExtractor(trusted_proxies=[])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1"}
        mock_request.client = None

        ip = extractor.get_client_ip(mock_request)
        assert ip == "unknown"

    def test_empty_forwarded_header_strips_spaces(self):
        """X-Forwarded-For values are properly stripped."""
        extractor = ClientIPExtractor(trusted_proxies=["1.2.3.4"])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "  192.168.1.1  ,  10.0.0.1  "}
        mock_request.client.host = "1.2.3.4"

        ip = extractor.get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_parse_allowlist_single_ip(self):
        """Single IP addresses are parsed correctly."""
        extractor = ClientIPExtractor(trusted_proxies=["192.168.1.1"])

        assert len(extractor._trusted_proxies) == 1
        assert str(extractor._trusted_proxies[0]) == "192.168.1.1/32"

    def test_parse_allowlist_cidr(self):
        """CIDR ranges are parsed correctly."""
        extractor = ClientIPExtractor(trusted_proxies=["192.168.0.0/16"])

        assert len(extractor._trusted_proxies) == 1
        assert str(extractor._trusted_proxies[0]) == "192.168.0.0/16"

    def test_parse_allowlist_mixed(self):
        """Mixed IP addresses and CIDR ranges are parsed."""
        extractor = ClientIPExtractor(
            trusted_proxies=["192.168.1.1", "10.0.0.0/8", "172.16.0.0/12"]
        )

        assert len(extractor._trusted_proxies) == 3

    def test_parse_allowlist_invalid_skipped(self):
        """Invalid IP addresses in allowlist are logged and skipped."""
        extractor = ClientIPExtractor(trusted_proxies=["192.168.1.1", "invalid", "10.0.0.0/8"])

        # Should only have 2 valid entries
        assert len(extractor._trusted_proxies) == 2

    def test_is_trusted_proxy_exact_match(self):
        """Exact IP match in allowlist is trusted."""
        extractor = ClientIPExtractor(trusted_proxies=["192.168.1.100"])

        assert extractor._is_trusted_proxy("192.168.1.100") is True
        assert extractor._is_trusted_proxy("192.168.1.101") is False

    def test_is_trusted_proxy_in_cidr(self):
        """IP within CIDR range is trusted."""
        extractor = ClientIPExtractor(trusted_proxies=["192.168.1.0/24"])

        assert extractor._is_trusted_proxy("192.168.1.1") is True
        assert extractor._is_trusted_proxy("192.168.1.100") is True
        assert extractor._is_trusted_proxy("192.168.2.1") is False

    def test_untrusted_client_logged(self):
        """Untrusted client using X-Forwarded-For is logged as warning."""
        extractor = ClientIPExtractor(trusted_proxies=["1.2.3.4"])

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1"}
        mock_request.client.host = "203.0.113.1"

        # Should return untrusted direct client IP
        ip = extractor.get_client_ip(mock_request)
        assert ip == "203.0.113.1"


class TestGetClientIPFunction:
    """Tests for the convenience function."""

    def test_get_client_ip_uses_extractor(self):
        """get_client_ip uses the global extractor."""
        import security.client_ip as client_ip_module

        # Save original extractor
        original = client_ip_module._extractor

        # Create and set a new extractor with known proxies
        extractor = ClientIPExtractor(trusted_proxies=["1.2.3.4"])
        client_ip_module._extractor = extractor

        try:
            mock_request = MagicMock()
            mock_request.headers = {"X-Forwarded-For": "10.0.0.1"}
            mock_request.client.host = "1.2.3.4"

            ip = client_ip_module.get_client_ip(mock_request)
            assert ip == "10.0.0.1"
        finally:
            # Restore original extractor
            client_ip_module._extractor = original