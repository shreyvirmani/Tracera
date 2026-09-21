from dataclasses import dataclass

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


@dataclass
class EvaluationMetrics:
    macro_f1: float
    critical_recall: float
    per_class_precision: dict[str, float]
    per_class_recall: dict[str, float]
    accuracy: float
    confusion_matrix: np.ndarray
    classification_report: str
    pr_auc: dict[str, float] | None = None

    def to_dict(self) -> dict:
        return {
            "macro_f1": self.macro_f1,
            "critical_recall": self.critical_recall,
            "per_class_precision": self.per_class_precision,
            "per_class_recall": self.per_class_recall,
            "accuracy": self.accuracy,
            "confusion_matrix": self.confusion_matrix.tolist(),
            "classification_report": self.classification_report,
            "pr_auc": self.pr_auc,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvaluationMetrics":
        return cls(
            macro_f1=data["macro_f1"],
            critical_recall=data["critical_recall"],
            per_class_precision=data["per_class_precision"],
            per_class_recall=data["per_class_recall"],
            accuracy=data["accuracy"],
            confusion_matrix=np.array(data["confusion_matrix"]),
            classification_report=data["classification_report"],
            pr_auc=data.get("pr_auc"),
        )


TIER_ORDER = ["low", "medium", "high", "critical"]
TIER_TO_IDX = {tier: i for i, tier in enumerate(TIER_ORDER)}


def evaluate_model(
    y_true: list[str],
    y_pred: list[str],
    y_proba: np.ndarray | None = None,
) -> EvaluationMetrics:
    """Evaluate model predictions with focus on macro F1 and critical recall."""

    # Convert labels to indices
    y_true_idx = [TIER_TO_IDX.get(t, 0) for t in y_true]
    y_pred_idx = [TIER_TO_IDX.get(t, 0) for t in y_pred]

    # Macro F1 (primary metric)
    macro_f1 = f1_score(y_true_idx, y_pred_idx, average="macro", zero_division=0)

    # Per-class metrics
    precision = precision_score(y_true_idx, y_pred_idx, average=None, zero_division=0)
    recall = recall_score(y_true_idx, y_pred_idx, average=None, zero_division=0)

    per_class_precision = {TIER_ORDER[i]: float(p) for i, p in enumerate(precision)}
    per_class_recall = {TIER_ORDER[i]: float(r) for i, r in enumerate(recall)}

    # Critical recall (secondary metric)
    critical_recall = per_class_recall.get("critical", 0.0)

    # Overall accuracy
    accuracy = accuracy_score(y_true_idx, y_pred_idx)

    # Confusion matrix
    cm = confusion_matrix(y_true_idx, y_pred_idx, labels=[0, 1, 2, 3])

    # Classification report
    report = classification_report(
        y_true_idx,
        y_pred_idx,
        labels=[0, 1, 2, 3],
        target_names=TIER_ORDER,
        zero_division=0,
    )

    # PR-AUC if probabilities provided
    pr_auc = None
    if y_proba is not None and y_proba.shape[1] == 4:
        from sklearn.metrics import average_precision_score

        try:
            # One-vs-rest PR-AUC
            y_true_bin = np.eye(4)[np.array(y_true_idx)]
            pr_auc_values = {}
            for i, tier in enumerate(TIER_ORDER):
                ap = average_precision_score(y_true_bin[:, i], y_proba[:, i])
                pr_auc_values[tier] = float(ap)
            pr_auc = pr_auc_values
        except Exception:
            pass

    return EvaluationMetrics(
        macro_f1=macro_f1,
        critical_recall=critical_recall,
        per_class_precision=per_class_precision,
        per_class_recall=per_class_recall,
        accuracy=accuracy,
        confusion_matrix=cm,
        classification_report=report,
        pr_auc=pr_auc,
    )


def compare_models(
    baseline_metrics: EvaluationMetrics,
    model_metrics: EvaluationMetrics,
) -> dict:
    """Compare model against baseline."""
    return {
        "macro_f1_improvement": model_metrics.macro_f1 - baseline_metrics.macro_f1,
        "critical_recall_improvement": model_metrics.critical_recall
        - baseline_metrics.critical_recall,
        "accuracy_improvement": model_metrics.accuracy - baseline_metrics.accuracy,
        "beats_baseline_macro_f1": model_metrics.macro_f1 > baseline_metrics.macro_f1,
        "beats_baseline_critical_recall": model_metrics.critical_recall
        > baseline_metrics.critical_recall,
    }
