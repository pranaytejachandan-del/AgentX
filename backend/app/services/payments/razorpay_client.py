import hmac
import hashlib
import logging
import uuid
from typing import Dict, Any, Optional
import razorpay

from app.config import settings
from app.services.payments.exceptions import InvalidWebhookSignatureException

logger = logging.getLogger("agentx.payments.razorpay_client")


class RazorpayClientWrapper:
    """
    Wrapper around official Razorpay Python SDK.
    Handles Payment Link creation, signature verification over raw request body bytes,
    and handles test-mode fallback.
    """

    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def create_payment_link(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke Razorpay Payment Link API: POST /v1/payment_links
        """
        # If test mode or mock keys are used, simulate valid API response
        if not self.key_id or self.key_id.startswith("rzp_test_dummy"):
            link_id = f"plink_{uuid.uuid4().hex[:14]}"
            reference_id = payload.get("reference_id", f"REF-{uuid.uuid4().hex[:8]}")
            short_url = f"https://rzp.io/i/{link_id}"
            return {
                "id": link_id,
                "entity": "payment_link",
                "amount": payload.get("amount"),
                "currency": payload.get("currency", "INR"),
                "status": "created",
                "reference_id": reference_id,
                "short_url": short_url,
                "description": payload.get("description", "AgentX B2B Procurement Order")
            }

        try:
            response = getattr(self.client, "payment_link").create(payload)
            return response
        except Exception as e:
            logger.error(f"Razorpay SDK create_payment_link failed: {str(e)}")
            raise

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
        """
        Verify Razorpay HMAC-SHA256 signature using exact raw request body bytes.
        """
        if not signature or not secret:
            return False

        try:
            expected_signature = hmac.new(
                secret.encode("utf-8"),
                raw_body,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Error computing HMAC-SHA256 webhook signature: {str(e)}")
            return False
