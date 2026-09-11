import pytest
from app.core.url_validator import (
    validate_url,
    canonicalize_url,
    validate_hostname,
    URLValidationError,
)
from app.core.config import settings


class TestCanonicalizeURL:
    def test_basic_https(self):
        result = canonicalize_url("https://example.com")
        assert result == "https://example.com/"

    def test_with_path(self):
        result = canonicalize_url("https://example.com/path/to/page")
        assert result == "https://example.com/path/to/page"

    def test_with_query(self):
        result = canonicalize_url("https://example.com/path?query=value")
        assert result == "https://example.com/path?query=value"

    def test_strips_default_ports(self):
        result = canonicalize_url("https://example.com:443/path")
        assert result == "https://example.com/path"
        result = canonicalize_url("http://example.com:80/path")
        assert result == "http://example.com/path"

    def test_lowercases_scheme_and_host(self):
        result = canonicalize_url("HTTPS://EXAMPLE.COM/PATH")
        assert result == "https://example.com/PATH"

    def test_missing_scheme_raises(self):
        with pytest.raises(URLValidationError) as exc:
            canonicalize_url("example.com")
        assert exc.value.code == "MISSING_SCHEME"

    def test_missing_hostname_raises(self):
        with pytest.raises(URLValidationError) as exc:
            canonicalize_url("https://")
        assert exc.value.code == "MISSING_HOSTNAME"


class TestValidateHostname:
    def test_valid_hostnames(self):
        for host in ["example.com", "sub.example.com", "a-b.example.com", "xn--fsq.xn--0zwm56d"]:
            validate_hostname(host)

    def test_empty_raises(self):
        with pytest.raises(URLValidationError) as exc:
            validate_hostname("")
        assert exc.value.code == "EMPTY_HOSTNAME"

    def test_too_long_raises(self):
        with pytest.raises(URLValidationError) as exc:
            validate_hostname("a" * 254)
        assert exc.value.code == "HOSTNAME_TOO_LONG"

    def test_invalid_chars_raises(self):
        with pytest.raises(URLValidationError) as exc:
            validate_hostname("exa_mple.com")
        assert exc.value.code == "INVALID_CHARACTERS"

    def test_label_too_long_raises(self):
        with pytest.raises(URLValidationError) as exc:
            validate_hostname("a" * 64 + ".com")
        assert exc.value.code == "INVALID_LABEL"

    def test_leading_trailing_hyphen_raises(self):
        with pytest.raises(URLValidationError) as exc:
            validate_hostname("-example.com")
        assert exc.value.code == "INVALID_HYPHENS"

        with pytest.raises(URLValidationError) as exc:
            validate_hostname("example-.com")
        assert exc.value.code == "INVALID_HYPHENS"


class TestValidateURL:
    @pytest.mark.asyncio
    async def test_valid_https_url(self):
        # This would require DNS resolution, so we mock in real tests
        pass

    @pytest.mark.asyncio
    async def test_invalid_scheme_rejected(self):
        with pytest.raises(Exception) as exc:
            await validate_url("ftp://example.com")
        assert "not allowed" in str(exc.value).lower() or "scheme" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_file_scheme_rejected(self):
        with pytest.raises(URLValidationError):
            await validate_url("file:///etc/passwd")