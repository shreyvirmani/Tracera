#!/usr/bin/env python3
"""
Tracera ML Phase 6: Tiny Common Crawl WAT Pilot

Acquires a small Common Crawl WAT sample, processes it through the full ML pipeline,
and produces a validated dataset + EDA report.

Pipeline:
    Common Crawl WAT (stream)
        -> filter usable HTTP/HTML records
        -> extract schema_v1 features (17 features)
        -> normalize origin / registrable domain (eTLD+1)
        -> deduplicate by origin
        -> 70/15/15 leakage-safe split by eTLD+1
        -> Parquet output
        -> EDA/validation report

Usage:
    python ml/data/pilot.py --target-origins 1000 --max-records 50000
"""

import json
import gzip
import argparse
import sys
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Iterator
from urllib.parse import urlparse
from dataclasses import asdict

import pandas as pd

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.features.schema_v1 import (
    MLFeaturesV1,
    DatasetMetadata,
    ML_FEATURE_SCHEMA_VERSION,
    extract_ml_features_from_production,
    extract_metadata_from_production,
)
from ml.preprocessing.normalize import (
    normalize_origin,
    extract_registrable_domain,
)
from ml.preprocessing.dedupe import (
    deduplicate_by_origin,
    get_deduplication_stats,
    DeduplicationPolicy,
)
from ml.preprocessing.split import (
    leakage_safe_split,
    verify_no_leakage,
    get_split_stats,
    SplitConfig,
)


# =============================================================================
# WAT ACQUISITION
# =============================================================================

COMMON_CRAWL_BASE_URL = "https://data.commoncrawl.org"
DEFAULT_CRAWL_ID = "CC-MAIN-2026-34"  # August 2026 crawl (latest as of Sep 2026)


def find_wat_segment(crawl_id: str) -> Optional[str]:
    """
    Attempt to find a WAT segment URL for the given crawl.
    Returns the first WAT file URL found, or None if not accessible.
    """
    import requests
    
    # Try to list segments via the index API first
    index_url = f"https://index.commoncrawl.org/{crawl_id}-index"
    params = {"url": "example.com", "limit": 1, "fields": "filename"}
    
    try:
        r = requests.get(index_url, params=params, timeout=30)
        if r.status_code == 200:
            for line in r.text.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line.split(' ', 2)[2])
                        warc_filename = data.get('filename', '')
                        if warc_filename and 'warc/' in warc_filename:
                            # Convert WARC path to WAT path
                            wat_filename = warc_filename.replace('/warc/', '/wat/').replace('.warc.gz', '.warc.wat.gz')
                            return f"{COMMON_CRAWL_BASE_URL}/{wat_filename}"
                    except (json.JSONDecodeError, IndexError):
                        continue
    except Exception as e:
        print(f"Warning: Could not query index API: {e}")
    
    return None


def stream_wat_records(wat_url: str, max_records: int) -> Iterator[Dict[str, Any]]:
    """
    Stream WAT records from a gzipped WARC file.
    Yields parsed WAT records one at a time (memory efficient).
    
    Common Crawl WAT files are WARC files where each record contains
    HTTP response metadata as a JSON payload in the Envelope format.
    """
    import requests
    
    try:
        response = requests.get(wat_url, stream=True, timeout=60)
        response.raise_for_status()
        
        with gzip.open(response.raw, 'rb') as f:
            record_count = 0
            buffer = b''
            in_headers = True
            content_length = 0
            
            for chunk in iter(lambda: f.read(8192), b''):
                buffer += chunk
                
                while True:
                    if in_headers:
                        # Look for end of headers (double CRLF)
                        header_end = buffer.find(b'\r\n\r\n')
                        if header_end == -1:
                            break
                        
                        # Parse headers
                        header_block = buffer[:header_end].decode('utf-8', errors='replace')
                        buffer = buffer[header_end + 4:]  # Skip \r\n\r\n
                        
                        # Parse WARC headers
                        content_length = 0
                        warc_type = None
                        for line in header_block.split('\r\n'):
                            if line.startswith('Content-Length:'):
                                content_length = int(line.split(':', 1)[1].strip())
                            elif line.startswith('WARC-Type:'):
                                warc_type = line.split(':', 1)[1].strip()
                        
                        in_headers = False
                    
                    else:
                        # Reading payload
                        if len(buffer) >= content_length:
                            payload = buffer[:content_length]
                            buffer = buffer[content_length:]
                            
                            # Only process 'metadata' type records (the actual WAT records)
                            if warc_type == 'metadata' and content_length > 0:
                                try:
                                    payload_str = payload.decode('utf-8', errors='replace')
                                    record = json.loads(payload_str)
                                    yield record
                                    record_count += 1
                                    if record_count >= max_records:
                                        return
                                except (json.JSONDecodeError, UnicodeDecodeError):
                                    pass
                            
                            in_headers = True
                        else:
                            break
                        
    except Exception as e:
        print(f"Error streaming WAT: {e}")
        raise


def try_download_real_wat(crawl_id: str, max_records: int) -> List[Dict[str, Any]]:
    """
    Attempt to download and parse real Common Crawl WAT data.
    Returns list of WAT records, or empty list if failed.
    """
    print(f"Attempting to download real WAT data from crawl {crawl_id}...")
    
    wat_url = find_wat_segment(crawl_id)
    if not wat_url:
        print("  Could not find accessible WAT segment URL")
        return []
    
    print(f"  Found WAT segment: {wat_url}")
    
    try:
        records = list(stream_wat_records(wat_url, max_records))
        print(f"  Successfully downloaded {len(records)} records")
        return records
    except Exception as e:
        print(f"  Failed to download/parse WAT: {e}")
        return []


# =============================================================================
# WAT -> SCHEMA_V1 FEATURE EXTRACTION
# =============================================================================

def extract_features_from_wat(wat_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract schema_v1 features from a WAT record.
    Returns None if record is not usable (e.g., not HTML, missing critical fields).
    """
    try:
        envelope = wat_record.get('Envelope', {})
        warc_meta = envelope.get('WARC-Header-Metadata', {})
        payload_meta = envelope.get('Payload-Metadata', {})
        http_meta = payload_meta.get('HTTP-Response-Metadata', {})
        
        # Basic fields
        url = warc_meta.get('WARC-Target-URI', '')
        status_code = int(http_meta.get('Status', 0))
        headers = http_meta.get('Headers', {})
        
        # Normalize headers: WAT has lists, we want first value
        norm_headers = {}
        for k, v in headers.items():
            if isinstance(v, list) and v:
                norm_headers[k.lower()] = v[0]
            elif isinstance(v, str):
                norm_headers[k.lower()] = v
        
        # Filter: only successful HTML responses
        if status_code != 200:
            return None
        
        content_type = norm_headers.get('content-type', '')
        if not content_type.startswith('text/html'):
            return None
        
        # Extract schema_v1 features
        https_enabled = url.startswith('https://')
        
        # Security headers
        hsts_present = 'strict-transport-security' in norm_headers
        csp_present = 'content-security-policy' in norm_headers
        x_content_type_options_present = norm_headers.get('x-content-type-options', '').lower() == 'nosniff'
        x_frame_options_present = 'x-frame-options' in norm_headers
        referrer_policy_present = 'referrer-policy' in norm_headers
        permissions_policy_present = 'permissions-policy' in norm_headers
        
        # Cookies
        cookie_header = norm_headers.get('set-cookie', '')
        cookie_data = parse_cookie_header(cookie_header, url)
        
        # Tech disclosure
        server_header_present = 'server' in norm_headers
        server_header_value = norm_headers.get('server')
        x_powered_by_present = 'x-powered-by' in norm_headers
        x_powered_by_value = norm_headers.get('x-powered-by')
        
        # Build feature dict
        features = {
            'status_code': status_code,
            'is_html': 1,
            'https_enabled': 1 if https_enabled else 0,
            'hsts_present': 1 if hsts_present else 0,
            'csp_present': 1 if csp_present else 0,
            'x_content_type_options_present': 1 if x_content_type_options_present else 0,
            'x_frame_options_present': 1 if x_frame_options_present else 0,
            'referrer_policy_present': 1 if referrer_policy_present else 0,
            'permissions_policy_present': 1 if permissions_policy_present else 0,
            'cookie_count': cookie_data['count'],
            'cookie_secure_ratio': cookie_data['secure_ratio'],
            'cookie_httponly_ratio': cookie_data['httponly_ratio'],
            'cookie_samesite_strict_ratio': cookie_data['samesite_strict_ratio'],
            'cookie_samesite_lax_ratio': cookie_data['samesite_lax_ratio'],
            'cookie_samesite_none_ratio': cookie_data['samesite_none_ratio'],
            'server_header_present': 1 if server_header_present else 0,
            'x_powered_by_present': 1 if x_powered_by_present else 0,
        }
        
        # Metadata
        cookie_header = norm_headers.get('set-cookie', '')
        cookie_info_available = bool(cookie_header)
        metadata = {
            'url': url,
            'origin': normalize_origin(url),
            'registrable_domain': extract_registrable_domain(urlparse(url).hostname or ''),
            'crawl_timestamp': warc_meta.get('WARC-Date', ''),
            'warc_filename': warc_meta.get('WARC-Payload-Digest', ''),  # proxy
            'record_id': warc_meta.get('WARC-Record-ID', ''),
            'server_header_value': server_header_value,
            'x_powered_by_value': x_powered_by_value,
            'content_type': content_type,
            'cookie_info_available': cookie_info_available,
        }
        
        return {'features': features, 'metadata': metadata}
        
    except Exception as e:
        # Silently skip malformed records
        return None


def parse_cookie_header(set_cookie_header: str, response_url: str) -> Dict[str, float]:
    """Parse Set-Cookie header (same logic as production extractor)."""
    if not set_cookie_header:
        return {
            'count': 0,
            'secure_ratio': 0.0,
            'httponly_ratio': 0.0,
            'samesite_strict_ratio': 0.0,
            'samesite_lax_ratio': 0.0,
            'samesite_none_ratio': 0.0,
        }
    
    cookies = []
    for part in set_cookie_header.split(','):
        part = part.strip()
        if '=' in part:
            cookies.append(part)
    
    if not cookies:
        return {
            'count': 0, 'secure_ratio': 0.0, 'httponly_ratio': 0.0,
            'samesite_strict_ratio': 0.0, 'samesite_lax_ratio': 0.0,
            'samesite_none_ratio': 0.0,
        }
    
    secure_count = 0
    httponly_count = 0
    samesite_strict = 0
    samesite_lax = 0
    samesite_none = 0
    
    response_domain = urlparse(response_url).hostname or ''
    
    for cookie in cookies:
        cookie_lower = cookie.lower()
        if 'secure' in cookie_lower:
            secure_count += 1
        if 'httponly' in cookie_lower:
            httponly_count += 1
        if 'samesite=strict' in cookie_lower:
            samesite_strict += 1
        elif 'samesite=lax' in cookie_lower:
            samesite_lax += 1
        elif 'samesite=none' in cookie_lower:
            samesite_none += 1
    
    total = len(cookies)
    return {
        'count': total,
        'secure_ratio': secure_count / total if total else 0.0,
        'httponly_ratio': httponly_count / total if total else 0.0,
        'samesite_strict_ratio': samesite_strict / total if total else 0.0,
        'samesite_lax_ratio': samesite_lax / total if total else 0.0,
        'samesite_none_ratio': samesite_none / total if total else 0.0,
    }


# =============================================================================
# SYNTHETIC FALLBACK
# =============================================================================

def generate_synthetic_records(num_records: int, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate synthetic WAT-like records for testing when real data unavailable."""
    import random
    from ml.data.pilot.generate_synthetic_wat import generate_wat_record
    
    random.seed(seed)
    records = []
    for i in range(num_records):
        records.append(generate_wat_record(i, num_records))
    return records


# =============================================================================
# PIPELINE
# =============================================================================

def run_pilot(
    target_origins: int = 1000,
    max_records: int = 50000,
    crawl_id: str = DEFAULT_CRAWL_ID,
    output_dir: str = "ml/data/pilot",
    seed: int = 42,
    use_synthetic_fallback: bool = True,
) -> Dict[str, Any]:
    """
    Run the complete pilot pipeline.
    Returns summary statistics.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "raw").mkdir(exist_ok=True)
    (output_path / "processed").mkdir(exist_ok=True)
    (output_path / "reports").mkdir(exist_ok=True)
    
    print("=" * 60)
    print("TRACERA ML PHASE 6: COMMON CRAWL WAT PILOT")
    print("=" * 60)
    print(f"Target origins: {target_origins}")
    print(f"Max records to process: {max_records}")
    print(f"Crawl ID: {crawl_id}")
    print(f"Output dir: {output_dir}")
    print(f"Seed: {seed}")
    print()
    
    # Step 1: Acquire WAT records
    print("STEP 1: Acquiring WAT records...")
    wat_records = try_download_real_wat(crawl_id, max_records)
    
    used_real_data = len(wat_records) > 0
    
    if not used_real_data and use_synthetic_fallback:
        print("  Real WAT unavailable, using synthetic fallback...")
        warnings.warn(
            "Real Common Crawl WAT data could not be accessed. "
            "Using synthetic data for pipeline validation. "
            "Results are NOT representative of real web data.",
            UserWarning
        )
        wat_records = generate_synthetic_records(max_records, seed)
    elif not used_real_data:
        raise RuntimeError("Real WAT data unavailable and synthetic fallback disabled")
    
    print(f"  Total WAT records: {len(wat_records)}")
    
    # Step 2: Extract features
    print("\nSTEP 2: Extracting schema_v1 features...")
    feature_records = []
    metadata_records = []
    stats = {
        'total_wat_records': len(wat_records),
        'filtered_non_200': 0,
        'filtered_non_html': 0,
        'extraction_failed': 0,
        'usable_records': 0,
    }
    
    for record in wat_records:
        result = extract_features_from_wat(record)
        if result is None:
            # Determine why it was filtered
            envelope = record.get('Envelope', {})
            http_meta = envelope.get('Payload-Metadata', {}).get('HTTP-Response-Metadata', {})
            status = int(http_meta.get('Status', 0))
            headers = http_meta.get('Headers', {})
            content_type = ''
            for k, v in headers.items():
                if k.lower() == 'content-type' and isinstance(v, list) and v:
                    content_type = v[0]
                    break
            
            if status != 200:
                stats['filtered_non_200'] += 1
            elif not content_type.startswith('text/html'):
                stats['filtered_non_html'] += 1
            else:
                stats['extraction_failed'] += 1
            continue
        
        feature_records.append(result['features'])
        metadata_records.append(result['metadata'])
        stats['usable_records'] += 1
    
    print(f"  Usable records: {stats['usable_records']}")
    print(f"  Filtered (non-200): {stats['filtered_non_200']}")
    print(f"  Filtered (non-HTML): {stats['filtered_non_html']}")
    print(f"  Extraction failed: {stats['extraction_failed']}")
    
    if stats['usable_records'] == 0:
        raise RuntimeError("No usable records extracted!")
    
    # Step 3: Create DataFrames
    print("\nSTEP 3: Building DataFrames...")
    features_df = pd.DataFrame(feature_records)
    metadata_df = pd.DataFrame(metadata_records)
    
    # Ensure all 17 feature columns exist
    expected_features = MLFeaturesV1.feature_names()
    for feat in expected_features:
        if feat not in features_df.columns:
            features_df[feat] = 0
    
    # Reorder to match schema
    features_df = features_df[expected_features]
    
    # Step 4: Normalize origins
    print("\nSTEP 4: Normalizing origins...")
    metadata_df['origin'] = metadata_df['url'].apply(normalize_origin)
    metadata_df['registrable_domain'] = metadata_df['url'].apply(
        lambda u: extract_registrable_domain(urlparse(u).hostname or '')
    )
    
    # Step 5: Deduplicate
    print("\nSTEP 5: Deduplicating by origin...")
    combined_df = pd.concat([features_df, metadata_df], axis=1)
    
    # Compute dedupe stats BEFORE deduplication
    pre_dedupe_rows = len(combined_df)
    pre_dedupe_unique = combined_df['origin'].nunique()
    combined_df = deduplicate_by_origin(combined_df, origin_col='origin')
    post_dedupe_rows = len(combined_df)
    post_dedupe_unique = combined_df['origin'].nunique()
    duplicate_removed = pre_dedupe_rows - post_dedupe_rows
    duplicate_rate = duplicate_removed / pre_dedupe_rows if pre_dedupe_rows > 0 else 0.0
    
    dedupe_stats = {
        'total_rows': pre_dedupe_rows,
        'unique_origins': pre_dedupe_unique,
        'unique_origins_after_dedupe': post_dedupe_unique,
        'duplicate_rows': duplicate_removed,
        'duplication_rate': duplicate_rate,
        'origins_with_duplicates': pre_dedupe_rows - pre_dedupe_unique,
        'max_duplicates_per_origin': pre_dedupe_rows - pre_dedupe_unique,
    }
    
    print(f"  Input records: {pre_dedupe_rows}")
    print(f"  Unique origins before dedupe: {pre_dedupe_unique}")
    print(f"  Records after dedupe: {post_dedupe_rows}")
    print(f"  Unique origins after dedupe: {post_dedupe_unique}")
    print(f"  Duplicate records removed: {duplicate_removed}")
    print(f"  Duplicate rate: {duplicate_rate:.2%}")
    
    # Step 6: Grouped split
    print("\nSTEP 6: Leakage-safe grouped split...")
    config = SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=seed)
    train_df, val_df, test_df = leakage_safe_split(combined_df, config)
    
    # Verify no leakage
    assert verify_no_leakage(train_df, val_df, test_df, group_col='registrable_domain')
    
    split_stats = get_split_stats(train_df, val_df, test_df, group_col='registrable_domain')
    print(f"  Train: {split_stats['train_rows']} rows, {split_stats['train_groups']} groups")
    print(f"  Val:   {split_stats['val_rows']} rows, {split_stats['val_groups']} groups")
    print(f"  Test:  {split_stats['test_rows']} rows, {split_stats['test_groups']} groups")
    print(f"  Leakage-free: {split_stats['leakage_free']}")
    
    # Step 7: Save outputs
    print("\nSTEP 7: Saving outputs...")
    
    # Save processed dataset (features + metadata)
    for name, df in [('train', train_df), ('val', val_df), ('test', test_df)]:
        out_path = output_path / "processed" / f"{name}.parquet"
        df.to_parquet(out_path, index=False)
        print(f"  Saved {name}: {out_path} ({len(df)} rows)")
    
    # Save full dataset
    full_path = output_path / "processed" / "full.parquet"
    combined_df.to_parquet(full_path, index=False)
    print(f"  Saved full dataset: {full_path}")
    
    # Step 8: EDA Report
    print("\nSTEP 8: Generating EDA report...")
    report = generate_eda_report(
        combined_df, train_df, val_df, test_df,
        stats, dedupe_stats, split_stats,
        used_real_data, crawl_id, seed
    )
    
    report_path = output_path / "reports" / "pilot_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Report saved: {report_path}")
    
    # Also save human-readable markdown
    md_path = output_path / "reports" / "pilot_report.md"
    with open(md_path, 'w') as f:
        f.write(format_report_markdown(report))
    print(f"  Markdown report: {md_path}")
    
    print("\n" + "=" * 60)
    print("PILOT COMPLETE")
    print("=" * 60)
    
    return report


def generate_eda_report(
    full_df: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    extract_stats: Dict,
    dedupe_stats: Dict,
    split_stats: Dict,
    used_real_data: bool,
    crawl_id: str,
    seed: int,
) -> Dict[str, Any]:
    """Generate comprehensive EDA report."""
    
    feature_cols = MLFeaturesV1.feature_names()
    
    # HTTP stats
    http_dist = full_df['status_code'].value_counts().to_dict() if 'status_code' in full_df else {}
    https_pct = (full_df['https_enabled'].mean() * 100) if 'https_enabled' in full_df else 0
    html_pct = (full_df['is_html'].mean() * 100) if 'is_html' in full_df else 0
    
    # Security headers
    header_cols = ['hsts_present', 'csp_present', 'x_content_type_options_present',
                   'x_frame_options_present', 'referrer_policy_present', 'permissions_policy_present']
    header_stats = {}
    for col in header_cols:
        if col in full_df.columns:
            present = int(full_df[col].sum())
            total = len(full_df)
            header_stats[col] = {
                'present': present,
                'absent': total - present,
                'present_pct': round(present / total * 100, 1) if total > 0 else 0,
            }
    
    # Cookies
    cookie_stats = {}
    if 'cookie_count' in full_df.columns:
        cookie_stats['origins_with_cookies'] = int((full_df['cookie_count'] > 0).sum())
        cookie_stats['cookie_count_distribution'] = full_df['cookie_count'].value_counts().to_dict()
        for ratio_col in ['cookie_secure_ratio', 'cookie_httponly_ratio',
                          'cookie_samesite_strict_ratio', 'cookie_samesite_lax_ratio',
                          'cookie_samesite_none_ratio']:
            if ratio_col in full_df.columns:
                cookie_stats[ratio_col] = {
                    'mean': round(float(full_df[ratio_col].mean()), 3),
                    'median': round(float(full_df[ratio_col].median()), 3),
                    'min': round(float(full_df[ratio_col].min()), 3),
                    'max': round(float(full_df[ratio_col].max()), 3),
                }
    
    # Tech disclosure
    disclosure_stats = {}
    for col in ['server_header_present', 'x_powered_by_present']:
        if col in full_df.columns:
            disclosure_stats[col] = {
                'present': int(full_df[col].sum()),
                'present_pct': round(float(full_df[col].mean() * 100), 1),
            }
    
    # Domain/platform concentration
    domain_stats = {}
    if 'registrable_domain' in full_df.columns:
        domain_counts = full_df['registrable_domain'].value_counts()
        domain_stats['unique_registrable_domains'] = len(domain_counts)
        domain_stats['top_20_domains'] = domain_counts.head(20).to_dict()
        domain_stats['top_20_pct_of_total'] = round(
            domain_counts.head(20).sum() / len(full_df) * 100, 1
        )
        
        # Platform concentration (cloud platforms)
        cloud_platforms = ['github.io', 'herokuapp.com', 'azurewebsites.net', 
                          'blogspot.com', 'netlify.app', 'vercel.app', 'pages.dev',
                          'firebaseapp.com', 'amazonaws.com', 'googleusercontent.com']
        platform_counts = {}
        for platform in cloud_platforms:
            count = sum(1 for d in full_df['registrable_domain'] if d == platform or d.endswith('.' + platform))
            if count > 0:
                platform_counts[platform] = count
        domain_stats['cloud_platform_concentration'] = platform_counts
    
    # Missingness
    missingness = {}
    for col in full_df.columns:
        missing = int(full_df[col].isna().sum())
        if missing > 0:
            missingness[col] = {
                'missing_count': missing,
                'missing_pct': round(missing / len(full_df) * 100, 1),
            }
    
    # Feature quality checks
    quality_checks = {}
    for col in feature_cols:
        if col in full_df.columns:
            checks = {}
            if full_df[col].dtype in ['int64', 'float64']:
                checks['dtype'] = str(full_df[col].dtype)
                checks['min'] = float(full_df[col].min())
                checks['max'] = float(full_df[col].max())
                # Binary features should be 0/1
                if col not in ['status_code', 'cookie_count']:
                    unique_vals = set(full_df[col].unique())
                    checks['is_binary'] = unique_vals.issubset({0, 1, 0.0, 1.0})
                    if not checks['is_binary']:
                        checks['unexpected_values'] = list(unique_vals - {0, 1, 0.0, 1.0})
                # Ratios should be in [0,1]
                if 'ratio' in col:
                    checks['in_range'] = (full_df[col].min() >= 0) and (full_df[col].max() <= 1)
            quality_checks[col] = checks
    
    report = {
        'pilot_info': {
            'timestamp': datetime.now().isoformat(),
            'used_real_common_crawl_data': used_real_data,
            'crawl_id': crawl_id,
            'seed': seed,
            'schema_version': ML_FEATURE_SCHEMA_VERSION,
        },
        'dataset_summary': {
            'total_wat_records_processed': extract_stats['total_wat_records'],
            'usable_records': extract_stats['usable_records'],
            'unique_origins_before_dedupe': dedupe_stats['unique_origins'],
            'unique_origins_after_dedupe': dedupe_stats.get('unique_origins_after_dedupe', dedupe_stats['unique_origins'] - dedupe_stats.get('duplicate_rows', 0)),
            'duplicate_rate': round(dedupe_stats['duplication_rate'], 4),
            'duplicate_records_removed': dedupe_stats.get('duplicate_rows', 0),
            'filtering': {
                'non_200_filtered': extract_stats['filtered_non_200'],
                'non_html_filtered': extract_stats['filtered_non_html'],
                'extraction_failed': extract_stats['extraction_failed'],
            },
        },
        'split_summary': split_stats,
        'http_distribution': http_dist,
        'https_percentage': round(https_pct, 1),
        'html_percentage': round(html_pct, 1),
        'security_headers': header_stats,
        'cookie_statistics': cookie_stats,
        'technology_disclosure': disclosure_stats,
        'domain_concentration': domain_stats,
        'missingness': missingness,
        'feature_quality_checks': quality_checks,
        'sanity_checks': {
            'no_duplicate_origins': full_df['origin'].nunique() == len(full_df),
            'no_eTLD1_leakage': split_stats['leakage_free'],
            'duplicate_rate_reasonable': dedupe_stats['duplication_rate'] < 1.0,
            'binary_features_are_binary': all(
                qc.get('is_binary', True) for qc in quality_checks.values() if 'is_binary' in qc
            ),
            'ratios_in_range': all(
                qc.get('in_range', True) for qc in quality_checks.values() if 'in_range' in qc
            ),
            'cookie_count_non_negative': (full_df['cookie_count'] >= 0).all() if 'cookie_count' in full_df else True,
            'status_codes_valid': full_df['status_code'].between(100, 599).all() if 'status_code' in full_df else True,
        },
    }
    
    return report


def format_report_markdown(report: Dict) -> str:
    """Format report as human-readable Markdown."""
    lines = []
    
    lines.append("# Tracera ML Phase 6: Common Crawl WAT Pilot Report")
    lines.append("")
    lines.append(f"**Generated:** {report['pilot_info']['timestamp']}")
    lines.append(f"**Schema Version:** {report['pilot_info']['schema_version']}")
    lines.append(f"**Real Common Crawl Data:** {'YES' if report['pilot_info']['used_real_common_crawl_data'] else 'NO (synthetic fallback)'}")
    lines.append(f"**Crawl ID:** {report['pilot_info']['crawl_id']}")
    lines.append(f"**Seed:** {report['pilot_info']['seed']}")
    lines.append("")
    
    # Dataset Summary
    lines.append("## Dataset Summary")
    ds = report['dataset_summary']
    lines.append(f"- **Total WAT records processed:** {ds['total_wat_records_processed']:,}")
    lines.append(f"- **Usable records (200 OK + HTML):** {ds['usable_records']:,}")
    lines.append(f"- **Unique origins before dedupe:** {ds.get('unique_origins_before_dedupe', ds['unique_origins_after_dedupe']):,}")
    lines.append(f"- **Unique origins after dedupe:** {ds['unique_origins_after_dedupe']:,}")
    lines.append(f"- **Duplicate rate:** {ds['duplicate_rate']:.2%}")
    lines.append(f"- **Duplicate records removed:** {ds.get('duplicate_records_removed', 0):,}")
    lines.append(f"- **Filtered (non-200):** {ds['filtering']['non_200_filtered']:,}")
    lines.append(f"- **Filtered (non-HTML):** {ds['filtering']['non_html_filtered']:,}")
    lines.append(f"- **Extraction failed:** {ds['filtering']['extraction_failed']:,}")
    lines.append("")
    
    # Split Summary
    lines.append("## Split Summary (70/15/15 by eTLD+1)")
    ss = report['split_summary']
    lines.append(f"- **Train:** {ss['train_rows']:,} rows, {ss['train_groups']:,} groups ({ss['train_group_ratio']:.1%})")
    lines.append(f"- **Val:**   {ss['val_rows']:,} rows, {ss['val_groups']:,} groups ({ss['val_group_ratio']:.1%})")
    lines.append(f"- **Test:**  {ss['test_rows']:,} rows, {ss['test_groups']:,} groups ({ss['test_group_ratio']:.1%})")
    lines.append(f"- **Leakage-free:** {'[OK]' if ss['leakage_free'] else '[FAIL]'}")
    lines.append("")
    
    # HTTP
    lines.append("## HTTP")
    lines.append(f"- **HTTPS:** {report['https_percentage']:.1f}%")
    lines.append(f"- **HTML:** {report['html_percentage']:.1f}%")
    lines.append(f"- **Status codes:** {report['http_distribution']}")
    lines.append("")
    
    # Security Headers
    lines.append("## Security Headers")
    for header, stats in report['security_headers'].items():
        lines.append(f"- **{header}:** {stats['present']:,} present ({stats['present_pct']:.1f}%), {stats['absent']:,} absent")
    lines.append("")
    
    # Cookies
    lines.append("## Cookies")
    cs = report['cookie_statistics']
    if cs:
        lines.append(f"- **Origins with cookies:** {cs.get('origins_with_cookies', 'N/A')}")
        if 'cookie_count_distribution' in cs:
            lines.append(f"- **Cookie count distribution:** {cs['cookie_count_distribution']}")
        for ratio, stats in cs.items():
            if ratio.endswith('_ratio'):
                lines.append(f"- **{ratio}:** mean={stats['mean']:.3f}, median={stats['median']:.3f}, range=[{stats['min']:.3f}, {stats['max']:.3f}]")
    lines.append("")
    
    # Tech Disclosure
    lines.append("## Technology Disclosure")
    for header, stats in report['technology_disclosure'].items():
        lines.append(f"- **{header}:** {stats['present']:,} ({stats['present_pct']:.1f}%)")
    lines.append("")
    
    # Domain Concentration
    lines.append("## Domain Concentration")
    dc = report['domain_concentration']
    lines.append(f"- **Unique eTLD+1 domains:** {dc.get('unique_registrable_domains', 'N/A')}")
    lines.append(f"- **Top 20 domains cover:** {dc.get('top_20_pct_of_total', 'N/A'):.1f}% of dataset")
    lines.append(f"- **Cloud platform concentration:**")
    for platform, count in dc.get('cloud_platform_concentration', {}).items():
        lines.append(f"  - {platform}: {count:,}")
    lines.append("")
    
    # Missingness
    lines.append("## Missingness")
    for col, stats in report['missingness'].items():
        lines.append(f"- **{col}:** {stats['missing_count']:,} ({stats['missing_pct']:.1f}%)")
    if not report['missingness']:
        lines.append("- None")
    lines.append("")
    
    # Sanity Checks
    lines.append("## Sanity Checks")
    for check, passed in report['sanity_checks'].items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        lines.append(f"- **{check}:** {status}")
    lines.append("")
    
    # Feature Quality
    lines.append("## Feature Quality Checks")
    for feat, checks in report['feature_quality_checks'].items():
        if checks:
            issues = []
            if not checks.get('is_binary', True):
                issues.append(f"non-binary values: {checks.get('unexpected_values', [])}")
            if not checks.get('in_range', True):
                issues.append("ratio out of [0,1] range")
            if issues:
                lines.append(f"- **{feat}:** {'; '.join(issues)}")
            else:
                lines.append(f"- **{feat}:** OK")
    lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Tracera ML Phase 6: Tiny Common Crawl WAT Pilot"
    )
    parser.add_argument("--target-origins", type=int, default=1000,
                        help="Target number of unique origins (default: 1000)")
    parser.add_argument("--max-records", type=int, default=50000,
                        help="Maximum WAT records to process (default: 50000)")
    parser.add_argument("--crawl-id", default=DEFAULT_CRAWL_ID,
                        help=f"Common Crawl crawl ID (default: {DEFAULT_CRAWL_ID})")
    parser.add_argument("--output-dir", default="ml/data/pilot",
                        help="Output directory (default: ml/data/pilot)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--no-synthetic-fallback", action="store_true",
                        help="Fail if real WAT data unavailable")
    
    args = parser.parse_args()
    
    try:
        report = run_pilot(
            target_origins=args.target_origins,
            max_records=args.max_records,
            crawl_id=args.crawl_id,
            output_dir=args.output_dir,
            seed=args.seed,
            use_synthetic_fallback=not args.no_synthetic_fallback,
        )
        print("\n[OK] Pilot completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] Pilot failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()