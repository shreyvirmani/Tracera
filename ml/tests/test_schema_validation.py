"""
Tests for MLFeaturesV1 runtime validation (Phase C).

Covers valid vectors, malformed types, out-of-range values, non-finite values,
bool-where-int, strict from_dict behavior, and numpy type tolerance.
"""

import numpy as np
import pytest

from ml.features.schema_v1 import (
    BINARY_FEATURES,
    COUNT_FEATURES,
    HTTP_FEATURES,
    ML_FEATURE_SCHEMA_VERSION,
    MLFeaturesV1,
    RATIO_FEATURES,
    FeatureValidationError,
)


def valid_kwargs(**overrides) -> dict:
    base = dict(
        status_code=200,
        is_html=1,
        https_enabled=1,
        hsts_present=1,
        csp_present=0,
        x_content_type_options_present=1,
        x_frame_options_present=0,
        referrer_policy_present=1,
        permissions_policy_present=0,
        cookie_count=3,
        cookie_secure_ratio=0.66,
        cookie_httponly_ratio=0.33,
        cookie_samesite_strict_ratio=0.33,
        cookie_samesite_lax_ratio=0.33,
        cookie_samesite_none_ratio=0.0,
        server_header_present=1,
        x_powered_by_present=0,
    )
    base.update(overrides)
    return base


class TestValidVectors:
    def test_validate_passes(self):
        MLFeaturesV1(**valid_kwargs()).validate()

    def test_default_vector_validates(self):
        # All-zero default: status_code=0 is the documented "not captured" sentinel.
        MLFeaturesV1().validate()

    def test_numpy_types_accepted(self):
        # Parquet/pandas round-trips produce numpy scalars — must not be rejected.
        f = MLFeaturesV1(**valid_kwargs(
            status_code=np.int64(200),
            is_html=np.int64(1),
            cookie_count=np.int64(2),
            cookie_secure_ratio=np.float64(0.5),
        ))
        f.validate()

    def test_group_counts_sum_to_seventeen(self):
        assert len(HTTP_FEATURES) == 3
        assert len(BINARY_FEATURES) == 8
        assert len(COUNT_FEATURES) == 1
        assert len(RATIO_FEATURES) == 5
        assert len(HTTP_FEATURES) + len(BINARY_FEATURES) + len(COUNT_FEATURES) + len(RATIO_FEATURES) == 17


class TestMalformedInputs:
    @pytest.mark.parametrize("field,value,message", [
        ("status_code", 999, "status_code"),
        ("status_code", 3.5, "status_code"),
        ("status_code", "200", "status_code"),
        ("is_html", 2, "is_html"),
        ("is_html", True, "is_html"),
        ("https_enabled", 7, "https_enabled"),
        ("hsts_present", "1", "hsts_present"),
        ("cookie_count", -1, "cookie_count"),
        ("cookie_count", 2.5, "cookie_count"),
        ("cookie_secure_ratio", 1.5, "cookie_secure_ratio"),
        ("cookie_httponly_ratio", -0.1, "cookie_httponly_ratio"),
        ("cookie_samesite_strict_ratio", float("nan"), "cookie_samesite_strict_ratio"),
        ("cookie_samesite_lax_ratio", float("inf"), "cookie_samesite_lax_ratio"),
        ("cookie_samesite_none_ratio", "0.5", "cookie_samesite_none_ratio"),
    ])
    def test_invalid_values_rejected(self, field, value, message):
        with pytest.raises(FeatureValidationError) as exc:
            MLFeaturesV1(**valid_kwargs(**{field: value})).validate()
        assert any(message in issue for issue in exc.value.issues)

    def test_all_issues_collected_at_once(self):
        bad = valid_kwargs(status_code=900, is_html=5, cookie_count=-2,
                           cookie_secure_ratio=2.0, cookie_httponly_ratio=float("nan"))
        with pytest.raises(FeatureValidationError) as exc:
            MLFeaturesV1(**bad).validate()
        assert len(exc.value.issues) >= 5

    def test_bool_rejected_for_status_code(self):
        # bool is an int subclass; must be rejected explicitly.
        with pytest.raises(FeatureValidationError):
            MLFeaturesV1(**valid_kwargs(status_code=True)).validate()


class TestFromDict:
    def test_strict_roundtrip(self):
        fv = MLFeaturesV1(**valid_kwargs())
        revived = MLFeaturesV1.from_dict(fv.to_dict())
        assert revived.to_array().tolist() == fv.to_array().tolist()

    def test_strict_missing_key_raises(self):
        d = valid_kwargs()
        d.pop("csp_present")
        with pytest.raises(FeatureValidationError, match="missing"):
            MLFeaturesV1.from_dict(d, strict=True)

    def test_none_values_rejected(self):
        d = valid_kwargs()
        d["cookie_secure_ratio"] = None
        with pytest.raises(FeatureValidationError, match="None"):
            MLFeaturesV1.from_dict(d)

    def test_lenient_mode_fills_defaults(self):
        d = {"status_code": 200}
        fv = MLFeaturesV1.from_dict(d, strict=False)
        assert fv.cookie_count == 0
        fv.validate()

    def test_inference_rejects_nan_in_stored_dict(self):
        d = valid_kwargs()
        d["cookie_secure_ratio"] = float("nan")
        with pytest.raises(FeatureValidationError, match="finite"):
            MLFeaturesV1.from_dict(d)


class TestArrayContract:
    def test_to_array_fixed_order_stability(self):
        # Feature order is a published interface — two vectors with the same
        # per-feature values MUST map to identical arrays.
        order1 = MLFeaturesV1(**valid_kwargs()).to_array().tolist()
        order2 = MLFeaturesV1(**valid_kwargs()).to_array().tolist()
        assert order1 == order2
        names = MLFeaturesV1.feature_names()
        fv = MLFeaturesV1(**valid_kwargs())
        for i, name in enumerate(names):
            assert float(fv.to_array()[i]) == float(getattr(fv, name))

    def test_schema_version_constant(self):
        assert ML_FEATURE_SCHEMA_VERSION == "v1"
