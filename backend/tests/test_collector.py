import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.collector.safe_collector import fetch, CollectorError
from app.core.url_validator import ValidatedURL


class TestSafeCollector:
    @pytest.mark.asyncio
    async def test_fetch_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html", "server": "nginx"}
        mock_response.content = b"<html><body>Hello</body></html>"
        mock_response.is_redirect = False

        validated_url = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        with patch("app.collector.safe_collector.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            with patch("app.collector.safe_collector._get_tls_info", return_value=None):
                response = await fetch(validated_url)

        assert response.status_code == 200
        assert response.content == b"<html><body>Hello</body></html>"
        assert response.redirect_count == 0
        assert response.error is None

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        validated_url = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        import httpx
        with patch("app.collector.safe_collector.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            with pytest.raises(CollectorError) as exc:
                await fetch(validated_url)
            assert exc.value.code == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_fetch_too_many_redirects(self):
        validated_url = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        import httpx
        with patch("app.collector.safe_collector.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TooManyRedirects("Too many"))

            with pytest.raises(CollectorError) as exc:
                await fetch(validated_url)
            assert exc.value.code == "TOO_MANY_REDIRECTS"

    @pytest.mark.asyncio
    async def test_fetch_redirect_then_success(self):
        redirect_response = MagicMock()
        redirect_response.status_code = 301
        redirect_response.headers = {"location": "https://example.com/new"}
        redirect_response.is_redirect = True
        redirect_response.content = b""

        final_response = MagicMock()
        final_response.status_code = 200
        final_response.headers = {"content-type": "text/html"}
        final_response.content = b"<html>Final</html>"
        final_response.is_redirect = False

        validated_url = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        with patch("app.collector.safe_collector.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=[redirect_response, final_response])
            with patch("app.collector.safe_collector._get_tls_info", return_value=None):
                with patch("app.collector.safe_collector.validate_redirect_url") as mock_validate:
                    mock_validate.return_value = ValidatedURL(
                        original_url="https://example.com/new",
                        canonical_url="https://example.com/new",
                        scheme="https",
                        hostname="example.com",
                        path="/new",
                    )
                    response = await fetch(validated_url)

        assert response.status_code == 200
        assert response.redirect_count == 1
        assert response.url == "https://example.com/new"

    @pytest.mark.asyncio
    async def test_fetch_redirect_to_private_ip_blocked(self):
        redirect_response = MagicMock()
        redirect_response.status_code = 301
        redirect_response.headers = {"location": "http://192.168.1.1/"}
        redirect_response.is_redirect = True

        validated_url = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        with patch("app.collector.safe_collector.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=redirect_response)
            with patch("app.collector.safe_collector.validate_redirect_url") as mock_validate:
                from app.core.url_validator import URLValidationError
                mock_validate.side_effect = URLValidationError("Private address blocked", "BLOCKED_PRIVATE")

                with pytest.raises(CollectorError) as exc:
                    await fetch(validated_url)
                assert exc.value.code == "REDIRECT_BLOCKED_PRIVATE"

    @pytest.mark.asyncio
    async def test_response_size_limit(self):
        large_content = b"x" * 3_000_000
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = large_content
        mock_response.is_redirect = False

        validated_url = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        with patch("app.collector.safe_collector.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(CollectorError) as exc:
                await fetch(validated_url)
            assert exc.value.code == "RESPONSE_TOO_LARGE"