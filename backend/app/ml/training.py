import numpy as np

from app.dataset.repository import get_dataset_version, get_samples_by_split
from app.ml.baseline import FixedBaseline
from app.ml.evaluation import compare_models, evaluate_model
from app.ml.features import (
    feature_vectors_to_matrix,
    label_to_tier,
    tier_to_label,
)
from app.ml.models import LogisticRegressionModel, RandomForestModel, XGBoostModel
from app.ml.tracking import Algorithm, ExperimentRecord


async def load_dataset(
    db,
    dataset_version: str,
    splits: list[str] = None,
) -> tuple:
    """Load dataset and convert to feature matrix and labels."""
    if splits is None:
        splits = ["train", "validation", "test"]

    dv = await get_dataset_version(db, dataset_version)
    if not dv:
        raise ValueError(f"Dataset version {dataset_version} not found")

    X_train, y_train = [], []
    X_val, y_val = [], []
    X_test, y_test = [], []

    for split in splits:
        samples = await get_samples_by_split(db, dv.id, split, limit=None)
        if not samples:
            continue

        features_list = [s.feature_vector for s in samples]
        X = feature_vectors_to_matrix(features_list)
        y = np.array([tier_to_label(s.risk_tier) for s in samples])

        if split == "train":
            X_train, y_train = X, y
        elif split == "validation":
            X_val, y_val = X, y
        elif split == "test":
            X_test, y_test = X, y

    return X_train, y_train, X_val, y_val, X_test, y_test


async def train_and_evaluate(
    algorithm: str,
    dataset_version: str,
    db,
    hyperparameters: dict = None,
    model_version: str = "1.0",
    notes: str = "",
):
    """Train a model and return (model, test_metrics, comparison, experiment_record)."""
    if hyperparameters is None:
        hyperparameters = {}

    X_train, y_train, X_val, y_val, X_test, y_test = await load_dataset(db, dataset_version)

    if len(X_train) == 0:
        raise ValueError("No training samples found")

    # Create and train model
    if algorithm == "logistic_regression":
        model = LogisticRegressionModel(version=model_version, **hyperparameters)
    elif algorithm == "random_forest":
        model = RandomForestModel(version=model_version, **hyperparameters)
    elif algorithm == "xgboost":
        model = XGBoostModel(version=model_version, **hyperparameters)
    elif algorithm == "fixed_baseline":
        model = FixedBaseline()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    if algorithm != "fixed_baseline":
        model.fit(X_train, y_train)

    # Evaluate on test set
    y_test_pred = model.predict(X_test)
    y_test_proba = model.predict_proba(X_test) if algorithm != "fixed_baseline" else None

    y_test_true_labels = [label_to_tier(int(idx)) for idx in y_test]
    y_test_pred_labels = [label_to_tier(int(p)) for p in y_test_pred]

    test_metrics = evaluate_model(y_test_true_labels, y_test_pred_labels, y_test_proba)

    # Compare with baseline
    baseline = FixedBaseline()

    dv = await get_dataset_version(db, dataset_version)
    test_samples = await get_samples_by_split(db, dv.id, "test", limit=None)
    test_features = [s.feature_vector for s in test_samples]
    baseline_pred = [baseline.predict(f) for f in test_features]
    baseline_true = [s.risk_tier for s in test_samples]

    baseline_metrics = evaluate_model(baseline_true, baseline_pred)
    test_metrics = evaluate_model(y_test_true_labels, y_test_pred_labels, y_test_proba)

    comparison = compare_models(baseline_metrics, test_metrics)

    # Create experiment record
    record = ExperimentRecord(
        model_name=f"{algorithm}_v{model_version}",
        model_version=model_version,
        algorithm=(
            Algorithm(algorithm) if algorithm != "fixed_baseline" else Algorithm.FIXED_BASELINE
        ),
        dataset_version=dataset_version,
        feature_schema_version="features-v1",
        hyperparameters=hyperparameters,
        metrics=test_metrics.to_dict(),
        notes=notes,
    )

    return model, test_metrics, comparison, record


async def run_baseline_evaluation(
    dataset_version: str,
    db,
) -> tuple:
    """Evaluate the fixed baseline on test set."""
    baseline = FixedBaseline()

    dv = await get_dataset_version(db, dataset_version)
    test_samples = await get_samples_by_split(db, dv.id, "test", limit=None)

    test_features = [s.feature_vector for s in test_samples]
    y_pred = [baseline.predict(f) for f in test_features]
    y_true = [s.risk_tier for s in test_samples]

    from app.ml.evaluation import evaluate_model

    metrics = evaluate_model(y_true, y_pred)

    return baseline, metrics
