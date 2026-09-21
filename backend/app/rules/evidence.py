from app.rules.models import FindingEvidence


class HTTPNotHTTPSEvidence(FindingEvidence):
    final_url: str
    scheme: str


class MissingHSTSEvidence(FindingEvidence):
    header: str = "Strict-Transport-Security"
    observed: bool = False
    final_url: str


class MissingCSPEvidence(FindingEvidence):
    header: str = "Content-Security-Policy"
    observed: bool = False


class MissingXContentTypeOptionsEvidence(FindingEvidence):
    header: str = "X-Content-Type-Options"
    observed: bool = False


class MissingXFrameOptionsEvidence(FindingEvidence):
    header: str = "X-Frame-Options"
    observed: bool = False


class MissingReferrerPolicyEvidence(FindingEvidence):
    header: str = "Referrer-Policy"
    observed: bool = False


class MissingPermissionsPolicyEvidence(FindingEvidence):
    header: str = "Permissions-Policy"
    observed: bool = False


class InsecureCookieEvidence(FindingEvidence):
    cookie_name: str
    secure: bool
    httponly: bool
    samesite: str | None


class MissingHttpOnlyEvidence(FindingEvidence):
    cookie_name: str
    httponly: bool
    secure: bool


class WeakSameSiteEvidence(FindingEvidence):
    cookie_name: str
    samesite: str | None


class ServerVersionDisclosureEvidence(FindingEvidence):
    header: str = "Server"
    value: str


class XPoweredByDisclosureEvidence(FindingEvidence):
    header: str = "X-Powered-By"
    value: str


class WildcardCORSWithCredentialsEvidence(FindingEvidence):
    header: str = "Access-Control-Allow-Origin"
    value: str
    credentials_header: str = "Access-Control-Allow-Credentials"
    credentials_value: str


class MixedContentEvidence(FindingEvidence):
    count: int
    resource_types: list[str]
    final_url: str


class ExcessiveResponseSizeEvidence(FindingEvidence):
    size_bytes: int
    threshold_bytes: int = 10_000_000
