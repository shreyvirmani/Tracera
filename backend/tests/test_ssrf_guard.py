import socket
from unittest.mock import patch

import pytest

from app.core.ssrf_guard import (
    SSRFGuardError,
    check_ssrf,
    is_multicast_ip,
    is_private_ip,
    resolve_hostname,
    validate_resolved_ips,
)
from app.core.url_validator import canonicalize_url


class TestIsPrivateIP:
    def test_private_10_range(self):
        assert is_private_ip("10.0.0.1") is True

    def test_private_172_range(self):
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True

    def test_private_192_range(self):
        assert is_private_ip("192.168.1.1") is True

    def test_loopback_not_private(self):
        assert is_private_ip("127.0.0.1") is False
        assert is_private_ip("::1") is False

    def test_link_local_not_private(self):
        assert is_private_ip("169.254.0.1") is False
        assert is_private_ip("fe80::1") is False

    def test_multicast_not_private(self):
        assert is_private_ip("224.0.0.1") is False
        assert is_private_ip("ff00::1") is False

    def test_public_ip(self):
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False

    def test_invalid_ip(self):
        assert is_private_ip("not-an-ip") is False


class TestIsMulticastIP:
    def test_multicast_ipv4(self):
        assert is_multicast_ip("224.0.0.1") is True
        assert is_multicast_ip("239.255.255.255") is True

    def test_multicast_ipv6(self):
        assert is_multicast_ip("ff00::1") is True

    def test_non_multicast(self):
        assert is_multicast_ip("8.8.8.8") is False
        assert is_multicast_ip("10.0.0.1") is False


class TestResolveHostname:
    @patch("socket.getaddrinfo")
    def test_resolves_to_ipv4(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 0)),
        ]
        results = resolve_hostname("example.com")
        assert len(results) == 1
        assert results[0].ip == "1.2.3.4"
        assert results[0].version == 4

    @patch("socket.getaddrinfo")
    def test_resolves_to_ipv6(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0)),
        ]
        results = resolve_hostname("example.com")
        assert len(results) == 1
        assert results[0].ip == "::1"
        assert results[0].version == 6

    @patch("socket.getaddrinfo")
    def test_dns_failure(self, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")
        with pytest.raises(SSRFGuardError) as exc:
            resolve_hostname("invalid.example")
        assert exc.value.code == "DNS_RESOLUTION_FAILED"


class TestValidateResolvedIPs:
    def test_allows_public_ip(self):
        from app.core.ssrf_guard import ResolvedIP

        ips = [ResolvedIP("8.8.8.8", 4, False, False, False, False, False)]
        result = validate_resolved_ips(ips)
        assert result.ip == "8.8.8.8"

    def test_blocks_loopback(self):
        from app.core.ssrf_guard import ResolvedIP

        ips = [ResolvedIP("127.0.0.1", 4, False, True, False, False, False)]
        with pytest.raises(SSRFGuardError) as exc:
            validate_resolved_ips(ips)
        assert exc.value.code == "LOOPBACK_BLOCKED"

    def test_blocks_private(self):
        from app.core.ssrf_guard import ResolvedIP

        ips = [ResolvedIP("10.0.0.1", 4, True, False, False, False, False)]
        with pytest.raises(SSRFGuardError) as exc:
            validate_resolved_ips(ips)
        assert exc.value.code == "PRIVATE_ADDRESS_BLOCKED"

    def test_blocks_link_local(self):
        from app.core.ssrf_guard import ResolvedIP

        ips = [ResolvedIP("169.254.0.1", 4, False, False, True, False, False)]
        with pytest.raises(SSRFGuardError) as exc:
            validate_resolved_ips(ips)
        assert exc.value.code == "LINK_LOCAL_BLOCKED"

    def test_blocks_multicast(self):
        from app.core.ssrf_guard import ResolvedIP

        ips = [ResolvedIP("224.0.0.1", 4, False, False, False, True, False)]
        with pytest.raises(SSRFGuardError) as exc:
            validate_resolved_ips(ips)
        assert exc.value.code == "MULTICAST_BLOCKED"

    def test_blocks_reserved(self):
        from app.core.ssrf_guard import ResolvedIP

        ips = [ResolvedIP("240.0.0.1", 4, False, False, False, False, True)]
        with pytest.raises(SSRFGuardError) as exc:
            validate_resolved_ips(ips)
        assert exc.value.code == "RESERVED_ADDRESS_BLOCKED"

    def test_empty_list_raises(self):
        with pytest.raises(SSRFGuardError) as exc:
            validate_resolved_ips([])
        assert exc.value.code == "NO_IP_RESOLVED"

    def test_prefers_first_public(self):
        from app.core.ssrf_guard import ResolvedIP

        ips = [
            ResolvedIP("10.0.0.1", 4, True, False, False, False, False),
            ResolvedIP("8.8.8.8", 4, False, False, False, False, False),
        ]
        with pytest.raises(SSRFGuardError) as exc:
            validate_resolved_ips(ips)
        assert exc.value.code == "PRIVATE_ADDRESS_BLOCKED"


class TestCheckSSRF:
    @patch("app.core.ssrf_guard.resolve_hostname")
    def test_allows_public_domain(self, mock_resolve):
        from app.core.ssrf_guard import ResolvedIP

        mock_resolve.return_value = [ResolvedIP("8.8.8.8", 4, False, False, False, False, False)]
        url = canonicalize_url("https://example.com")
        result = check_ssrf(url)
        assert result.ip == "8.8.8.8"

    @patch("app.core.ssrf_guard.resolve_hostname")
    def test_blocks_localhost(self, mock_resolve):
        from app.core.ssrf_guard import ResolvedIP

        mock_resolve.return_value = [ResolvedIP("127.0.0.1", 4, False, True, False, False, False)]
        url = canonicalize_url("http://localhost")
        with pytest.raises(SSRFGuardError) as exc:
            check_ssrf(url)
        assert exc.value.code == "LOOPBACK_BLOCKED"

    @patch("app.core.ssrf_guard.resolve_hostname")
    def test_blocks_private_ip(self, mock_resolve):
        from app.core.ssrf_guard import ResolvedIP

        mock_resolve.return_value = [ResolvedIP("192.168.1.1", 4, True, False, False, False, False)]
        url = canonicalize_url("http://192.168.1.1")
        with pytest.raises(SSRFGuardError) as exc:
            check_ssrf(url)
        assert exc.value.code == "PRIVATE_ADDRESS_BLOCKED"

    @patch("app.core.ssrf_guard.resolve_hostname")
    def test_blocks_metadata_endpoint(self, mock_resolve):
        from app.core.ssrf_guard import ResolvedIP

        mock_resolve.return_value = [
            ResolvedIP("169.254.169.254", 4, False, False, True, False, False)
        ]
        url = canonicalize_url("http://169.254.169.254")
        with pytest.raises(SSRFGuardError) as exc:
            check_ssrf(url)
        assert exc.value.code == "LINK_LOCAL_BLOCKED"
