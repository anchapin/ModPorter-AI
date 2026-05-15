"""
Tests for URL security module (SSRF protection).

Issue: #1533 - security(backend): verify webhook SSRF guard against RFC1918 targets
"""

import pytest
from unittest import mock

from security.url_security import (
    is_safe_url,
    is_private_ip,
    get_hostname_from_url,
    SSRFProtectionError,
    validate_url_or_raise,
)


class TestIsPrivateIp:
    """Tests for is_private_ip function"""

    # RFC1918 private ranges
    def test_10_private(self):
        """10.0.0.0/8 is private"""
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("10.255.255.255") is True
        assert is_private_ip("10.123.45.67") is True

    def test_172_16_private(self):
        """172.16.0.0/12 is private"""
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True
        assert is_private_ip("172.20.1.1") is True

    def test_192_168_private(self):
        """192.168.0.0/16 is private"""
        assert is_private_ip("192.168.0.1") is True
        assert is_private_ip("192.168.255.255") is True
        assert is_private_ip("192.168.1.100") is True

    # Loopback
    def test_loopback_ipv4(self):
        """127.0.0.0/8 is loopback"""
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.255.255.255") is True

    # Link-local
    def test_link_local_169_254(self):
        """169.254.0.0/16 is link-local"""
        assert is_private_ip("169.254.0.1") is True
        assert is_private_ip("169.254.255.255") is True

    # IPv6
    def test_ipv6_loopback(self):
        """::1 is IPv6 loopback"""
        assert is_private_ip("::1") is True

    def test_ipv6_link_local(self):
        """fe80::/10 is IPv6 link-local"""
        assert is_private_ip("fe80::1") is True
        assert is_private_ip("fe80:0000:0000:0000:0000:0000:0000:0001") is True

    # Public IPs
    def test_public_ip(self):
        """Public IPs should not be flagged as private"""
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False
        assert is_private_ip("93.184.216.34") is False  # example.com

    # Edge cases
    def test_ipv6_scope_id_stripped(self):
        """IPv6 scope IDs should be stripped before checking"""
        assert is_private_ip("fe80::1%eth0") is True

    def test_invalid_ip(self):
        """Invalid IPs should return True (fail secure)"""
        assert is_private_ip("not-an-ip") is True
        assert is_private_ip("") is True


class TestGetHostnameFromUrl:
    """Tests for get_hostname_from_url function"""

    def test_http_url(self):
        assert get_hostname_from_url("http://example.com/path") == "example.com"

    def test_https_url(self):
        assert get_hostname_from_url("https://example.com/path?query=1") == "example.com"

    def test_url_with_port(self):
        assert get_hostname_from_url("http://example.com:8080/path") == "example.com"

    def test_url_with_port_ipv4(self):
        assert get_hostname_from_url("http://192.168.1.1:8080/path") == "192.168.1.1"

    def test_invalid_url(self):
        assert get_hostname_from_url("not-a-url") is None


class TestIsSafeUrl:
    """Tests for is_safe_url function"""

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_safe_public_url(self, mock_getaddrinfo):
        """Public URLs should be allowed"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80))
        ]
        assert is_safe_url("http://example.com/file.zip") is True

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_blocked_10_private(self, mock_getaddrinfo):
        """10.x.x.x should be blocked"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("10.0.0.1", 80))
        ]
        assert is_safe_url("http://example.com/file.zip") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_blocked_172_private(self, mock_getaddrinfo):
        """172.16-31.x.x should be blocked"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("172.16.0.1", 80))
        ]
        assert is_safe_url("http://example.com/file.zip") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_blocked_192_168_private(self, mock_getaddrinfo):
        """192.168.x.x should be blocked"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("192.168.1.1", 80))
        ]
        assert is_safe_url("http://example.com/file.zip") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_blocked_loopback(self, mock_getaddrinfo):
        """127.x.x.x should be blocked"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 80))
        ]
        assert is_safe_url("http://localhost/file.zip") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_blocked_link_local(self, mock_getaddrinfo):
        """169.254.x.x should be blocked"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("169.254.0.1", 80))
        ]
        assert is_safe_url("http://169.254.0.1/file.zip") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_unsafe_scheme(self, mock_getaddrinfo):
        """Non-http/https schemes should be blocked"""
        assert is_safe_url("ftp://example.com/file.zip") is False
        assert is_safe_url("file:///etc/passwd") is False
        assert is_safe_url("dict://localhost/") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_missing_hostname(self, mock_getaddrinfo):
        """URLs without hostname should be blocked"""
        assert is_safe_url("http:///path") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_dns_resolution_failure(self, mock_getaddrinfo):
        """Failed DNS resolution should return False"""
        import socket
        mock_getaddrinfo.side_effect = socket.gaierror("Name resolution failed")
        assert is_safe_url("http://invalid-example.com/file.zip") is False

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_multiple_ips_one_private(self, mock_getaddrinfo):
        """If any resolved IP is private, URL should be blocked"""
        # First IP is public, second is private
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80)),  # Public
            (2, 1, 6, "", ("192.168.1.1", 80)),   # Private
        ]
        assert is_safe_url("http://example.com/file.zip") is False


class TestValidateUrlOrRaise:
    """Tests for validate_url_or_raise function"""

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_safe_url_passes(self, mock_getaddrinfo):
        """Safe URL should not raise"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80))
        ]
        # Should not raise
        validate_url_or_raise("http://example.com/file.zip")

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_private_ip_raises(self, mock_getaddrinfo):
        """Private IP should raise SSRFProtectionError"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("192.168.1.1", 80))
        ]
        with pytest.raises(SSRFProtectionError) as exc_info:
            validate_url_or_raise("http://example.com/file.zip")
        assert "192.168.1.1" in str(exc_info.value)

    @mock.patch("security.url_security.socket.getaddrinfo")
    def test_loopback_raises(self, mock_getaddrinfo):
        """Loopback IP should raise SSRFProtectionError"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 80))
        ]
        with pytest.raises(SSRFProtectionError) as exc_info:
            validate_url_or_raise("http://localhost/file.zip")
        assert "127.0.0.1" in str(exc_info.value)

    def test_invalid_scheme_raises(self):
        """Invalid scheme should raise SSRFProtectionError"""
        with pytest.raises(SSRFProtectionError):
            validate_url_or_raise("ftp://example.com/file.zip")