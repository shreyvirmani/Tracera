import pytest

from app.core.url_validator import (
    URLValidationError,
    canonicalize_url,
    validate_hostname,
    validate_port,
    validate_scheme,
)


class TestValidateScheme:
    def test_valid_http(self):
        assert validate_scheme("http://example.com") == "http"

    def test_valid_https(self):
        assert validate_scheme("https://example.com") == "https"

    def test_invalid_scheme_ftp(self):
        with pytest.raises(URLValidationError) as exc:
            validate_scheme("ftp://example.com")
        assert exc.value.code == "INVALID_SCHEME"

    def test_invalid_scheme_file(self):
        with pytest.raises(URLValidationError) as exc:
            validate_scheme("file:///etc/passwd")
        assert exc.value.code == "INVALID_SCHEME"

    def test_case_insensitive(self):
        assert validate_scheme("HTTP://example.com") == "http"
        assert validate_scheme("HTTPS://example.com") == "https"


class TestValidateHostname:
    def test_valid_hostname(self):
        assert validate_hostname("example.com") == "example.com"

    def test_valid_subdomain(self):
        assert validate_hostname("sub.example.com") == "sub.example.com"

    def test_valid_ipv4(self):
        assert validate_hostname("192.168.1.1") == "192.168.1.1"

    def test_valid_ipv6(self):
        assert validate_hostname("::1") == "::1"

    def test_empty_hostname(self):
        with pytest.raises(URLValidationError) as exc:
            validate_hostname("")
        assert exc.value.code == "EMPTY_HOSTNAME"

    def test_invalid_hostname(self):
        with pytest.raises(URLValidationError) as exc:
            validate_hostname("invalid..hostname")
        assert exc.value.code == "INVALID_HOSTNAME"


class TestValidatePort:
    def test_valid_port(self):
        assert validate_port(8080, "http") == 8080

    def test_default_http_port(self):
        assert validate_port(None, "http") == 80

    def test_default_https_port(self):
        assert validate_port(None, "https") == 443

    def test_invalid_port_zero(self):
        with pytest.raises(URLValidationError) as exc:
            validate_port(0, "http")
        assert exc.value.code == "INVALID_PORT"

    def test_invalid_port_too_high(self):
        with pytest.raises(URLValidationError) as exc:
            validate_port(65536, "http")
        assert exc.value.code == "INVALID_PORT"


class TestCanonicalizeURL:
    def test_simple_http(self):
        result = canonicalize_url("http://example.com")
        assert result.canonical_url == "http://example.com/"
        assert result.scheme == "http"
        assert result.host == "example.com"
        assert result.port == 80

    def test_simple_https(self):
        result = canonicalize_url("https://example.com")
        assert result.canonical_url == "https://example.com/"
        assert result.port == 443

    def test_with_path(self):
        result = canonicalize_url("https://example.com/path/to/resource")
        assert result.canonical_url == "https://example.com/path/to/resource"

    def test_with_query(self):
        result = canonicalize_url("https://example.com/path?query=value")
        assert result.canonical_url == "https://example.com/path?query=value"

    def test_with_port(self):
        result = canonicalize_url("https://example.com:8443/path")
        assert result.canonical_url == "https://example.com:8443/path"
        assert result.port == 8443

    def test_default_port_not_in_canonical(self):
        result = canonicalize_url("https://example.com:443/path")
        assert result.canonical_url == "https://example.com/path"

    def test_case_insensitive_host(self):
        result = canonicalize_url("https://EXAMPLE.COM")
        assert result.host == "example.com"

    def test_missing_path_defaults_to_root(self):
        result = canonicalize_url("https://example.com")
        assert result.path == "/"

    def test_ipv4_host(self):
        result = canonicalize_url("http://192.168.1.1:8080")
        assert result.host == "192.168.1.1"
        assert result.port == 8080

    def test_invalid_scheme_raises(self):
        with pytest.raises(URLValidationError) as exc:
            canonicalize_url("ftp://example.com")
        assert exc.value.code == "INVALID_SCHEME"

    def test_invalid_hostname_raises(self):
        with pytest.raises(URLValidationError) as exc:
            canonicalize_url("https://invalid..hostname")
        assert exc.value.code == "INVALID_HOSTNAME"
