import json
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.config import settings
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.order import Order, PaymentStatus
from app.models.audit_event import AuditEvent, ActorType

from app.services.payments.constants import (
    EVENT_PAYMENT_LINK_PAID,
    EVENT_PAYMENT_LINK_PARTIALLY_PAID,
    EVENT_PAYMENT_LINK_CANCELLED,
    EVENT_PAYMENT_LINK_EXPIRED,
    INR_PAISE_MULTIPLIER
)
from app.services.payments.schemas import WebhookProcessResponse
from app.services.payments.razorpay_client import RazorpayClientWrapper
from app.services.payments.exceptions import (
    InvalidWebhookSignatureException,
    PaymentAmountMismatchException
)

logger = logging.getLogger("agentx.payments.webhook_service")


class WebhookService:
    """
    Webhook Service for handling Razorpay webhook notifications.
    Enforces HMAC-SHA256 signature verification over raw request body bytes,
    event idempotency tracking via event ID, and payment state transitions.
    """

    @staticmethod
    def process_webhook(
        raw_body: bytes,
        signature: str,
        event_id: Optional[str],
        db: Session
    ) -> WebhookProcessResponse:
        """
        Process Razorpay webhook payload safely after raw HMAC signature verification.
        """
        logger.info(f"Processing webhook request (Event ID: {event_id})")

        # 1. Mandatory Raw HMAC-SHA256 Signature Verification
        is_valid_sig = RazorpayClientWrapper.verify_webhook_signature(
            raw_body=raw_body,
            signature=signature,
            secret=settings.RAZORPAY_WEBHOOK_SECRET
        )

        if not is_valid_sig:
            logger.warning("Razorpay webhook signature verification failed.")
            # Log audit event if DB transaction is possible
            try:
                db.add(AuditEvent(
                    request_id=1,  # System fallback
                    event_type="PAYMENT_WEBHOOK_SIGNATURE_FAILED",
                    actor=ActorType.WEBHOOK.value,
                    event_data={"event_id": event_id, "signature": signature[:10] + "..." if signature else None}
                ))
                db.commit()
            except Exception:
                pass
            raise InvalidWebhookSignatureException("Invalid Razorpay webhook signature.")

        # 2. Event Idempotency Check
        if event_id:
            existing_event = db.query(AuditEvent).filter(
                AuditEvent.event_type.in_([
                    "PAYMENT_CONFIRMED",
                    "PAYMENT_CANCELLED",
                    "PAYMENT_EXPIRED",
                    "PAYMENT_WEBHOOK_PROCESSED"
                ]),
                AuditEvent.event_data.op("->>")("event_id") == event_id
            ).first()

            if existing_event:
                logger.info(f"Duplicate webhook event ID '{event_id}' detected. Skipping state mutation.")
                db.add(AuditEvent(
                    request_id=existing_event.request_id,
                    event_type="PAYMENT_WEBHOOK_DUPLICATE",
                    actor=ActorType.WEBHOOK.value,
                    event_data={"event_id": event_id}
                ))
                db.commit()
                return WebhookProcessResponse(
                    status="duplicate",
                    event_id=event_id,
                    message="Webhook event already processed."
                )

        # 3. Parse JSON Payload strictly AFTER signature verification
        try:
            payload: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse webhook JSON body: {str(e)}")
            raise ValueError(f"Invalid JSON payload: {str(e)}")

        event_name = payload.get("event")
        plink_entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

        link_id = plink_entity.get("id")
        ref_id = plink_entity.get("reference_id")

        if not link_id and not ref_id:
            logger.warning(f"Webhook payload missing payment link ID and reference ID for event '{event_name}'.")
            return WebhookProcessResponse(
                status="ignored",
                event_id=event_id,
                message="Missing payment link identifier."
            )

        # Query Order by razorpay_payment_link_id or reference_id (AGENTX-{order_id})
        order: Optional[Order] = None
        if link_id:
            order = db.query(Order).filter_by(razorpay_payment_link_id=link_id).first()

        if not order and ref_id and ref_id.startswith("AGENTX-"):
            try:
                order_id_val = int(ref_id.replace("AGENTX-", ""))
                order = db.query(Order).filter_by(id=order_id_val).first()
            except ValueError:
                pass

        if not order:
            logger.warning(f"No matching AgentX Order found for Payment Link ID '{link_id}' / Ref '{ref_id}'.")
            return WebhookProcessResponse(
                status="ignored",
                event_id=event_id,
                message="Order not found for payment link."
            )

        p_req = db.query(ProcurementRequest).filter_by(id=order.request_id).first()

        # 4. Handle Specific Event Types
        if event_name == EVENT_PAYMENT_LINK_PAID:
            paid_amount_paise = plink_entity.get("amount_paid") or payment_entity.get("amount") or 0
            expected_amount_paise = int(order.total_amount * INR_PAISE_MULTIPLIER)

            # Amount validation
            if paid_amount_paise < expected_amount_paise:
                logger.error(f"Payment amount mismatch for Order #{order.id}: Expected {expected_amount_paise} paise, received {paid_amount_paise} paise.")
                db.add(AuditEvent(
                    request_id=order.request_id,
                    event_type="PAYMENT_AMOUNT_MISMATCH",
                    actor=ActorType.WEBHOOK.value,
                    event_data={
                        "event_id": event_id,
                        "expected_paise": expected_amount_paise,
                        "paid_paise": paid_amount_paise
                    }
                ))
                db.commit()
                raise PaymentAmountMismatchException(f"Paid amount ({paid_amount_paise}) is less than expected amount ({expected_amount_paise}).")

            # Update Order & ProcurementRequest state to PAID / COMPLETED
            order.payment_status = PaymentStatus.PAID.value
            if payment_entity.get("id"):
                order.razorpay_payment_id = payment_entity.get("id")

            if p_req:
                p_req.execution_status = ExecutionStatus.COMPLETED.value

            db.add(AuditEvent(
                request_id=order.request_id,
                event_type="PAYMENT_CONFIRMED",
                actor=ActorType.WEBHOOK.value,
                event_data={
                    "event_id": event_id,
                    "order_id": order.id,
                    "razorpay_payment_id": order.razorpay_payment_id,
                    "amount_paid": float(order.total_amount)
                }
            ))
            db.add(AuditEvent(
                request_id=order.request_id,
                event_type="PAYMENT_WEBHOOK_PROCESSED",
                actor=ActorType.WEBHOOK.value,
                event_data={"event_id": event_id, "event_name": event_name}
            ))
            db.commit()

            return WebhookProcessResponse(
                status="success",
                event_id=event_id,
                message=f"Order #{order.id} successfully marked as PAID."
            )

        elif event_name == EVENT_PAYMENT_LINK_PARTIALLY_PAID:
            amount_paid = plink_entity.get("amount_paid") or payment_entity.get("amount") or 0
            db.add(AuditEvent(
                request_id=order.request_id,
                event_type="PAYMENT_PARTIALLY_PAID",
                actor=ActorType.WEBHOOK.value,
                event_data={"event_id": event_id, "amount_paid_paise": amount_paid}
            ))
            db.commit()
            return WebhookProcessResponse(
                status="success",
                event_id=event_id,
                message=f"Partial payment recorded for Order #{order.id}."
            )

        elif event_name == EVENT_PAYMENT_LINK_CANCELLED:
            order.payment_status = PaymentStatus.CANCELLED.value
            if p_req:
                p_req.execution_status = ExecutionStatus.CANCELLED.value

            db.add(AuditEvent(
                request_id=order.request_id,
                event_type="PAYMENT_CANCELLED",
                actor=ActorType.WEBHOOK.value,
                event_data={"event_id": event_id}
            ))
            db.commit()
            return WebhookProcessResponse(
                status="success",
                event_id=event_id,
                message=f"Payment link cancelled for Order #{order.id}."
            )

        elif event_name == EVENT_PAYMENT_LINK_EXPIRED:
            order.payment_status = PaymentStatus.EXPIRED.value
            if p_req:
                p_req.execution_status = ExecutionStatus.FAILED.value

            db.add(AuditEvent(
                request_id=order.request_id,
                event_type="PAYMENT_EXPIRED",
                actor=ActorType.WEBHOOK.value,
                event_data={"event_id": event_id}
            ))
            db.commit()
            return WebhookProcessResponse(
                status="success",
                event_id=event_id,
                message=f"Payment link expired for Order #{order.id}."
            )

        else:
            logger.info(f"Unhandled webhook event '{event_name}'.")
            return WebhookProcessResponse(
                status="ignored",
                event_id=event_id,
                message=f"Event '{event_name}' ignored."
            )
