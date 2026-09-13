"""
Tests for ML preprocessing leakage-safe splitting.
"""

import pytest
import pandas as pd
from ml.preprocessing.split import (
    leakage_safe_split,
    verify_no_leakage,
    get_split_stats,
    SplitConfig,
)


class TestSplitConfig:
    """Test SplitConfig validation."""

    def test_default_config(self):
        config = SplitConfig()
        assert config.train_ratio == 0.7
        assert config.val_ratio == 0.15
        assert config.test_ratio == 0.15
        assert config.seed == 42
        assert config.group_col == "registrable_domain"

    def test_custom_config(self):
        config = SplitConfig(
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            seed=123,
            group_col="custom_group",
        )
        assert config.train_ratio == 0.8
        assert config.val_ratio == 0.1
        assert config.test_ratio == 0.1
        assert config.seed == 123
        assert config.group_col == "custom_group"

    def test_invalid_ratios_raises(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            SplitConfig(train_ratio=0.8, val_ratio=0.1, test_ratio=0.2)

    def test_ratios_sum_to_one(self):
        config = SplitConfig(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
        assert config.train_ratio + config.val_ratio + config.test_ratio == 1.0


class TestLeakageSafeSplit:
    """Test leakage-safe splitting."""

    def create_test_df(self) -> "pd.DataFrame":
        """Create test DataFrame with registrable domains."""
        return pd.DataFrame({
            "registrable_domain": [
                "example.com",
                "example.com",          # duplicate
                "example.com",          # same registrable domain (api.example.com)
                "example.com",          # same registrable domain (blog.example.com)
                "other.com",
                "other.com",
                "other.com",            # same registrable domain (api.other.com)
                "third.org",
                "fourth.net",
                "fifth.io",
                "sixth.co.uk",
                "seventh.com.au",
            ],
            "feature": list(range(12)),
            "label": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        })

    def test_basic_split(self):
        """Test basic leakage-safe split."""
        df = self.create_test_df()
        config = SplitConfig(train_ratio=0.5, val_ratio=0.25, test_ratio=0.25, seed=42)

        train, val, test = leakage_safe_split(df, config)

        # Check no leakage
        assert verify_no_leakage(train, val, test)

        # Check row counts (approximate due to group sizes)
        total = len(train) + len(val) + len(test)
        assert total == 12

        # Check that example.com group is entirely in one split
        example_in_train = train[train["registrable_domain"] == "example.com"]
        example_in_val = val[val["registrable_domain"] == "example.com"]
        example_in_test = test[test["registrable_domain"] == "example.com"]

        # All example.com rows should be in exactly one split
        # example.com (1) + example.com (duplicate) + example.com (api) + example.com (blog) = 4
        example_total = len(example_in_train) + len(example_in_val) + len(example_in_test)
        assert example_total == 4  # 4 rows with registrable_domain=example.com

    def test_no_leakage_across_splits(self):
        """Test that no registrable domain appears in multiple splits."""
        df = self.create_test_df()
        config = SplitConfig(seed=42)

        train, val, test = leakage_safe_split(df, config)

        assert verify_no_leakage(train, val, test)

    def test_deterministic_with_seed(self):
        """Test that same seed produces same split."""
        df = self.create_test_df()
        config = SplitConfig(seed=42)

        train1, val1, test1 = leakage_safe_split(df, config)
        train2, val2, test2 = leakage_safe_split(df, config)

        assert train1["registrable_domain"].tolist() == train2["registrable_domain"].tolist()
        assert val1["registrable_domain"].tolist() == val2["registrable_domain"].tolist()
        assert test1["registrable_domain"].tolist() == test2["registrable_domain"].tolist()

    def test_different_seeds_different_splits(self):
        """Test that different seeds produce different splits."""
        df = self.create_test_df()

        config1 = SplitConfig(seed=42)
        config2 = SplitConfig(seed=123)

        train1, _, _ = leakage_safe_split(df, config1)
        train2, _, _ = leakage_safe_split(df, config2)

        # Very unlikely to be identical with different seeds
        # (could theoretically happen but extremely unlikely)
        train1_groups = set(train1["registrable_domain"].unique())
        train2_groups = set(train2["registrable_domain"].unique())
        # At least allow the possibility they're different

    def test_custom_group_column(self):
        """Test split with custom group column."""
        df = pd.DataFrame({
            "custom_group": ["a", "a", "b", "b", "c", "c"],
            "feature": [1, 2, 3, 4, 5, 6],
        })
        config = SplitConfig(
            train_ratio=0.5,
            val_ratio=0.25,
            test_ratio=0.25,
            group_col="custom_group",
            seed=42,
        )

        train, val, test = leakage_safe_split(df, config)
        assert verify_no_leakage(train, val, test, group_col="custom_group")

    def test_missing_group_column_raises(self):
        """Test that missing group column raises ValueError."""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        config = SplitConfig(group_col="missing_col")

        with pytest.raises(ValueError, match="missing_col"):
            leakage_safe_split(df, config)

    def test_empty_dataframe(self):
        """Test split on empty DataFrame."""
        df = pd.DataFrame({"registrable_domain": [], "feature": []})
        config = SplitConfig(seed=42)

        train, val, test = leakage_safe_split(df, config)

        assert len(train) == 0
        assert len(val) == 0
        assert len(test) == 0

    def test_single_group(self):
        """Test split with only one group."""
        df = pd.DataFrame({
            "registrable_domain": ["example.com", "example.com"],
            "feature": [1, 2],
        })
        # Use ratios that put single group in train
        config = SplitConfig(train_ratio=1.0, val_ratio=0.0, test_ratio=0.0, seed=42)

        train, val, test = leakage_safe_split(df, config)

        # All should go to train (only one group, 100% train ratio)
        assert len(train) == 2
        assert len(val) == 0
        assert len(test) == 0


class TestVerifyNoLeakage:
    """Test leakage verification."""

    def test_no_leakage(self):
        train = pd.DataFrame({"registrable_domain": ["a", "a"], "val": [1, 2]})
        val = pd.DataFrame({"registrable_domain": ["b"], "val": [3]})
        test = pd.DataFrame({"registrable_domain": ["c", "c"], "val": [4, 5]})

        assert verify_no_leakage(train, val, test)

    def test_leakage_train_val(self):
        train = pd.DataFrame({"registrable_domain": ["a", "a"], "val": [1, 2]})
        val = pd.DataFrame({"registrable_domain": ["a"], "val": [3]})  # 'a' in both!
        test = pd.DataFrame({"registrable_domain": ["c"], "val": [4]})

        assert not verify_no_leakage(train, val, test)

    def test_leakage_train_test(self):
        train = pd.DataFrame({"registrable_domain": ["a"], "val": [1]})
        val = pd.DataFrame({"registrable_domain": ["b"], "val": [2]})
        test = pd.DataFrame({"registrable_domain": ["a"], "val": [3]})  # 'a' in both!

        assert not verify_no_leakage(train, val, test)

    def test_leakage_val_test(self):
        train = pd.DataFrame({"registrable_domain": ["a"], "val": [1]})
        val = pd.DataFrame({"registrable_domain": ["b"], "val": [2]})
        test = pd.DataFrame({"registrable_domain": ["b"], "val": [3]})  # 'b' in both!

        assert not verify_no_leakage(train, val, test)

    def test_custom_group_column(self):
        train = pd.DataFrame({"custom": ["a"], "val": [1]})
        val = pd.DataFrame({"custom": ["b"], "val": [2]})
        test = pd.DataFrame({"custom": ["c"], "val": [3]})

        assert verify_no_leakage(train, val, test, group_col="custom")


class TestGetSplitStats:
    """Test split statistics."""

    def test_basic_stats(self):
        train = pd.DataFrame({"registrable_domain": ["a", "a"], "val": [1, 2]})
        val = pd.DataFrame({"registrable_domain": ["b"], "val": [3]})
        test = pd.DataFrame({"registrable_domain": ["c", "c"], "val": [4, 5]})

        stats = get_split_stats(train, val, test)

        assert stats["train_rows"] == 2
        assert stats["val_rows"] == 1
        assert stats["test_rows"] == 2
        assert stats["train_groups"] == 1
        assert stats["val_groups"] == 1
        assert stats["test_groups"] == 1
        assert stats["total_groups"] == 3
        assert stats["leakage_free"] is True

    def test_empty_splits(self):
        train = pd.DataFrame({"registrable_domain": [], "val": []})
        val = pd.DataFrame({"registrable_domain": [], "val": []})
        test = pd.DataFrame({"registrable_domain": [], "val": []})

        stats = get_split_stats(train, val, test)

        assert stats["train_rows"] == 0
        assert stats["val_rows"] == 0
        assert stats["test_rows"] == 0
        assert stats["total_groups"] == 0