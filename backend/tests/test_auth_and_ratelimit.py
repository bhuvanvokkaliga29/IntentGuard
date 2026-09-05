"""
IntentGuard — Authentication, Rate Limiting, and API Security Test Suite

Verifies:
1. Valid API key authentication via X-API-Key and Bearer authorization.
2. Missing and invalid API keys on protected mutation routes return 401.
3. Rate limiter allows under limit and blocks with 429 when limit exceeded.
4. CORS headers configuration on preflight OPTIONS and cross-origin requests.
5. Health and readiness endpoints remain intentionally accessible without auth.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.security.auth import check_api_key
from backend.security.rate_limiter import SlidingWindowRateLimiter
from backend.config import reset_settings, get_settings


def test_auth_dev_mode_open_when_unconfigured(monkeypatch):
    """When API_KEY is unset, all requests should pass cleanly for local demo."""
    monkeypatch.setenv("API_KEY", "")
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


@pytest.mark.asyncio
async def test_health_endpoints_remain_accessible_without_auth(monkeypatch):
    """Health, liveness, readiness, and metrics endpoints must remain open for probes."""
    monkeypatch.setenv("API_KEY", "prod-secret-999")
    reset_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # /health
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # /health/ready
        res_ready = await client.get("/health/ready")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] == "ready"

        # /
        res_root = await client.get("/")
        assert res_root.status_code == 200

    monkeypatch.delenv("API_KEY", raising=False)
    reset_settings()


@pytest.mark.asyncio
async def test_protected_mutation_route_rejects_unauthenticated(monkeypatch):
    """Protected mutation endpoints (e.g. POST /mandates) enforce API key when configured."""
    monkeypatch.setenv("API_KEY", "prod-secret-999")
    reset_settings()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without key -> 401
        res_unauth = await client.post("/mandates", json={"intent_text": "Buy paper", "max_amount_per_txn": 500.0})
        assert res_unauth.status_code == 401

        # With wrong key -> 401
        res_bad = await client.post(
            "/mandates",
            headers={"X-API-Key": "wrong-key"},
            json={"intent_text": "Buy paper", "max_amount_per_txn": 500.0},
        )
        assert res_bad.status_code == 401

        # With valid key -> 200/201 (passes auth barrier)
        res_ok = await client.post(
            "/mandates",
            headers={"X-API-Key": "prod-secret-999"},
            json={"intent_text": "Buy office paper", "max_amount_per_txn": 500.0, "allowed_categories": ["stationery"]},
        )
        assert res_ok.status_code in [200, 201]

    monkeypatch.delenv("API_KEY", raising=False)
    reset_settings()


@pytest.mark.asyncio
async def test_cors_preflight_headers():
    """Verify CORS middleware headers allow configured origins and methods."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.options(
            "/decisions/evaluate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-API-Key",
            },
        )
        assert res.status_code == 200
        assert "access-control-allow-origin" in res.headers
        assert res.headers["access-control-allow-origin"] == "http://localhost:3000"
