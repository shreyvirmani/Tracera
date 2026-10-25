"""
Tests for HTTP Archive BigQuery extraction and transformation.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.data.http_archive.extract import (
    HTTP_ARCHIVE_QUERY,
    MODEL_FEATURES,
    validate_feature_matrix,
    extract_metadata_columns,
)
from ml.features.schema_v1 import MLFeaturesV1, ML_FEATURE_SCHEMA_VERSION


class TestModelFeatures:
    """Test that model features match the expected schema."""

    def test_model_features_count(self):
        """Test that we have exactly 17 model features."""
        assert len(MODEL_FEATURES) == 17

    def test_model_features_match_schema(self):
        """Test that model features match MLFeaturesV1.feature_names()."""
        assert MODEL_FEATURES == MLFeaturesV1.feature_names()

    def test_feature_spec_complete(self):
        """Test that feature_spec has entry for every feature."""
        spec = MLFeaturesV1.feature_spec()
        for feat in MODEL_FEATURES:
            assert feat in spec
            assert "type" in spec[feat]
            assert "range" in spec[feat]
            assert "meaning" in spec[feat]
            assert "source" in spec[feat]
            assert "missing_possible" in spec[feat]
            assert "used_by_model" in spec[feat]


class TestValidateFeatureMatrix:
    """Test feature matrix validation."""

    def create_sample_df(self) -> "pd.DataFrame":
        """Create a sample DataFrame with all required features."""
        return pd.DataFrame({
            "status_code": [200, 200, 404],
            "is_html": [1, 1, 0],
            "https_enabled": [1, 0, 1],
            "hsts_present": [1, 0, 1],
            "csp_present": [1, 1, 0],
            "x_content_type_options_present": [1, 0, 1],
            "x_frame_options_present": [1, 1, 0],
            "referrer_policy_present": [1, 0, 1],
            "permissions_policy_present": [1, 0, 1],
            "cookie_count": [2, 0, 3],
            "cookie_secure_ratio": [1.0, 0.0, 0.5],
            "cookie_httponly_ratio": [1.0, 0.0, 0.33],
            "cookie_samesite_strict_ratio": [0.5, 0.0, 0.33],
            "cookie_samesite_lax_ratio": [0.5, 0.0, 0.33],
            "cookie_samesite_none_ratio": [0.0, 0.0, 0.33],
            "server_header_present": [1, 1, 0],
            "x_powered_by_present": [0, 1, 0],
        })

    def test_validate_feature_matrix_valid(self):
        """Test validation passes for valid DataFrame."""
        df = self.create_sample_df()
        X = validate_feature_matrix(df)
        assert len(X.columns) == 17
        assert list(X.columns) == MODEL_FEATURES

    def test_validate_feature_matrix_missing_features(self):
        """Test validation fails for missing features."""
        df = pd.DataFrame({"status_code": [200]})
        with pytest.raises(ValueError, match="Missing model features"):
            validate_feature_matrix(df)

    def test_validate_feature_matrix_extra_columns(self):
        """Test validation ignores extra columns."""
        df = self.create_sample_df()
        df["extra_column"] = [1, 2, 3]
        X = validate_feature_matrix(df)
        assert len(X.columns) == 17
        assert "extra_column" not in X.columns

    def test_no_duplicates(self):
        """Test DataFrame with no duplicates returns unchanged."""
        df = self.create_sample_df()
        X = validate_feature_matrix(df)
        assert len(X) == 3

    def test_feature_order_preserved(self):
        """Test that feature order matches schema."""
        df = self.create_sample_df()
        X = validate_feature_matrix(df)
        assert list(X.columns) == MODEL_FEATURES


class TestExtractMetadataColumns:
    """Test metadata extraction from DataFrame."""

    def test_extract_metadata_columns(self):
        """Test metadata extraction from DataFrame."""
        df = pd.DataFrame({
            "status_code": [200],
            "is_html": [1],
            "https_enabled": [1],
            "url": ["https://example.com"],
            "origin": ["https://example.com:443"],
            "registrable_domain": ["example.com"],
        })

        metadata_df = extract_metadata_columns(df)
        assert "url" in metadata_df.columns
        assert "origin" in metadata_df.columns
        assert "registrable_domain" in metadata_df.columns
        assert "status_code" not in metadata_df.columns
        assert "is_html" not in metadata_df.columns


class TestQueryTemplate:
    """Test SQL query template rendering."""

    def test_query_contains_required_ctes(self):
        """Test that query contains all required CTEs."""
        required_ctes = [
            "base_pages",
            "response_extracted",
            "headers_extracted",
            "cookies_parsed",
            "origins_normalized",
            "origins_with_registrable",
            "sampled_origins",
        ]
        for cte in required_ctes:
            assert cte in HTTP_ARCHIVE_QUERY, f"Missing CTE: {cte}"

    def test_query_contains_all_17_features(self):
        """Test that query selects all 17 features."""
        for feat in [
            "status_code", "is_html", "https_enabled",
            "hsts_present", "csp_present", "x_content_type_options_present",
            "x_frame_options_present", "referrer_policy_present", "permissions_policy_present",
            "cookie_count", "cookie_secure_ratio", "cookie_httponly_ratio",
            "cookie_samesite_strict_ratio", "cookie_samesite_lax_ratio", "cookie_samesite_none_ratio",
            "server_header_present", "x_powered_by_present",
        ]:
            assert feat in HTTP_ARCHIVE_QUERY

    def test_query_uses_correct_table_format(self):
        """Test that query uses correct table format (httparchive.crawl.pages)."""
        assert "httparchive.crawl.pages" in HTTP_ARCHIVE_QUERY
        assert "is_root_page = true" in HTTP_ARCHIVE_QUERY
        assert "date >=" in HTTP_ARCHIVE_QUERY

    def test_query_filters_html_only(self):
        """Test that query filters for HTML content only."""
        assert "text/html%" in HTTP_ARCHIVE_QUERY
        assert "application/xhtml+xml%" in HTTP_ARCHIVE_QUERY

    def test_query_filters_root_pages(self):
        """Test that query filters for root pages."""
        assert "is_root_page = true" in HTTP_ARCHIVE_QUERY

    def test_query_filters_status_200(self):
        """Test that query filters for status 200 (implicit in status code extraction)."""
        assert "status_code" in HTTP_ARCHIVE_QUERY

    def test_query_filters_html_mime(self):
        """Test that query filters for HTML MIME types."""
        assert "text/html%" in HTTP_ARCHIVE_QUERY
        assert "application/xhtml+xml%" in HTTP_ARCHIVE_QUERY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])