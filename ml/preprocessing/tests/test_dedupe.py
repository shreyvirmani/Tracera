"""
Tests for ML preprocessing deduplication.
"""

import pytest
import pandas as pd
from ml.preprocessing.dedupe import (
    deduplicate_by_origin,
    DeduplicationPolicy,
    get_deduplication_stats,
)


class TestDeduplicationPolicy:
    """Test DeduplicationPolicy configuration."""

    def test_default_policy(self):
        policy = DeduplicationPolicy()
        assert policy.timestamp_col == "crawl_timestamp"
        assert policy.status_col == "status_code"
        assert policy.prefer_status == 200
        assert policy.feature_completeness_col is None

    def test_custom_policy(self):
        policy = DeduplicationPolicy(
            timestamp_col="crawled_at",
            status_col="http_status",
            prefer_status=301,
            feature_completeness_col="feature_score",
        )
        assert policy.timestamp_col == "crawled_at"
        assert policy.status_col == "http_status"
        assert policy.prefer_status == 301
        assert policy.feature_completeness_col == "feature_score"


class TestDeduplicateByOrigin:
    """Test deduplication by origin."""

    def create_test_df(self) -> "pd.DataFrame":
        """Create a test DataFrame with duplicate origins."""
        return pd.DataFrame({
            "origin": [
                "https://example.com:443",
                "https://example.com:443",
                "https://example.com:443",
                "http://other.com:80",
                "http://other.com:80",
                "https://unique.com:443",
            ],
            "crawl_timestamp": [
                "2026-01-15T10:00:00Z",
                "2026-01-15T11:00:00Z",  # latest
                "2026-01-15T09:00:00Z",
                "2026-01-15T10:00:00Z",
                "2026-01-15T10:00:00Z",  # same timestamp
                "2026-01-15T10:00:00Z",
            ],
            "status_code": [
                200,
                200,  # latest, preferred
                404,
                200,
                301,  # same timestamp, but 200 preferred
                200,
            ],
            "feature_a": [1, 2, 3, 4, 5, 6],
        })

    def test_basic_deduplication(self):
        """Test basic deduplication keeps latest timestamp."""
        df = self.create_test_df()
        result = deduplicate_by_origin(df)

        assert len(result) == 3  # 3 unique origins
        origins = result["origin"].tolist()
        assert "https://example.com:443" in origins
        assert "http://other.com:80" in origins
        assert "https://unique.com:443" in origins

        # For example.com, should keep the 11:00 record (latest)
        example_row = result[result["origin"] == "https://example.com:443"]
        assert example_row["crawl_timestamp"].iloc[0] == "2026-01-15T11:00:00Z"
        assert example_row["feature_a"].iloc[0] == 2

    def test_prefers_200_status(self):
        """Test that 200 status is preferred when timestamps are equal."""
        df = self.create_test_df()
        result = deduplicate_by_origin(df)

        # For other.com, both have same timestamp (10:00), but first has 200, second has 301
        # Should keep the 200 status one
        other_row = result[result["origin"] == "http://other.com:80"]
        assert other_row["status_code"].iloc[0] == 200
        assert other_row["feature_a"].iloc[0] == 4

    def test_unique_origin_kept(self):
        """Test that unique origins are kept unchanged."""
        df = self.create_test_df()
        result = deduplicate_by_origin(df)

        unique_row = result[result["origin"] == "https://unique.com:443"]
        assert unique_row["feature_a"].iloc[0] == 6

    def test_empty_dataframe(self):
        """Test deduplication on empty DataFrame."""
        df = pd.DataFrame({
            "origin": [],
            "crawl_timestamp": [],
            "status_code": [],
        })
        result = deduplicate_by_origin(df)
        assert len(result) == 0

    def test_no_duplicates(self):
        """Test DataFrame with no duplicates returns unchanged."""
        df = pd.DataFrame({
            "origin": ["https://a.com:443", "https://b.com:443"],
            "crawl_timestamp": ["2026-01-15T10:00:00Z", "2026-01-15T11:00:00Z"],
            "status_code": [200, 200],
        })
        result = deduplicate_by_origin(df)
        assert len(result) == 2
        assert result["origin"].tolist() == ["https://a.com:443", "https://b.com:443"]

    def test_missing_origin_column_raises(self):
        """Test that missing origin column raises ValueError."""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        with pytest.raises(ValueError, match="origin"):
            deduplicate_by_origin(df, origin_col="origin")

    def test_missing_timestamp_column_raises(self):
        """Test that missing timestamp column raises ValueError."""
        df = pd.DataFrame({
            "origin": ["https://a.com:443", "https://a.com:443"],
            "status_code": [200, 200],
        })
        with pytest.raises(ValueError, match="crawl_timestamp"):
            deduplicate_by_origin(df)

    def test_missing_status_column_raises(self):
        """Test that missing status column raises ValueError."""
        df = pd.DataFrame({
            "origin": ["https://a.com:443", "https://a.com:443"],
            "crawl_timestamp": ["2026-01-15T10:00:00Z", "2026-01-15T11:00:00Z"],
        })
        with pytest.raises(ValueError, match="status_code"):
            deduplicate_by_origin(df)

    def test_custom_policy(self):
        """Test deduplication with custom policy."""
        df = pd.DataFrame({
            "origin": ["https://a.com:443", "https://a.com:443"],
            "crawled_at": ["2026-01-15T10:00:00Z", "2026-01-15T11:00:00Z"],
            "http_status": [301, 200],
        })
        policy = DeduplicationPolicy(
            timestamp_col="crawled_at",
            status_col="http_status",
            prefer_status=301,
        )
        result = deduplicate_by_origin(df, policy=policy)

        # Should prefer 301 status even though second has later timestamp
        # Actually, timestamp is first sort key, so later timestamp wins
        # But if timestamps were equal, 301 would be preferred
        assert len(result) == 1
        assert result["http_status"].iloc[0] == 200  # Later timestamp wins


class TestDeduplicationStats:
    """Test deduplication statistics."""

    def test_basic_stats(self):
        df = pd.DataFrame({
            "origin": [
                "https://a.com:443",
                "https://a.com:443",
                "https://b.com:443",
                "https://c.com:443",
                "https://c.com:443",
                "https://c.com:443",
            ],
        })
        stats = get_deduplication_stats(df)

        assert stats["total_rows"] == 6
        assert stats["unique_origins"] == 3
        assert stats["duplicate_rows"] == 3
        assert stats["duplication_rate"] == 0.5
        assert stats["origins_with_duplicates"] == 2  # a.com and c.com
        assert stats["max_duplicates_per_origin"] == 3  # c.com has 3

    def test_no_duplicates_stats(self):
        df = pd.DataFrame({
            "origin": ["https://a.com:443", "https://b.com:443"],
        })
        stats = get_deduplication_stats(df)

        assert stats["total_rows"] == 2
        assert stats["unique_origins"] == 2
        assert stats["duplicate_rows"] == 0
        assert stats["duplication_rate"] == 0.0
        assert stats["origins_with_duplicates"] == 0
        assert stats["max_duplicates_per_origin"] == 1

    def test_empty_dataframe_stats(self):
        df = pd.DataFrame({"origin": []})
        stats = get_deduplication_stats(df)

        assert stats["total_rows"] == 0
        assert stats["unique_origins"] == 0
        assert stats["duplicate_rows"] == 0
        assert stats["duplication_rate"] == 0.0
        assert stats["origins_with_duplicates"] == 0
        assert stats["max_duplicates_per_origin"] == 0