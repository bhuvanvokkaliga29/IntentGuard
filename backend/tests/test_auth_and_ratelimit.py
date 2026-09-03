"""
IntentGuard — Authentication & Rate Limiting Test Suite
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from backend.security.auth import check_api_key
from backend.security.rate_limiter import SlidingWindowRateLimiter
from backend.config import reset_settings, get_settings


def test_auth_dev_mode_open_when_unconfigured(monkeypatch):
    """When API_KEY is unset, all requests should pass cleanly for local demo."""
    monkeypatch.delenv("API_KEY", raising=False)
    reset_settings()

    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.url.path = "/decisions/evaluate"

    assert check_api_key(mock_request) is True


def test_auth_enforces_when_configured(monkeypatch):
    """When API_KEY is configured, valid key succeeds, invalid/missing fails."""
    monkeypatch.setenv("API_KEY", "secret-test-key-12345")
    reset_settings()

    mock_request = MagicMock()
    mock_request.url.path = "/decisions/evaluate"

    # 1. Missing key -> 401
    mock_request.headers = {}
    with pytest.raises(HTTPException) as exc1:
        check_api_key(mock_request)
    assert exc1.value.status_code == 401

    # 2. Invalid key -> 401
    mock_request.headers = {"X-API-Key": "wrong-key"}
    with pytest.raises(HTTPException) as exc2:
        check_api_key(mock_request)
    assert exc2.value.status_code == 401

    # 3. Valid key via X-API-Key -> True
    mock_request.headers = {"X-API-Key": "secret-test-key-12345"}
    assert check_api_key(mock_request) is True

    # 4. Valid key via Bearer token -> True
    mock_request.headers = {"Authorization": "Bearer secret-test-key-12345"}
    assert check_api_key(mock_request) is True

    # Cleanup
    monkeypatch.delenv("API_KEY", raising=False)
    reset_settings()


def test_rate_limiter_allows_under_limit():
    """Requests under limit are allowed."""
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        assert limiter.is_allowed("192.168.1.100") is True


def test_rate_limiter_blocks_over_limit():
    """Requests over limit are blocked and return retry-after."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    assert limiter.is_allowed("192.168.1.101") is True
    assert limiter.is_allowed("192.168.1.101") is True
    assert limiter.is_allowed("192.168.1.101") is True
    assert limiter.is_allowed("192.168.1.101") is False

    retry_after = limiter.get_retry_after("192.168.1.101")
    assert retry_after > 0
