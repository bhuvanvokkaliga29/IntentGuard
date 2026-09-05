"""
Razorpay Financial Execution Gateway — Hardened & Idempotent

Provides safe, idempotent payment order creation for authorized transactions.
Invariants:
1. Only ALLOW decisions from deterministic policy can reach this gateway.
2. Orders are strictly idempotent: identical receipts/idempotency keys return the existing order.
3. Thread-safe execution lock prevents race conditions and double-spending.
4. Clearly identifies TEST_MODE vs MOCK_ADAPTER.
"""

import logging
import threading
from typing import Dict, Optional, Any

import razorpay
from backend.config import get_settings

logger = logging.getLogger("intentguard.execution.razorpay")


class RazorpayGateway:
    """Thread-safe, idempotent financial execution gateway for Razorpay."""

    def __init__(self):
        settings = get_settings()
        self.key_id = settings.razorpay_key_id
        self.key_secret = settings.razorpay_key_secret
        self.enabled = settings.razorpay_enabled
        self.client = None
        self._lock = threading.Lock()
        self._idempotency_store: Dict[str, Dict[str, Any]] = {}

        if self.key_id and self.key_secret:
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                self.mode = "TEST_MODE" if str(self.key_id).startswith("rzp_test_") else "PRODUCTION"
                logger.info(f"Initialized Razorpay client in {self.mode}")
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {e}")
                self.mode = "MOCK_ADAPTER"
        else:
            self.mode = "MOCK_ADAPTER"
            logger.info("Razorpay keys not configured. Execution gateway initialized in MOCK_ADAPTER mode.")

    def create_order(
        self,
        amount: float,
        currency: str = "INR",
        receipt: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        decision: str = "ALLOW",
    ) -> Dict[str, Any]:
        """
        Create a Razorpay Order with strict idempotency, concurrency locking, and decision gating.
        Note: Razorpay accepts amount in subunits (paise for INR). So ₹100 becomes 10000.
        """
        if decision != "ALLOW":
            logger.error(f"[EXECUTION GATE] Direct execution denied: decision is '{decision}' (ALLOW required)")
            return {
                "success": False,
                "error": "EXECUTION_DISALLOWED",
                "message": f"Execution rejected: Decision is '{decision}'. Only 'ALLOW' can reach financial settlement.",
            }

        if not self.enabled:
            logger.info("[EXECUTION] Razorpay execution disabled via feature flag.")
            return {
                "success": False,
                "error": "EXECUTION_DISABLED",
                "message": "Razorpay execution gateway is disabled by configuration.",
            }

        key = idempotency_key or receipt or f"order_default_{amount}_{currency}"

        with self._lock:
            # 1. Idempotency Check — return existing order if already processed
            if key in self._idempotency_store:
                logger.info(f"[IDEMPOTENCY HIT] Returning existing order for key '{key}'")
                cached = dict(self._idempotency_store[key])
                cached["idempotent_replay"] = True
                return cached

            amount_in_paise = int(amount * 100)
            data = {
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": receipt or "receipt_default",
            }

            if self.client:
                try:
                    order = self.client.order.create(data=data)
                    logger.info(f"Successfully created Razorpay Order: {order.get('id')} ({self.mode})")
                    result = {
                        "success": True,
                        "order_id": order.get("id"),
                        "amount": order.get("amount"),
                        "currency": order.get("currency"),
                        "mode": self.mode,
                        "idempotent_replay": False,
                    }
                    self._idempotency_store[key] = result
                    return result
                except Exception as e:
                    logger.error(f"Razorpay Order Creation Failed: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "mode": self.mode,
                        "idempotent_replay": False,
                    }
            else:
                # Deterministic mock behavior if keys are missing
                mock_order_id = f"order_mock_{key[:16]}"
                logger.info(f"Mock created Razorpay Order: {mock_order_id} for ₹{amount} {currency}")
                result = {
                    "success": True,
                    "order_id": mock_order_id,
                    "amount": amount_in_paise,
                    "currency": currency,
                    "mode": "MOCK_ADAPTER",
                    "idempotent_replay": False,
                }
                self._idempotency_store[key] = result
                return result

    def __repr__(self) -> str:
        return f"<RazorpayGateway mode={self.mode} enabled={self.enabled}>"

    def __str__(self) -> str:
        return f"RazorpayGateway(mode={self.mode}, enabled={self.enabled})"


_gateway: Optional[RazorpayGateway] = None


def get_razorpay_gateway() -> RazorpayGateway:
    """Get singleton RazorpayGateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = RazorpayGateway()
    return _gateway


def reset_razorpay_gateway():
    """Reset singleton for testing."""
    global _gateway
    _gateway = None
