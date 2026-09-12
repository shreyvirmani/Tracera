import ipaddress
import socket
from dataclasses import dataclass
from typing import Literal

from app.core.url_validator import ValidatedURL


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


PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]


MULTICAST_RANGES = [
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("ff00::/8"),
]


def is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in PRIVATE_RANGES)
    except ValueError:
        return False


def is_multicast_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in MULTICAST_RANGES)
    except ValueError:
        return False


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
            results.append(
                ResolvedIP(
                    ip=ip_str,
                    version=4 if ip.version == 4 else 6,
                    is_private=any(ip in network for network in PRIVATE_RANGES),
                    is_loopback=ip.is_loopback,
                    is_link_local=ip.is_link_local,
                    is_multicast=any(ip in network for network in MULTICAST_RANGES),
                    is_reserved=ip.is_reserved,
                )
            )
        except ValueError:
            continue

    return results


def validate_resolved_ips(resolved_ips: list[ResolvedIP]) -> ResolvedIP:
    if not resolved_ips:
        raise SSRFGuardError("No IP addresses resolved", "NO_IP_RESOLVED")

    for resolved in resolved_ips:
        if resolved.is_loopback:
            raise SSRFGuardError(
                f"Loopback address blocked: {resolved.ip}",
                "LOOPBACK_BLOCKED",
                resolved.ip,
            )
        if resolved.is_multicast:
            raise SSRFGuardError(
                f"Multicast address blocked: {resolved.ip}",
                "MULTICAST_BLOCKED",
                resolved.ip,
            )
        if resolved.is_link_local:
            raise SSRFGuardError(
                f"Link-local address blocked: {resolved.ip}",
                "LINK_LOCAL_BLOCKED",
                resolved.ip,
            )
        if resolved.is_reserved:
            raise SSRFGuardError(
                f"Reserved address blocked: {resolved.ip}",
                "RESERVED_ADDRESS_BLOCKED",
                resolved.ip,
            )
        if resolved.is_private:
            raise SSRFGuardError(
                f"Private address blocked: {resolved.ip}",
                "PRIVATE_ADDRESS_BLOCKED",
                resolved.ip,
            )

    return resolved_ips[0]


def check_ssrf(url: ValidatedURL) -> ResolvedIP:
    resolved_ips = resolve_hostname(url.host)
    safe_ip = validate_resolved_ips(resolved_ips)
    return safe_ip
