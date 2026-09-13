from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


class BaseMLModel(ABC):
    """Abstract base class for ML models."""

    def __init__(self, model_name: str, version: str = "1.0"):
        self.model_name = model_name
        self.version = version
        self.model: object | None = None
        self.scaler: StandardScaler | None = None
        self.is_fitted = False
        self.feature_names: list[str] = []

    @abstractmethod
    def _create_model(self) -> object:
        pass

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaseMLModel":
        self.model = self._create_model()
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def get_metadata(self) -> dict:
        return {
            "model_name": self.model_name,
            "model_version": self.version,
            "model_type": self.__class__.__name__,
            "is_fitted": self.is_fitted,
        }

    def save(self, path: str) -> None:
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "metadata": self.get_metadata(),
                "feature_names": self.feature_names,
            },
            path,
        )

    @classmethod
    def load(cls, path: str) -> "BaseMLModel":
        data = joblib.load(path)
        instance = cls.__new__(cls)
        instance.model_name = data["metadata"]["model_name"]
        instance.version = data["metadata"]["model_version"]
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance.is_fitted = data["metadata"]["is_fitted"]
        instance.feature_names = data["feature_names"]
        return instance


class LogisticRegressionModel(BaseMLModel):
    def __init__(self, version: str = "1.0", **kwargs):
        super().__init__("logistic_regression", version)
        self.kwargs = kwargs

    def _create_model(self) -> LogisticRegression:
        return LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
            **self.kwargs,
        )


class RandomForestModel(BaseMLModel):
    def __init__(self, version: str = "1.0", **kwargs):
        super().__init__("random_forest", version)
        self.kwargs = kwargs

    def _create_model(self) -> RandomForestClassifier:
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
            **self.kwargs,
        )


class XGBoostModel(BaseMLModel):
    def __init__(self, version: str = "1.0", **kwargs):
        super().__init__("xgboost", version)
        self.kwargs = kwargs

    def _create_model(self) -> XGBClassifier:
        return XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
            **self.kwargs,
        )
