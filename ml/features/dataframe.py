"""
DataFrame-level validation/coercion for MLFeaturesV1 datasets.

Single shared implementation used by the data pipelines and the evaluation
framework (replacing the earlier ad-hoc `validate_feature_matrix` copies).

Policy (documented, explicit — never silent):
- Missing feature *columns* are an error (dataset does not match the schema).
- NaN in a numeric feature cell is coerced to the documented default (0 / 0.0)
  and counted in the report (n_nan_coerced).
- Non-numeric garbage in a feature cell drops the affected row, counted in
  drop_reasons.
- Rows failing MLFeaturesV1.validate() (bad ranges, bad types after coercion)
  are dropped, with the first issue naming the reason.
- Float 0.0/1.0 for int features is coerced (parquet round-trip artifact),
  counted once per column (n_type_coerced).

The function never mutates the input DataFrame.
"""

from dataclasses import dataclass, field as dc_field

import numpy as np
import pandas as pd

from ml.features.schema_v1 import (
    MLFeaturesV1,
    BINARY_FEATURES,
    FeatureValidationError,
)


@dataclass
class FeatureFrameReport:
    """Summary of what happened during validation/coercion."""
    n_rows_in: int = 0
    n_rows_out: int = 0
    n_dropped: int = 0
    n_nan_coerced: int = 0            # cells where NaN -> documented default
    n_type_coerced: int = 0           # columns where 0.0/1.0 float -> int
    drop_reasons: dict = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "n_rows_in": self.n_rows_in,
            "n_rows_out": self.n_rows_out,
            "n_dropped": self.n_dropped,
            "n_nan_coerced": self.n_nan_coerced,
            "n_type_coerced": self.n_type_coerced,
            "drop_reasons": self.drop_reasons,
        }


def validate_feature_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, FeatureFrameReport]:
    """
    Validate a dataset against MLFeaturesV1.

    Returns a frame whose first columns are the 17 features in canonical
    MLFeaturesV1.feature_names() order (integer dtypes restored for int
    features), followed by any non-feature columns from the input.
    """
    feature_names = MLFeaturesV1.feature_names()
    missing_columns = [c for c in feature_names if c not in df.columns]
    if missing_columns:
        raise ValueError(
            f"dataset is missing {len(missing_columns)} feature column(s): {missing_columns}"
        )

    int_features = (
        ["status_code", "is_html", "https_enabled", "cookie_count"] + BINARY_FEATURES
    )

    report = FeatureFrameReport(n_rows_in=len(df))
    cleaned = df.copy()
    drop_mask = np.zeros(len(cleaned), dtype=bool)

    for col in feature_names:
        series = cleaned[col]
        numeric = pd.to_numeric(series, errors="coerce")

        # Non-numeric garbage -> drop affected rows.
        bad = series.notna() & numeric.isna()
        if bad.any():
            drop_mask |= bad.to_numpy()
            report.drop_reasons[f"{col}:non_numeric"] = int(bad.sum())

        # NaN -> documented default (0), counted.
        n_nan = int(numeric.isna().sum()) - int((series.notna() & numeric.isna()).sum())
        if n_nan > 0:
            report.n_nan_coerced += n_nan

        if col in int_features and not pd.api.types.is_integer_dtype(numeric):
            report.n_type_coerced += 1
        cleaned[col] = numeric

    # Fill the NaNs that remain (documented default 0 / 0.0).
    cleaned[feature_names] = cleaned[feature_names].fillna(0)

    # Row-level contract validation through the canonical vector validator.
    invalid_row_indices: list[int] = []
    for i in range(len(cleaned)):
        raw = {k: cleaned.iloc[i][k] for k in feature_names}
        # Parquet/DataFrame round-trips ints as floats; integral floats map to int
        # (200.0 -> 200). Non-integral floats stay float and the validator drops them.
        row = {}
        for k, v in raw.items():
            if k in int_features and pd.api.types.is_number(v) and not pd.isna(v) and v == int(v):
                row[k] = int(v)
            else:
                row[k] = v
        try:
            MLFeaturesV1.from_dict(row, strict=True).validate()
        except FeatureValidationError as e:
            invalid_row_indices.append(i)
            if e.issues:
                name, _, _ = e.issues[0].partition(":")
                key = f"{name.strip()}:invalid_value"
                report.drop_reasons[key] = report.drop_reasons.get(key, 0) + 1

    drop_mask[invalid_row_indices] = True

    build = pd.concat(
        [cleaned.loc[~drop_mask, feature_names], cleaned.loc[~drop_mask, :]],
        axis=1,
    )
    build = build.loc[:, ~build.columns.duplicated()]
    feature_df = build[feature_names + [c for c in build.columns[~build.columns.isin(feature_names)]]].reset_index(drop=True)

    for col in int_features:
        feature_df[col] = feature_df[col].astype(np.int64)

    report.n_rows_out = len(feature_df)
    report.n_dropped = report.n_rows_in - report.n_rows_out
    return feature_df, report
