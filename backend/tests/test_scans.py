from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestCreateScan:
    def test_valid_url_returns_scan_id(self):
        with (
            patch("app.api.v1.scans.check_ssrf") as mock_ssrf,
            patch("app.api.v1.scans.collect", new_callable=AsyncMock) as mock_collect,
        ):
            from app.collector.collector import CollectorResponse
            from app.core.ssrf_guard import ResolvedIP

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

            response = client.post("/api/v1/scans", json={"url": "https://example.com"})

            assert response.status_code == 200
            data = response.json()
            assert "scan_id" in data
            assert data["status"] == "completed"
            assert data["metadata"] is not None
            assert data["metadata"]["status_code"] == 200
            assert data["metadata"]["content_length"] == 17

    def test_invalid_scheme_returns_error(self):
        response = client.post("/api/v1/scans", json={"url": "ftp://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "INVALID_SCHEME"

    def test_invalid_hostname_returns_error(self):
        response = client.post("/api/v1/scans", json={"url": "https://invalid..hostname"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "INVALID_HOSTNAME"

    def test_empty_url_returns_validation_error(self):
        response = client.post("/api/v1/scans", json={"url": ""})

        assert response.status_code == 422

    def test_missing_url_returns_validation_error(self):
        response = client.post("/api/v1/scans", json={})

        assert response.status_code == 422

    @patch("app.api.v1.scans.check_ssrf")
    def test_ssrf_loopback_blocked(self, mock_ssrf):
        from app.core.ssrf_guard import SSRFGuardError

        mock_ssrf.side_effect = SSRFGuardError(
            "Loopback address blocked: 127.0.0.1",
            "LOOPBACK_BLOCKED",
            "127.0.0.1",
        )

        response = client.post("/api/v1/scans", json={"url": "http://localhost"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "LOOPBACK_BLOCKED"

    @patch("app.api.v1.scans.check_ssrf")
    def test_ssrf_private_ip_blocked(self, mock_ssrf):
        from app.core.ssrf_guard import SSRFGuardError

        mock_ssrf.side_effect = SSRFGuardError(
            "Private address blocked: 192.168.1.1",
            "PRIVATE_ADDRESS_BLOCKED",
            "192.168.1.1",
        )

        response = client.post("/api/v1/scans", json={"url": "http://192.168.1.1"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "PRIVATE_ADDRESS_BLOCKED"

    @patch("app.api.v1.scans.check_ssrf")
    @patch("app.api.v1.scans.collect", new_callable=AsyncMock)
    def test_collector_timeout(self, mock_collect, mock_ssrf):
        from app.collector.collector import CollectorError
        from app.core.ssrf_guard import ResolvedIP

        mock_ssrf.return_value = ResolvedIP("8.8.8.8", 4, False, False, False, False, False)
        mock_collect.side_effect = CollectorError("Request timed out", "TIMEOUT")

        response = client.post("/api/v1/scans", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "TIMEOUT"

    @patch("app.api.v1.scans.check_ssrf")
    @patch("app.api.v1.scans.collect", new_callable=AsyncMock)
    def test_collector_too_many_redirects(self, mock_collect, mock_ssrf):
        from app.collector.collector import CollectorError
        from app.core.ssrf_guard import ResolvedIP

        mock_ssrf.return_value = ResolvedIP("8.8.8.8", 4, False, False, False, False, False)
        mock_collect.side_effect = CollectorError("Too many redirects", "TOO_MANY_REDIRECTS")

        response = client.post("/api/v1/scans", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "TOO_MANY_REDIRECTS"

    @patch("app.api.v1.scans.check_ssrf")
    @patch("app.api.v1.scans.collect", new_callable=AsyncMock)
    def test_collector_response_too_large(self, mock_collect, mock_ssrf):
        from app.collector.collector import CollectorError
        from app.core.ssrf_guard import ResolvedIP

        mock_ssrf.return_value = ResolvedIP("8.8.8.8", 4, False, False, False, False, False)
        mock_collect.side_effect = CollectorError(
            "Response size exceeds limit",
            "RESPONSE_TOO_LARGE",
        )

        response = client.post("/api/v1/scans", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "RESPONSE_TOO_LARGE"
