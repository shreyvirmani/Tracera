import re
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, Optional
from pydantic import BaseModel, field_validator

from app.core.config import settings, is_private_ip


class URLValidationError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class ValidatedURL(BaseModel):
    original_url: str
    canonical_url: str
    scheme: str
    hostname: str
    port: Optional[int] = None
    path: str
    query: Optional[str] = None
    resolved_ips: list[str] = []

    @field_validator("scheme")
    @classmethod
    def validate_scheme(cls, v: str) -> str:
        if v not in settings.ssrf_allowed_schemes:
            raise ValueError(f"Scheme '{v}' not allowed")
        return v


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        raise URLValidationError("Missing URL scheme", "MISSING_SCHEME")
    if not parsed.hostname:
        raise URLValidationError("Missing hostname", "MISSING_HOSTNAME")

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()
    port = parsed.port
    path = parsed.path or "/"
    query = parsed.query

    if port and ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        port = None

    netloc = hostname
    if port:
        netloc = f"{hostname}:{port}"

    canonical = f"{scheme}://{netloc}{path}"
    if query:
        canonical += f"?{query}"

    return canonical


def validate_hostname(hostname: str) -> None:
    if not hostname:
        raise URLValidationError("Empty hostname", "EMPTY_HOSTNAME")

    if len(hostname) > 253:
        raise URLValidationError("Hostname too long", "HOSTNAME_TOO_LONG")

    if hostname.startswith(".") or hostname.endswith("."):
        raise URLValidationError("Invalid hostname format", "INVALID_HOSTNAME_FORMAT")

    labels = hostname.split(".")
    for label in labels:
        if not label or len(label) > 63:
            raise URLValidationError("Invalid hostname label", "INVALID_LABEL")
        if not re.match(r"^[a-z0-9-]+$", label, re.IGNORECASE):
            raise URLValidationError("Invalid hostname characters", "INVALID_CHARACTERS")
        if label.startswith("-") or label.endswith("-"):
            raise URLValidationError("Invalid label hyphens", "INVALID_HYPHENS")


async def resolve_and_validate(hostname: str) -> list[str]:
    import socket
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        infos = await loop.getaddrinfo(hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise URLValidationError(f"DNS resolution failed: {e}", "DNS_FAILED")

    ips = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)

    if not ips:
        raise URLValidationError("No IP addresses resolved", "NO_IPS")

    for ip in ips:
        if settings.ssrf_block_loopback and ipaddress.ip_address(ip).is_loopback:
            raise URLValidationError(f"Loopback address blocked: {ip}", "BLOCKED_LOOPBACK")
        if settings.ssrf_block_private and is_private_ip(ip):
            raise URLValidationError(f"Private address blocked: {ip}", "BLOCKED_PRIVATE")
        if settings.ssrf_block_link_local and ipaddress.ip_address(ip).is_link_local:
            raise URLValidationError(f"Link-local address blocked: {ip}", "BLOCKED_LINK_LOCAL")
        if settings.ssrf_block_multicast and ipaddress.ip_address(ip).is_multicast:
            raise URLValidationError(f"Multicast address blocked: {ip}", "BLOCKED_MULTICAST")

    return ips


async def validate_url(url: str) -> ValidatedURL:
    canonical = canonicalize_url(url)
    parsed = urlparse(canonical)

    validate_hostname(parsed.hostname or "")

    resolved_ips = await resolve_and_validate(parsed.hostname or "")

    return ValidatedURL(
        original_url=url,
        canonical_url=canonical,
        scheme=parsed.scheme,
        hostname=parsed.hostname or "",
        port=parsed.port,
        path=parsed.path or "/",
        query=parsed.query or None,
        resolved_ips=resolved_ips,
    )


def validate_redirect_url(redirect_url: str, original_validated: ValidatedURL) -> ValidatedURL:
    canonical = canonicalize_url(redirect_url)
    parsed = urlparse(canonical)

    validate_hostname(parsed.hostname or "")

    return ValidatedURL(
        original_url=redirect_url,
        canonical_url=canonical,
        scheme=parsed.scheme,
        hostname=parsed.hostname or "",
        port=parsed.port,
        path=parsed.path or "/",
        query=parsed.query or None,
        resolved_ips=[],
    )