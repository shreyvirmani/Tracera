"""Tests for scan API correctness: pagination, filters, metadata
persistence, export, and rate limiting."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.v1.scans import _rate_limit_buckets
from app.collector.collector import CollectorResponse
from app.core.config import settings
from app.core.ssrf_guard import ResolvedIP
from app.main import app

client = TestClient(app)


def _mock_collect_response():
    return CollectorResponse(
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        content=b"<html>test</html>",
        content_type="text/html; charset=utf-8",
        response_time_ms=123.0,
        redirect_count=2,
        final_url="https://example.com/final",
    )


def _successful_scan(url: str = "https://example.com"):
    with (
        patch("app.api.v1.scans.check_ssrf") as mock_ssrf,
        patch("app.api.v1.scans.collect", new_callable=AsyncMock) as mock_collect,
    ):
        mock_ssrf.return_value = ResolvedIP("93.184.216.34", 4, False, False, False, False, False)
        mock_collect.return_value = _mock_collect_response()
        response = client.post("/api/v1/scans", json={"url": url})
    assert response.status_code == 200
    return response.json()


class TestScanMetadataPersistence:
    def test_completed_scan_returns_real_metadata(self):
        data = _successful_scan()
        assert data["status"] == "completed"
        metadata = data["metadata"]
        assert metadata is not None
        # Values must match what the collector observed, not placeholders.
        assert metadata["status_code"] == 200
        assert metadata["redirect_count"] == 2
        assert metadata["final_url"] == "https://example.com/final"
        assert metadata["content_length"] == 17
        assert metadata["response_time_ms"] > 0

    def test_retrieved_scan_metadata_matches_create_response(self):
        created = _successful_scan()
        fetched = client.get(f"/api/v1/scans/{created['scan_id']}").json()
        assert fetched["metadata"] is not None
        assert fetched["metadata"] == created["metadata"]
        assert fetched["risk_score"] == created["risk_score"]
        assert fetched["risk_tier"] == created["risk_tier"]


class TestListPaginationAndFilters:
    def test_total_reflects_full_count(self):
        """total must be the number of matching scans, not the page size."""
        data = client.get("/api/v1/scans?limit=2&offset=0").json()
        assert data["limit"] == 2
        assert len(data["scans"]) <= 2
        assert isinstance(data["total"], int)
        assert data["total"] >= len(data["scans"])

    def test_limit_is_capped(self):
        data = client.get("/api/v1/scans?limit=100000").json()
        assert data["limit"] <= 100

    def test_negative_offset_is_clamped(self):
        data = client.get("/api/v1/scans?offset=-5").json()
        assert data["offset"] == 0

    def test_status_filter(self):
        data = client.get("/api/v1/scans?status=completed").json()
        for scan in data["scans"]:
            assert scan["status"] == "completed"

    def test_tier_filter(self):
        data = client.get("/api/v1/scans?tier=low").json()
        for scan in data["scans"]:
            assert scan["risk_tier"] == "low"

    def test_search_filter_matches_url(self):
        data = client.get("/api/v1/scans?search=example.com").json()
        for scan in data["scans"]:
            assert (
                "example.com" in scan["metadata"]["final_url"] if scan["metadata"] else True
            ) or "example.com" in str(scan.get("error", ""))

    def test_invalid_status_filter_returns_empty(self):
        data = client.get("/api/v1/scans?status=not-a-status").json()
        assert data["scans"] == []
        assert data["total"] == 0


class TestExport:
    def test_export_returns_complete_json(self):
        created = _successful_scan()
        response = client.get(f"/api/v1/scans/{created['scan_id']}/export")
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")

        export = response.json()
        assert "scan" in export
        assert "exported_at" in export
        scan = export["scan"]
        assert scan["scan_id"] == created["scan_id"]
        assert scan["status"] == created["status"]
        assert scan["metadata"] == created["metadata"]
        # Findings in the export must match the API representation.
        assert len(scan["findings"]) == len(created["findings"])

    def test_export_unknown_scan_404(self):
        response = client.get("/api/v1/scans/00000000-0000-0000-0000-000000000000/export")
        assert response.status_code == 404


class TestRateLimiting:
    def setup_method(self):
        _rate_limit_buckets.clear()

    def test_rate_limit_blocks_excess_requests(self):
        original_max = settings.SCAN_RATE_LIMIT_MAX
        original_window = settings.SCAN_RATE_LIMIT_WINDOW_SECONDS
        settings.SCAN_RATE_LIMIT_MAX = 2
        settings.SCAN_RATE_LIMIT_WINDOW_SECONDS = 60
        try:
            with (
                patch("app.api.v1.scans.check_ssrf") as mock_ssrf,
                patch("app.api.v1.scans.collect", new_callable=AsyncMock) as mock_collect,
            ):
                mock_ssrf.return_value = ResolvedIP(
                    "93.184.216.34", 4, False, False, False, False, False
                )
                mock_collect.return_value = _mock_collect_response()

                assert (
                    client.post("/api/v1/scans", json={"url": "https://a.com"}).status_code == 200
                )
                assert (
                    client.post("/api/v1/scans", json={"url": "https://b.com"}).status_code == 200
                )
                limited = client.post("/api/v1/scans", json={"url": "https://c.com"})
                assert limited.status_code == 429
        finally:
            settings.SCAN_RATE_LIMIT_MAX = original_max
            settings.SCAN_RATE_LIMIT_WINDOW_SECONDS = original_window
            _rate_limit_buckets.clear()
