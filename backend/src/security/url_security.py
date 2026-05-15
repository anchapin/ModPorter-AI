"""
URL Security Module

Provides SSRF (Server-Side Request Forgery) protection by validating URLs
before making HTTP requests. Blocks requests to private, loopback, and
link-local IP addresses.

RFC1918 private address ranges:
- 10.0.0.0/8 (10.x.x.x)
- 172.16.0.0/12 (172.16.x.x - 172.31.x.x)
- 192.168.0.0/16 (192.168.x.x)

Also blocks:
- Loopback: 127.0.0.0/8
- Link-local: 169.254.0.0/16
- IPv6 loopback: ::1
- IPv6 link-local: fe80::/10
"""

import ipaddress
import logging
import socket
import urllib.parse
from typing import List, Tuple

logger = logging.getLogger(__name__)


class SSRFProtectionError(Exception):
    """Raised when a URL targets a blocked IP range (RFC1918, loopback, etc.)"""

    def __init__(self, ip_address: str, hostname: str, ip_range: str = "private"):
        self.ip_address = ip_address
        self.hostname = hostname
        self.ip_range = ip_range
        super().__init__(
            f"Blocked RFC1918/private IP address: {ip_address} "
            f"(resolved from hostname: {hostname}, range: {ip_range})"
        )


def is_private_ip(ip: str) -> bool:
    """
    Check if an IP address is private (RFC1918), loopback, or link-local.

    Args:
        ip: IP address string (either IPv4 or IPv6)

    Returns:
        True if the IP is in a blocked range, False otherwise
    """
    try:
        ip_str = ip.split("%")[0]  # Strip IPv6 scope ID if present
        ip_obj = ipaddress.ip_address(ip_str)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
    except ValueError:
        # If we can't parse it as an IP, treat it as potentially dangerous
        logger.warning(f"Could not parse IP address: {ip}")
        return True  # Fail secure


def get_hostname_from_url(url: str) -> str | None:
    """
    Extract hostname from a URL.

    Args:
        url: The URL to parse

    Returns:
        Hostname string or None if invalid/missing
    """
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def is_safe_url(url: str, allowed_schemes: tuple = ("http", "https")) -> bool:
    """
    Validate that a URL does not target a private, loopback, or link-local IP.

    This function resolves the hostname via DNS and checks all returned
    IP addresses against the blocklist.

    Args:
        url: The URL to validate
        allowed_schemes: Tuple of allowed URL schemes (default: http, https)

    Returns:
        True if the URL is safe (public IP), False if it targets a blocked range
    """
    try:
        parsed = urllib.parse.urlparse(url)

        # Check scheme
        if parsed.scheme not in allowed_schemes:
            logger.warning(f"Unsafe scheme '{parsed.scheme}' in URL")
            return False

        hostname = parsed.hostname
        if not hostname:
            logger.warning("No hostname found in URL")
            return False

        # Resolve hostname to IP addresses
        try:
            # getaddrinfo returns list of (family, type, proto, canonname, sockaddr)
            # For IPv4, sockaddr is (address, port)
            # For IPv6, sockaddr is (address, port, flowinfo, scopeid)
            infos: List[Tuple] = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            logger.warning(f"Could not resolve hostname: {hostname}")
            return False

        # Check all resolved IPs
        for info in infos:
            sockaddr = info[4]
            if isinstance(sockaddr, tuple):
                ip = sockaddr[0]
            else:
                # Handle IPv6 tuple format (address, port, flowinfo, scopeid)
                ip = sockaddr[0]

            if is_private_ip(ip):
                logger.warning(
                    f"Blocked private/loopback IP: {ip} for hostname: {hostname}"
                )
                return False

        return True

    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return False


def validate_url_or_raise(url: str, allowed_schemes: tuple = ("http", "https")) -> None:
    """
    Validate a URL and raise SSRFProtectionError if it's unsafe.

    Args:
        url: The URL to validate
        allowed_schemes: Tuple of allowed URL schemes

    Raises:
        SSRFProtectionError: If the URL targets a private, loopback, or link-local IP
    """
    try:
        parsed = urllib.parse.urlparse(url)

        if parsed.scheme not in allowed_schemes:
            raise SSRFProtectionError(
                ip_address="N/A",
                hostname=parsed.hostname or "unknown",
                ip_range=f"scheme:{parsed.scheme}",
            )

        hostname = parsed.hostname
        if not hostname:
            raise SSRFProtectionError(
                ip_address="N/A",
                hostname="unknown",
                ip_range="no hostname",
            )

        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise SSRFProtectionError(
                ip_address="unresolved",
                hostname=hostname,
                ip_range=f"DNS error: {e}",
            )

        for info in infos:
            sockaddr = info[4]
            if isinstance(sockaddr, tuple):
                ip = sockaddr[0]
            else:
                ip = sockaddr[0]

            ip_str = ip.split("%")[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_private:
                    raise SSRFProtectionError(
                        ip_address=ip_str,
                        hostname=hostname,
                        ip_range="RFC1918 private",
                    )
                if ip_obj.is_loopback:
                    raise SSRFProtectionError(
                        ip_address=ip_str,
                        hostname=hostname,
                        ip_range="loopback",
                    )
                if ip_obj.is_link_local:
                    raise SSRFProtectionError(
                        ip_address=ip_str,
                        hostname=hostname,
                        ip_range="link-local",
                    )
            except ValueError:
                raise SSRFProtectionError(
                    ip_address=ip_str,
                    hostname=hostname,
                    ip_range="unparseable",
                )

    except SSRFProtectionError:
        raise
    except Exception as e:
        raise SSRFProtectionError(
            ip_address="unknown",
            hostname=get_hostname_from_url(url) or "unknown",
            ip_range=f"validation error: {e}",
        )