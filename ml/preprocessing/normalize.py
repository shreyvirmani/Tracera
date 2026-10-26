"""
Normalization utilities for ML pipeline.

Provides:
- Origin normalization (scheme://host:port with default ports)
- Registrable domain (eTLD+1) extraction using publicsuffix2
- URL normalization

These functions are used for:
1. Deduplication (by origin)
2. Leakage-safe train/val/test splitting (by registrable domain)
3. Provenance tracking

NEVER use these as model features. They are for preprocessing/metadata only.
"""

from urllib.parse import urlparse
from typing import Optional, Set
import publicsuffix2


def get_public_suffix_list() -> publicsuffix2.PublicSuffixList:
    """Get cached Public Suffix List instance."""
    if not hasattr(get_public_suffix_list, "_psl"):
        get_public_suffix_list._psl = publicsuffix2.PublicSuffixList()
    return get_public_suffix_list._psl


def _get_psl_tree() -> dict:
    """Get the PSL tree root dict (second element of the root tuple)."""
    psl = get_public_suffix_list()
    return psl.root[1]


def _traverse_psl_tree(
    host_labels: list,
    tree: tuple,
    index: int = 0
) -> tuple:
    """
    Traverse the PSL tree to find the longest matching public suffix.

    Args:
        host_labels: Domain labels in reverse order (e.g., ['com', 'github', 'user'] for user.github.io)
        tree: PSL tree node (flags, children_dict)
        index: Current index in host_labels

    Returns:
        Tuple of (matched_public_suffix, is_public_suffix)
    """
    if index >= len(host_labels):
        return "", False

    flags, children = tree
    label = host_labels[index]

    # Check exact match
    if label in children:
        child = children[label]
        if isinstance(child, tuple):
            child_flags, child_dict = child
            if child_flags == 0:
                if index + 1 < len(host_labels):
                    deeper_suffix, is_ps = _traverse_psl_tree(host_labels, child, index + 1)
                    if is_ps:
                        return deeper_suffix, True
                return ".".join(reversed(host_labels[:index + 1])), True
            elif child_flags == 1:
                return "", False
        elif child == 0:
            return ".".join(reversed(host_labels[:index + 1])), True

    # Check wildcard match
    if "*" in children:
        child = children["*"]
        if isinstance(child, tuple):
            child_flags, child_dict = child
            if child_flags == 0:
                if index + 1 < len(host_labels):
                    deeper_suffix, is_ps = _traverse_psl_tree(host_labels, child, index + 1)
                    if is_ps:
                        return deeper_suffix, True
                return ".".join(reversed(host_labels[:index + 1])), True
            elif child_flags == 1:
                return "", False
        elif child == 0:
            return ".".join(reversed(host_labels[:index + 1])), True

    return "", False


def get_correct_public_suffix(host: str) -> str:
    """
    Correctly extract the public suffix (eTLD) by traversing the PSL tree.

    This fixes the library's get_public_suffix which fails for subdomains
    of private PSL entries (e.g., user.github.io -> github.io instead of user.github.io).

    Args:
        host: Hostname (e.g., "user.github.io")

    Returns:
        Public suffix (eTLD) (e.g., "github.io")
    """
    if not host:
        return ""

    host = host.lower().strip()
    labels = host.split(".")
    rev_labels = list(reversed(labels))

    tree = _get_psl_tree()

    tld = rev_labels[0]
    if tld not in tree:
        return host

    tld_node = tree[tld]
    if not isinstance(tld_node, tuple):
        return host

    matched, is_ps = _traverse_psl_tree(rev_labels, tld_node, 1)

    if is_ps and matched:
        return matched

    return tld


# Known cloud platform domains for platform-level grouping.
# These are PSL private-section domains where users can register subdomains.
# We group by the platform domain (e.g., github.io) rather than the full registrable domain
# (e.g., user.github.io) for leakage-safe splitting.
CLOUD_PLATFORM_DOMAINS: Set[str] = {
    # GitHub Pages
    "github.io",
    "githubusercontent.com",
    "githubpreview.dev",
    # Heroku
    "herokuapp.com",
    "herokussl.com",
    # Azure
    "azurewebsites.net",
    "azurecontainer.io",
    "azure-mobile.net",
    "cloudapp.net",
    # Google
    "blogspot.com",
    "blogspot.ae", "blogspot.al", "blogspot.am", "blogspot.ba", "blogspot.be",
    "blogspot.bg", "blogspot.bj", "blogspot.ca", "blogspot.cf", "blogspot.ch",
    "blogspot.cl", "blogspot.co.at", "blogspot.co.id", "blogspot.co.il",
    "blogspot.co.ke", "blogspot.co.nz", "blogspot.co.uk", "blogspot.co.za",
    "blogspot.cf", "blogspot.ch", "blogspot.cv", "blogspot.cz", "blogspot.de",
    "blogspot.dk", "blogspot.fi", "blogspot.fr", "blogspot.gr", "blogspot.hk",
    "blogspot.hr", "blogspot.hu", "blogspot.ie", "blogspot.in", "blogspot.is",
    "blogspot.it", "blogspot.jp", "blogspot.kr", "blogspot.li", "blogspot.lt",
    "blogspot.lu", "blogspot.md", "blogspot.mk", "blogspot.mr", "blogspot.mx",
    "blogspot.my", "blogspot.nl", "blogspot.no", "blogspot.pe", "blogspot.pt",
    "blogspot.qa", "blogspot.re", "blogspot.ro", "blogspot.rs", "blogspot.ru",
    "blogspot.se", "blogspot.sg", "blogspot.si", "blogspot.sk", "blogspot.sn",
    "blogspot.td", "blogspot.tw", "blogspot.ug", "blogspot.vn",
    "appspot.com",
    "firebaseapp.com",
    "web.app",
    "run.app",
    "cloudfunctions.net",
    "googleapis.com",
    "googlecode.com",
    "withgoogle.com",
    "withyoutube.com",
    # AWS
    "elasticbeanstalk.com",
    "awsmppl.com",
    "amazonaws.com",
    "cloudfront.net",
    "elb.amazonaws.com",
    "s3.amazonaws.com",
    # Netlify
    "netlify.app",
    "netlify.com",
    # Vercel
    "vercel.app",
    "now.sh",
    # Render
    "render.com",
    "onrender.com",
    # Fly.io
    "fly.dev",
    # Railway
    "railway.app",
    # GitLab
    "gitlab.io",
    # Surge
    "surge.sh",
    # Cloudflare
    "workers.dev",
    "pages.dev",
    # Fastly
    "fastly.net",
    "fastlylb.net",
    "fastly-terrarium.com",
    # DigitalOcean
    "digitaloceanspaces.com",
    # Heroku (additional)
    "herokucdn.com",
    # Netlify (additional)
    "netlify.global",
    # Cloudflare Pages
    "cloudflarepages.com",
    # Render (additional)
    "render.com",
    # Deno Deploy
    "deno.dev",
    # Supabase
    "supabase.co",
    # PlanetScale
    "planetscale.dev",
    # Neon
    "neon.tech",
    # Turso
    "turso.io",
    # Cloudflare Workers
    "workers.dev",
    # GitHub Pages (additional)
    "github.io",
    "githubpreview.dev",
}


def _count_labels(domain: str) -> int:
    """Count the number of labels in a domain."""
    if not domain:
        return 0
    return len(domain.split("."))


def _is_cloud_platform_domain(host: str) -> bool:
    """Check if host ends with a known cloud platform domain."""
    host = host.lower()
    for platform in CLOUD_PLATFORM_DOMAINS:
        if host == platform or host.endswith("." + platform):
            return True
    return False



def _get_cloud_platform_domain(host: str) -> Optional[str]:
    """Return the cloud platform domain if host is on a known platform."""
    host = host.lower()
    # Sort by length ascending so base platforms (shorter) are checked before subdomains
    for platform in sorted(CLOUD_PLATFORM_DOMAINS, key=len):
        if host == platform or host.endswith("." + platform):
            return platform
    return None


def normalize_url(url: str) -> str:
    """
    Normalize a URL to canonical form.

    - Lowercases scheme and host
    - Removes default ports (80 for HTTP, 443 for HTTPS)
    - Ensures path starts with /
    - Removes fragment

    Args:
        url: Raw URL string

    Returns:
        Normalized URL string
    """
    parsed = urlparse(url.strip())

    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid URL: missing scheme or hostname: {url}")

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

    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"

    return normalized


def normalize_origin(url: str) -> str:
    """
    Normalize a URL to its origin: scheme://host:port

    Unlike normalize_url, this:
    - Keeps explicit ports (including default ports for clarity in metadata)
    - Strips path, query, fragment
    - Returns only the origin component

    Args:
        url: Raw URL string

    Returns:
        Origin string (e.g., "https://example.com:443", "http://example.org:8080")
    """
    parsed = urlparse(url.strip())

    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid URL: missing scheme or hostname: {url}")

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()
    port = parsed.port

    if port is None:
        port = 443 if scheme == "https" else 80

    return f"{scheme}://{hostname}:{port}"


def extract_registrable_domain(host: str) -> str:
    """
    Extract the grouping domain for leakage-safe splitting.

    For ICANN domains (com, co.uk, etc.): returns eTLD+1 (e.g., example.com)
    For Private PSL sections (github.io, herokuapp.com, etc.): returns the
    platform domain (e.g., github.io for user.github.io) to group by platform.

    For known cloud platforms (AWS, Google Cloud, etc.): returns the platform
    domain (e.g., amazonaws.com for s3.amazonaws.com).

    This ensures leakage-safe splitting where subdomains of the same platform
    or organization stay together.

    Args:
        host: Hostname (e.g., "www.example.com", "user.github.io")

    Returns:
        Grouping domain for leakage-safe splitting

    Raises:
        ValueError: If host is empty or invalid
    """
    if not host:
        raise ValueError("Empty hostname")

    host = host.lower().strip()

    if host == "localhost" or host.endswith(".localhost"):
        return "localhost"

    import ipaddress
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass

    # First, check if this is a known cloud platform
    platform = _get_cloud_platform_domain(host)
    if platform:
        return platform

    # Otherwise, use the library's SLD (eTLD+1 for ICANN)
    psl = get_public_suffix_list()
    sld = psl.get_sld(host)

    return sld


def extract_registrable_domain_from_url(url: str) -> str:
    """
    Extract registrable domain directly from a URL.

    Args:
        url: Full URL string

    Returns:
        Registrable domain (eTLD+1 for ICANN, platform domain for cloud platforms)
    """
    parsed = urlparse(url.strip())
    if not parsed.hostname:
        raise ValueError(f"URL missing hostname: {url}")
    return extract_registrable_domain(parsed.hostname)
