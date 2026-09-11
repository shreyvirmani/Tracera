from dataclasses import dataclass, asdict
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from app.core.config import settings
from app.collector.safe_collector import CollectorResponse


@dataclass
class FeatureVector:
    feature_schema_version: str

    # HTTP
    status_code: int
    response_size_bytes: int
    response_time_ms: float
    content_type: Optional[str]
    redirect_count: int
    https_enabled: bool

    # Security headers
    hsts_present: bool
    csp_present: bool
    x_content_type_options_present: bool
    x_frame_options_present: bool
    referrer_policy_present: bool
    permissions_policy_present: bool

    # Cookies
    cookie_count: int
    cookie_secure_ratio: float
    cookie_httponly_ratio: float
    cookie_samesite_strict_ratio: float
    cookie_samesite_lax_ratio: float
    cookie_samesite_none_ratio: float
    third_party_cookie_indicators: int

    # TLS
    cert_expiry_days: Optional[int]
    cert_is_expired: bool
    tls_version: Optional[str]
    cert_subject_cn: Optional[str]
    cert_issuer_cn: Optional[str]

    # HTML/Structure
    html_size_bytes: int
    script_count: int
    stylesheet_count: int
    image_count: int
    iframe_count: int
    form_count: int
    external_domain_count: int
    mixed_content_count: int

    # Technology disclosure
    server_header_present: bool
    server_header_value: Optional[str]
    x_powered_by_present: bool
    x_powered_by_value: Optional[str]
    framework_indicators: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def extract_features(response: CollectorResponse, validated_url) -> FeatureVector:
    headers = {k.lower(): v for k, v in response.headers.items()}
    content = response.content
    html = content.decode("utf-8", errors="replace")

    # HTTP features
    https_enabled = response.url.startswith("https://")
    content_type = headers.get("content-type")

    # Security headers
    hsts_present = "strict-transport-security" in headers
    csp_present = "content-security-policy" in headers
    x_content_type_options_present = headers.get("x-content-type-options", "").lower() == "nosniff"
    x_frame_options_present = "x-frame-options" in headers
    referrer_policy_present = "referrer-policy" in headers
    permissions_policy_present = "permissions-policy" in headers

    # Cookies
    cookie_data = _parse_cookies(headers.get("set-cookie", ""), response.url)

    # TLS
    tls_info = _extract_tls(response.tls_info)

    # HTML/Structure
    html_features = _extract_html_features(html, response.url)

    # Technology disclosure
    tech_features = _extract_tech_features(headers, html)

    return FeatureVector(
        feature_schema_version=settings.feature_schema_version,
        status_code=response.status_code,
        response_size_bytes=len(content),
        response_time_ms=response.response_time_ms,
        content_type=content_type,
        redirect_count=response.redirect_count,
        https_enabled=https_enabled,
        hsts_present=hsts_present,
        csp_present=csp_present,
        x_content_type_options_present=x_content_type_options_present,
        x_frame_options_present=x_frame_options_present,
        referrer_policy_present=referrer_policy_present,
        permissions_policy_present=permissions_policy_present,
        cookie_count=cookie_data["count"],
        cookie_secure_ratio=cookie_data["secure_ratio"],
        cookie_httponly_ratio=cookie_data["httponly_ratio"],
        cookie_samesite_strict_ratio=cookie_data["samesite_strict_ratio"],
        cookie_samesite_lax_ratio=cookie_data["samesite_lax_ratio"],
        cookie_samesite_none_ratio=cookie_data["samesite_none_ratio"],
        third_party_cookie_indicators=cookie_data["third_party_indicators"],
        cert_expiry_days=tls_info["expiry_days"],
        cert_is_expired=tls_info["is_expired"],
        tls_version=tls_info["version"],
        cert_subject_cn=tls_info["subject_cn"],
        cert_issuer_cn=tls_info["issuer_cn"],
        html_size_bytes=html_features["html_size"],
        script_count=html_features["script_count"],
        stylesheet_count=html_features["stylesheet_count"],
        image_count=html_features["image_count"],
        iframe_count=html_features["iframe_count"],
        form_count=html_features["form_count"],
        external_domain_count=html_features["external_domains"],
        mixed_content_count=html_features["mixed_content"],
        server_header_present=tech_features["server_present"],
        server_header_value=tech_features["server_value"],
        x_powered_by_present=tech_features["powered_by_present"],
        x_powered_by_value=tech_features["powered_by_value"],
        framework_indicators=tech_features["frameworks"],
    )


def _parse_cookies(set_cookie_header: str, response_url: str) -> dict:
    if not set_cookie_header:
        return {
            "count": 0,
            "secure_ratio": 0.0,
            "httponly_ratio": 0.0,
            "samesite_strict_ratio": 0.0,
            "samesite_lax_ratio": 0.0,
            "samesite_none_ratio": 0.0,
            "third_party_indicators": 0,
        }

    cookies = []
    for part in set_cookie_header.split(","):
        part = part.strip()
        if "=" in part:
            cookies.append(part)

    if not cookies:
        return {
            "count": 0,
            "secure_ratio": 0.0,
            "httponly_ratio": 0.0,
            "samesite_strict_ratio": 0.0,
            "samesite_lax_ratio": 0.0,
            "samesite_none_ratio": 0.0,
            "third_party_indicators": 0,
        }

    secure_count = 0
    httponly_count = 0
    samesite_strict = 0
    samesite_lax = 0
    samesite_none = 0
    third_party = 0

    response_domain = urlparse(response_url).hostname or ""

    for cookie in cookies:
        cookie_lower = cookie.lower()
        if "secure" in cookie_lower:
            secure_count += 1
        if "httponly" in cookie_lower:
            httponly_count += 1
        if "samesite=strict" in cookie_lower:
            samesite_strict += 1
        elif "samesite=lax" in cookie_lower:
            samesite_lax += 1
        elif "samesite=none" in cookie_lower:
            samesite_none += 1

        if "domain=" in cookie_lower:
            domain_start = cookie_lower.index("domain=") + 7
            domain_end = cookie_lower.find(";", domain_start)
            if domain_end == -1:
                domain_end = len(cookie_lower)
            cookie_domain = cookie_lower[domain_start:domain_end].strip().lstrip(".")
            if cookie_domain and cookie_domain != response_domain and not cookie_domain.endswith("." + response_domain):
                third_party += 1

    total = len(cookies)
    return {
        "count": total,
        "secure_ratio": secure_count / total if total else 0.0,
        "httponly_ratio": httponly_count / total if total else 0.0,
        "samesite_strict_ratio": samesite_strict / total if total else 0.0,
        "samesite_lax_ratio": samesite_lax / total if total else 0.0,
        "samesite_none_ratio": samesite_none / total if total else 0.0,
        "third_party_indicators": third_party,
    }


def _extract_tls(tls_info: Optional[dict]) -> dict:
    if not tls_info:
        return {
            "expiry_days": None,
            "is_expired": False,
            "version": None,
            "subject_cn": None,
            "issuer_cn": None,
        }

    from datetime import datetime

    not_after = tls_info.get("not_after")
    expiry_days = None
    is_expired = False

    if not_after:
        try:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            expiry_days = (expiry - datetime.utcnow()).days
            is_expired = expiry_days < 0
        except Exception:
            pass

    subject = tls_info.get("subject", {})
    issuer = tls_info.get("issuer", {})

    return {
        "expiry_days": expiry_days,
        "is_expired": is_expired,
        "version": tls_info.get("version"),
        "subject_cn": subject.get("commonName") or subject.get("CN"),
        "issuer_cn": issuer.get("commonName") or issuer.get("CN"),
    }


def _extract_html_features(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    scripts = soup.find_all("script")
    stylesheets = soup.find_all("link", rel="stylesheet")
    images = soup.find_all("img")
    iframes = soup.find_all("iframe")
    forms = soup.find_all("form")

    base_domain = urlparse(base_url).hostname or ""
    external_domains = set()
    mixed_content = 0

    for tag in soup.find_all(["script", "link", "img", "iframe", "a"], src=True):
        src = tag.get("src") or tag.get("href") or ""
        if src.startswith("http://") and base_url.startswith("https://"):
            mixed_content += 1
        if src.startswith("http"):
            parsed = urlparse(src)
            if parsed.hostname and parsed.hostname != base_domain:
                external_domains.add(parsed.hostname)

    for tag in soup.find_all(["script", "link", "img", "iframe"], src=True):
        src = tag.get("src", "")
        if src.startswith("http://") and base_url.startswith("https://"):
            mixed_content += 1

    return {
        "html_size": len(html.encode("utf-8")),
        "script_count": len(scripts),
        "stylesheet_count": len(stylesheets),
        "image_count": len(images),
        "iframe_count": len(iframes),
        "form_count": len(forms),
        "external_domains": len(external_domains),
        "mixed_content": mixed_content,
    }


def _extract_tech_features(headers: dict, html: str) -> dict:
    server = headers.get("server", "")
    powered_by = headers.get("x-powered-by", "")

    frameworks = []
    html_lower = html.lower()

    framework_patterns = {
        "react": ["react", "__REACT_DEVTOOLS_GLOBAL_HOOK__"],
        "nextjs": ["__NEXT_DATA__", "next.js", "/_next/"],
        "vue": ["vue.js", "vue.min.js", "__VUE__"],
        "angular": ["angular.js", "angular.min.js", "ng-version"],
        "django": ["csrfmiddlewaretoken", "django"],
        "rails": ["rails", "ruby on rails"],
        "laravel": ["laravel", "laravel_session"],
        "express": ["express", "x-powered-by: express"],
        "wordpress": ["wp-content", "wp-includes", "wordpress"],
        "cloudflare": ["cloudflare", "__cfduid"],
    }

    for fw, patterns in framework_patterns.items():
        for pattern in patterns:
            if pattern in html_lower or pattern in server.lower() or pattern in powered_by.lower():
                frameworks.append(fw)
                break

    return {
        "server_present": bool(server),
        "server_value": server if server else None,
        "powered_by_present": bool(powered_by),
        "powered_by_value": powered_by if powered_by else None,
        "frameworks": list(set(frameworks)),
    }