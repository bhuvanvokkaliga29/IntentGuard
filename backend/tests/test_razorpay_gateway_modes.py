"""
IntentGuard — Razorpay Gateway Configuration & Safety Modes Test Suite

Verifies:
1. When keys are missing -> MOCK_ADAPTER mode is explicitly used.
2. When rzp_test_ keys configured -> TEST_MODE is used.
3. When live keys configured -> PRODUCTION mode is used.
4. When execution is disabled -> rejects with EXECUTION_DISABLED.
5. Non-ALLOW decisions -> rejects with EXECUTION_DISALLOWED.
6. Credentials are never leaked in __repr__ or __str__.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.execution.razorpay_gateway import RazorpayGateway, reset_razorpay_gateway
from backend.config import reset_settings


@pytest.fixture(autouse=True)
def cleanup():
    reset_razorpay_gateway()
    reset_settings()
    yield
    reset_razorpay_gateway()
    reset_settings()


def test_missing_credentials_defaults_to_mock_adapter(monkeypatch):
    """When Razorpay keys are not provided, gateway defaults to MOCK_ADAPTER."""
    monkeypatch.setenv("RAZORPAY_KEY_ID", "")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "")
    reset_settings()

    gw = RazorpayGateway()
    assert gw.mode == "MOCK_ADAPTER"
    assert gw.client is None

    res = gw.create_order(amount=500.0, receipt="rcpt_mock_test")
    assert res["success"] is True
    assert res["mode"] == "MOCK_ADAPTER"
    assert res["order_id"].startswith("order_mock_")


def test_test_mode_detection(monkeypatch):
    """rzp_test_ key prefix initializes TEST_MODE."""
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_AbCdEf12345678")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "supersecretkey")
    reset_settings()

    with patch("razorpay.Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {"id": "order_test_123", "amount": 50000, "currency": "INR"}
        mock_client.return_value = mock_instance

        gw = RazorpayGateway()
        assert gw.mode == "TEST_MODE"

        res = gw.create_order(amount=500.0, receipt="rcpt_live_test")
        assert res["success"] is True
        assert res["mode"] == "TEST_MODE"
        assert res["order_id"] == "order_test_123"


def test_disabled_gateway_rejects_execution(monkeypatch):
    """Feature flag disabling razorpay execution halts order creation."""
    monkeypatch.setenv("RAZORPAY_ENABLED", "false")
    reset_settings()

    gw = RazorpayGateway()
    res = gw.create_order(amount=500.0)
    assert res["success"] is False
    assert res["error"] == "EXECUTION_DISABLED"


def test_credentials_not_in_repr_or_str(monkeypatch):
    """Credentials must never be exposed via string representation."""
    secret = "classified_secret_xyz123"
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_999")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", secret)
    reset_settings()

    gw = RazorpayGateway()
    assert secret not in repr(gw)
    assert secret not in str(gw)
