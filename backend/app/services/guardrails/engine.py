import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.config import settings
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.order import Order, ApprovalStatus, PaymentStatus
from app.models.product import Product
from app.models.vendor import Vendor
from app.models.audit_event import AuditEvent, ActorType
from app.models.negotiation_trace import NegotiationTrace

from app.services.guardrails.constants import POLICY_VERSION, HUMAN_APPROVAL_THRESHOLD, DEFAULT_CURRENCY
from app.services.guardrails.schemas import (
    GuardrailResult,
    RuleValidationResult,
    PolicyViolation,
    ApprovalActionResponse
)
from app.services.guardrails.rules import (
    validate_max_unit_price,
    validate_max_budget,
    validate_quantity_integrity,
    validate_delivery_time,
    validate_certifications,
    validate_gst_verification,
    validate_currency_consistency,
    validate_entity_integrity
)
from app.services.guardrails.exceptions import (
    PolicyViolationException,
    InvalidApprovalStateException,
    DealTamperedException
)

logger = logging.getLogger("agentx.guardrails.engine")


class GuardrailEngine:
    """
    Deterministic Financial Safety Guardrail & Policy Engine.
    Independently calculates financial totals, enforces compliance rules,
    evaluates human approval thresholds, and manages immutability snapshots.
    """

    @staticmethod
    def run_policy_check(
        request_id: int,
        db: Session,
        override_deal: Optional[Dict[str, Any]] = None
    ) -> GuardrailResult:
        """
        Execute deterministic policy validation for a procurement request.
        """
        logger.info(f"Starting policy check for Procurement Request ID {request_id}")

        p_req = db.query(ProcurementRequest).filter_by(id=request_id).first()
        if not p_req:
            raise ValueError(f"ProcurementRequest ID {request_id} not found.")

        # Update request status to POLICY_CHECK if in early active stage
        if p_req.execution_status in [
            ExecutionStatus.CREATED.value,
            ExecutionStatus.PARSING.value,
            ExecutionStatus.DISCOVERING.value,
            ExecutionStatus.NEGOTIATING.value
        ]:
            p_req.execution_status = ExecutionStatus.POLICY_CHECK.value

        # Log policy check started audit event
        db.add(AuditEvent(
            request_id=request_id,
            event_type="POLICY_CHECK_STARTED",
            actor=ActorType.GUARDRAIL_ENGINE.value,
            event_data={"policy_version": POLICY_VERSION}
        ))
        db.commit()

        # Extract authoritative constraints from procurement request
        constraints = p_req.extracted_constraints or {}
        requested_quantity = int(constraints.get("quantity") or 1)
        max_unit_price = Decimal(str(constraints.get("max_unit_price"))) if constraints.get("max_unit_price") is not None else None
        max_budget = p_req.max_budget or (Decimal(str(constraints.get("max_budget"))) if constraints.get("max_budget") is not None else None)
        lead_time_val = constraints.get("max_lead_time_days")
        max_lead_time_days = int(lead_time_val) if lead_time_val is not None else None
        required_certs = constraints.get("required_certifications") or []

        # Find negotiated deal details (from existing Order, override_deal, or NegotiationTrace & AuditEvent)
        order = db.query(Order).filter_by(request_id=request_id).order_by(Order.id.desc()).first()

        product_id: Optional[int] = None
        vendor_id: Optional[int] = None
        negotiated_unit_price: Optional[Decimal] = None
        negotiated_quantity: int = requested_quantity

        if override_deal:
            product_id = override_deal.get("product_id")
            vendor_id = override_deal.get("vendor_id")
            negotiated_unit_price = Decimal(str(override_deal.get("negotiated_unit_price")))
            negotiated_quantity = int(override_deal.get("quantity", requested_quantity))
        elif order:
            product_id = order.product_id
            vendor_id = order.vendor_id
            negotiated_unit_price = order.negotiated_unit_price
            negotiated_quantity = order.quantity
        else:
            # Look up last DEAL_AGREED audit event or negotiation trace
            deal_audit = db.query(AuditEvent).filter(
                AuditEvent.request_id == request_id,
                AuditEvent.event_type == "DEAL_AGREED"
            ).order_by(AuditEvent.id.desc()).first()

            if deal_audit and deal_audit.event_data:
                ed = deal_audit.event_data
                product_id = ed.get("product_id")
                vendor_id = ed.get("vendor_id")
                negotiated_unit_price = Decimal(str(ed.get("final_unit_price"))) if ed.get("final_unit_price") else None

            # Fallback to latest negotiation trace proposed/counter price if needed
            if negotiated_unit_price is None:
                last_trace = db.query(NegotiationTrace).filter_by(request_id=request_id).order_by(NegotiationTrace.turn_number.desc()).first()
                if last_trace and last_trace.counter_price:
                    negotiated_unit_price = last_trace.counter_price

        if not product_id or not vendor_id or negotiated_unit_price is None:
            raise ValueError(f"No valid negotiated deal found for ProcurementRequest ID {request_id}.")

        product = db.query(Product).filter_by(id=product_id).first()
        vendor = db.query(Vendor).filter_by(id=vendor_id).first()

        if not product or not vendor:
            raise ValueError("Product or Vendor record not found for validated deal.")

        # Independent server-side total calculation: total = quantity * unit_price
        total_amount = Decimal(str(round(negotiated_quantity * negotiated_unit_price, 2)))

        # Run 8 deterministic validation rules
        rules: List[RuleValidationResult] = []
        violations: List[PolicyViolation] = []

        def run_rule(res_tuple):
            r_res, r_viol = res_tuple
            rules.append(r_res)
            if r_viol:
                violations.append(r_viol)
                db.add(AuditEvent(
                    request_id=request_id,
                    event_type="POLICY_RULE_FAILED",
                    actor=ActorType.SYSTEM.value,
                    event_data={
                        "rule_name": r_res.rule_name,
                        "actual": r_res.actual_value,
                        "expected": r_res.expected_value,
                        "reason": r_res.message
                    }
                ))
            else:
                db.add(AuditEvent(
                    request_id=request_id,
                    event_type="POLICY_RULE_PASSED",
                    actor=ActorType.SYSTEM.value,
                    event_data={
                        "rule_name": r_res.rule_name,
                        "actual": r_res.actual_value,
                        "message": r_res.message
                    }
                ))

        # Rule 1: Max unit price
        run_rule(validate_max_unit_price(negotiated_unit_price, max_unit_price))

        # Rule 2: Max budget
        run_rule(validate_max_budget(total_amount, max_budget))

        # Rule 3: Quantity integrity
        run_rule(validate_quantity_integrity(negotiated_quantity, requested_quantity))

        # Rule 4: Delivery time
        run_rule(validate_delivery_time(product.lead_time_days, max_lead_time_days))

        # Rule 5: Required certifications
        run_rule(validate_certifications(product.certifications, required_certs))

        # Rule 6: Vendor GST verification
        run_rule(validate_gst_verification(vendor.gst_verified))

        # Rule 7: Currency consistency
        run_rule(validate_currency_consistency(DEFAULT_CURRENCY, DEFAULT_CURRENCY, DEFAULT_CURRENCY))

        # Rule 8: Product & Vendor entity integrity
        run_rule(validate_entity_integrity(request_id, product_id, vendor_id, request_id, product_id, vendor_id))

        all_rules_passed = len(violations) == 0
        now_dt = datetime.now(timezone.utc)

        # Build deal snapshot for immutability
        snapshot = {
            "request_id": request_id,
            "product_id": product_id,
            "vendor_id": vendor_id,
            "quantity": negotiated_quantity,
            "negotiated_unit_price": float(negotiated_unit_price),
            "total_amount": float(total_amount),
            "currency": DEFAULT_CURRENCY,
            "lead_time_days": product.lead_time_days,
            "certifications": product.certifications or [],
            "policy_version": POLICY_VERSION,
            "validated_at": now_dt.isoformat()
        }

        # Upsert Order record
        if not order:
            order = Order(
                request_id=request_id,
                vendor_id=vendor_id,
                product_id=product_id,
                quantity=negotiated_quantity,
                negotiated_unit_price=negotiated_unit_price,
                total_amount=total_amount,
                currency=DEFAULT_CURRENCY,
                approval_status=ApprovalStatus.PENDING.value,
                payment_status=PaymentStatus.NOT_STARTED.value,
                deal_snapshot=snapshot
            )
            db.add(order)
            db.flush()
        else:
            order.vendor_id = vendor_id
            order.product_id = product_id
            order.quantity = negotiated_quantity
            order.negotiated_unit_price = negotiated_unit_price
            order.total_amount = total_amount
            order.currency = DEFAULT_CURRENCY
            order.deal_snapshot = snapshot

        # Determine approval requirement: strictly total_amount > HUMAN_APPROVAL_THRESHOLD
        approval_required = False
        final_status = ""

        if not all_rules_passed:
            final_status = "POLICY_VIOLATION"
            p_req.execution_status = ExecutionStatus.FAILED.value
            order.approval_status = ApprovalStatus.REJECTED.value

            db.add(AuditEvent(
                request_id=request_id,
                event_type="POLICY_VIOLATION",
                actor=ActorType.SYSTEM.value,
                event_data={
                    "violations_count": len(violations),
                    "policy_version": POLICY_VERSION
                }
            ))
        else:
            if total_amount > HUMAN_APPROVAL_THRESHOLD:
                approval_required = True
                if order.approval_status == ApprovalStatus.APPROVED.value or p_req.execution_status in [
                    ExecutionStatus.READY_FOR_PAYMENT.value,
                    ExecutionStatus.PAYMENT_PENDING.value,
                    ExecutionStatus.PAID.value,
                    ExecutionStatus.COMPLETED.value
                ]:
                    final_status = "PASS"
                else:
                    final_status = "APPROVAL_REQUIRED"
                    p_req.execution_status = ExecutionStatus.APPROVAL_REQUIRED.value
                    order.approval_status = ApprovalStatus.PENDING.value

                db.add(AuditEvent(
                    request_id=request_id,
                    event_type="APPROVAL_REQUIRED",
                    actor=ActorType.SYSTEM.value,
                    event_data={
                        "total_amount": float(total_amount),
                        "threshold": float(HUMAN_APPROVAL_THRESHOLD),
                        "reason": f"Total amount ₹{total_amount:,.2f} exceeds human approval threshold ₹{HUMAN_APPROVAL_THRESHOLD:,.2f}."
                    }
                ))
            else:
                approval_required = False
                final_status = "READY_FOR_PAYMENT"
                if p_req.execution_status not in [
                    ExecutionStatus.PAYMENT_PENDING.value,
                    ExecutionStatus.PAID.value,
                    ExecutionStatus.COMPLETED.value
                ]:
                    p_req.execution_status = ExecutionStatus.READY_FOR_PAYMENT.value
                order.approval_status = ApprovalStatus.NOT_REQUIRED.value

                db.add(AuditEvent(
                    request_id=request_id,
                    event_type="PAYMENT_READY",
                    actor=ActorType.SYSTEM.value,
                    event_data={
                        "total_amount": float(total_amount),
                        "reason": f"Total amount ₹{total_amount:,.2f} is within threshold ₹{HUMAN_APPROVAL_THRESHOLD:,.2f}."
                    }
                ))

        db.add(AuditEvent(
            request_id=request_id,
            event_type="POLICY_CHECK_COMPLETED",
            actor=ActorType.SYSTEM.value,
            event_data={
                "status": final_status,
                "all_rules_passed": all_rules_passed,
                "approval_required": approval_required,
                "total_amount": float(total_amount),
                "policy_version": POLICY_VERSION
            }
        ))

        db.commit()
        db.refresh(order)

        return GuardrailResult(
            request_id=request_id,
            order_id=order.id,
            status=final_status,
            all_rules_passed=all_rules_passed,
            approval_required=approval_required,
            total_amount=total_amount,
            currency=DEFAULT_CURRENCY,
            rules=rules,
            violations=violations,
            policy_version=POLICY_VERSION,
            validated_at=now_dt
        )

    @staticmethod
    def approve_deal(
        request_id: int,
        db: Session,
        notes: Optional[str] = None
    ) -> ApprovalActionResponse:
        """
        Grant human approval for a pending deal.
        Re-validates deal immutability and rules before authorizing. Idempotent.
        """
        p_req = db.query(ProcurementRequest).filter_by(id=request_id).first()
        if not p_req:
            raise ValueError(f"ProcurementRequest ID {request_id} not found.")

        order = db.query(Order).filter_by(request_id=request_id).order_by(Order.id.desc()).first()
        if not order:
            raise ValueError(f"No order record found for ProcurementRequest ID {request_id}.")

        # Idempotency check: If already approved and payment ready, return existing state
        if (
            order.approval_status == ApprovalStatus.APPROVED.value
            and p_req.execution_status in [ExecutionStatus.READY_FOR_PAYMENT.value, ExecutionStatus.PAYMENT_PENDING.value]
        ):
            return ApprovalActionResponse(
                request_id=request_id,
                order_id=order.id,
                approval_status=ApprovalStatus.APPROVED.value,
                execution_status=p_req.execution_status,
                message="Deal is already approved and ready for payment."
            )

        if order.approval_status == ApprovalStatus.REJECTED.value:
            raise InvalidApprovalStateException(f"ProcurementRequest ID {request_id} was previously rejected and cannot be approved.")

        if p_req.execution_status != ExecutionStatus.APPROVAL_REQUIRED.value or order.approval_status != ApprovalStatus.PENDING.value:
            raise InvalidApprovalStateException(f"ProcurementRequest ID {request_id} is not currently awaiting approval (Status: {p_req.execution_status}).")

        # Verify snapshot integrity first
        if order.deal_snapshot:
            snap = order.deal_snapshot
            if (
                snap.get("product_id") != order.product_id or
                snap.get("vendor_id") != order.vendor_id or
                snap.get("quantity") != order.quantity or
                Decimal(str(snap.get("negotiated_unit_price"))) != order.negotiated_unit_price or
                Decimal(str(snap.get("total_amount"))) != order.total_amount
            ):
                raise DealTamperedException("Deal details have been tampered with or modified since policy check.")

        # Update approval and execution status
        order.approval_status = ApprovalStatus.APPROVED.value
        p_req.execution_status = ExecutionStatus.READY_FOR_PAYMENT.value

        db.add(AuditEvent(
            request_id=request_id,
            event_type="APPROVAL_GRANTED",
            actor=ActorType.HUMAN_ADMIN.value,
            event_data={
                "order_id": order.id,
                "notes": notes,
                "total_amount": float(order.total_amount)
            }
        ))
        db.add(AuditEvent(
            request_id=request_id,
            event_type="PAYMENT_READY",
            actor=ActorType.SYSTEM.value,
            event_data={
                "order_id": order.id,
                "reason": "Human approval granted."
            }
        ))

        db.commit()

        return ApprovalActionResponse(
            request_id=request_id,
            order_id=order.id,
            approval_status=ApprovalStatus.APPROVED.value,
            execution_status=ExecutionStatus.READY_FOR_PAYMENT.value,
            message=f"Procurement request ID {request_id} successfully approved and marked ready for payment."
        )

    @staticmethod
    def reject_deal(
        request_id: int,
        db: Session,
        notes: Optional[str] = None
    ) -> ApprovalActionResponse:
        """
        Reject a pending deal. Idempotent.
        """
        p_req = db.query(ProcurementRequest).filter_by(id=request_id).first()
        if not p_req:
            raise ValueError(f"ProcurementRequest ID {request_id} not found.")

        order = db.query(Order).filter_by(request_id=request_id).order_by(Order.id.desc()).first()
        if not order:
            raise ValueError(f"No order record found for ProcurementRequest ID {request_id}.")

        # Idempotency check: If already rejected, return existing state
        if (
            order.approval_status == ApprovalStatus.REJECTED.value
            and p_req.execution_status == ExecutionStatus.CANCELLED.value
        ):
            return ApprovalActionResponse(
                request_id=request_id,
                order_id=order.id,
                approval_status=ApprovalStatus.REJECTED.value,
                execution_status=ExecutionStatus.CANCELLED.value,
                message="Deal is already rejected."
            )

        if order.approval_status == ApprovalStatus.APPROVED.value:
            raise InvalidApprovalStateException(f"ProcurementRequest ID {request_id} has already been approved and cannot be rejected.")

        if p_req.execution_status != ExecutionStatus.APPROVAL_REQUIRED.value or order.approval_status != ApprovalStatus.PENDING.value:
            raise InvalidApprovalStateException(f"ProcurementRequest ID {request_id} is not currently awaiting approval.")

        # Update approval and execution status
        order.approval_status = ApprovalStatus.REJECTED.value
        p_req.execution_status = ExecutionStatus.CANCELLED.value

        db.add(AuditEvent(
            request_id=request_id,
            event_type="APPROVAL_REJECTED",
            actor=ActorType.HUMAN_ADMIN.value,
            event_data={
                "order_id": order.id,
                "notes": notes,
                "total_amount": float(order.total_amount)
            }
        ))

        db.commit()

        return ApprovalActionResponse(
            request_id=request_id,
            order_id=order.id,
            approval_status=ApprovalStatus.REJECTED.value,
            execution_status=ExecutionStatus.CANCELLED.value,
            message=f"Procurement request ID {request_id} has been rejected."
        )
