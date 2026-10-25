import pytest

from app.api.v1.scans import _rate_limit_buckets


@pytest.fixture(autouse=True)
def clear_rate_limit_buckets():
    """Keep scan-creation rate limiting from leaking between tests."""
    _rate_limit_buckets.clear()
    yield
    _rate_limit_buckets.clear()
