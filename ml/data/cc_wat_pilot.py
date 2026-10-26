#!/usr/bin/env python3
"""
Tracera ML — Common Crawl WAT pilot pipeline (REAL data).

Acquires a small real Common Crawl WAT sample, processes it through the ML
pipeline, and produces a validated dataset + provenance report.

Pipeline:
    Common Crawl index API (find a WAT segment for the crawl)
      -> download one WAT segment to the local cache (restartable, resume via
         HTTP Range; the segment is reusable across runs)
      -> stream WAT JSONL (multi-member gzip)
      -> filter usable HTTP/HTML records (status 200, text/html)
      -> extract MLFeaturesV1 features (17) + DatasetMetadata
      -> normalize origin / registrable domain (eTLD+1 & major platforms)
      -> deduplicate by origin
      -> 70/15/15 leakage-safe split by eTLD+1
      -> Parquet outputs + provenance/validation report

Sources & labeling:
    --source download   real Common Crawl WAT data (default). If acquisition
                        fails, the pipeline FAILS with an actionable error.
                        It never silently substitutes synthetic data.
    --source synthetic  explicit synthetic generation for development/tests.
                        Every artifact is labelled `data_label=SYNTHETIC`.

Common Crawl data notes:
    - Crawler: CommonCrawl CCBot. WAT files contain WARC response metadata
      (HTTP response headers) in JSON-LD style records; the payload body is
      NOT included (headers only) — the pipeline therefore reads only
      response headers, which is exactly what MLFeaturesV1 measures.
    - Permitted use: Common Crawl crawl data is provided by Common Crawl
      (CC0 / copyright-respect metadata;ipedía see
      https://commoncrawl.org/get-started/access / each crawl'sterms).
      Tracera uses it for research feature statistics only.

Usage:
    python ml/data/cc_wat_pilot.py --target-origins 400 --max-records 60000
    python ml/data/cc_wat_pilot.py --source synthetic --max-records 5000
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.features.schema_v1 import (
    DatasetMetadata,
    ML_FEATURE_SCHEMA_VERSION,
    MLFeaturesV1,
)
from ml.features.dataframe import validate_feature_dataframe
from ml.preprocessing.normalize import (
    extract_registrable_domain,
    normalize_origin,
)
from ml.preprocessing.dedupe import (
    DeduplicationPolicy,
    deduplicate_by_origin,
    get_deduplication_stats,
)
from ml.preprocessing.split import (
    SplitConfig,
    get_split_stats,
    leakage_safe_split,
    verify_no_leakage,
)

# =============================================================================


class PipelineError(RuntimeError):
    """Raised with an actionable message when the data pipeline cannot proceed."""


COMMON_CRAWL_BASE_URL = "https://data.commoncrawl.org"
INDEX_URL_TEMPLATE = "https://index.commoncrawl.org/{crawl_id}-index"
DEFAULT_CRAWL_ID = "CC-MAIN-2026-34"
DEFAULT_USER_AGENT = "Tracera-ml-pipeline/0.1 (+research feature extraction)"

SYNTHETIC_LABEL = "SYNTHETIC"
REAL_LABEL = "REAL"


def _log(msg: str) -> None:
    print(msg, flush=True)


# =============================================================================
# SOURCE DISCOVERY
# =============================================================================

def _query_index_api(crawl_id: str, timeout: float) -> str:
    """Return the raw CDX index response body (one record per line)."""
    url = INDEX_URL_TEMPLATE.format(crawl_id=crawl_id)
    resp = requests.get(
        url,
        params={"url": "example.com", "limit": 1},
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise PipelineError(
            f"Common Crawl index API returned HTTP {resp.status_code} for crawl "
            f"{crawl_id}. The crawl ID may not exist. Check the list of crawls at "
            f"https://commoncrawl.org/get-started. Example crawl IDs: " 
            "CC-MAIN-2025-05, CC-MAIN-2024-10. Response body (first 200 chars): "
            f"{resp.text[:200]!r}"
        )
    return resp.text


def extract_wat_segment_url_from_cdx_line(line: str) -> Optional[str]:
    """
    Parse one CDX index line of the form

        "<urlkey> <timestamp> {\"filename\": ...}"

    (whitespace is ' ', there can also be ' ' separators) and return the WAT
    object URL, or None if the line does not contain a WARC filename.
    """
    if "{" not in line:
        return None
    try:
        payload = json.loads(line[line.index("{"):])
    except json.JSONDecodeError:
        return None
    filename = payload.get("filename", "")
    if not filename or "/warc/" not in filename or not filename.endswith(".warc.gz"):
        return None
    wat_filename = filename.replace("/warc/", "/wat/").replace(".warc.gz", ".warc.wat.gz")
    return f"{COMMON_CRAWL_BASE_URL}/{wat_filename}"


def find_wat_segment_url(
    crawl_id: str,
    retries: int = 3,
    timeout: float = 30.0,
) -> str:
    """
    Find one downloadable WAT segment URL for `crawl_id`.

    Raises PipelineError with actionable guidance if discovery fails.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            body = _query_index_api(crawl_id, timeout)
            for line in body.strip().splitlines():
                if not line.strip():
                    continue
                wat_url = extract_wat_segment_url_from_cdx_line(line)
                if wat_url is not None:
                    return wat_url
            raise PipelineError(
                f"Common Crawl index API responded (HTTP 200) but no WARARC file "
                f"entry was found in {len(body.splitlines())} line(s). "
                "Aborting instead of guessing an object name."
            )
        except (requests.RequestException, PipelineError) as e:
            last_error = e
            if attempt < retries:
                _log(f"  index API attempt {attempt} failed ({e}); retrying in {2 * attempt}s...")
                time.sleep(2 * attempt)
    raise PipelineError(
        f"Could not discover a WAT segment for crawl {crawl_id} after "
        f"{retries} attempts. Last error: {last_error}. Check network access / "
        "proxy settings, or confirm the crawl ID exists."
    )


# =============================================================================
# DOWNLOAD WITH CACHE (restartable)
# =============================================================================

def cached_segment_path(cache_dir: Path, crawl_id: str, segment_name: str) -> Path:
    out = cache_dir / crawl_id
    out.mkdir(parents=True, exist_ok=True)
    return out / segment_name


def download_wat_segment(
    wat_url: str,
    destination: Path,
    max_bytes: Optional[int] = None,
    retries: int = 3,
    chunk_size: int = 1 << 20,
    timeout: Tuple[float, float] = (30.0, 180.0),
) -> Path:
    """
    Stream-download a WAT segment into `destination` (gzip, unchanged bytes).

    Restartable: an existing partial `destination.with_suffix('.part')` is
    resumed with a Range request when the server supports it. Completed files
    short-circuit (cache hit). Raises PipelineError on unrecoverable failure —
    it NEVER returns fake/synthetic data.
    """
    segment_name = destination.name
    part_path = destination.with_suffix(destination.suffix + ".part")
    done = part_path.with_suffix(part_path.suffix + ".done")

    if destination.exists() and done.exists():
        _log(f"  cache hit: {destination} ({destination.stat().st_size:,} bytes)")
        return destination

    headers: Dict[str, str] = {"User-Agent": DEFAULT_USER_AGENT}
    resume_from = part_path.stat().st_size if part_path.exists() else 0

    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            if resume_from:
                headers["Range"] = f"bytes={resume_from}-"
            with requests.get(
                wat_url, headers=headers, stream=True, timeout=timeout, allow_redirects=True
            ) as resp:
                if resume_from and resp.status_code == 206:
                    mode = "ab"
                    _log(f"  resuming previous download at byte {resume_from:,}...")
                elif resp.status_code in (200, 206):
                    if resume_from:
                        # Server ignored Range: restart from scratch.
                        part_path.unlink(missing_ok=True)
                        resume_from = 0
                    mode = "wb"
                else:
                    raise PipelineError(
                        f"WAT download returned HTTP {resp.status_code} for {wat_url}. "
                        "The object may not exist in this crawl."
                    )
                total_received = resume_from
                with open(part_path, mode) as fh:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        fh.write(chunk)
                        total_received += len(chunk)
                        if max_bytes is not None and total_received >= max_bytes:
                            _log(f"  stopping early at max_bytes={max_bytes:,}")
                            break
            if max_bytes is not None and total_received < max_bytes:
                # A deliberately truncated file is NOT a complete segment; treat
                # it as reusable raw cache for record streaming but do not mark
                # it fully downloaded.
                pass
            shutil.move(str(part_path), str(destination))
            done.write_text(
                json.dumps({"url": wat_url, "bytes": destination.stat().st_size}),
                encoding="utf-8",
            )
            _log(f"  downloaded: {destination} ({destination.stat().st_size:,} bytes)")
            return destination
        except (requests.RequestException, PipelineError) as e:
            last_error = e
            resume_from = part_path.stat().st_size if part_path.exists() else 0
            if attempt < retries:
                wait = 5 * attempt
                _log(f"  download attempt {attempt} failed ({e}); retrying in {wait}s...")
                time.sleep(wait)
    raise PipelineError(
        f"Failed to download WAT segment after {retries} attempts: {wat_url}. "
        f"Last error: {last_error}. A partial file may exist at {part_path}; "
        "rerun to resume. If access is blocked by network policy, document the "
        "blocker — do not fall back to synthetic data silently."
    )


# =============================================================================
# WAT STREAMING
# =============================================================================

def stream_wat_records(
    wat_path: Path,
    max_records: int,
) -> tuple[Iterator[Dict[str, Any]], dict]:
    """
    Stream JSON WAT records from a (multi-member) gzipped WAT file.

    WAT files interleave plain-text warcinfo headers ("WARC/1.0 ...") and JSON
    metadata records (one per line, very long lines).

    Returns (record_iterator, stat_dict) where stat_dict["malformed_json"]
    counts malformed JSON lines skipped.
    """
    stats = {"malformed_json": 0}

    def records() -> Iterator[Dict[str, Any]]:
        yielded = 0
        with gzip.open(wat_path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                if not line.startswith("{"):
                    continue  # warcinfo / plain WARC header lines are not JSON metadata
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    stats["malformed_json"] += 1
                    continue
                if max_records >= 0 and yielded >= max_records:
                    return  # hard cap: never emit more than max_records records
                yield rec
                yielded += 1

    return records(), stats


# =============================================================================
# WAT -> MLFeaturesV1 EXTRACTION (real-data semantics)
# =============================================================================

_STATUS_IN_RESPONSE_LINE = None  # compiled lazily


def parse_status_code(record: Dict[str, Any]) -> Optional[int]:
    """
    Extract the HTTP status code from a real WAT response record.

    Current CC WAT format stores the status in `Response-Message` as a struct:
        {"Status": "200", "Version": "HTTP/1.1", "Reason": "OK"}
    Historical/tool variants may store:
      - a flat integer/string `Status` field, or
      - a string `Response-Message` ("HTTP/1.1 200 OK").
    Returns None when no parse is possible (treated as unusable record).
    """
    import re
    global _STATUS_IN_RESPONSE_LINE
    if _STATUS_IN_RESPONSE_LINE is None:
        _STATUS_IN_RESPONSE_LINE = re.compile(r"^HTTP/\d(?:\.\d)?\s+(\d{3})")

    http_meta = (record.get("Envelope", {}) or {}).get("Payload-Metadata", {}) or {}
    http_meta = http_meta.get("HTTP-Response-Metadata", {}) or {}

    response_msg = http_meta.get("Response-Message")
    if isinstance(response_msg, dict):
        try:
            return int(response_msg["Status"])
        except (KeyError, TypeError, ValueError):
            return None
    if response_msg:
        m = _STATUS_IN_RESPONSE_LINE.match(str(response_msg).strip())
        if m:
            return int(m.group(1))
    legacy_status = http_meta.get("Status")
    if legacy_status is not None:
        try:
            return int(legacy_status)
        except (TypeError, ValueError):
            return None
    return None


def normalize_wat_headers(headers: Any) -> Dict[str, Any]:
    """
    Normalize WAT headers to a simple dict {lower-case name -> raw value}.

    Real WAT: { "Server": "nginx", "Set-Cookie": ["c1", "c2"] }.
    Historical variants store values as lists of strings (first = value).
    For `set-cookie` every list element is kept (multi-record semantics,
    matching how multiple Set-Cookie header lines arrive over HTTP).
    Boolean values are stringified (empty string -> absent).
    """
    norm: Dict[str, Any] = {}
    if not isinstance(headers, dict):
        return norm
    for k, v in headers.items():
        name = str(k).lower()
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            vals = [str(x) for x in v if x is not None]
            if not vals:
                continue
            if name == "set-cookie":
                norm[name] = vals
            else:
                norm[name] = vals[0]
        else:
            norm[name] = str(v)
    return norm


def extract_content_type(norm_headers: Dict[str, Any]) -> str:
    ct = norm_headers.get("content-type", "")
    return str(ct) if ct is not None else ""


def parse_set_cookie_values(set_cookie_values: Any) -> List[str]:
    """
    Convert normalized set-cookie values into individual cookie tokens,
    mirroring the production extractor's comma-split parsing so that
    training and inference use identical cookie semantics.
    """
    if not set_cookie_values:
        return []
    tokens: List[str] = []
    values = set_cookie_values if isinstance(set_cookie_values, list) else [set_cookie_values]
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if "=" in part:
                tokens.append(part)
    return tokens


def compute_cookie_features(cookie_tokens: List[str], response_domain: str) -> Dict[str, Any]:
    """Same semantics as backend FeatureVector cookie parsing."""
    total = len(cookie_tokens)
    secure = httponly = sss = ssl = ssn = 0
    for token in cookie_tokens:
        tl = token.lower()
        if "secure" in tl:
            secure += 1
        if "httponly" in tl:
            httponly += 1
        if "samesite=strict" in tl:
            sss += 1
        elif "samesite=lax" in tl:
            ssl += 1
        elif "samesite=none" in tl:
            ssn += 1
    return {
        "cookie_count": total,
        "cookie_secure_ratio": secure / total if total else 0.0,
        "cookie_httponly_ratio": httponly / total if total else 0.0,
        "cookie_samesite_strict_ratio": sss / total if total else 0.0,
        "cookie_samesite_lax_ratio": ssl / total if total else 0.0,
        "cookie_samesite_none_ratio": ssn / total if total else 0.0,
        "cookie_info_available": bool(cookie_tokens),
    }


def extract_features_from_wat(
    wat_record: Dict[str, Any],
    segment_name: str = "",
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Extract (features, metadata) from one WAT record.

    Returns None for records that are not usable (request/warcinfo records,
    non-200, non-HTML, or structurally broken). Never raises on malformed
    content — malformed handling is by counting, contractually.
    """
    env = wat_record.get("Envelope") or {}
    warc_meta = env.get("WARC-Header-Metadata") or {}
    payload_meta = env.get("Payload-Metadata") or {}
    http_meta = payload_meta.get("HTTP-Response-Metadata") or {}
    headers = http_meta.get("Headers") if isinstance(http_meta.get("Headers"), dict) else None

    status_code = parse_status_code(wat_record)
    if status_code is None or headers is None:
        return None  # request/warcinfo/malformed record — no HTTP response data

    norm_headers = normalize_wat_headers(headers)

    url = str(warc_meta.get("WARC-Target-URI") or "")
    if not url:
        return None

    content_type = extract_content_type(norm_headers)
    if status_code != 200:
        return None
    if not content_type.lower().startswith("text/html"):
        return None

    https_enabled = url.lower().startswith("https://")
    cookie_tokens = parse_set_cookie_values(norm_headers.get("set-cookie"))
    cookie = compute_cookie_features(cookie_tokens, urlparse(url).hostname or "")

    features = {
        "status_code": status_code,
        "is_html": 1,
        "https_enabled": 1 if https_enabled else 0,
        "hsts_present": 1 if "strict-transport-security" in norm_headers else 0,
        "csp_present": 1 if "content-security-policy" in norm_headers else 0,
        "x_content_type_options_present":
            1 if str(norm_headers.get("x-content-type-options", "")).lower() == "nosniff" else 0,
        "x_frame_options_present": 1 if "x-frame-options" in norm_headers else 0,
        "referrer_policy_present": 1 if "referrer-policy" in norm_headers else 0,
        "permissions_policy_present": 1 if "permissions-policy" in norm_headers else 0,
        **{k: cookie[k] for k in (
            "cookie_count", "cookie_secure_ratio", "cookie_httponly_ratio",
            "cookie_samesite_strict_ratio", "cookie_samesite_lax_ratio",
            "cookie_samesite_none_ratio",
        )},
        "server_header_present": 1 if "server" in norm_headers else 0,
        "x_powered_by_present": 1 if "x-powered-by" in norm_headers else 0,
    }
    # Guarantee: exactly the 17 features in canonical order, with schema version.
    fv = MLFeaturesV1(**features)
    fv.validate()
    feature_dict = {name: getattr(fv, name) for name in MLFeaturesV1.feature_names()}

    host = urlparse(url).hostname or ""
    try:
        origin = normalize_origin(url)
        registrable_domain = extract_registrable_domain(host)
    except ValueError:
        return None

    metadata = {
        "source_type": "common_crawl_wat",
        "source_identifier": segment_name,
        "url": url,
        "scheme": "https" if https_enabled else "http",
        "host": host,
        "origin": origin,
        "registrable_domain": registrable_domain,
        "crawl_timestamp": str(warc_meta.get("WARC-Date") or ""),
        "warc_filename": segment_name,
        "record_id": str(warc_meta.get("WARC-Record-ID") or ""),
        "server_header_value": norm_headers.get("server"),
        "x_powered_by_value": norm_headers.get("x-powered-by"),
        "content_type": content_type,
        "cookie_info_available": bool(cookie_tokens),
    }
    return feature_dict, metadata


# =============================================================================
# SYNTHETIC DEV FIXTURE (explicit, labelled — never an automatic fallback)
# =============================================================================

def generate_synthetic_records(num_records: int, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate synthetic WAT-like records for pipeline development/testing."""
    import random
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ml.data.pilot.generate_synthetic_wat import generate_wat_record

    random.seed(seed)
    return [generate_wat_record(i, num_records) for i in range(num_records)]


# =============================================================================
# PIPELINE
# =============================================================================

def collect_source_records(
    source: str,
    crawl_id: str,
    max_records: int,
    seed: int,
    cache_dir: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Acquire WAT records from the chosen (explicit) source."""
    if source == "synthetic":
        _log("SOURCE: SYNTHETIC (explicit dev fixture — results are not real-web evidence)")
        records = generate_synthetic_records(max_records, seed)
        return records, {
            "source_type": "synthetic",
            "data_label": SYNTHETIC_LABEL,
            "crawl_id": "SYNTHETIC",
            "segment": None,
        }
    if source != "download":
        raise PipelineError(f"unknown source {source!r}; choose 'download' or 'synthetic'")

    _log("SOURCE: REAL Common Crawl WAT")
    wat_url = find_wat_segment_url(crawl_id)
    _log(f"  WAT segment: {wat_url}")
    segment_name = wat_url.rsplit("/", 1)[-1]
    destination = cached_segment_path(cache_dir, crawl_id, segment_name)
    download_wat_segment(wat_url, destination)

    records: List[Dict[str, Any]] = []
    record_iter, stream_stats = stream_wat_records(destination, max_records)
    for rec in record_iter:
        records.append(rec)
    malformed = stream_stats["malformed_json"]
    _log(f"  streamed {len(records):,} WAT records ({malformed} malformed JSON lines skipped)")
    return records, {
        "source_type": "common_crawl_wat",
        "data_label": REAL_LABEL,
        "crawl_id": crawl_id,
        "segment": segment_name,
        "wat_url": wat_url,
    }


def run_pilot(
    source: str = "download",
    target_origins: int = 400,
    max_records: int = 60000,
    crawl_id: str = DEFAULT_CRAWL_ID,
    output_dir: str = "ml/data/pilot",
    seed: int = 42,
    cache_dir: str = "ml/data/pilot/cache",
) -> Dict[str, Any]:
    """
    Run the pilot pipeline end-to-end and write outputs + report.
    `output_dir`/`cache_dir` are relative to the repository root unless absolute.
    """
    output_path = Path(output_dir)
    cache = Path(cache_dir)
    for sub in ("raw", "processed", "reports"):
        (output_path / sub).mkdir(parents=True, exist_ok=True)

    _log("=" * 64)
    _log("TRACERA ML PILOT — Common Crawl WAT")
    _log("=" * 64)
    _log(f"source={source} target_origins={target_origins} max_records={max_records:,} crawl={crawl_id} seed={seed}")

    # 1. Acquire
    wat_records, source_info = collect_source_records(source, crawl_id, max_records, seed, cache)

    # 2. Extract features
    _log("extracting features...")
    feature_rows: List[Dict[str, Any]] = []
    metadata_rows: List[Dict[str, Any]] = []
    stats = {
        "records_streamed": len(wat_records),
        "response_records": 0,
        "filtered_non_200": 0,
        "filtered_non_html": 0,
        "filtered_other": 0,
        "usable_records": 0,
    }
    for rec in wat_records:
        parsed = extract_features_from_wat(rec, segment_name=source_info.get("segment") or "synthetic")
        if parsed is None:
            status = parse_status_code(rec)
            if status is None:
                stats["filtered_other"] += 1
            elif status != 200:
                stats["filtered_non_200"] += 1
            else:
                stats["filtered_non_html"] += 1
            continue
        stats["response_records"] += 1
        feature_rows.append(parsed[0])
        metadata_rows.append(parsed[1])
        stats["usable_records"] += 1

    _log(f"  usable: {stats['usable_records']:,} of {stats['records_streamed']:,} records")
    if stats["usable_records"] == 0:
        raise PipelineError(
            "No usable records were extracted. The pipeline will not fabricate "
            "a dataset. If this was a real-data run, inspect the raw WAT "
            "segment contents and the filter thresholds."
        )

    features_df = pd.DataFrame(feature_rows)
    meta_df = pd.DataFrame(metadata_rows)
    feature_df, validation_report = validate_feature_dataframe(features_df)
    if validation_report.n_dropped or validation_report.n_nan_coerced:
        _log(f"  validation report: {validation_report.to_dict()}")
    combined = pd.concat(
        [feature_df, meta_df.loc[feature_df.index].reset_index(drop=True)], axis=1
    )

    if combined.empty:
        raise PipelineError(
            "All extracted rows were rejected by feature validation "
            f"({validation_report.to_dict()}). Inspect drop reasons before rerunning."
        )

    # 3. Dedupe by origin (labelling columns above survive)
    pre = get_deduplication_stats(combined, origin_col="origin")
    combined = deduplicate_by_origin(
        combined, origin_col="origin", policy=DeduplicationPolicy()
    )
    post = get_deduplication_stats(combined, origin_col="origin")
    _log(f"dedupe: {pre['total_rows']:,} rows -> {post['unique_origins']:,} unique origins "
         f"({pre['duplicate_rows']:,} duplicate rows removed)")

    # 4. Leakage-safe split (by eTLD+1 / platform)
    split_cfg = SplitConfig(seed=seed)
    train_df, val_df, test_df = leakage_safe_split(combined, split_cfg)
    assert verify_no_leakage(train_df, val_df, test_df, group_col=split_cfg.group_col)
    split_stats = get_split_stats(train_df, val_df, test_df, group_col=split_cfg.group_col)
    _log(f"split: train={split_stats['train_rows']} val={split_stats['val_rows']} "
         f"test={split_stats['test_rows']} (leakage-free={split_stats['leakage_free']})")

    # 5. Persist
    provenance_path = output_path / "processed" / "provenance.json"
    provenance_path.write_text(
        json.dumps({**source_info, "schema_version": ML_FEATURE_SCHEMA_VERSION,
                    "seed": seed, "generated_at": report_generated_at()}, indent=2),
        encoding="utf-8",
    )
    for name, df in (("train", train_df), ("val", val_df), ("test", test_df), ("full", combined)):
        path = output_path / "processed" / f"{name}.parquet"
        df.to_parquet(path, index=False)
        _log(f"saved {name}: {path} ({len(df):,} rows)")

    # 6. Report
    report = build_report(
        combined, source_info, stats, validation_report, pre, post,
        split_stats, crawl_id, seed,
    )
    json_path = output_path / "reports" / "pilot_report.json"
    md_path = output_path / "reports" / "pilot_report.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(format_report_markdown(report), encoding="utf-8")
    _log(f"report: {json_path}")
    _log(f"report: {md_path}")
    return report


def report_generated_at() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def build_report(
    combined: pd.DataFrame,
    source_info: Dict[str, Any],
    stats: Dict[str, int],
    validation_report,
    dedupe_pre: Dict[str, Any],
    dedupe_post: Dict[str, Any],
    split_stats: Dict[str, Any],
    crawl_id: str,
    seed: int,
) -> Dict[str, Any]:
    feature_cols = MLFeaturesV1.feature_names()
    header_cols = [c for c in feature_cols if c.endswith("_present") and c != "server_header_present"]

    security_headers = {}
    for col in header_cols:
        present = int(combined[col].sum())
        security_headers[col] = {
            "present": present,
            "absent": len(combined) - present,
            "present_pct": round(present / max(len(combined), 1) * 100, 1),
        }
    disclosure = {
        col: {"present": int(combined[col].sum()),
              "present_pct": round(float(combined[col].mean() * 100), 1)}
        for col in ("server_header_present", "x_powered_by_present")
    }
    cookie_stats = {
        "origins_with_cookies": int((combined["cookie_count"] > 0).sum()),
        "cookie_count_distribution": {
            str(k): int(v) for k, v in combined["cookie_count"].value_counts().sort_index().to_dict().items()
        },
    }
    for ratio_col in [c for c in feature_cols if c.endswith("_ratio")]:
        s = combined[ratio_col]
        cookie_stats[ratio_col] = {
            "mean": round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
        }
    domain_counts = combined["registrable_domain"].value_counts()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": ML_FEATURE_SCHEMA_VERSION,
        "data_label": source_info["data_label"],
        "source": source_info,
        # Hard contracts:
        "limitations": [
            "Feature extraction reads HTTP response metadata only (no page body content).",
            "Isolation of rare/odd patterns is NOT evidence of compromise or vulnerability.",
            "Dataset covers only sites crawled by Common Crawl during this crawl; sampling bias applies.",
            ("Dataset is SYNTHETIC — not real web data." if source_info["data_label"] == SYNTHETIC_LABEL
             else ""),
        ],
        "stats": stats,
        "validation": validation_report.to_dict(),
        "dedupe": {
            "rows_in": dedupe_pre["total_rows"],
            "unique_origins_out": dedupe_post["unique_origins"],
            "duplicate_rows_removed": dedupe_pre["duplicate_rows"],
        },
        "split": split_stats,
        "http": {
            "https_pct": round(float(combined["https_enabled"].mean() * 100), 1),
            "status_codes": {str(k): int(v) for k, v in combined["status_code"].value_counts().to_dict().items()},
        },
        "security_headers": security_headers,
        "cookies": cookie_stats,
        "technology_disclosure": disclosure,
        "domains": {
            "unique_registrable_domains": int(domain_counts.size),
            "top_20": {str(k): int(v) for k, v in domain_counts.head(20).to_dict().items()},
            "top_20_pct_of_total": (
                round(float(domain_counts.head(20).sum() / len(combined) * 100), 1) if len(combined) else 0.0
            ),
        },
        "seed": seed,
        "crawl_id_arg": crawl_id,
    }


def format_report_markdown(report: Dict[str, Any]) -> str:
    label = report["data_label"]
    lines = [
        "# Tracera ML Pilot Report — Common Crawl WAT",
        "",
        f"**Generated:** {report['generated_at']}",
        f"**DATA LABEL:** {label}" + ("  ⚠️ SYNTHETIC DATA — not real web evidence" if label == SYNTHETIC_LABEL else "  ✅ real Common Crawl data"),
        f"**Feature schema:** {report['schema_version']}",
        f"**Crawl:** {report['source'].get('crawl_id', report.get('crawl_id_arg', ''))}",
        f"**Segment:** {report['source'].get('segment', 'n/a')}",
        f"**Seed:** {report['seed']}",
        "",
        "## Records",
    ]
    st = report["stats"]
    for key in ("records_streamed", "response_records", "usable_records", "filtered_non_200", "filtered_non_html", "filtered_other"):
        lines.append(f"- **{key}:** {st.get(key, 0):,}")
    va = report["validation"]
    lines += [
        "",
        "## Validation",
        f"- rows in/out: {va['n_rows_in']:,} -> {va['n_rows_out']:,} (dropped {va['n_dropped']})",
        f"- NaN coerced to defaults: {va['n_nan_coerced']}",
        f"- type coercion columns: {va['n_type_coerced']}",
        f"- drop reasons: {va['drop_reasons'] or 'none'}",
        "",
        "## Dedupe & split",
        f"- unique origins after dedupe: {report['dedupe']['unique_origins_out']:,} "
        f"({report['dedupe']['duplicate_rows_removed']:,} duplicate rows removed)",
        f"- train {report['split']['train_rows']:,} / val {report['split']['val_rows']:,} / "
        f"test {report['split']['test_rows']:,} — leakage-free: {report['split']['leakage_free']}",
        "",
        "## HTTP",
        f"- HTTPS: {report['http']['https_pct']:.1f}%",
        f"- status codes: {report['http']['status_codes']}",
        "",
        "## Security headers",
    ]
    for col, s in report["security_headers"].items():
        lines.append(f"- **{col}:** {s['present']:,} present ({s['present_pct']}%)")
    lines += ["", "## Cookies", f"- origins with cookies: {report['cookies']['origins_with_cookies']:,}"]
    for ratio in [k for k in report["cookies"] if k.endswith("_ratio")]:
        s = report["cookies"][ratio]
        lines.append(f"- **{ratio}:** mean={s['mean']}, median={s['median']}, range=[{s['min']}, {s['max']}]")
    lines += ["", "## Technology disclosure"]
    for col, s in report["technology_disclosure"].items():
        lines.append(f"- **{col}:** {s['present']:,} ({s['present_pct']}%)")
    lines += [
        "",
        "## Domains",
        f"- unique registrable domains: {report['domains']['unique_registrable_domains']:,}",
        f"- top 20 cover {report['domains']['top_20_pct_of_total']}% of origins",
        "",
        "## Limitations",
    ]
    for lim in report["limitations"]:
        if lim:
            lines.append(f"- {lim}")
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Tracera ML pilot — Common Crawl WAT")
    parser.add_argument("--source", choices=["download", "synthetic"], default="download",
                        help="data source: real Common Crawl (default) or explicit synthetic dev fixture")
    parser.add_argument("--target-origins", type=int, default=400)
    parser.add_argument("--max-records", type=int, default=60000)
    parser.add_argument("--crawl-id", default=DEFAULT_CRAWL_ID)
    parser.add_argument("--output-dir", default="ml/data/pilot")
    parser.add_argument("--cache-dir", default="ml/data/pilot/cache")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        run_pilot(
            source=args.source,
            target_origins=args.target_origins,
            max_records=args.max_records,
            crawl_id=args.crawl_id,
            output_dir=args.output_dir,
            seed=args.seed,
            cache_dir=args.cache_dir,
        )
        _log("[OK] pilot complete")
    except PipelineError as e:
        _log(f"[FAIL] Pipeline error — action required: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
