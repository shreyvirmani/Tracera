"""
Tracera ML integration contract (backend).

WHAT'S PRODUCED
--------------
`MLAnalysisResult` is a fully versioned, optional, additive part of the scan API.
It never replaces, overrides, or re-weights deterministic findings / risk scores.

Fields (always present):
    status:                       "analyzed" | "unavailable"
    analysis_version:             contract version of THIS structure ("ml_analysis_v1")
    feature_schema_version:       ML feature schema used ("v1")
    interpretation:               plain-language meaning and limits of the field

Additional fields when status == "analyzed":
    data_label:                   STRICT provenance of the training data.
                                  "REAL"  — trained on real crawler data. Still NOT a
                                            verdict: see interpretation.
                                  "SYNTHETIC" — development/testing only data; the
                                            score carries no real-world meaning.
    anomaly_score:                float; HIGHER = the website's header/cookie
                                  configuration is MORE statistically atypical
                                  relative to the model's training corpus.
    anomaly_flag:                 True when anomaly_score exceeds the model's
                                  validation threshold.
    model_version:                artifact/model identifier
    score_interpretation:         canonical explanation string (stable for UI)

Additional fields when status == "unavailable":
    unavailability_reason:        one of:
        "ml_disabled"                 — disabled via settings
        "ml_package_unavailable"      — `ml` package or numpy/sklearn not installed
        "artifact_not_found"          — no trained model artifact available
        "artifact_incompatible"       — artifact trained with different feature schema
        "artifact_corrupt"            — artifact unreadable / invalid metadata
        "invalid_features"            — scan features violate the ML schema
        "analysis_error"              — unexpected failure (scan unaffected)

GUARANTEES MADE TO THE SCAN PIPELINE
------------------------------------
- `analyze_scan_features` NEVER raises. The scan pipeline stays fully functional
  when ML analysis is unavailable for any reason (missing artifact, dependency,
  bad features, bugs).
- Deterministic findings and risk scores are computed and presented exactly as
  before; the ML result is displayed separately and cannot silently alter them.
- No synthesized/fake values: unknown/unavailable is reported as such.

MEANING AND LIMITS (for the frontend)
-------------------------------------
An Isolation Forest anomaly score measures statistical RARENESS within the
training corpus. It is NOT a probability of compromise, not a vulnerability
detection, and not a maliciousness verdict. The interpretation strings below are
canonical and must be shown verbatim along with any score.
"""
