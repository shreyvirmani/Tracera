import ipaddress
import socket
from dataclasses import dataclass
from typing import Literal

from app.core.url_validator import URLValidationError, ValidatedURL, canonicalize_url


@dataclass(frozen=True)
class ResolvedIP:
    ip: str
    version: Literal[4, 6]
    is_private: bool
    is_loopback: bool
    is_link_local: bool
    is_multicast: bool
    is_reserved: bool


class SSRFGuardError(Exception):
    def __init__(self, message: str, code: str, resolved_ip: str | None = None):
        super().__init__(message)
        self.code = code
        self.resolved_ip = resolved_ip


# Networks that must never be scanned, beyond what ipaddress's is_private /
# is_reserved flags catch. Python's stdlib flags differ between versions, so
# the sensitive ranges are listed explicitly for defense in depth.
BLOCKED_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),  # "this" network
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918 private
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT shared address space
    ipaddress.ip_network("127.0.0.0/8"),  # loopback
    ipaddress.ip_network("169.254.0.0/16"),  # link-local (cloud metadata lives here)
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 private
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),  # 6to4 relay anycast (deprecated)
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 private
    ipaddress.ip_network("198.18.0.0/15"),  # benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # multicast
    ipaddress.ip_network("240.0.0.0/4"),  # reserved
    ipaddress.ip_network("255.255.255.255/32"),  # broadcast
    # IPv6
    ipaddress.ip_network("::/128"),  # unspecified
    ipaddress.ip_network("::1/128"),  # loopback
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped (checked per-address too)
    ipaddress.ip_network("64:ff9b::/96"),  # NAT64 well-known prefix
    ipaddress.ip_network("100::/64"),  # discard-only
    ipaddress.ip_network("2001:db8::/32"),  # documentation
    ipaddress.ip_network("fc00::/7"),  # unique local
    ipaddress.ip_network("fe80::/10"),  # link-local
    ipaddress.ip_network("ff00::/8"),  # multicast
]


PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]


MULTICAST_RANGES = [
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("ff00::/8"),
]


def is_blocked_ip(ip_str: str) -> tuple[bool, str]:
    """Return (blocked, reason) for an IP address string."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True, "INVALID_ADDRESS"

    # Unwrap IPv4-mapped IPv6 addresses so ::ffff:10.0.0.1 is judged by its
    # embedded IPv4 address, not by the (public-looking) wrapper.
    if ip.version == 6:
        mapped = ip.ipv4_mapped
        if mapped is not None:
            ip = mapped

    if ip.is_loopback:
        return True, "LOOPBACK_BLOCKED"
    if ip.is_multicast:
        return True, "MULTICAST_BLOCKED"
    if ip.is_link_local:
        return True, "LINK_LOCAL_BLOCKED"
    if ip.is_reserved:
        return True, "RESERVED_ADDRESS_BLOCKED"
    if ip.is_private:
        return True, "PRIVATE_ADDRESS_BLOCKED"

    for network in BLOCKED_NETWORKS:
        if ip in network:
            return True, "PROHIBITED_ADDRESS_BLOCKED"

    return False, ""


def is_private_ip(ip_str: str) -> bool:
    """Strict RFC1918 check. Use is_blocked_ip for the full SSRF screen."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in PRIVATE_RANGES)
    except ValueError:
        return False


def is_multicast_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return ip.is_multicast


def resolve_hostname(hostname: str) -> list[ResolvedIP]:
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFGuardError(
            f"DNS resolution failed for {hostname}: {e}", "DNS_RESOLUTION_FAILED"
        ) from e

    results = []
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        blocked, _ = is_blocked_ip(ip_str)
        results.append(
            ResolvedIP(
                ip=ip_str,
                version=ip.version,
                is_private=blocked,
                is_loopback=ip.is_loopback,
                is_link_local=ip.is_link_local,
                is_multicast=ip.is_multicast,
                is_reserved=ip.is_reserved,
            )
        )

    return results


def validate_resolved_ips(resolved_ips: list[ResolvedIP]) -> ResolvedIP:
    if not resolved_ips:
        raise SSRFGuardError("No IP addresses resolved", "NO_IP_RESOLVED")

    for resolved in resolved_ips:
        blocked, code = is_blocked_ip(resolved.ip)
        if blocked:
            raise SSRFGuardError(
                f"Prohibited destination address blocked: {resolved.ip}",
                code,
                resolved.ip,
            )

    return resolved_ips[0]


def check_ssrf(url: ValidatedURL) -> ResolvedIP:
    resolved_ips = resolve_hostname(url.host)
    return validate_resolved_ips(resolved_ips)


def validate_redirect_target(location_url: str) -> tuple[ValidatedURL, ResolvedIP]:
    """Fully validate a redirect destination before a request is made to it.

    Redirects are a classic SSRF bypass: a permitted public target can redirect
    the collector to an internal address. Every hop is therefore canonicalized,
    port-policy checked, DNS-resolved, and IP-screened exactly like an initial
    request.
    """
    try:
        validated = canonicalize_url(location_url)
    except URLValidationError as e:
        raise SSRFGuardError(f"Redirect target rejected: {e}", "REDIRECT_TARGET_BLOCKED") from e

    resolved = check_ssrf(validated)
    return validated, resolved
