"""Security tests for the hardened collector and SSRF guard.

All live-socket tests use loopback-only local fixtures; no test traffic
leaves the machine.
"""

from unittest.mock import patch

import pytest

from app.collector.collector import CollectorError, collect
from app.core.ssrf_guard import (
    SSRFGuardError,
    is_blocked_ip,
    validate_redirect_target,
)
from app.core.url_validator import URLValidationError, canonicalize_url
from tests.fixtures_http import start_ok_server, start_redirect_server, stop


def _loopback_target(port: int):
    from app.core.ssrf_guard import ResolvedIP

    url = canonicalize_url(f"http://127.0.0.1:{port}/")
    ip = ResolvedIP("127.0.0.1", 4, False, True, False, False, False)
    return url, ip


class TestIsBlockedIP:
    def test_blocks_cgnat_range(self):
        blocked, _ = is_blocked_ip("100.64.1.1")
        assert blocked is True

    def test_blocks_6to4_relay(self):
        blocked, _ = is_blocked_ip("192.88.99.1")
        assert blocked is True

    def test_blocks_benchmark_range(self):
        blocked, _ = is_blocked_ip("198.18.0.1")
        assert blocked is True

    def test_blocks_ipv4_mapped_private(self):
        blocked, _ = is_blocked_ip("::ffff:10.0.0.1")
        assert blocked is True

    def test_blocks_ipv4_mapped_loopback(self):
        blocked, _ = is_blocked_ip("::ffff:127.0.0.1")
        assert blocked is True

    def test_blocks_this_network(self):
        blocked, _ = is_blocked_ip("0.0.0.0")
        assert blocked is True

    def test_blocks_nat64_prefix(self):
        blocked, _ = is_blocked_ip("64:ff9b::808:808")
        assert blocked is True

    def test_allows_public_ip(self):
        blocked, _ = is_blocked_ip("8.8.8.8")
        assert blocked is False

    def test_allows_public_ipv6(self):
        blocked, _ = is_blocked_ip("2606:4700::1111")
        assert blocked is False

    def test_blocks_invalid(self):
        blocked, _ = is_blocked_ip("not-an-ip")
        assert blocked is True


class TestPortPolicy:
    def test_rejects_non_http_port(self):
        with pytest.raises(URLValidationError) as exc:
            canonicalize_url("http://example.com:6379/")
        assert exc.value.code == "PORT_NOT_ALLOWED"

    def test_rejects_ssh_port(self):
        with pytest.raises(URLValidationError) as exc:
            canonicalize_url("https://example.com:22/")
        assert exc.value.code == "PORT_NOT_ALLOWED"

    def test_allows_standard_ports(self):
        assert canonicalize_url("http://example.com:80/").port == 80
        assert canonicalize_url("https://example.com:443/").port == 443
        assert canonicalize_url("http://example.com:8080/").port == 8080
        assert canonicalize_url("https://example.com:8443/").port == 8443


class TestRedirectRevalidation:
    def test_redirect_to_loopback_is_blocked(self):
        """A public-style target must not be able to redirect us internally."""
        redirect_server, redirect_port = start_redirect_server("http://127.0.0.1:1/")
        ok_server, ok_port = start_ok_server()
        try:
            url, ip = _loopback_target(ok_port)
            # The initial target is the ok server; it doesn't redirect, so
            # point the redirect server chain manually: use redirect server
            # as the initial target redirecting to loopback port 1.
            url, ip = _loopback_target(redirect_port)
            with pytest.raises(CollectorError) as exc:
                import asyncio

                asyncio.run(collect(url, ip))
            assert exc.value.code == "REDIRECT_TARGET_BLOCKED"
        finally:
            stop(redirect_server)
            stop(ok_server)

    def test_redirect_to_disallowed_port_is_blocked(self):
        redirect_server, redirect_port = start_redirect_server("http://127.0.0.1:6379/")
        try:
            url, ip = _loopback_target(redirect_port)
            with pytest.raises(CollectorError) as exc:
                import asyncio

                asyncio.run(collect(url, ip))
            assert exc.value.code == "REDIRECT_TARGET_BLOCKED"
        finally:
            stop(redirect_server)

    def test_validate_redirect_target_rejects_bad_scheme(self):
        with pytest.raises(SSRFGuardError) as exc:
            validate_redirect_target("ftp://example.com/")
        assert exc.value.code == "REDIRECT_TARGET_BLOCKED"

    def test_validate_redirect_target_rejects_private_host(self):
        with pytest.raises(SSRFGuardError):
            validate_redirect_target("http://10.0.0.5/")

    def test_validate_redirect_target_allows_public_host(self):
        with patch("app.core.ssrf_guard.resolve_hostname") as mock_resolve:
            from app.core.ssrf_guard import ResolvedIP

            mock_resolve.return_value = [
                ResolvedIP("93.184.216.34", 4, False, False, False, False, False)
            ]
            validated, ip = validate_redirect_target("https://example.com/page")
            assert validated.host == "example.com"
            assert ip.ip == "93.184.216.34"

    def test_allowed_redirect_reaches_pinned_connection(self):
        """A redirect passing revalidation is followed (connection to the
        fake public IP then fails, proving the hop was attempted)."""
        redirect_server, redirect_port = start_redirect_server("http://allowed.test:80/")
        try:
            url, ip = _loopback_target(redirect_port)
            with (
                patch("app.core.ssrf_guard.resolve_hostname") as mock_resolve,
                patch("app.core.ssrf_guard.is_blocked_ip", return_value=(False, "")),
            ):
                from app.core.ssrf_guard import ResolvedIP

                mock_resolve.return_value = [
                    ResolvedIP("93.184.216.34", 4, False, False, False, False, False)
                ]
                import asyncio

                with pytest.raises(CollectorError) as exc:
                    asyncio.run(collect(url, ip))
                # Revalidation passed and the pinned connection was attempted
                # to the (unroutable in tests) resolved address.
                assert exc.value.code in ("REQUEST_FAILED", "TIMEOUT")
        finally:
            stop(redirect_server)


class TestConnectionPinning:
    def test_collect_connects_to_validated_ip(self):
        """The collector must reach the server at the validated IP even when
        DNS would resolve the hostname elsewhere (rebinding defense)."""
        ok_server, ok_port = start_ok_server()
        try:
            url, ip = _loopback_target(ok_port)
            # Simulate DNS poisoning: any resolution would return a different
            # address. The collector must ignore DNS entirely.
            with patch("socket.getaddrinfo") as mock_dns:
                mock_dns.side_effect = AssertionError("DNS must not be consulted")
                import asyncio

                response = asyncio.run(collect(url, ip))
            assert response.status_code == 200
            assert b"ok" in response.content
        finally:
            stop(ok_server)

    def test_response_metadata_recorded(self):
        ok_server, ok_port = start_ok_server()
        try:
            url, ip = _loopback_target(ok_port)
            import asyncio

            response = asyncio.run(collect(url, ip))
            assert response.content_type == "text/html"
            assert response.redirect_count == 0
            assert response.response_time_ms > 0
            assert response.final_url.endswith("/")
        finally:
            stop(ok_server)
