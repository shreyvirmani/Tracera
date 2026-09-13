import numpy as np
import pytest

from app.features.schema import FeatureVector
from app.ml.baseline import FixedBaseline
from app.ml.evaluation import EvaluationMetrics, compare_models, evaluate_model
from app.ml.features import feature_vector_to_array, label_to_tier, tier_to_label
from app.ml.models import LogisticRegressionModel, RandomForestModel, XGBoostModel
from app.ml.tracking import Algorithm, ExperimentRecord, ExperimentTracker


class TestFixedBaseline:
    def test_predict_returns_tier(self):
        baseline = FixedBaseline()
        # Create minimal feature vector
        from app.features.schema import (
            CookieFeatures,
            HTMLFeatures,
            HTTPFeatures,
            SecurityHeaderFeatures,
            TechnologyFeatures,
            TLSFeatures,
        )

        features = FeatureVector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=1000,
                response_time_ms=100,
                content_type="text/html",
                redirect_count=0,
                https_enabled=True,
            ),
            security_headers=SecurityHeaderFeatures(),
            cookies=CookieFeatures(
                total_cookies=0,
                secure_cookies=0,
                httponly_cookies=0,
                samesite_cookies=0,
                session_cookies=0,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
            tls=TLSFeatures(),
            html=HTMLFeatures(
                html_size_bytes=1000,
                script_count=0,
                stylesheet_count=0,
                image_count=0,
                iframe_count=0,
                form_count=0,
                external_domain_count=0,
                mixed_content_count=0,
            ),
            technology=TechnologyFeatures(),
        )
        tier = baseline.predict(features)
        assert tier in ["low", "medium", "high", "critical"]

    def test_predict_proba_returns_distribution(self):
        baseline = FixedBaseline()
        from app.features.schema import (
            CookieFeatures,
            HTMLFeatures,
            HTTPFeatures,
            SecurityHeaderFeatures,
            TechnologyFeatures,
            TLSFeatures,
        )

        features = FeatureVector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=1000,
                response_time_ms=100,
                content_type="text/html",
                redirect_count=0,
                https_enabled=True,
            ),
            security_headers=SecurityHeaderFeatures(),
            cookies=CookieFeatures(
                total_cookies=0,
                secure_cookies=0,
                httponly_cookies=0,
                samesite_cookies=0,
                session_cookies=0,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
            tls=TLSFeatures(),
            html=HTMLFeatures(
                html_size_bytes=1000,
                script_count=0,
                stylesheet_count=0,
                image_count=0,
                iframe_count=0,
                form_count=0,
                external_domain_count=0,
                mixed_content_count=0,
            ),
            technology=TechnologyFeatures(),
        )
        proba = baseline.predict_proba(features)
        assert proba.shape == (4,)
        assert abs(proba.sum() - 1.0) < 1e-6


class TestFeatureConversion:
    def test_tier_to_label(self):
        assert tier_to_label("low") == 0
        assert tier_to_label("medium") == 1
        assert tier_to_label("high") == 2
        assert tier_to_label("critical") == 3

    def test_label_to_tier(self):
        assert label_to_tier(0) == "low"
        assert label_to_tier(1) == "medium"
        assert label_to_tier(2) == "high"
        assert label_to_tier(3) == "critical"

    def test_feature_vector_to_array(self):
        from app.features.schema import (
            CookieFeatures,
            HTMLFeatures,
            HTTPFeatures,
            SecurityHeaderFeatures,
            TechnologyFeatures,
            TLSFeatures,
        )

        features = FeatureVector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=1000,
                response_time_ms=100,
                content_type="text/html",
                redirect_count=0,
                https_enabled=True,
            ),
            security_headers=SecurityHeaderFeatures(hsts="max-age=31536000"),
            cookies=CookieFeatures(
                total_cookies=2,
                secure_cookies=1,
                httponly_cookies=1,
                samesite_cookies=1,
                session_cookies=1,
                persistent_cookies=1,
                third_party_indicators=0,
            ),
            tls=TLSFeatures(
                cert_expiry_days=30,
                cert_expired=False,
                tls_version="TLSv1.3",
                cipher_suite="TLS_AES_256_GCM_SHA384",
            ),
            html=HTMLFeatures(
                html_size_bytes=5000,
                script_count=5,
                stylesheet_count=2,
                image_count=10,
                iframe_count=1,
                form_count=1,
                external_domain_count=3,
                mixed_content_count=0,
                has_password_field=True,
                has_file_upload=False,
            ),
            technology=TechnologyFeatures(
                server_header_present=True,
                x_powered_by_present=False,
                framework_indicators=["nginx"],
            ),
        )
        arr = feature_vector_to_array(features)
        assert arr.shape == (39,)  # Expected feature count
        assert arr[0] == 200  # status_code
        assert arr[4] == 1.0  # https_enabled
        assert arr[5] == 1.0  # hsts present
        assert arr[11] == 0.0  # csp not present


class TestEvaluation:
    def test_evaluate_model_perfect(self):
        y_true = ["low", "medium", "high", "critical"] * 10
        y_pred = ["low", "medium", "high", "critical"] * 10
        metrics = evaluate_model(y_true, y_pred)
        assert metrics.macro_f1 == 1.0
        assert metrics.critical_recall == 1.0
        assert metrics.accuracy == 1.0

    def test_evaluate_model_all_wrong(self):
        y_true = ["low"] * 10 + ["critical"] * 10
        y_pred = ["critical"] * 10 + ["low"] * 10
        metrics = evaluate_model(y_true, y_pred)
        assert metrics.macro_f1 < 1.0
        assert metrics.critical_recall == 0.0

    def test_evaluate_model_imbalanced(self):
        y_true = ["low"] * 80 + ["medium"] * 15 + ["high"] * 4 + ["critical"] * 1
        y_pred = ["low"] * 100
        metrics = evaluate_model(y_true, y_pred)
        assert metrics.macro_f1 < 0.5
        assert metrics.critical_recall == 0.0
        assert metrics.per_class_precision["low"] == 0.8


class TestCompareModels:
    def test_compare_improvement(self):
        baseline = EvaluationMetrics(
            macro_f1=0.5,
            critical_recall=0.3,
            per_class_precision={},
            per_class_recall={},
            accuracy=0.6,
            confusion_matrix=np.eye(4),
            classification_report="",
        )
        model = EvaluationMetrics(
            macro_f1=0.7,
            critical_recall=0.6,
            per_class_precision={},
            per_class_recall={},
            accuracy=0.8,
            confusion_matrix=np.eye(4),
            classification_report="",
        )
        comparison = compare_models(baseline, model)
        assert comparison["macro_f1_improvement"] == pytest.approx(0.2)
        assert comparison["critical_recall_improvement"] == pytest.approx(0.3)
        assert comparison["beats_baseline_macro_f1"] is True
        assert comparison["beats_baseline_critical_recall"] is True

    def test_compare_degradation(self):
        baseline = EvaluationMetrics(
            macro_f1=0.7,
            critical_recall=0.6,
            per_class_precision={},
            per_class_recall={},
            accuracy=0.8,
            confusion_matrix=np.eye(4),
            classification_report="",
        )
        model = EvaluationMetrics(
            macro_f1=0.5,
            critical_recall=0.3,
            per_class_precision={},
            per_class_recall={},
            accuracy=0.6,
            confusion_matrix=np.eye(4),
            classification_report="",
        )
        comparison = compare_models(baseline, model)
        assert comparison["macro_f1_improvement"] == pytest.approx(-0.2)
        assert comparison["beats_baseline_macro_f1"] is False
        assert comparison["beats_baseline_critical_recall"] is False


class TestExperimentTracking:
    def test_experiment_record_roundtrip(self):
        record = ExperimentRecord(
            model_name="logistic_regression_v1.0",
            model_version="1.0",
            algorithm=Algorithm.LOGISTIC_REGRESSION,
            dataset_version="v1.0.0",
            hyperparameters={"C": 1.0},
            metrics={"macro_f1": 0.85, "critical_recall": 0.8},
            notes="Test experiment",
        )
        data = record.to_dict()
        restored = ExperimentRecord.from_dict(data)
        assert restored.model_name == record.model_name
        assert restored.algorithm == record.algorithm
        assert restored.metrics == record.metrics

    def test_experiment_tracker(self, tmp_path):
        tracker = ExperimentTracker(str(tmp_path / "experiments"))
        record = ExperimentRecord(
            model_name="test_v1.0",
            model_version="1.0",
            algorithm=Algorithm.RANDOM_FOREST,
            dataset_version="v1.0.0",
            metrics={"macro_f1": 0.85},
        )
        tracker.log_experiment(record)
        experiments = tracker.get_experiments(dataset_version="v1.0.0")
        assert len(experiments) == 1
        assert experiments[0].model_name == "test_v1.0"


class TestMLModels:
    def test_logistic_regression_fit_predict(self):
        X = np.random.rand(100, 10)
        y = np.random.randint(0, 4, 100)
        model = LogisticRegressionModel()
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == 100
        assert model.is_fitted

    def test_random_forest_fit_predict(self):
        X = np.random.rand(50, 10)
        y = np.random.randint(0, 4, 50)
        model = RandomForestModel()
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == 50
        assert model.is_fitted

    def test_xgboost_fit_predict(self):
        X = np.random.rand(50, 10)
        y = np.random.randint(0, 4, 50)
        model = XGBoostModel()
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == 50
        assert model.is_fitted

    def test_model_save_load(self, tmp_path):
        X = np.random.rand(50, 10)
        y = np.random.randint(0, 4, 50)
        model = LogisticRegressionModel()
        model.fit(X, y)

        path = tmp_path / "model.joblib"
        model.save(str(path))
        loaded = LogisticRegressionModel.load(str(path))
        assert loaded.is_fitted
        assert loaded.model_name == model.model_name
        preds_orig = model.predict(X)
        preds_loaded = loaded.predict(X)
        np.testing.assert_array_equal(preds_orig, preds_loaded)
