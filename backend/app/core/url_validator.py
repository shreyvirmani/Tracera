import ipaddress
import re
from urllib.parse import urlparse

from pydantic import BaseModel


class ValidatedURL(BaseModel):
    original_url: str
    canonical_url: str
    scheme: str
    host: str
    port: int | None = None
    path: str
    query: str | None = None


SCHEME_PATTERN = re.compile(r"^https?$", re.IGNORECASE)
HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)
IPV4_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
IPV6_PATTERN = re.compile(
    r"^("
    r"([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|"
    r"([0-9a-fA-F]{1,4}:){1,7}:|"
    r"([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|"
    r"([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|"
    r"([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|"
    r"([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|"
    r"([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|"
    r"[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|"
    r":((:[0-9a-fA-F]{1,4}){1,7}|:)|"
    r"fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|"
    r"::(ffff(:0{1,4})?:)?((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9])|"
    r"([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9])"
    r")$"
)

RESERVED_HOSTNAMES = {"localhost"}


class URLValidationError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def validate_scheme(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if not SCHEME_PATTERN.match(scheme):
        raise URLValidationError(
            f"Invalid scheme: {scheme}. Only http and https are allowed.",
            "INVALID_SCHEME",
        )
    return scheme


def validate_hostname(host: str) -> str:
    host = host.lower().strip()
    if not host:
        raise URLValidationError("Hostname is empty", "EMPTY_HOSTNAME")

    if host in RESERVED_HOSTNAMES:
        return host

    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass

    if not HOSTNAME_PATTERN.match(host):
        raise URLValidationError(f"Invalid hostname format: {host}", "INVALID_HOSTNAME")

    return host


def validate_port(port: int | None, scheme: str) -> int:
    if port is not None:
        if not (1 <= port <= 65535):
            raise URLValidationError(
                f"Invalid port: {port}. Must be between 1 and 65535.", "INVALID_PORT"
            )
        return port

    return 443 if scheme == "https" else 80


def canonicalize_url(url: str) -> ValidatedURL:
    parsed = urlparse(url.strip())

    scheme = validate_scheme(url)
    host = validate_hostname(parsed.hostname or "")
    port = validate_port(parsed.port, scheme)

    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path

    query = parsed.query if parsed.query else None

    canonical = f"{scheme}://{host}"
    if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
        canonical += f":{port}"
    canonical += path
    if query:
        canonical += f"?{query}"

    return ValidatedURL(
        original_url=url,
        canonical_url=canonical,
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        query=query,
    )
