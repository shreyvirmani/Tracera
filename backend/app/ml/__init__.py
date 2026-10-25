"""
Tracera backend ML integration (`ml_analysis_v1` contract).

Import surface for the scan API:
- analyze_scan_features(feature_dict) -> MLAnalysisResult (never raises)
- result_to_dict(result) -> JSON-safe dict

Docs: backend/app/ml/contract.py
"""

# `contract` is a documentation-only module; all objects live in `service`.
from app.ml.service import (
    ANALYSIS_VERSION,
    MLAnalysisResult,
    MLAnalysisStatus,
    analyze_scan_features,
    ml_features_from_scan_dict,
    result_to_dict,
)

__all__ = [
    "ANALYSIS_VERSION",
    "MLAnalysisResult",
    "MLAnalysisStatus",
    "analyze_scan_features",
    "ml_features_from_scan_dict",
    "result_to_dict",
]
