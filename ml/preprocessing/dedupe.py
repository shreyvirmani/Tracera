"""
Deduplication for ML dataset construction.

Dataset unit: origin = scheme + host + port

Deduplication policy:
- Keep the record with the latest crawl timestamp per origin
- If timestamps are equal, prefer status 200 over other statuses
- If still tied, prefer the record with more complete headers/features

This ensures each origin appears exactly once in the dataset,
preventing the same website from producing multiple training samples.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass(frozen=True)
class DeduplicationPolicy:
    """
    Policy for deduplicating records by origin.

    Attributes:
        timestamp_col: Column name for crawl timestamp (used for "latest wins")
        status_col: Column name for HTTP status code
        prefer_status: Status code to prefer when timestamps are equal (default 200)
        feature_completeness_col: Optional column indicating feature completeness
    """
    timestamp_col: str = "crawl_timestamp"
    status_col: str = "status_code"
    prefer_status: int = 200
    feature_completeness_col: Optional[str] = None


def deduplicate_by_origin(
    df: pd.DataFrame,
    origin_col: str = "origin",
    policy: Optional[DeduplicationPolicy] = None,
) -> pd.DataFrame:
    """
    Deduplicate a DataFrame by origin, keeping the best record per origin.

    Args:
        df: Input DataFrame with at least an origin column
        origin_col: Name of the origin column
        policy: DeduplicationPolicy configuration

    Returns:
        Deduplicated DataFrame with one row per origin

    Raises:
        ValueError: If origin_col is not in DataFrame
    """
    if origin_col not in df.columns:
        raise ValueError(f"Column '{origin_col}' not found in DataFrame")

    policy = policy or DeduplicationPolicy()

    # Check required columns
    required_cols = [policy.timestamp_col, policy.status_col]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found for deduplication")

    # Create status priority column
    df = df.copy()
    df["_status_priority"] = (df[policy.status_col] != policy.prefer_status).astype(int)

    # Sort by: origin, timestamp (descending), status priority (ascending)
    df_sorted = df.sort_values(
        by=[origin_col, policy.timestamp_col, "_status_priority"],
        ascending=[True, False, True]
    )

    # Keep first (latest timestamp, preferred status) per origin
    result = df_sorted.drop_duplicates(subset=[origin_col], keep="first").drop(columns=["_status_priority"])

    return result.reset_index(drop=True)


def get_deduplication_stats(
    df: pd.DataFrame,
    origin_col: str = "origin",
) -> dict:
    """
    Get statistics about duplication in the dataset.

    Args:
        df: Input DataFrame
        origin_col: Name of the origin column

    Returns:
        Dictionary with duplication statistics
    """
    total_rows = len(df)
    unique_origins = df[origin_col].nunique()
    duplicate_count = total_rows - unique_origins

    # Origins with duplicates
    origin_counts = df.groupby(origin_col).size()
    max_duplicates = origin_counts.max() if len(origin_counts) > 0 else 0
    origins_with_duplicates = (origin_counts > 1).sum()

    return {
        "total_rows": int(total_rows),
        "unique_origins": int(unique_origins),
        "duplicate_rows": int(duplicate_count),
        "duplication_rate": float(duplicate_count / total_rows) if total_rows > 0 else 0.0,
        "origins_with_duplicates": int(origins_with_duplicates),
        "max_duplicates_per_origin": int(max_duplicates),
    }