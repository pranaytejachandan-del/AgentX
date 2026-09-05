import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.order import Order, ApprovalStatus, PaymentStatus
from app.models.audit_event import AuditEvent, ActorType

from app.services.guardrails import GuardrailEngine
from app.services.payments.constants import INR_PAISE_MULTIPLIER, DEFAULT_CURRENCY, REFERENCE_PREFIX
from app.services.payments.schemas import PaymentLinkResponse
from app.services.payments.razorpay_client import RazorpayClientWrapper
from app.services.payments.exceptions import InvalidPaymentStateException

logger = logging.getLogger("agentx.payments.payment_service")


class PaymentService:
    """
    Service for initializing Razorpay Payment Links with strict pre-payment guardrail validation,
    authoritative server-side amount calculation, and idempotency control.
    """

    @staticmethod
    def create_payment_link(request_id: int, db: Session) -> PaymentLinkResponse:
        """
        Create a Razorpay Payment Link for a deal in READY_FOR_PAYMENT state.
        """
        logger.info(f"Payment link creation requested for Procurement Request ID {request_id}")

        p_req = db.query(ProcurementRequest).filter_by(id=request_id).first()
        if not p_req:
            raise ValueError(f"ProcurementRequest ID {request_id} not found.")

        # Log creation request audit event
        db.add(AuditEvent(
            request_id=request_id,
            event_type="PAYMENT_CREATION_REQUESTED",
            actor=ActorType.USER.value,
            event_data={"current_status": p_req.execution_status}
        ))
        db.commit()

        # Check status security boundary
        allowed_statuses = [
            ExecutionStatus.READY_FOR_PAYMENT.value,
            ExecutionStatus.PAYMENT_PENDING.value,
        ]

        if p_req.execution_status in [
            ExecutionStatus.APPROVAL_REQUIRED.value,
            ExecutionStatus.FAILED.value,
            ExecutionStatus.CANCELLED.value,
            ExecutionStatus.PAID.value,
            ExecutionStatus.COMPLETED.value
        ]:
            raise InvalidPaymentStateException(
                f"Cannot create payment link for request in status '{p_req.execution_status}'."
            )

        if p_req.execution_status not in allowed_statuses:
            raise InvalidPaymentStateException(
                f"Payment creation requires status READY_FOR_PAYMENT or PAYMENT_PENDING, got '{p_req.execution_status}'."
            )

        order = db.query(Order).filter_by(request_id=request_id).order_by(Order.id.desc()).first()
        if not order:
            raise ValueError(f"No order record found for ProcurementRequest ID {request_id}.")

        if order.approval_status == ApprovalStatus.PENDING.value or p_req.execution_status == ExecutionStatus.APPROVAL_REQUIRED.value:
            raise InvalidPaymentStateException("Payment creation blocked: Deal requires human approval which has not been granted.")

        if order.approval_status == ApprovalStatus.REJECTED.value:
            raise InvalidPaymentStateException("Payment creation blocked: Deal was rejected.")

        # Idempotency check: If link already created and payment pending, return existing active link
        if order.razorpay_payment_link_id and order.razorpay_payment_link_url and order.payment_status == PaymentStatus.PAYMENT_PENDING.value:
            logger.info(f"Returning existing active payment link '{order.razorpay_payment_link_id}' for Order #{order.id}")
            amount_paise = int(order.total_amount * INR_PAISE_MULTIPLIER)
            return PaymentLinkResponse(
                request_id=request_id,
                order_id=order.id,
                payment_status=order.payment_status,
                razorpay_payment_link_id=order.razorpay_payment_link_id,
                payment_url=order.razorpay_payment_link_url,
                amount=amount_paise,
                currency=order.currency or DEFAULT_CURRENCY
            )

        # Re-fetch order (already validated at policy check, snapshot ensures immutability)
        order = db.query(Order).filter_by(request_id=request_id).order_by(Order.id.desc()).first()
        if not order:
            raise ValueError(f"No order found for procurement request {request_id}")

        # Validate snapshot integrity & vendor verification
        if order.deal_snapshot:
            snap = order.deal_snapshot
            if (
                snap.get("product_id") != order.product_id or
                snap.get("vendor_id") != order.vendor_id or
                snap.get("quantity") != order.quantity or
                Decimal(str(snap.get("negotiated_unit_price"))) != order.negotiated_unit_price or
                Decimal(str(snap.get("total_amount"))) != order.total_amount
            ):
                raise InvalidPaymentStateException("Deal details have been tampered with or modified since policy check.")

        from app.models.vendor import Vendor
        vendor = db.query(Vendor).filter_by(id=order.vendor_id).first()
        if not vendor or not vendor.gst_verified:
            raise InvalidPaymentStateException(f"Vendor ID {order.vendor_id} is not GST verified.")

        # Authoritative server-side amount calculation
        total_amount = order.total_amount
        amount_paise = int(total_amount * INR_PAISE_MULTIPLIER)
        currency = order.currency or DEFAULT_CURRENCY
        reference_id = f"{REFERENCE_PREFIX}{order.id}"

        payment_payload = {
            "amount": amount_paise,
            "currency": currency,
            "reference_id": reference_id,
            "description": f"AgentX Order #{order.id} for Procurement Request #{request_id}",
            "callback_url": settings.RAZORPAY_CALLBACK_URL,
            "callback_method": "get"
        }

        # Create Payment Link via Razorpay SDK client
        client_wrapper = RazorpayClientWrapper()
        try:
            link_resp = client_wrapper.create_payment_link(payment_payload)
        except Exception as e:
            logger.error(f"Failed to create Razorpay Payment Link: {str(e)}")
            order.payment_failure_reason = str(e)
            db.commit()
            raise ValueError(f"Razorpay Payment Link creation failed: {str(e)}")

        link_id = link_resp["id"]
        short_url = link_resp["short_url"]
        now_dt = datetime.now(timezone.utc)

        # Persist Razorpay identifiers and status
        order.razorpay_payment_link_id = link_id
        order.razorpay_payment_link_url = short_url
        order.payment_link_created_at = now_dt
        order.payment_status = PaymentStatus.PAYMENT_PENDING.value
        p_req.execution_status = ExecutionStatus.PAYMENT_PENDING.value

        db.add(AuditEvent(
            request_id=request_id,
            event_type="PAYMENT_LINK_CREATED",
            actor=ActorType.PAYMENT_SERVICE.value,
            event_data={
                "order_id": order.id,
                "razorpay_payment_link_id": link_id,
                "payment_url": short_url,
                "amount_paise": amount_paise,
                "currency": currency,
                "timestamp": now_dt.isoformat()
            }
        ))

        db.commit()
        db.refresh(order)

        return PaymentLinkResponse(
            request_id=request_id,
            order_id=order.id,
            payment_status=order.payment_status,
            razorpay_payment_link_id=link_id,
            payment_url=short_url,
            amount=amount_paise,
            currency=currency
        )
