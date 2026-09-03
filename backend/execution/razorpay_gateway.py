"""
Razorpay Financial Execution Gateway
"""

import logging
import razorpay
from backend.config import get_settings

logger = logging.getLogger("intentguard.execution.razorpay")

class RazorpayGateway:
    def __init__(self):
        settings = get_settings()
        self.key_id = settings.razorpay_key_id
        self.key_secret = settings.razorpay_key_secret
        self.client = None

        if self.key_id and self.key_secret:
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {e}")
        else:
            logger.warning("Razorpay keys not configured. Execution gateway will mock API calls.")

    def create_order(self, amount: float, currency: str = "INR", receipt: str = None) -> dict:
        """
        Create a Razorpay Order. 
        Note: Razorpay accepts amount in subunits (paise for INR). So ₹100 becomes 10000.
        """
        amount_in_paise = int(amount * 100)
        data = {
            "amount": amount_in_paise,
            "currency": currency,
            "receipt": receipt or "receipt#1"
        }

        if self.client:
            try:
                order = self.client.order.create(data=data)
                logger.info(f"Successfully created Razorpay Order: {order.get('id')}")
                return {
                    "success": True,
                    "order_id": order.get("id"),
                    "amount": order.get("amount"),
                    "currency": order.get("currency")
                }
            except Exception as e:
                logger.error(f"Razorpay Order Creation Failed: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        else:
            # Mock behavior if keys are missing
            mock_order_id = f"order_mock_{receipt}"
            logger.info(f"Mock created Razorpay Order: {mock_order_id} for {amount} {currency}")
            return {
                "success": True,
                "order_id": mock_order_id,
                "amount": amount_in_paise,
                "currency": currency
            }

_gateway = None

def get_razorpay_gateway() -> RazorpayGateway:
    global _gateway
    if _gateway is None:
        _gateway = RazorpayGateway()
    return _gateway
