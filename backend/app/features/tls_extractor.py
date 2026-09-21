from datetime import UTC, datetime

from app.collector.collector import CollectorResponse
from app.features.schema import TLSFeatures


def extract_tls_features(response: CollectorResponse) -> TLSFeatures:
    if not response.final_url.startswith("https://"):
        return TLSFeatures()

    tls_info = response.tls_info
    if not tls_info:
        return TLSFeatures(
            tls_version="unknown",
        )

    cert = tls_info.get("certificate")
    expiry_days = None
    cert_expired = False

    if cert and "not_after" in cert:
        try:
            not_after = datetime.fromisoformat(cert["not_after"].replace("Z", "+00:00"))
            now = datetime.now(UTC)
            delta = not_after - now
            expiry_days = delta.days
            cert_expired = delta.total_seconds() < 0
        except Exception:
            pass

    return TLSFeatures(
        cert_expiry_days=expiry_days,
        cert_expired=cert_expired,
        tls_version=tls_info.get("tls_version"),
        cipher_suite=tls_info.get("cipher_suite"),
        cert_subject=cert.get("subject") if cert else None,
        cert_issuer=cert.get("issuer") if cert else None,
        san_count=len(cert.get("subject_alt_names", [])) if cert else None,
    )
