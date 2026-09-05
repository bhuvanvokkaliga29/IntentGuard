"""
IntentGuard — Unified Execution Path Regression Suite

Proves:
1. BLOCK decisions never reach execution adapter.
2. ESCALATE decisions never reach execution adapter.
3. ALLOW decisions reach execution adapter exactly once.
4. Replaying identical proposals is strictly idempotent (no double execution).
5. Direct invocations of gateway.create_order without ALLOW are rejected.
"""

import pytest
import uuid
from backend.execution.razorpay_gateway import get_razorpay_gateway, reset_razorpay_gateway
from backend.orchestrator.pipeline import stage_guard_execution_boundary


@pytest.fixture(autouse=True)
def reset_gateway():
    reset_razorpay_gateway()
    yield
    reset_razorpay_gateway()


def test_block_never_reaches_execution():
    """BLOCK decision is strictly stopped before reaching payment gateway."""
    proposal = {
        "id": str(uuid.uuid4()),
        "amount": 2500.0,
        "merchant_name": "Rogue Vendor",
        "item_description": "Unauthorized item",
    }
    result = stage_guard_execution_boundary("BLOCK", proposal)

    assert result["executed"] is False
    assert result["status"] == "BLOCKED_BY_GUARDRAIL"
    assert result["order"] is None

    # Gateway state must be completely untouched
    gateway = get_razorpay_gateway()
    assert len(gateway._idempotency_store) == 0


def test_escalate_never_reaches_execution():
    """ESCALATE decision is strictly stopped before reaching payment gateway."""
    proposal = {
        "id": str(uuid.uuid4()),
        "amount": 1200.0,
        "merchant_name": "Ambiguous Vendor",
        "item_description": "Vague services",
    }
    result = stage_guard_execution_boundary("ESCALATE", proposal)

    assert result["executed"] is False
    assert result["status"] == "BLOCKED_BY_GUARDRAIL"
    assert result["order"] is None

    # Gateway state must be completely untouched
    gateway = get_razorpay_gateway()
    assert len(gateway._idempotency_store) == 0


def test_allow_reaches_execution_exactly_once():
    """ALLOW decision executes payment order exactly once through the authoritative path."""
    proposal = {
        "id": str(uuid.uuid4()),
        "amount": 750.0,
        "currency": "INR",
        "merchant_name": "Stationery Mart",
        "item_description": "Ballpoint pens",
        "idempotency_key": f"key_{uuid.uuid4().hex[:10]}",
    }
    result = stage_guard_execution_boundary("ALLOW", proposal)

    assert result["executed"] is True
    assert result["status"] == "DISPATCHED"
    assert result["order"] is not None
    assert result["order"]["success"] is True
    assert result["order"]["idempotent_replay"] is False
    assert "order_id" in result["order"]


def test_duplicate_requests_remain_idempotent():
    """Duplicate requests with identical idempotency key return existing order without double-execution."""
    shared_key = f"idem_{uuid.uuid4().hex[:12]}"
    proposal = {
        "id": str(uuid.uuid4()),
        "amount": 1500.0,
        "currency": "INR",
        "merchant_name": "Tech Supplies India",
        "item_description": "HDMI Cables",
        "idempotency_key": shared_key,
    }

    # First attempt
    res1 = stage_guard_execution_boundary("ALLOW", proposal)
    assert res1["executed"] is True
    assert res1["order"]["idempotent_replay"] is False
    order_id_1 = res1["order"]["order_id"]

    # Replay attempt (e.g., retried HTTP request)
    res2 = stage_guard_execution_boundary("ALLOW", proposal)
    assert res2["executed"] is True
    assert res2["order"]["idempotent_replay"] is True
    order_id_2 = res2["order"]["order_id"]

    assert order_id_1 == order_id_2, "Idempotent replay must yield identical order ID"


def test_gateway_directly_rejects_non_allow_decision():
    """Direct execution call to RazorpayGateway with non-ALLOW decision is denied."""
    gateway = get_razorpay_gateway()

    res_block = gateway.create_order(
        amount=500.0,
        currency="INR",
        receipt="rcpt_test",
        decision="BLOCK",
    )
    assert res_block["success"] is False
    assert res_block["error"] == "EXECUTION_DISALLOWED"

    res_escalate = gateway.create_order(
        amount=500.0,
        currency="INR",
        receipt="rcpt_test",
        decision="ESCALATE",
    )
    assert res_escalate["success"] is False
    assert res_escalate["error"] == "EXECUTION_DISALLOWED"
