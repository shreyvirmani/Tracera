"""
Tests for ML preprocessing normalization.

Tests cover:
- URL normalization
- Origin normalization (with default ports)
- Registrable domain (eTLD+1) extraction
- Edge cases and public suffix handling
"""

import pytest
from ml.preprocessing.normalize import (
    normalize_url,
    normalize_origin,
    extract_registrable_domain,
    extract_registrable_domain_from_url,
)


class TestNormalizeURL:
    """Test URL normalization."""

    def test_basic_https(self):
        assert normalize_url("https://example.com") == "https://example.com/"

    def test_with_path(self):
        assert normalize_url("https://example.com/path/to/page") == "https://example.com/path/to/page"

    def test_with_query(self):
        assert normalize_url("https://example.com/path?query=value") == "https://example.com/path?query=value"

    def test_strips_default_ports(self):
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"

    def test_keeps_non_default_ports(self):
        assert normalize_url("https://example.com:8443/path") == "https://example.com:8443/path"
        assert normalize_url("http://example.com:8080/path") == "http://example.com:8080/path"

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/PATH") == "https://example.com/PATH"

    def test_missing_scheme_raises(self):
        with pytest.raises(ValueError, match="missing scheme"):
            normalize_url("example.com")

    def test_missing_hostname_raises(self):
        with pytest.raises(ValueError, match="missing scheme or hostname"):
            normalize_url("https://")

    def test_preserves_path_case(self):
        # Path case should be preserved
        assert normalize_url("https://example.com/Path/To/Page") == "https://example.com/Path/To/Page"

    def test_removes_fragment(self):
        # Fragment is not preserved by urlparse in our implementation
        # Actually urlparse keeps fragment separate, we don't include it
        result = normalize_url("https://example.com/path#section")
        assert "#" not in result


class TestNormalizeOrigin:
    """Test origin normalization."""

    def test_basic_https(self):
        assert normalize_origin("https://example.com") == "https://example.com:443"

    def test_basic_http(self):
        assert normalize_origin("http://example.com") == "http://example.com:80"

    def test_with_explicit_port(self):
        assert normalize_origin("https://example.com:8443") == "https://example.com:8443"
        assert normalize_origin("http://example.com:8080") == "http://example.com:8080"

    def test_strips_path_query_fragment(self):
        assert normalize_origin("https://example.com/path?query=value#frag") == "https://example.com:443"

    def test_lowercases(self):
        assert normalize_origin("HTTPS://EXAMPLE.COM:8443/PATH") == "https://example.com:8443"

    def test_missing_scheme_raises(self):
        with pytest.raises(ValueError, match="missing scheme"):
            normalize_origin("example.com")

    def test_missing_hostname_raises(self):
        with pytest.raises(ValueError, match="missing scheme or hostname"):
            normalize_origin("https://")


class TestExtractRegistrableDomain:
    """Test eTLD+1 (registrable domain) extraction."""

    # Standard domains
    def test_simple_domain(self):
        assert extract_registrable_domain("example.com") == "example.com"

    def test_www_subdomain(self):
        assert extract_registrable_domain("www.example.com") == "example.com"

    def test_deep_subdomain(self):
        assert extract_registrable_domain("api.v2.service.example.com") == "example.com"

    # Country-code TLDs
    def test_co_uk(self):
        assert extract_registrable_domain("example.co.uk") == "example.co.uk"
        assert extract_registrable_domain("www.example.co.uk") == "example.co.uk"
        assert extract_registrable_domain("blog.example.co.uk") == "example.co.uk"

    def test_com_au(self):
        assert extract_registrable_domain("example.com.au") == "example.com.au"
        assert extract_registrable_domain("www.example.com.au") == "example.com.au"

    def test_org_uk(self):
        assert extract_registrable_domain("example.org.uk") == "example.org.uk"

    # Public suffixes that are NOT registrable
    def test_github_io(self):
        # github.io is a public suffix
        assert extract_registrable_domain("github.io") == "github.io"
        # But subdomains of github.io have github.io as registrable domain
        assert extract_registrable_domain("user.github.io") == "github.io"

    def test_herokuapp_com(self):
        assert extract_registrable_domain("myapp.herokuapp.com") == "herokuapp.com"

    def test_azurewebsites_net(self):
        assert extract_registrable_domain("myapp.azurewebsites.net") == "azurewebsites.net"

    # Special cases
    def test_localhost(self):
        assert extract_registrable_domain("localhost") == "localhost"
        assert extract_registrable_domain("sub.localhost") == "localhost"

    def test_ipv4_address(self):
        assert extract_registrable_domain("192.168.1.1") == "192.168.1.1"
        assert extract_registrable_domain("10.0.0.1") == "10.0.0.1"

    def test_ipv6_address(self):
        assert extract_registrable_domain("[::1]") == "[::1]"
        assert extract_registrable_domain("2001:db8::1") == "2001:db8::1"

    def test_invalid_host_raises(self):
        with pytest.raises(ValueError, match="Empty hostname"):
            extract_registrable_domain("")

    def test_case_insensitive(self):
        assert extract_registrable_domain("WWW.EXAMPLE.COM") == "example.com"
        assert extract_registrable_domain("Example.COM") == "example.com"

    # Multi-label TLDs
    def test_edu_br(self):
        assert extract_registrable_domain("university.edu.br") == "university.edu.br"
        assert extract_registrable_domain("www.university.edu.br") == "university.edu.br"

    def test_gov_uk(self):
        assert extract_registrable_domain("department.gov.uk") == "department.gov.uk"

    # Private TLDs (should work if in PSL)
    def test_test_tld(self):
        # .test is a reserved TLD and is in PSL as a public suffix
        # example.test -> public suffix "test", registrable domain "test"
        assert extract_registrable_domain("example.test") == "test"


class TestExtractRegistrableDomainFromURL:
    """Test registrable domain extraction directly from URL."""

    def test_from_https_url(self):
        assert extract_registrable_domain_from_url("https://www.example.com/path") == "example.com"

    def test_from_http_url(self):
        assert extract_registrable_domain_from_url("http://api.example.com:8080") == "example.com"

    def test_from_co_uk_url(self):
        assert extract_registrable_domain_from_url("https://blog.example.co.uk/page") == "example.co.uk"

    def test_missing_hostname_raises(self):
        with pytest.raises(ValueError, match="missing hostname"):
            extract_registrable_domain_from_url("https://")


class TestNormalizationConsistency:
    """Test that normalization functions are consistent."""

    def test_normalize_url_then_origin(self):
        """normalize_url then normalize_origin should be consistent."""
        url = "https://EXAMPLE.COM:443/Path?Query=value"
        norm_url = normalize_url(url)
        origin = normalize_origin(norm_url)
        assert origin == "https://example.com:443"

    def test_origin_then_registrable(self):
        """normalize_origin then extract_registrable_domain should work."""
        url = "https://www.example.com:8443/path"
        origin = normalize_origin(url)
        # Origin includes port, extract hostname for registrable domain
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        reg_domain = extract_registrable_domain(parsed.hostname)
        assert reg_domain == "example.com"

    def test_idempotent_normalize_url(self):
        """normalize_url should be idempotent."""
        url = "https://Example.COM:443/Path"
        first = normalize_url(url)
        second = normalize_url(first)
        assert first == second

    def test_idempotent_normalize_origin(self):
        """normalize_origin should be idempotent."""
        url = "https://Example.COM:443/Path"
        first = normalize_origin(url)
        second = normalize_origin(first)
        assert first == second


class TestRealWorldDomains:
    """Test with real-world domain patterns."""

    def test_google_domains(self):
        assert extract_registrable_domain("www.google.com") == "google.com"
        assert extract_registrable_domain("mail.google.com") == "google.com"
        assert extract_registrable_domain("drive.google.com") == "google.com"

    def test_amazon_domains(self):
        assert extract_registrable_domain("www.amazon.com") == "amazon.com"
        assert extract_registrable_domain("aws.amazon.com") == "amazon.com"
        # s3.amazonaws.com is a cloud platform, grouped by platform domain
        assert extract_registrable_domain("s3.amazonaws.com") == "amazonaws.com"  # platform domain

    def test_microsoft_domains(self):
        assert extract_registrable_domain("www.microsoft.com") == "microsoft.com"
        assert extract_registrable_domain("login.microsoftonline.com") == "microsoftonline.com"

    def test_cloudflare_domains(self):
        assert extract_registrable_domain("example.cloudflare.com") == "cloudflare.com"

    def test_subdomain_on_public_suffix(self):
        # These are on public suffixes
        assert extract_registrable_domain("mysite.github.io") == "github.io"
        assert extract_registrable_domain("myapp.herokuapp.com") == "herokuapp.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])