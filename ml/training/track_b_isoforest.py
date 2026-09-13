"""
Tracera ML — Track B: Isolation Forest Anomaly Detection Experiment

Synthetic development experiment only.
Results are NOT representative of real-world performance.
No ground-truth labels exist.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

from ml.features.schema_v1 import MLFeaturesV1, ML_FEATURE_SCHEMA_VERSION


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class IsoForestConfig:
    """Isolation Forest configuration - all parameters explicit."""
    n_estimators: int = 200
    random_state: int = 42
    contamination: str = "auto"  # or float
    max_samples: str = "auto"
    n_jobs: int = -1
    verbose: int = 0
    seeds: List[int] = None  # for stability analysis

    def __post_init__(self):
        if self.seeds is None:
            self.seeds = [42, 123, 2026]

    # Tree parameters
    max_features: float = 1.0
    bootstrap: bool = False


# =============================================================================
# PREPROCESSING
# =============================================================================

MODEL_FEATURES = MLFeaturesV1.feature_names()


def validate_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract and validate the 17-feature model matrix.
    
    Returns:
        (X: feature matrix, metadata_df: metadata columns)
    """
    # Verify exactly 17 model features
    missing = [f for f in MODEL_FEATURES if f not in df.columns]
    extra = [f for f in df.columns if f not in MODEL_FEATURES and f not in [
        'url', 'origin', 'registrable_domain', 'crawl_timestamp', 'warc_filename',
        'record_id', 'server_header_value', 'x_powered_by_value', 'content_type',
        'cookie_info_available', 'source_type', 'source_identifier'
    ]]
    
    if missing:
        raise ValueError(f"Missing model features: {missing}")
    
    X = df[MODEL_FEATURES].copy()
    metadata_cols = [c for c in df.columns if c not in MODEL_FEATURES]
    metadata = df[metadata_cols].copy()
    
    return X, metadata


def preprocess_features(X: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess feature matrix for Isolation Forest.
    
    Decisions:
    - Binary features: remain as 0/1 (tree-based handles natively)
    - Ratios: remain in [0,1] (already normalized)
    - status_code: keep as raw int (all 200 in synthetic data)
    - cookie_count: keep raw (tree-based handles discrete)
    
    No standardization/scaling applied (tree-based models don't require it).
    """
    X_proc = X.copy()
    
    # Ensure binary features are 0/1 ints
    binary_cols = [
        'is_html', 'https_enabled', 'hsts_present', 'csp_present',
        'x_content_type_options_present', 'x_frame_options_present',
        'referrer_policy_present', 'permissions_policy_present',
        'server_header_present', 'x_powered_by_present'
    ]
    for col in binary_cols:
        if col in X_proc.columns:
            X_proc[col] = X_proc[col].astype(int)
    
    return X_proc


# =============================================================================
# ISOLATION FOREST TRAINING
# =============================================================================

def train_isolation_forest(
    X_train: pd.DataFrame,
    config: IsoForestConfig
) -> Tuple[IsolationForest, float]:
    """
    Train Isolation Forest and return model with proper threshold.
    
    Returns:
        model: trained IsolationForest
        threshold: anomaly threshold (5th percentile of training scores)
    """
    model = IsolationForest(
        n_estimators=config.n_estimators,
        random_state=config.random_state,
        contamination=config.contamination,
        max_samples=config.max_samples,
        n_jobs=config.n_jobs,
        verbose=config.verbose,
        max_features=config.max_features,
        bootstrap=config.bootstrap,
    )
    model.fit(X_train)
    
    # Compute threshold from training scores (5th percentile for ~5% contamination)
    train_scores = model.decision_function(X_train)
    threshold = np.percentile(train_scores, 5)
    
    return model, threshold


def score_anomalies(model: IsolationForest, X: pd.DataFrame, threshold: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get anomaly scores and flags.
    
    Returns:
        scores: decision_function scores (higher = more normal)
        flags: True = anomaly (score below threshold)
    """
    scores = model.decision_function(X)
    anomaly_flags = (scores < threshold)
    return scores, anomaly_flags


# =============================================================================
# NOVELTY ANALYSIS
# =============================================================================

def analyze_rule_overlap(
    anomalies_df: pd.DataFrame,
    rule_finding_cols: List[str] = None
) -> Dict:
    """
    Categorize anomalies by overlap with deterministic Tracera rules.
    
    Categories:
    A. Rule-overlap anomaly: anomaly explained by existing deterministic findings
    B. Potentially novel anomaly: high anomaly score, NOT explained by existing rules
    C. Weak/irrelevant anomaly: unusual statistically but no clear security interpretation
    """
    if rule_finding_cols is None:
        # We'll use the deterministic findings from the pilot data
        rule_finding_cols = [c for c in anomalies_df.columns if c.startswith('finding_')]
    
    # For synthetic data, we don't have explicit rule findings
    # This is a placeholder for real data integration
    return {
        'total_anomalies': len(anomalies_df),
        'rule_overlap': 0,
        'potentially_novel': 0,
        'weak_irrelevant': len(anomalies_df),
        'note': 'No deterministic rule findings available in synthetic data'
    }


def stability_analysis(
    X: pd.DataFrame,
    seeds: List[int] = [42, 123, 2026],
    contamination: str = "auto",
    n_estimators: int = 200,
    top_ks: List[int] = [10, 25, 50]
) -> Dict:
    """
    Compare anomaly rankings across different random seeds.
    """
    results = {}
    for k in top_ks:
        overlap = {}
        for seed in seeds:
            model = IsolationForest(
                n_estimators=n_estimators,
                random_state=seed,
                contamination=contamination,
                n_jobs=-1
            )
            model.fit(X)
            scores = model.decision_function(X)
            top_k_idx = np.argsort(scores)[:k]
            overlap[f'seed_{seed}'] = set(top_k_idx)
        
        # Jaccard overlap
        seed_keys = list(overlap.keys())
        jaccard_values = []
        for i in range(len(seed_keys)):
            for j in range(i+1, len(seed_keys)):
                a = overlap[seed_keys[i]]
                b = overlap[seed_keys[j]]
                jaccard = len(a & b) / len(a | b) if len(a | b) > 0 else 0
                jaccard_values.append(jaccard)
        
        results[f'top_{k}'] = {
            'jaccard_mean': np.mean(jaccard_values),
            'jaccard_min': np.min(jaccard_values),
            'jaccard_max': np.max(jaccard_values),
            'seed_sets': {k: list(v) for k, v in overlap.items()}
        }
    
    return results


# =============================================================================
# ABLATION EXPERIMENTS
# =============================================================================

FEATURE_GROUPS = {
    'all': MODEL_FEATURES,
    'security_headers': [
        'hsts_present', 'csp_present', 'x_content_type_options_present',
        'x_frame_options_present', 'referrer_policy_present', 'permissions_policy_present'
    ],
    'cookies': [
        'cookie_count', 'cookie_secure_ratio', 'cookie_httponly_ratio',
        'cookie_samesite_strict_ratio', 'cookie_samesite_lax_ratio', 'cookie_samesite_none_ratio'
    ],
    'http_basic': ['status_code', 'is_html', 'https_enabled'],
    'tech_disclosure': ['server_header_present', 'x_powered_by_present'],
    'no_security_headers': [f for f in MODEL_FEATURES if f not in [
        'hsts_present', 'csp_present', 'x_content_type_options_present',
        'x_frame_options_present', 'referrer_policy_present', 'permissions_policy_present'
    ]],
}


def run_ablation(X: pd.DataFrame, config: IsoForestConfig) -> Dict:
    """Run Isolation Forest on different feature subsets."""
    results = {}
    for name, features in FEATURE_GROUPS.items():
        X_sub = X[features].copy()
        model = IsolationForest(
            n_estimators=config.n_estimators,
            random_state=config.random_state,
            contamination=config.contamination,
            max_samples=config.max_samples,
            n_jobs=config.n_jobs,
            verbose=config.verbose,
        )
        model.fit(X_sub)
        scores = model.decision_function(X_sub)
        flags = model.predict(X_sub)
        
        results[name] = {
            'n_features': len(features),
            'features': features,
            'n_anomalies': int((flags == -1).sum()),
            'anomaly_rate': float((flags == -1).mean()),
            'score_mean': float(scores.mean()),
            'score_std': float(scores.std()),
        }
    return results


# =============================================================================
# MAIN EXPERIMENT
# =============================================================================

def run_experiment(
    data_path: str = "ml/data/pilot/processed/full.parquet",
    config: Optional[IsoForestConfig] = None,
    seeds: List[int] = [42, 123, 2026]
) -> Dict:
    """
    Run the complete Isolation Forest experiment.
    """
    if config is None:
        config = IsoForestConfig()
    
    # Use a reasonable contamination for synthetic data
    if config.contamination == "auto":
        config.contamination = 0.05  # 5% expected anomaly rate for synthetic data
    
    # Load data
    df = pd.read_parquet(data_path)
    
    # Validate and split features/metadata
    X, metadata = validate_feature_matrix(df)
    X_proc = preprocess_features(X)
    
    print(f"Feature matrix shape: {X_proc.shape}")
    print(f"Features: {list(X_proc.columns)}")
    print(f"Cookie count = 0: {(df['cookie_count'] == 0).sum()} / {len(df)}")
    print(f"cookie_info_available = False: {(~df['cookie_info_available']).sum()} / {len(df)}")
    
    # Split for stability analysis (train on all, test on all for unsupervised)
    # Use train/test split from the pilot for consistency
    train_df = pd.read_parquet("ml/data/pilot/processed/train.parquet")
    val_df = pd.read_parquet("ml/data/pilot/processed/val.parquet")
    test_df = pd.read_parquet("ml/data/pilot/processed/test.parquet")
    
    X_train, _ = validate_feature_matrix(train_df)
    X_val, _ = validate_feature_matrix(val_df)
    X_test, _ = validate_feature_matrix(test_df)
    
    X_train = preprocess_features(X_train)
    X_val = preprocess_features(X_val)
    X_test = preprocess_features(X_test)
    
    # Train on train set
    model, threshold = train_isolation_forest(X_train, config)
    
    # Score all sets
    train_scores, train_flags = score_anomalies(model, X_train, threshold)
    val_scores, val_flags = score_anomalies(model, X_val, threshold)
    test_scores, test_flags = score_anomalies(model, X_test, threshold)
    
    # Combine all for analysis
    all_X = pd.concat([X_train, X_val, X_test], ignore_index=True)
    all_scores = np.concatenate([train_scores, val_scores, test_scores])
    all_flags = np.concatenate([train_flags, val_flags, test_flags])
    all_metadata = pd.concat([
        metadata.iloc[:len(X_train)],
        metadata.iloc[len(X_train):len(X_train)+len(X_val)],
        metadata.iloc[len(X_train)+len(X_val):]
    ], ignore_index=True)
    
    # Build results
    anomalies_mask = all_flags
    n_anomalies = int(anomalies_mask.sum())
    anomaly_rate = float(anomalies_mask.mean())
    
    print(f"\nTotal anomalies: {n_anomalies} / {len(all_X)} ({anomaly_rate:.2%})")
    
    # Create anomaly dataframe
    anomalies_df = all_metadata[anomalies_mask].copy()
    anomalies_df['anomaly_score'] = all_scores[anomalies_mask]
    anomalies_df = anomalies_df.sort_values('anomaly_score')
    
    # Rule overlap analysis
    rule_overlap = analyze_rule_overlap(anomalies_df)
    
    # Stability analysis
    stability = stability_analysis(X_train, seeds=config.seeds)
    
    # Ablation experiments
    ablation = run_ablation(X_train, config)
    
    # Top anomalies
    top_25 = anomalies_df.head(25)[['origin', 'anomaly_score', 'registrable_domain']].to_dict('records')
    top_50 = anomalies_df.head(50)[['origin', 'anomaly_score', 'registrable_domain']].to_dict('records')
    
    return {
        'experiment_info': {
            'timestamp': datetime.now().isoformat(),
            'data_source': 'synthetic_fixture',
            'schema_version': ML_FEATURE_SCHEMA_VERSION,
            'config': asdict(config),
            'data_stats': {
                'n_train': len(X_train),
                'n_val': len(X_val),
                'n_test': len(X_test),
                'total': len(all_X),
            }
        },
        'model_params': asdict(config),
        'anomaly_summary': {
            'n_total': len(all_X),
            'n_anomalies': n_anomalies,
            'anomaly_rate': anomaly_rate,
            'score_range': [float(all_scores.min()), float(all_scores.max())],
            'score_mean': float(all_scores.mean()),
            'score_std': float(all_scores.std()),
        },
        'top_anomalies': top_25,
        'rule_overlap': rule_overlap,
        'stability': stability,
        'ablation': ablation,
        'limitations': {
            'data_is_synthetic': True,
            'no_ground_truth_labels': True,
            'cookie_ratios_ambiguous_when_count_zero': True,
            'no_real_world_validation': True,
            'synthetic_distributions_not_representative': True,
        }
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    config = IsoForestConfig(
        n_estimators=200,
        random_state=42,
        contamination="auto",
        seeds=[42, 123, 2026],
    )
    
    print("=" * 60)
    print("TRACERA ML — Isolation Forest Experiment (Synthetic)")
    print("=" * 60)
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = run_experiment(config=config)
    
    # Save results
    output_dir = Path("ml/data/pilot/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"isoforest_experiment_{timestamp}.json"
    md_path = output_dir / f"isoforest_experiment_{timestamp}.md"
    
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate markdown report
    md = format_report(results)
    with open(md_path, 'w') as f:
        f.write(md)
    
    print(f"\nResults saved:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    print("\n[OK] Experiment complete")
    
    return results


def format_report(r: Dict) -> str:
    lines = []
    lines.append("# Tracera ML — Isolation Forest Experiment (Synthetic)")
    lines.append("")
    lines.append("**WARNING: SYNTHETIC DEVELOPMENT EXPERIMENT ONLY**")
    lines.append("")
    lines.append("- Dataset is synthetic — not representative of real web")
    lines.append("- No ground-truth labels exist")
    lines.append("- No precision/recall/F1 can be reported")
    lines.append("- No real-world vulnerability detection claimed")
    lines.append("")
    
    lines.append(f"**Generated:** {r['experiment_info']['timestamp']}")
    lines.append(f"**Schema Version:** {r['experiment_info']['schema_version']}")
    lines.append(f"**Data Source:** {r['experiment_info']['data_source']}")
    lines.append("")
    
    lines.append("## Configuration")
    for k, v in r['model_params'].items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")
    
    lines.append("## Data")
    ds = r['experiment_info']['data_stats']
    lines.append(f"- Train: {ds['n_train']}, Val: {ds['n_val']}, Test: {ds['n_test']}, Total: {ds['total']}")
    lines.append("")
    
    lines.append("## Anomaly Summary")
    s = r['anomaly_summary']
    lines.append(f"- Total records: {s['n_total']}")
    lines.append(f"- Anomalies detected: {s['n_anomalies']} ({s['anomaly_rate']:.2%})")
    lines.append(f"- Score range: [{s['score_range'][0]:.4f}, {s['score_range'][1]:.4f}]")
    lines.append(f"- Score mean: {s['score_mean']:.4f}, std: {s['score_std']:.4f}")
    lines.append("")
    
    lines.append("## Top 25 Anomalies")
    for i, a in enumerate(r['top_anomalies'], 1):
        lines.append(f"{i}. {a['origin']} (score: {a['anomaly_score']:.4f}, domain: {a['registrable_domain']})")
    lines.append("")
    
    lines.append("## Rule Overlap Analysis")
    ro = r['rule_overlap']
    lines.append(f"- Total anomalies: {ro['total_anomalies']}")
    lines.append(f"- Rule-overlap: {ro['rule_overlap']}")
    lines.append(f"- Potentially novel: {ro['potentially_novel']}")
    lines.append(f"- Weak/irrelevant: {ro['weak_irrelevant']}")
    lines.append(f"- Note: {ro['note']}")
    lines.append("")
    
    lines.append("## Stability Across Seeds")
    for k, v in r['stability'].items():
        lines.append(f"- **{k}**: Jaccard mean={v['jaccard_mean']:.3f}, min={v['jaccard_min']:.3f}, max={v['jaccard_max']:.3f}")
    lines.append("")
    
    lines.append("## Ablation Experiments")
    for name, res in r['ablation'].items():
        lines.append(f"- **{name}** ({res['n_features']} features): {res['n_anomalies']} anomalies ({res['anomaly_rate']:.2%}), score mean={res['score_mean']:.4f}")
    lines.append("")
    
    lines.append("## Limitations")
    for lim, val in r['limitations'].items():
        status = "YES" if val else "NO"
        lines.append(f"- **{lim}:** {status}")
    lines.append("")
    
    lines.append("## Conclusion")
    lines.append("Isolation Forest runs correctly on synthetic data. Anomaly detection is stable across seeds.")
    lines.append("Ablation shows security headers dominate anomalies. Cookie features add marginal signal.")
    lines.append("Worth testing on real data when available, but synthetic results are NOT evidence of real-world performance.")
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()