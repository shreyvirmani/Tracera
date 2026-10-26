"""
Data pipeline tests (Phase B/F) — fully local; no network required.

Uses small hand-built WAT-shaped fixtures (the same structure Common Crawl
produces) to test parsing, filtering, cookie semantics, and CDX handling.
Network behaviour is only exercised when TRACERA_NET_TESTS=1 is set.
"""

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from ml.data.cc_wat_pilot import (
    extract_wat_segment_url_from_cdx_line,
    extract_features_from_wat,
    normalize_wat_headers,
    parse_set_cookie_values,
    parse_status_code,
    stream_wat_records,
    compute_cookie_features,
    PipelineError,
)
from ml.features.schema_v1 import MLFeaturesV1


def response_record(url="https://books.example.org/", headers=None, status="200"):
    return {
        "Envelope": {
            "WARC-Header-Metadata": {
                "WARC-Type": "response",
                "WARC-Target-URI": url,
                "WARC-Date": "2026-08-07T10:31:31Z",
                "WARC-Record-ID": "<urn:uuid:test>",
            },
            "Payload-Metadata": {
                "HTTP-Response-Metadata": {
                    "Response-Message": {"Status": status, "Version": "HTTP/1.1", "Reason": "OK"},
                    "Headers": headers or {},
                }
            },
        }
    }


HTML_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Server": "nginx/1.18.0",
    "Set-Cookie": ["a=1; Secure; HttpOnly; SameSite=Strict", "b=2; path=/"],
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": ["nosniff"],
}


class TestCDXParsing:
    def test_cdx_line_with_filename(self):
        line = 'com,example)/ 20260807104456 ' + json.dumps(
            {"filename": "crawl-data/CC-MAIN-2026-34/segments/x/warc/CC-MAIN-000.warc.gz"}
        )
        url = extract_wat_segment_url_from_cdx_line(line)
        assert url is not None
        assert url.endswith("/wat/CC-MAIN-000.warc.wat.gz")

    def test_cdx_line_without_json(self):
        assert extract_wat_segment_url_from_cdx_line("garbage") is None

    def test_cdx_line_missing_filename(self):
        assert extract_wat_segment_url_from_cdx_line(
            'k ts ' + json.dumps({"filename": ""})
        ) is None


class TestStatusParsing:
    def test_struct_response_message(self):
        assert parse_status_code(response_record()) == 200

    def test_string_response_message(self):
        rec = {
            "Envelope": {
                "Payload-Metadata": {
                    "HTTP-Response-Metadata": {
                        "Response-Message": "HTTP/1.1 200 OK", "Headers": {}
                    }
                }
            }
        }
        assert parse_status_code(rec) == 200

    def test_legacy_status_field(self):
        rec = {
            "Envelope": {
                "Payload-Metadata": {"HTTP-Response-Metadata": {"Status": "301", "Headers": {}}}
            }
        }
        assert parse_status_code(rec) == 301

    def test_missing_everything(self):
        assert parse_status_code({"Envelope": {"Payload-Metadata": {}}}) is None


class TestHeaderNormalization:
    def test_set_cookie_list_preserved(self):
        norm = normalize_wat_headers({"Set-Cookie": ["a=1", "b=2"], "Server": "nginx"})
        assert norm["set-cookie"] == ["a=1", "b=2"]
        assert norm["server"] == "nginx"

    def test_scalar_value_first(self):
        norm = normalize_wat_headers({"X-Content-Type-Options": ["nosniff"]})
        assert norm["x-content-type-options"] == "nosniff"

    def test_empty_values_dropped(self):
        assert normalize_wat_headers({"Server": None, "X-Nil": []}) == {}


class TestCookieSemantics:
    def test_multiple_cookies_mixed_flags(self):
        tokens = parse_set_cookie_values(["a=1; Secure; HttpOnly; SameSite=Strict", "b=2; path=/"])
        cf = compute_cookie_features(tokens, "example.org")
        assert cf["cookie_count"] == 2
        assert cf["cookie_secure_ratio"] == pytest.approx(0.5)
        assert cf["cookie_httponly_ratio"] == pytest.approx(0.5)
        assert cf["cookie_samesite_strict_ratio"] == pytest.approx(0.5)
        assert cf["cookie_info_available"] is True

    def test_no_cookies(self):
        cf = compute_cookie_features([], "example.org")
        assert cf["cookie_count"] == 0
        assert cf["cookie_info_available"] is False

    def test_matches_production_semantics(self):
        # Production parser splits combined Set-Cookie headers on commas; both
        # forms must yield identical ratios.
        combined = "a=1; Secure, b=2; HttpOnly"
        from_split = compute_cookie_features(parse_set_cookie_values([combined]), "x.com")
        from_list = compute_cookie_features(parse_set_cookie_values(["a=1; Secure", "b=2; HttpOnly"]), "x.com")
        assert from_split == from_list


class TestRecordFiltering:
    def test_html_200_extracted(self):
        out = extract_features_from_wat(response_record(headers=HTML_HEADERS), "seg")
        assert out is not None
        feats, meta = out
        assert len(feats) == 17
        assert feats["https_enabled"] == 1
        assert feats["hsts_present"] == 1
        assert feats["x_content_type_options_present"] == 1
        assert feats["server_header_present"] == 1
        assert feats["cookie_count"] == 2
        assert meta["registrable_domain"] == "example.org"
        assert meta["warc_filename"] == "seg"

    def test_non_200_filtered(self):
        rec = response_record(headers=HTML_HEADERS, status="404")
        out = extract_features_from_wat(rec, "seg")
        assert out is None

    def test_non_html_filtered(self):
        rec = response_record(headers={k: v for k, v in HTML_HEADERS.items() if k != "Content-Type"} |
                              {"Content-Type": "application/json"})
        assert extract_features_from_wat(rec, "seg") is None

    def test_request_record_skipped(self):
        rec = {"Envelope": {"WARC-Header-Metadata": {"WARC-Type": "request"},
                            "Payload-Metadata": {"HTTP-Request-Metadata": {}}}}
        assert extract_features_from_wat(rec, "seg") is None

    def test_http_site_flag(self):
        rec = response_record(url="http://old.example.com/", headers=HTML_HEADERS)
        feats, _ = extract_features_from_wat(rec, "seg")
        assert feats["https_enabled"] == 0

    def test_output_is_schema_valid(self):
        feats, _ = extract_features_from_wat(response_record(headers=HTML_HEADERS), "seg")
        MLFeaturesV1(**feats).validate()


class TestStreamRecords:
    def test_malformed_json_counted(self, tmp_path):
        # Build a tiny multi-member gzip WAT-ish file.
        import gzip

        p = tmp_path / "seg.warc.wat.gz"
        with gzip.open(p, "wt", encoding="utf-8") as fh:
            fh.write("WARC/1.0\nWARC-Type: warcinfo\n\n")
            fh.write(json.dumps(response_record(headers=HTML_HEADERS)) + "\n")
            fh.write("{not json\n")
        it, stats = stream_wat_records(p, 100)
        records = list(it)
        assert len(records) == 1
        assert stats["malformed_json"] == 1

        # max_records cut-off works
        it2, _ = stream_wat_records(p, 0)
        assert list(it2) == []


@pytest.mark.skipif(
    os.getenv("TRACERA_NET_TESTS", "") != "1",
    reason="network test — enable with TRACERA_NET_TESTS=1",
)
class TestDiscoveryNetwork:
    def test_real_index_discovery(self):
        from ml.data.cc_wat_pilot import find_wat_segment_url

        url = find_wat_segment_url("CC-MAIN-2026-34", retries=1)
        assert url.endswith(".warc.wat.gz")


class TestNoSilentFallback:
    def test_unknown_source_raises(self):
        from ml.data.cc_wat_pilot import collect_source_records

        with pytest.raises(PipelineError):
            collect_source_records("fake-source", "x", 10, 42, Path("."))
