from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FeatureSchemaVersion(str, Enum):
    V1 = "features-v1"


class HTTPFeatures(BaseModel):
    status_code: int
    response_size_bytes: int
    response_time_ms: float
    content_type: str | None = None
    redirect_count: int
    https_enabled: bool
    server_header: str | None = None
    x_powered_by: str | None = None


class SecurityHeaderFeatures(BaseModel):
    hsts: str | None = None
    csp: str | None = None
    x_content_type_options: str | None = None
    x_frame_options: str | None = None
    referrer_policy: str | None = None
    permissions_policy: str | None = None
    cross_origin_embedder_policy: str | None = None
    cross_origin_opener_policy: str | None = None
    cross_origin_resource_policy: str | None = None


class CookieFeatures(BaseModel):
    total_cookies: int
    secure_cookies: int
    httponly_cookies: int
    samesite_cookies: int
    session_cookies: int
    persistent_cookies: int
    third_party_indicators: int


class TLSFeatures(BaseModel):
    cert_expiry_days: int | None = None
    cert_expired: bool = False
    tls_version: str | None = None
    cipher_suite: str | None = None
    cert_subject: str | None = None
    cert_issuer: str | None = None
    san_count: int | None = None


class HTMLFeatures(BaseModel):
    html_size_bytes: int
    script_count: int
    stylesheet_count: int
    image_count: int
    iframe_count: int
    form_count: int
    external_domain_count: int
    mixed_content_count: int
    has_password_field: bool = False
    has_file_upload: bool = False


class TechnologyFeatures(BaseModel):
    server_header_present: bool = False
    x_powered_by_present: bool = False
    framework_indicators: list[str] = Field(default_factory=list)


class FeatureVector(BaseModel):
    feature_schema_version: FeatureSchemaVersion = FeatureSchemaVersion.V1
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    http: HTTPFeatures
    security_headers: SecurityHeaderFeatures
    cookies: CookieFeatures
    tls: TLSFeatures
    html: HTMLFeatures
    technology: TechnologyFeatures
