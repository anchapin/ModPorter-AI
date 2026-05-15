"""
Client IP Extraction Utility

Provides secure extraction of client IP addresses from requests,
validating X-Forwarded-For headers against a trusted proxy allowlist
to prevent IP spoofing attacks.

Issue: #1534 - security(backend): validate X-Forwarded-For against trusted proxy allowlist
"""

import ipaddress
import logging
from typing import Optional, List
from fastapi import Request

from config import settings

logger = logging.getLogger(__name__)


class ClientIPExtractor:
    """
    Secure client IP extractor that validates X-Forwarded-For against trusted proxies.

    When behind proxies (load balancers, CDN, etc.), the X-Forwarded-For header
    can be set by clients to spoof their IP address. This class ensures that
    X-Forwarded-For is only trusted when the direct client is a known trusted proxy.
    """

    def __init__(self, trusted_proxies: Optional[List[str]] = None):
        """
        Initialize the extractor with trusted proxy list.

        Args:
            trusted_proxies: List of IP addresses or CIDR ranges to trust as proxies.
                           If None, reads from TRUSTED_PROXY_ALLOWLIST config.
        """
        if trusted_proxies is not None:
            # Build comma-separated string from list
            allowlist_str = ",".join(trusted_proxies) if isinstance(trusted_proxies, list) else trusted_proxies
            self._trusted_proxies = self._parse_allowlist(allowlist_str)
        else:
            self._trusted_proxies = self._parse_allowlist(
                settings.trusted_proxy_allowlist
            )

    def _parse_allowlist(self, allowlist_str: str) -> List[ipaddress.IPv4Network]:
        """
        Parse comma-separated allowlist string into list of networks.

        Args:
            allowlist_str: Comma-separated IP addresses and CIDR ranges

        Returns:
            List of IPv4Network objects representing trusted proxies
        """
        if not allowlist_str:
            return []

        networks = []
        for item in allowlist_str.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                # Support both single IPs and CIDR ranges
                if "/" in item:
                    networks.append(ipaddress.IPv4Network(item, strict=False))
                else:
                    # Single IP - create /32 network
                    networks.append(ipaddress.IPv4Network(f"{item}/32", strict=False))
            except ValueError as e:
                logger.warning(f"Invalid trusted proxy address '{item}': {e}")

        return networks

    def _is_trusted_proxy(self, ip_str: str) -> bool:
        """
        Check if an IP address is in the trusted proxy allowlist.

        Args:
            ip_str: IP address string to check

        Returns:
            True if the IP is a trusted proxy
        """
        if not self._trusted_proxies:
            return False

        try:
            ip = ipaddress.IPv4Address(ip_str)
            return any(ip in network for network in self._trusted_proxies)
        except ValueError:
            return False

    def get_client_ip(self, request: Request) -> str:
        """
        Extract the real client IP address from a request.

        Validates X-Forwarded-For header against trusted proxy allowlist.
        If the direct client is not a trusted proxy, X-Forwarded-For is ignored
        to prevent IP spoofing attacks.

        Args:
            request: FastAPI Request object

        Returns:
            Client IP address string, or "unknown" if not determinable
        """
        # Get direct client IP (always trusted as it's the immediate connection)
        direct_client_ip = None
        if request.client:
            direct_client_ip = request.client.host

        # Check for X-Forwarded-For header
        forwarded = request.headers.get("X-Forwarded-For")

        if forwarded:
            # X-Forwarded-For is present - check if direct client is a trusted proxy
            if direct_client_ip and self._is_trusted_proxy(direct_client_ip):
                # Direct client is a trusted proxy - trust the X-Forwarded-For header
                # The header format is "client_ip, proxy1_ip, proxy2_ip, ..."
                # We take the FIRST IP as that's the original client
                client_ip = forwarded.split(",")[0].strip()
                if client_ip:
                    logger.debug(
                        f"Trusted proxy {direct_client_ip} forwarded for {client_ip}"
                    )
                    return client_ip
            else:
                # Direct client is NOT a trusted proxy - X-Forwarded-For could be spoofed
                # Log potential attack and fall back to direct client IP
                if direct_client_ip:
                    logger.warning(
                        f"X-Forwarded-For '{forwarded}' ignored from untrusted client "
                        f"{direct_client_ip}. Possible spoofing attempt."
                    )
                    return direct_client_ip
                else:
                    logger.warning(
                        f"X-Forwarded-For '{forwarded}' ignored - no direct client IP"
                    )

        # Fall back to direct client IP or unknown
        return direct_client_ip or "unknown"


# Global extractor instance
_extractor: Optional[ClientIPExtractor] = None


def get_client_ip_extractor() -> ClientIPExtractor:
    """Get or create the global client IP extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ClientIPExtractor()
    return _extractor


def get_client_ip(request: Request) -> str:
    """
    Convenience function to extract client IP from request.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address string
    """
    return get_client_ip_extractor().get_client_ip(request)