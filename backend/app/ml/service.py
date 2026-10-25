"""
ML analysis service (backend).

Converts scan features -> MLFeaturesV1 -> validated anomaly output, with total
graceful degradation. See backend/app/ml/contract.py for the documented contract
(versioned `ml_analysis_v1`).
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

ANALYSIS_VERSION = "ml_analysis_v1"

SCORE_INTERPRETATION_ANALYZED = (
    "Statistical anomaly score: higher means this website's header/cookie "
    "configuration is more atypical relative to the model's training corpus "
    "(crawler-collected HTTP metadata). This is NOT a probability of compromise, "
    "a vulnerability detection, or a maliciousness verdict."
)
SCORE_INTERPRETATION_UNAVAILABLE = (
    "ML analysis unavailable; deterministic findings and risk score are "
    "unaffected and remain the primary evidence."
)


class MLAnalysisStatus(str, Enum):
    ANALYZED = "analyzed"
    UNAVAILABLE = "unavailable"


class MLAnalysisResult(BaseModel):
    status: MLAnalysisStatus
    analysis_version: str = ANALYSIS_VERSION
    feature_schema_version: Optional[str] = None
    data_label: Optional[str] = None           # REAL | SYNTHETIC — provenance of training data
    model_version: Optional[str] = None
    anomaly_score: Optional[float] = None       # higher = more statistically atypical
    anomaly_flag: Optional[bool] = None
    score_interpretation: Optional[str] = None
    interpretation: str = SCORE_INTERPRETATION_UNAVAILABLE
    unavailability_reason: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Feature mapping: production scan feature dict -> MLFeaturesV1
# ---------------------------------------------------------------------------

def ml_features_from_scan_dict(scan_feature_dict: Dict[str, Any]):
    """Build (and validate) the 17-feature ML vector from stored scan features."""
    from ml.features.schema_v1 import MLFeaturesV1

    kwargs = {
        "status_code": scan_feature_dict.get("status_code") or 0,
        "https_enabled": 1 if scan_feature_dict.get("https_enabled") else 0,
        "hsts_present": 1 if scan_feature_dict.get("hsts_present") else 0,
        "csp_present": 1 if scan_feature_dict.get("csp_present") else 0,
        "x_content_type_options_present":
            1 if scan_feature_dict.get("x_content_type_options_present") else 0,
        "x_frame_options_present": 1 if scan_feature_dict.get("x_frame_options_present") else 0,
        "referrer_policy_present": 1 if scan_feature_dict.get("referrer_policy_present") else 0,
        "permissions_policy_present":
            1 if scan_feature_dict.get("permissions_policy_present") else 0,
        "cookie_count": scan_feature_dict.get("cookie_count") or 0,
        "cookie_secure_ratio": scan_feature_dict.get("cookie_secure_ratio") or 0.0,
        "cookie_httponly_ratio": scan_feature_dict.get("cookie_httponly_ratio") or 0.0,
        "cookie_samesite_strict_ratio":
            scan_feature_dict.get("cookie_samesite_strict_ratio") or 0.0,
        "cookie_samesite_lax_ratio": scan_feature_dict.get("cookie_samesite_lax_ratio") or 0.0,
        "cookie_samesite_none_ratio": scan_feature_dict.get("cookie_samesite_none_ratio") or 0.0,
        "server_header_present": 1 if scan_feature_dict.get("server_header_present") else 0,
        "x_powered_by_present": 1 if scan_feature_dict.get("x_powered_by_present") else 0,
    }
    # is_html is derived from content_type, mirroring the WAT/live adapters.
    content_type = str(scan_feature_dict.get("content_type") or "")
    kwargs["is_html"] = 1 if content_type.lower().startswith("text/html") else 0
    return MLFeaturesV1(**kwargs)


# ---------------------------------------------------------------------------
# Unavailable-result helpers
# ---------------------------------------------------------------------------

def _unavailable(reason: str, detail: Optional[dict] = None, **extra) -> MLAnalysisResult:
    return MLAnalysisResult(
        status=MLAnalysisStatus.UNAVAILABLE,
        unavailability_reason=reason,
        detail=detail,
        interpretation=SCORE_INTERPRETATION_UNAVAILABLE if reason != "ml_disabled" else (
            "ML analysis disabled by configuration; deterministic findings and risk "
            "score are unaffected."
        ),
        **extra,
    )


def _artifact_dir() -> Path:
    from app.core.config import settings

    if getattr(settings, "ml_artifact_dir", None):
        return Path(settings.ml_artifact_dir)
    # Default: repo-root ml/artifacts relative to backend/app/ml/service.py
    return Path(__file__).resolve().parents[3] / "ml" / "artifacts" / "isoforest_v1"


# ---------------------------------------------------------------------------
# Main entry point — never raises
# ---------------------------------------------------------------------------

def analyze_scan_features(scan_feature_dict: Dict[str, Any], *, enabled: Optional[bool] = None) -> MLAnalysisResult:
    """
    Analyze stored scan features. Total graceful degradation:
    any problem yields status="unavailable" with an actionable reason.
    """
    try:
        from app.core.config import settings

        ml_enabled = settings.ml_analysis_enabled if enabled is None else enabled
        if not ml_enabled:
            return _unavailable("ml_disabled", feature_schema_version=None)
    except Exception as e:  # config failure — still never crash the scan
        return _unavailable("analysis_error", detail={"stage": "config", "error": str(e)})

    try:
        features = ml_features_from_scan_dict(scan_feature_dict)
        features.validate()
    except ModuleNotFoundError as e:
        # `ml` (or numpy/sklearn) not importable in this deployment — never
        # mislabel a packaging problem as bad scan features.
        return _unavailable(
            "ml_package_unavailable",
            detail={"stage": "feature_mapping", "missing_module": e.name},
        )
    except Exception as e:
        issues = getattr(e, "issues", None)
        return _unavailable(
            "invalid_features",
            detail={"stage": "feature_mapping_or_validation", "issues": issues}
            if issues
            else {"stage": "feature_mapping_or_validation", "error": str(e)},
        )

    # Load model artifact
    try:
        from ml.training.model_io import ModelArtifactError, load_model

        model, threshold_abs, metadata = load_model(_artifact_dir())
    except ModuleNotFoundError as e:
        return _unavailable(
            "ml_package_unavailable",
            detail={"stage": "model_loading", "missing_module": e.name},
            feature_schema_version=features.feature_schema_version,
        )
    except ModelArtifactError as e:
        reason_map = {
            "not_found": "artifact_not_found",
            "missing_file": "artifact_not_found",
            "corrupt": "artifact_corrupt",
            "schema_mismatch": "artifact_incompatible",
            "dimension_mismatch": "artifact_incompatible",
        }
        return _unavailable(
            reason_map.get(e.reason, "analysis_error"),
            detail={"stage": "model_loading", "artifact_reason": e.reason, "detail": e.detail},
            feature_schema_version=features.feature_schema_version,
        )
    except Exception as e:  # unknown artifact failure — degrade, never raise
        return _unavailable(
            "analysis_error",
            detail={"stage": "model_loading", "error": str(e)},
            feature_schema_version=features.feature_schema_version,
        )

    # Inference
    try:
        import numpy as np
        import warnings

        X = features.to_array().reshape(1, -1)
        # The artifact was fitted on a named DataFrame; inference uses the
        # validated MLFeaturesV1 feature order (identical to
        # MLFeaturesV1.feature_names()), so sklearn's missing-name warning is
        # a false positive and is suppressed to keep API logs clean.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*X does not have valid feature names.*",
                module="sklearn",
            )
            decision = float(model.decision_function(X)[0])
        anomaly_score = float(-decision)  # higher = more atypical (see contract)
        # Saved threshold lives on the anomaly-score scale (P5 of train
        # decision_function negated at save time, see ml/training/model_io.py).
        anomaly_flag = bool(anomaly_score >= threshold_abs)
        return MLAnalysisResult(
            status=MLAnalysisStatus.ANALYZED,
            feature_schema_version=metadata.feature_schema_version,
            data_label=metadata.data_label,
            model_version=metadata.model_version,
            anomaly_score=round(anomaly_score, 6),
            anomaly_flag=anomaly_flag,
            score_interpretation=SCORE_INTERPRETATION_ANALYZED,
            interpretation=(
                f"Trained on {metadata.data_label} data ({metadata.model_version}). "
                + SCORE_INTERPRETATION_ANALYZED
            ),
            detail={
                "threshold": round(float(threshold_abs), 6),
                "train_rows": metadata.train_rows,
                "scores_are_not_probabilities": True,
            },
        )
    except Exception as e:
        return _unavailable(
            "analysis_error",
            detail={"stage": "inference", "error": str(e)},
            feature_schema_version=features.feature_schema_version,
        )


def result_to_dict(result: MLAnalysisResult) -> Dict[str, Any]:
    """Safe JSON-serializable form for API responses/reports."""
    return json.loads(result.model_dump_json())
