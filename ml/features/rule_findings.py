"""
Deterministic rule mirroring over MLFeaturesV1.

Re-implements the subset of backend rule engine checks (backend/app/rules/engine.py)
whose inputs exist entirely within the ML feature schema + metadata, so that the
evaluation framework can compare model output with deterministic findings on the
same dataset rows.

The mirror is intentionally limited to rules that share identical semantics with
the backend. HTML/TLS rules (mixed content, cert expiry, response size, CORS)
need fields MLFeaturesV1 does not carry and are out of scope here. Any drift
between this mirror and the backend engine must be fixed on both sides together
(see ml/tests/test_rule_findings.py::test_mirror_matches_backend_on_synonymous_inputs).
"""

from ml.features.schema_v1 import MLFeaturesV1

# Metadata-conditional rules need these extra values.
RULE_IDS_WITH_METADATA = ("CFG-SERVER-001", "CFG-XPB-001")


def compute_rule_findings(
    features: "MLFeaturesV1",
    server_header_value: str | None = None,
    x_powered_by_value: str | None = None,
) -> dict[str, bool]:
    """
    Compute which mirrored deterministic rules WOULD fire for one observation.

    Returns a dict rule_id -> bool (True = rule fires). Rule IDs and severity
    semantics match backend/app/rules/engine.py:

    - SEC-HTTPS-001  NoHTTPSRule              (https_enabled == 0)
    - SEC-HSTS-001   MissingHSTSRule          (https + missing HSTS)
    - SEC-CSP-001    MissingCSPRule
    - SEC-XCTO-001   MissingXContentTypeOptionsRule (present but != nosniff counts as present in backend)
    - SEC-XFO-001    MissingXFrameOptionsRule
    - SEC-RP-001     MissingReferrerPolicyRule
    - SEC-PP-001     MissingPermissionsPolicyRule
    - SEC-COOKIE-001 InsecureCookieRule       (https + cookies + secure_ratio < 1)
    - SEC-COOKIE-002 MissingHttpOnlyRule      (cookies + httponly_ratio < 1)
    - SEC-COOKIE-003 WeakSameSiteRule         (any SameSite=None while https, or undefined SameSite)
    - CFG-SERVER-001 ServerVersionDisclosureRule (Server header has digit and '/')
    - CFG-XPB-001    XPoweredByDisclosureRule (X-Powered-By non-empty)
    - SEC-HEADERS-001 MissingSecurityHeadersRule (>= 3 of the 4 headers missing)
    """
    f = features
    https = bool(f.https_enabled)
    has_cookies = f.cookie_count > 0

    server_hist = server_header_value if isinstance(server_header_value, str) else None
    xpb_hist = x_powered_by_value if isinstance(x_powered_by_value, str) else None

    fired: dict[str, bool] = {
        "SEC-HTTPS-001": not https,
        "SEC-HSTS-001": https and not f.hsts_present,
        "SEC-CSP-001": not f.csp_present,
        "SEC-XCTO-001": not f.x_content_type_options_present,
        "SEC-XFO-001": not f.x_frame_options_present,
        "SEC-RP-001": not f.referrer_policy_present,
        "SEC-PP-001": not f.permissions_policy_present,
        "SEC-COOKIE-001": https and has_cookies and f.cookie_secure_ratio < 1.0,
        "SEC-COOKIE-002": has_cookies and f.cookie_httponly_ratio < 1.0,
        "SEC-COOKIE-003": (
            (has_cookies and f.cookie_samesite_none_ratio > 0 and https)
            or (has_cookies and (f.cookie_samesite_strict_ratio
                                 + f.cookie_samesite_lax_ratio
                                 + f.cookie_samesite_none_ratio) < 1.0)
        ),
        "CFG-SERVER-001": bool(
            server_hist
            and any(c.isdigit() for c in server_hist)
            and "/" in server_hist
        ),
        "CFG-XPB-001": bool(xpb_hist),
        "SEC-HEADERS-001": (
            sum([
                https and not f.hsts_present,
                not f.csp_present,
                not f.x_frame_options_present,
                not f.x_content_type_options_present,
            ]) >= 3
        ),
    }
    return fired


def compute_rule_findings_matrix(
    feature_frame: "pd.DataFrame",
    server_col: str = "server_header_value",
    xpb_col: str = "x_powered_by_value",
) -> "pd.DataFrame" :
    """
    Compute the mirrored-rule boolean matrix for every row of a feature frame.
    Missing metadata columns are treated as absent values, never as errors
    (presence falls back to features.server_header_present/x_powered_by_present).
    """
    import pandas as pd  # local import keeps this module importable without pandas for schema users

    all_rule_ids = list(compute_rule_findings(MLFeaturesV1()).keys())
    n = len(feature_frame)

    server_vals = feature_frame[server_col] if server_col in feature_frame else pd.Series([None] * n, index=feature_frame.index)
    xpb_vals = feature_frame[xpb_col] if xpb_col in feature_frame else pd.Series([None] * n, index=feature_frame.index)

    rows = []
    for row in feature_frame.itertuples(index=False):
        f = MLFeaturesV1(**{k: getattr(row, k) for k in MLFeaturesV1.feature_names()})
        fired = compute_rule_findings(
            f,
            server_header_value=server_vals.iloc[len(rows)] if server_vals.iloc[len(rows)] is not None else None,
            x_powered_by_value=xpb_vals.iloc[len(rows)] if xpb_vals.iloc[len(rows)] is not None else None,
        )
        rows.append(fired)
    out = pd.DataFrame(rows, columns=all_rule_ids).reindex(feature_frame.index)
    out["n_rule_findings"] = out.sum(axis=1).astype("int64")
    return out
