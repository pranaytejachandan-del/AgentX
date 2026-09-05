import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.procurement import ParseProcurementRequest, ParseProcurementResponse
from app.services.intent_parser import parse_procurement_prompt
from app.exceptions.intent_exceptions import IncompletePromptException, IntentParserException
from app.database.connection import get_db

from app.services.guardrails import GuardrailEngine, GuardrailResult
from app.services.guardrails.schemas import ApprovalActionRequest, ApprovalActionResponse
from app.services.guardrails.exceptions import (
    PolicyViolationException,
    InvalidApprovalStateException,
    DealTamperedException
)

from app.models.order import Order
from app.models.procurement_request import ProcurementRequest
from app.models.negotiation_trace import NegotiationTrace
from app.models.audit_event import AuditEvent
from app.schemas.procurement import ProcurementConstraintSchema
from app.schemas.discovery import DiscoverOffersResponse
from app.schemas.negotiation import NegotiateOfferRequest
from app.services.vendor_discovery import discover_offers
from app.services.negotiation_engine import run_negotiation

from app.services.payments import PaymentService, PaymentLinkResponse
from app.services.payments.exceptions import InvalidPaymentStateException

logger = logging.getLogger("agentx.routes.procurement")
router = APIRouter(prefix="/api/procurement", tags=["Procurement & Guardrails"])


@router.post(
    "/parse",
    response_model=ParseProcurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse natural language procurement prompt into structured constraints"
)
async def parse_prompt(
    payload: ParseProcurementRequest,
    db: Session = Depends(get_db)
):
    """
    Parse a user's natural language procurement prompt into strict, validated, machine-readable
    ProcurementConstraintSchema constraints and persist the procurement request record.
    """
    try:
        response = await parse_procurement_prompt(
            prompt=payload.prompt,
            user_id=payload.user_id,
            db=db
        )
        return response
    except IncompletePromptException as e:
        logger.warning(f"Incomplete prompt submitted: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except IntentParserException as e:
        logger.error(f"Intent parser exception: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in /api/procurement/parse: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while parsing procurement constraints."
        )


@router.post(
    "/{request_id}/policy-check",
    response_model=GuardrailResult,
    status_code=status.HTTP_200_OK,
    summary="Execute deterministic financial guardrails and policy validation for a procurement request"
)
async def execute_policy_check(
    request_id: int,
    db: Session = Depends(get_db)
):
    """
    Run 8 deterministic financial and business policy rules on the negotiated deal stored in the database.
    Evaluates human approval threshold (> ₹100,000) and produces immutable deal snapshot.
    """
    try:
        result = GuardrailEngine.run_policy_check(request_id=request_id, db=db)
        return result
    except ValueError as e:
        logger.warning(f"Policy check not found / invalid: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PolicyViolationException as e:
        logger.warning(f"Policy violation in request {request_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in policy check for request {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during policy validation."
        )


@router.post(
    "/{request_id}/approve",
    response_model=ApprovalActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Grant human approval for a pending procurement deal"
)
async def approve_procurement_request(
    request_id: int,
    payload: Optional[ApprovalActionRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Grant human approval for a deal awaiting authorization.
    Re-runs policy validation and verifies deal snapshot immutability. Server ignores any financial body overrides.
    """
    try:
        notes = payload.notes if payload else None
        response = GuardrailEngine.approve_deal(request_id=request_id, db=db, notes=notes)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidApprovalStateException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except (PolicyViolationException, DealTamperedException) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error approving request {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during approval execution."
        )


@router.post(
    "/{request_id}/reject",
    response_model=ApprovalActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a pending procurement deal"
)
async def reject_procurement_request(
    request_id: int,
    payload: Optional[ApprovalActionRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Reject a pending procurement deal and stop transaction progression toward payment.
    """
    try:
        notes = payload.notes if payload else None
        response = GuardrailEngine.reject_deal(request_id=request_id, db=db, notes=notes)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidApprovalStateException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error rejecting request {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during rejection execution."
        )


@router.post(
    "/{request_id}/payment",
    response_model=PaymentLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Razorpay Payment Link for a validated READY_FOR_PAYMENT deal"
)
async def create_payment(
    request_id: int,
    db: Session = Depends(get_db)
):
    """
    Initiate Razorpay Payment Link creation for a deal in READY_FOR_PAYMENT state.
    Re-executes Feature 5 guardrails and calculates payment amount server-side (paise).
    Client-supplied price/amount input is ignored.
    """
    try:
        response = PaymentService.create_payment_link(request_id=request_id, db=db)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidPaymentStateException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PolicyViolationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating payment for request {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while creating Razorpay payment link."
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List all procurement requests with dashboard summaries"
)
def list_procurement_requests(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated list of procurement requests for the dashboard with summary metrics.
    """
    from app.models.procurement_request import ProcurementRequest
    from app.models.order import Order

    query = db.query(ProcurementRequest)
    if status_filter:
        query = query.filter(ProcurementRequest.execution_status == status_filter)
    
    total_count = query.count()
    requests = query.order_by(ProcurementRequest.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for req in requests:
        order = db.query(Order).filter(Order.request_id == req.id).first()
        order_summary = None
        if order:
            order_summary = {
                "id": order.id,
                "vendor_id": order.vendor_id,
                "vendor_name": order.vendor.name if order.vendor else None,
                "product_id": order.product_id,
                "product_title": order.product.name if order.product else None,
                "quantity": order.quantity,
                "negotiated_unit_price": float(order.negotiated_unit_price),
                "total_amount": float(order.total_amount),
                "currency": order.currency,
                "approval_status": order.approval_status,
                "payment_status": order.payment_status,
                "razorpay_payment_link_url": order.razorpay_payment_link_url,
                "razorpay_payment_link_id": order.razorpay_payment_link_id
            }
        
        items.append({
            "id": req.id,
            "user_id": req.user_id,
            "raw_prompt": req.raw_prompt,
            "extracted_constraints": req.extracted_constraints,
            "execution_status": req.execution_status,
            "max_budget": float(req.max_budget) if req.max_budget is not None else None,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            "order": order_summary
        })

    # Summary metrics counts
    all_reqs = db.query(ProcurementRequest).all()
    metrics = {
        "total": len(all_reqs),
        "active": sum(1 for r in all_reqs if r.execution_status in ["CREATED", "PARSING", "DISCOVERING", "NEGOTIATING", "POLICY_CHECK"]),
        "awaiting_approval": sum(1 for r in all_reqs if r.execution_status == "APPROVAL_REQUIRED"),
        "payment_pending": sum(1 for r in all_reqs if r.execution_status in ["READY_FOR_PAYMENT", "PAYMENT_PENDING"]),
        "completed": sum(1 for r in all_reqs if r.execution_status in ["PAID", "COMPLETED"]),
        "failed": sum(1 for r in all_reqs if r.execution_status in ["FAILED", "CANCELLED"])
    }

    return {
        "items": items,
        "total": total_count,
        "metrics": metrics
    }


@router.get(
    "/{request_id}",
    status_code=status.HTTP_200_OK,
    summary="Get complete detail and execution trace for a procurement request"
)
def get_procurement_request_detail(
    request_id: int,
    db: Session = Depends(get_db)
):
    """
    Fetch comprehensive request information including parsed constraints, order deal,
    discovered offers, negotiation history, guardrail evaluation, execution trace, and audit log.
    """
    from app.models.procurement_request import ProcurementRequest
    from app.models.order import Order
    from app.models.negotiation_trace import NegotiationTrace
    from app.models.audit_event import AuditEvent
    from app.services.vendor_discovery import discover_offers
    from app.schemas.procurement import ProcurementConstraintSchema

    req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProcurementRequest {request_id} not found."
        )

    order = db.query(Order).filter(Order.request_id == request_id).first()

    # Discovered offers
    offers_data = []
    if req.extracted_constraints:
        try:
            constraints_obj = ProcurementConstraintSchema(**req.extracted_constraints)
            disco_resp = discover_offers(constraints=constraints_obj, top_k=5, db=db, request_id=None)
            offers_data = [o.model_dump(mode="json") for o in disco_resp.offers]
            if not offers_data and disco_resp.near_matches:
                offers_data = [o.model_dump(mode="json") for o in disco_resp.near_matches[:5]]
        except Exception as e:
            logger.warning(f"Could not calculate discovered offers for detail view: {e}")

    # Negotiation traces
    traces = db.query(NegotiationTrace).filter(
        NegotiationTrace.request_id == request_id
    ).order_by(NegotiationTrace.turn_number.asc()).all()

    trace_items = [{
        "id": t.id,
        "turn_number": t.turn_number,
        "buyer_agent_message": t.buyer_agent_message,
        "supplier_agent_message": t.supplier_agent_message,
        "proposed_price": float(t.proposed_price) if t.proposed_price is not None else None,
        "counter_price": float(t.counter_price) if t.counter_price is not None else None,
        "negotiation_status": t.negotiation_status,
        "timestamp": t.timestamp.isoformat() if t.timestamp else None,
        "decision_summary": t.decision_summary
    } for t in traces]

    # Savings & Negotiation summary
    negotiation_summary = None
    if trace_items:
        initial_price = trace_items[0].get("counter_price") or trace_items[0].get("proposed_price") or 0
        final_price = trace_items[-1].get("counter_price") or trace_items[-1].get("proposed_price") or 0
        qty = order.quantity if order else (req.extracted_constraints.get("quantity") if req.extracted_constraints else 1) or 1
        unit_savings = max(0.0, float(initial_price) - float(final_price))
        total_savings = unit_savings * float(qty)

        negotiation_summary = {
            "initial_price": float(initial_price),
            "final_price": float(final_price),
            "quantity": qty,
            "total_amount": float(final_price) * float(qty),
            "unit_savings": unit_savings,
            "total_savings": total_savings,
            "status": trace_items[-1].get("negotiation_status")
        }

    # Guardrails evaluation
    guardrail_result = None
    if order:
        try:
            res = GuardrailEngine.run_policy_check(request_id=request_id, db=db)
            guardrail_result = res.model_dump(mode="json")
            db.refresh(req)
        except PolicyViolationException as e:
            guardrail_result = {
                "request_id": request_id,
                "passed_all": False,
                "requires_human_approval": False,
                "rules": [],
                "error": str(e)
            }
        except Exception as e:
            logger.warning(f"Policy check failed for detail view: {e}")

    # Audit events
    audit_records = db.query(AuditEvent).filter(
        AuditEvent.request_id == request_id
    ).order_by(AuditEvent.timestamp.asc()).all()

    audit_items = [{
        "id": a.id,
        "event_type": a.event_type,
        "actor": a.actor,
        "event_data": a.event_data,
        "timestamp": a.timestamp.isoformat() if a.timestamp else None
    } for a in audit_records]

    # Synthesize execution trace timeline
    execution_trace = []
    execution_trace.append({
        "stage": "REQUEST_CREATED",
        "title": "Request Created",
        "timestamp": req.created_at.isoformat() if req.created_at else None,
        "actor": "USER",
        "summary": f"User submitted procurement prompt: '{req.raw_prompt}'"
    })

    if req.extracted_constraints:
        c = req.extracted_constraints
        execution_trace.append({
            "stage": "PARSING",
            "title": "Intent Parsed",
            "timestamp": req.created_at.isoformat() if req.created_at else None,
            "actor": "INTENT_AGENT",
            "summary": f"Extracted item '{c.get('item_description')}', quantity {c.get('quantity')}, target ₹{c.get('target_unit_price')}, max ₹{c.get('max_unit_price')}"
        })

    if offers_data:
        execution_trace.append({
            "stage": "DISCOVERING",
            "title": "Offers Discovered",
            "timestamp": req.updated_at.isoformat() if req.updated_at else None,
            "actor": "DISCOVERY_AGENT",
            "summary": f"Retrieved candidate offers. Top offer: {offers_data[0].get('product_title')} by {offers_data[0].get('vendor_name')} at ₹{offers_data[0].get('unit_price')}"
        })

    if trace_items:
        execution_trace.append({
            "stage": "NEGOTIATING",
            "title": "Negotiation Completed",
            "timestamp": trace_items[-1].get("timestamp"),
            "actor": "NEGOTIATION_AGENT",
            "summary": f"Completed {len(trace_items)} negotiation turns. Final price: ₹{trace_items[-1].get('counter_price') or trace_items[-1].get('proposed_price')} / unit."
        })

    if guardrail_result:
        passed = guardrail_result.get("passed_all", False)
        requires_appr = guardrail_result.get("requires_human_approval", False)
        summary_text = "All 8 financial guardrail rules passed cleanly." if passed else "Guardrail policy evaluation performed."
        if requires_appr:
            summary_text += " Transaction total > ₹100,000 threshold, requiring Human Approval."
        execution_trace.append({
            "stage": "POLICY_CHECK",
            "title": "Financial Policy Check",
            "timestamp": req.updated_at.isoformat() if req.updated_at else None,
            "actor": "GUARDRAIL_ENGINE",
            "summary": summary_text
        })

    if order:
        if order.approval_status == "APPROVED":
            execution_trace.append({
                "stage": "APPROVAL_REQUIRED",
                "title": "Human Approval Granted",
                "timestamp": order.updated_at.isoformat() if order.updated_at else None,
                "actor": "HUMAN_ADMIN",
                "summary": "Procurement manager approved the negotiated deal."
            })
        elif order.approval_status == "REJECTED":
            execution_trace.append({
                "stage": "APPROVAL_REQUIRED",
                "title": "Human Approval Rejected",
                "timestamp": order.updated_at.isoformat() if order.updated_at else None,
                "actor": "HUMAN_ADMIN",
                "summary": "Procurement manager rejected the transaction."
            })

        if order.razorpay_payment_link_url:
            execution_trace.append({
                "stage": "READY_FOR_PAYMENT",
                "title": "Razorpay Payment Link Created",
                "timestamp": order.payment_link_created_at.isoformat() if order.payment_link_created_at else order.updated_at.isoformat(),
                "actor": "PAYMENT_SERVICE",
                "summary": f"Generated Razorpay Payment Link ID {order.razorpay_payment_link_id} for ₹{float(order.total_amount):,.2f}."
            })

        if order.payment_status == "PAID":
            execution_trace.append({
                "stage": "PAID",
                "title": "Payment Confirmed",
                "timestamp": order.updated_at.isoformat() if order.updated_at else None,
                "actor": "WEBHOOK",
                "summary": f"Razorpay payment confirmed via HMAC-SHA256 verified webhook (Payment ID: {order.razorpay_payment_id})."
            })
            execution_trace.append({
                "stage": "COMPLETED",
                "title": "Procurement Completed",
                "timestamp": order.updated_at.isoformat() if order.updated_at else None,
                "actor": "SYSTEM",
                "summary": "Autonomous procurement workflow successfully completed end-to-end."
            })

    order_data = None
    if order:
        order_data = {
            "id": order.id,
            "request_id": order.request_id,
            "vendor_id": order.vendor_id,
            "vendor_name": order.vendor.name if order.vendor else None,
            "product_id": order.product_id,
            "product_title": order.product.name if order.product else None,
            "quantity": order.quantity,
            "negotiated_unit_price": float(order.negotiated_unit_price),
            "total_amount": float(order.total_amount),
            "currency": order.currency,
            "approval_status": order.approval_status,
            "payment_status": order.payment_status,
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_payment_link_id": order.razorpay_payment_link_id,
            "razorpay_payment_link_url": order.razorpay_payment_link_url,
            "razorpay_payment_id": order.razorpay_payment_id,
            "payment_failure_reason": order.payment_failure_reason,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None
        }

    return {
        "request": {
            "id": req.id,
            "user_id": req.user_id,
            "raw_prompt": req.raw_prompt,
            "extracted_constraints": req.extracted_constraints,
            "execution_status": req.execution_status,
            "max_budget": float(req.max_budget) if req.max_budget is not None else None,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        },
        "order": order_data,
        "discovered_offers": offers_data,
        "negotiation_traces": trace_items,
        "negotiation_summary": negotiation_summary,
        "guardrail_result": guardrail_result,
        "execution_trace": execution_trace,
        "audit_events": audit_items
    }


@router.post(
    "/orchestrate",
    status_code=status.HTTP_200_OK,
    summary="Execute full autonomous AgentX workflow from prompt to policy check"
)
async def orchestrate_procurement_request(
    payload: ParseProcurementRequest,
    db: Session = Depends(get_db)
):
    """
    Run end-to-end autonomous procurement:
    1. Parse natural language prompt.
    2. Discover top catalog offers.
    3. Run multi-turn agent negotiation with top vendor offer.
    4. Execute 8-rule financial policy guardrails.
    5. Set state to APPROVAL_REQUIRED or READY_FOR_PAYMENT.
    """
    from app.schemas.procurement import ProcurementConstraintSchema
    from app.schemas.negotiation import NegotiateOfferRequest
    from app.services.vendor_discovery import discover_offers

    # 1. Parse prompt
    parse_res = await parse_procurement_prompt(prompt=payload.prompt, user_id=payload.user_id, db=db)
    req_id = parse_res.request_id

    if parse_res.status == "needs_clarification" or not req_id:
        if not req_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to parse procurement request prompt")
        return get_procurement_request_detail(request_id=req_id, db=db)

    constraints = parse_res.constraints

    # 2. Discover offers
    disco_res = discover_offers(constraints=constraints, top_k=5, db=db, request_id=req_id)
    
    candidate = None
    if disco_res.offers:
        candidate = disco_res.offers[0]
    elif disco_res.near_matches:
        candidate = disco_res.near_matches[0]

    if not candidate:
        return get_procurement_request_detail(request_id=req_id, db=db)

    # 3. Negotiate offer
    neg_req = NegotiateOfferRequest(
        request_id=req_id,
        offer=candidate,
        constraints=constraints
    )
    await run_negotiation(payload=neg_req, db=db)

    # 4. Policy check
    try:
        GuardrailEngine.run_policy_check(request_id=req_id, db=db)
    except Exception as e:
        logger.warning(f"Orchestrate policy check warning: {e}")

    return get_procurement_request_detail(request_id=req_id, db=db)


@router.post(
    "/reset-demo",
    status_code=status.HTTP_200_OK,
    summary="Reset demo state and re-seed clean product catalog for live judge presentation"
)
def reset_demo_state(db: Session = Depends(get_db)):
    """
    Safely reset demo requests, orders, negotiation traces, and audit events,
    and re-seed baseline product catalog items for clean hackathon demo runs.
    """
    try:
        db.query(AuditEvent).delete()
        db.query(NegotiationTrace).delete()
        db.query(Order).delete()
        db.query(ProcurementRequest).delete()
        db.commit()

        from seed import seed_database
        seed_database(session=db)

        return {
            "status": "success",
            "message": "Demo state reset successfully. Catalog re-seeded for judge presentation."
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting demo state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset demo state."
        )

