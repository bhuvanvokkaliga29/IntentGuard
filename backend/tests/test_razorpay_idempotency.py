"""
IntentGuard — Razorpay Gateway Idempotency & Concurrency Tests
"""

import concurrent.futures
import pytest
from backend.execution.razorpay_gateway import RazorpayGateway


def test_razorpay_idempotency_replay():
    """Identical order calls with same receipt return identical order_id and idempotent_replay=True."""
    gateway = RazorpayGateway()

    res1 = gateway.create_order(amount=500.0, currency="INR", receipt="receipt_test_001")
    assert res1["success"] is True
    order_id1 = res1["order_id"]
    assert res1["idempotent_replay"] is False

    # Second call with same receipt (client retry after network loss)
    res2 = gateway.create_order(amount=500.0, currency="INR", receipt="receipt_test_001")
    assert res2["success"] is True
    assert res2["order_id"] == order_id1
    assert res2["idempotent_replay"] is True


def test_razorpay_concurrent_duplicate_prevention():
    """Concurrent requests with same key cannot create duplicate financial orders."""
    gateway = RazorpayGateway()
    order_results = []

    def make_order():
        return gateway.create_order(amount=1200.0, currency="INR", receipt="receipt_concurrent_999")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_order) for _ in range(5)]
        for f in concurrent.futures.as_completed(futures):
            order_results.append(f.result())

    # All must succeed
    assert all(r["success"] is True for r in order_results)

    # Exactly one unique order_id generated across all concurrent calls
    order_ids = set(r["order_id"] for r in order_results)
    assert len(order_ids) == 1

    # Exactly 4 of them must be marked as idempotent_replay
    replays = [r for r in order_results if r["idempotent_replay"] is True]
    assert len(replays) == 4
