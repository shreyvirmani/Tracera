"""
Leakage-safe train/validation/test splitting for ML datasets.

Groups by registrable domain (eTLD+1) so that subdomains of the same
organization/platform never appear in different splits.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import pandas as pd
import random


@dataclass(frozen=True)
class SplitConfig:
    """Configuration for leakage-safe splitting."""
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    seed: int = 42
    group_col: str = "registrable_domain"

    def __post_init__(self):
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")


def leakage_safe_split(
    df: pd.DataFrame,
    config: Optional["SplitConfig"] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split DataFrame into train/val/test with leakage-safe grouping.

    Groups by registrable_domain (eTLD+1) so that all subdomains
    of the same organization/platform stay in the same split.

    Args:
        df: Input DataFrame with a registrable_domain column
        config: SplitConfig with ratios and group column

    Returns:
        Tuple of (train_df, val_df, test_df)

    Raises:
        ValueError: If group_col not in DataFrame or ratios invalid
    """
    config = config or SplitConfig()

    if config.group_col not in df.columns:
        raise ValueError(f"Group column '{config.group_col}' not found in DataFrame")

    # Get unique groups
    groups = df[config.group_col].unique().tolist()

    # Shuffle groups deterministically
    rng = random.Random(config.seed)
    rng.shuffle(groups)

    # Calculate split indices
    n = len(groups)
    n_train = int(n * config.train_ratio)
    n_val = int(n * config.val_ratio)

    train_groups = set(groups[:n_train])
    val_groups = set(groups[n_train:n_train + n_val])
    test_groups = set(groups[n_train + n_val:])

    # Split DataFrame
    train_df = df[df[config.group_col].isin(train_groups)].copy()
    val_df = df[df[config.group_col].isin(val_groups)].copy()
    test_df = df[df[config.group_col].isin(test_groups)].copy()

    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


def verify_no_leakage(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    group_col: str = "registrable_domain",
) -> bool:
    """
    Verify that no groups appear in more than one split.

    Args:
        train_df: Training DataFrame
        val_df: Validation DataFrame
        test_df: Test DataFrame
        group_col: Column name for groups

    Returns:
        True if no leakage, False otherwise
    """
    train_groups = set(train_df[group_col].unique())
    val_groups = set(val_df[group_col].unique())
    test_groups = set(test_df[group_col].unique())

    # Check intersections
    train_val = train_groups & val_groups
    train_test = train_groups & test_groups
    val_test = val_groups & test_groups

    if train_val:
        print(f"LEAKAGE: {len(train_val)} groups in both train and val: {train_val}")
        return False
    if train_test:
        print(f"LEAKAGE: {len(train_test)} groups in both train and test: {train_test}")
        return False
    if val_test:
        print(f"LEAKAGE: {len(val_test)} groups in both val and test: {val_test}")
        return False

    return True


def get_split_stats(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    group_col: str = "registrable_domain",
) -> dict:
    """
    Get statistics about the split.

    Args:
        train_df: Training DataFrame
        val_df: Validation DataFrame
        test_df: Test DataFrame
        group_col: Column name for groups

    Returns:
        Dictionary with split statistics
    """
    train_groups = set(train_df[group_col].unique())
    val_groups = set(val_df[group_col].unique())
    test_groups = set(test_df[group_col].unique())

    all_groups = train_groups | val_groups | test_groups

    return {
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "train_groups": len(train_groups),
        "val_groups": len(val_groups),
        "test_groups": len(test_groups),
        "total_groups": len(all_groups),
        "train_group_ratio": len(train_groups) / len(all_groups) if all_groups else 0.0,
        "val_group_ratio": len(val_groups) / len(all_groups) if all_groups else 0.0,
        "test_group_ratio": len(test_groups) / len(all_groups) if all_groups else 0.0,
        "leakage_free": verify_no_leakage(train_df, val_df, test_df, group_col),
    }