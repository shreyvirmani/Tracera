import pytest
from unittest.mock import AsyncMock, patch

from app.collector.collector import CollectorResponse
from app.core.ssrf_guard import ResolvedIP, SSRFGuardError
from app.collector.collector import CollectorError


class TestCreateScan:
    @pytest.mark.asyncio
    @patch("app.api.v1.scans.collect", new_callable=AsyncMock)
    @patch("app.api.v1.scans.check_ssrf")
    async def test_valid_url_returns_scan_id(self, mock_ssrf, mock_collect, client):
        mock_ssrf.return_value = ResolvedIP("8.8.8.8", 4, False, False, False, False, False)
        mock_collect.return_value = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html>test</html>",
            content_type="text/html",
            response_time_ms=100.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        response = await client.post("/api/v1/scans", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data
        assert data["status"] == "completed"
        assert data["metadata"] is not None
        assert data["metadata"]["status_code"] == 200
        assert data["metadata"]["content_length"] == 17

    @pytest.mark.asyncio
    async def test_invalid_scheme_returns_error(self, client):
        response = await client.post("/api/v1/scans", json={"url": "ftp://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "INVALID_SCHEME"

    @pytest.mark.asyncio
    async def test_invalid_hostname_returns_error(self, client):
        response = await client.post("/api/v1/scans", json={"url": "https://invalid..hostname"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "INVALID_HOSTNAME"

    @pytest.mark.asyncio
    async def test_empty_url_returns_validation_error(self, client):
        response = await client.post("/api/v1/scans", json={"url": ""})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_url_returns_validation_error(self, client):
        response = await client.post("/api/v1/scans", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.api.v1.scans.check_ssrf")
    async def test_ssrf_loopback_blocked(self, mock_ssrf, client):
        mock_ssrf.side_effect = SSRFGuardError(
            "Loopback address blocked: 127.0.0.1",
            "LOOPBACK_BLOCKED",
            "127.0.0.1",
        )

        response = await client.post("/api/v1/scans", json={"url": "http://localhost"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "LOOPBACK_BLOCKED"

    @pytest.mark.asyncio
    @patch("app.api.v1.scans.check_ssrf")
    async def test_ssrf_private_ip_blocked(self, mock_ssrf, client):
        mock_ssrf.side_effect = SSRFGuardError(
            "Private address blocked: 192.168.1.1",
            "PRIVATE_ADDRESS_BLOCKED",
            "192.168.1.1",
        )

        response = await client.post("/api/v1/scans", json={"url": "http://192.168.1.1"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "PRIVATE_ADDRESS_BLOCKED"

    @pytest.mark.asyncio
    @patch("app.api.v1.scans.collect", new_callable=AsyncMock)
    @patch("app.api.v1.scans.check_ssrf")
    async def test_collector_timeout(self, mock_ssrf, mock_collect, client):
        mock_ssrf.return_value = ResolvedIP("8.8.8.8", 4, False, False, False, False, False)
        mock_collect.side_effect = CollectorError("Request timed out", "TIMEOUT")

        response = await client.post("/api/v1/scans", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "TIMEOUT"

    @pytest.mark.asyncio
    @patch("app.api.v1.scans.collect", new_callable=AsyncMock)
    @patch("app.api.v1.scans.check_ssrf")
    async def test_collector_too_many_redirects(self, mock_ssrf, mock_collect, client):
        mock_ssrf.return_value = ResolvedIP("8.8.8.8", 4, False, False, False, False, False)
        mock_collect.side_effect = CollectorError("Too many redirects", "TOO_MANY_REDIRECTS")

        response = await client.post("/api/v1/scans", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "TOO_MANY_REDIRECTS"

    @pytest.mark.asyncio
    @patch("app.api.v1.scans.collect", new_callable=AsyncMock)
    @patch("app.api.v1.scans.check_ssrf")
    async def test_collector_response_too_large(self, mock_ssrf, mock_collect, client):
        mock_ssrf.return_value = ResolvedIP("8.8.8.8", 4, False, False, False, False, False)
        mock_collect.side_effect = CollectorError(
            "Response size exceeds limit",
            "RESPONSE_TOO_LARGE",
        )

        response = await client.post("/api/v1/scans", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "RESPONSE_TOO_LARGE"