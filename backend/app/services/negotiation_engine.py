import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, cast
from typing_extensions import TypedDict
from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END

from app.schemas.procurement import ProcurementConstraintSchema
from app.schemas.discovery import OfferCandidate
from app.schemas.negotiation import (
    NegotiateOfferRequest,
    NegotiationResultResponse,
    NegotiationTurnTrace
)
from app.services.buyer_agent import get_buyer_action
from app.services.supplier_simulator import SupplierSimulator
from app.models.negotiation_trace import NegotiationTrace, NegotiationStatus
from app.models.audit_event import AuditEvent, ActorType
from app.models.procurement_request import ProcurementRequest, ExecutionStatus

logger = logging.getLogger("agentx.negotiation_engine")

MAX_TURNS = 4


class NegotiationStateDict(TypedDict):
    request_id: Optional[int]
    product_id: int
    vendor_id: int
    quantity: int
    target_unit_price: Optional[Decimal]
    max_unit_price: Decimal
    supplier_base_price: Decimal
    supplier_min_allowable_price: Decimal
    current_buyer_offer: Optional[Decimal]
    current_supplier_offer: Decimal
    current_turn: int
    max_turns: int
    negotiation_status: str
    buyer_message: Optional[str]
    supplier_message: Optional[str]
    agreed_unit_price: Optional[Decimal]
    decision_summary: Optional[str]
    trace: List[Dict[str, Any]]


async def node_initialize(state: NegotiationStateDict) -> NegotiationStateDict:
    """Initialize negotiation session and validate baseline feasibility."""
    logger.info(f"Initializing negotiation for product ID {state['product_id']} (Turn 1/{state['max_turns']})")
    
    # Check baseline economic feasibility
    if state["supplier_min_allowable_price"] > state["max_unit_price"]:
        state["negotiation_status"] = "NEGOTIATION_FAILED"
        state["decision_summary"] = (
            f"Supplier minimum price (₹{state['supplier_min_allowable_price']:,.2f}) "
            f"exceeds buyer maximum budget ceiling (₹{state['max_unit_price']:,.2f})."
        )
    else:
        state["negotiation_status"] = "INITIALIZED"
        state["decision_summary"] = "Negotiation session initialized successfully."
        
    return state


async def node_buyer_turn(state: NegotiationStateDict) -> NegotiationStateDict:
    """Execute Buyer Agent turn."""
    if state["negotiation_status"] in ["DEAL_AGREED", "NEGOTIATION_FAILED"]:
        return state

    action = await get_buyer_action(
        target_unit_price=state["target_unit_price"],
        max_unit_price=state["max_unit_price"],
        quantity=state["quantity"],
        supplier_current_offer=state["current_supplier_offer"],
        previous_buyer_offer=state["current_buyer_offer"],
        turn_number=state["current_turn"],
        max_turns=state["max_turns"]
    )

    # Independent validation: proposed price <= max_unit_price
    proposed_price = action.proposed_unit_price
    if proposed_price > state["max_unit_price"]:
        logger.warning(f"Proposed price ₹{proposed_price} > max budget ₹{state['max_unit_price']}. Clamping to max.")
        proposed_price = state["max_unit_price"]

    state["current_buyer_offer"] = proposed_price
    state["buyer_message"] = action.message
    state["negotiation_status"] = "BUYER_OFFER"
    
    logger.info(f"Turn {state['current_turn']}: Buyer offered ₹{proposed_price:,.2f}")
    return state


async def node_supplier_turn(state: NegotiationStateDict) -> NegotiationStateDict:
    """Execute Supplier Simulator turn."""
    if state["negotiation_status"] in ["DEAL_AGREED", "NEGOTIATION_FAILED"]:
        return state

    buyer_offer = state["current_buyer_offer"] or Decimal("0")

    supplier_action, new_supplier_offer, supplier_msg = SupplierSimulator.evaluate_buyer_offer(
        base_price=state["supplier_base_price"],
        min_allowable_price=state["supplier_min_allowable_price"],
        current_supplier_offer=state["current_supplier_offer"],
        buyer_offer=buyer_offer,
        turn_number=state["current_turn"],
        max_turns=state["max_turns"]
    )

    state["current_supplier_offer"] = new_supplier_offer
    state["supplier_message"] = supplier_msg

    if supplier_action == "ACCEPT":
        state["negotiation_status"] = "DEAL_AGREED"
        state["agreed_unit_price"] = new_supplier_offer
        state["decision_summary"] = f"Supplier accepted buyer offer of ₹{new_supplier_offer:,.2f} per unit on turn {state['current_turn']}."
    else:
        state["negotiation_status"] = "SUPPLIER_RESPONSE"

    logger.info(f"Turn {state['current_turn']}: Supplier counter ₹{new_supplier_offer:,.2f} (Action: {supplier_action})")
    return state


async def node_evaluate_deal(state: NegotiationStateDict) -> NegotiationStateDict:
    """Evaluate turn status and determine if deal is agreed or requires another turn."""
    # Append trace record for current turn
    now_iso = datetime.now(timezone.utc).isoformat()
    turn_summary = f"Buyer: ₹{state['current_buyer_offer'] or 0:,.2f} | Supplier: ₹{state['current_supplier_offer']:,.2f}"

    trace_entry = {
        "turn_number": state["current_turn"],
        "buyer_agent_message": state.get("buyer_message"),
        "supplier_agent_message": state.get("supplier_message"),
        "proposed_price": state.get("current_buyer_offer"),
        "counter_price": state.get("current_supplier_offer"),
        "negotiation_status": state["negotiation_status"],
        "decision_summary": state.get("decision_summary") or turn_summary,
        "timestamp": now_iso
    }
    state["trace"].append(trace_entry)

    # Check termination conditions
    if state["negotiation_status"] == "DEAL_AGREED":
        return state

    supplier_offer = state["current_supplier_offer"]

    # Deal acceptance rule: supplier offer <= max_unit_price AND supplier offer >= min_allowable_price
    cur_buyer = state.get("current_buyer_offer")
    buyer_accepted = cur_buyer is not None and cur_buyer >= supplier_offer
    if (
        supplier_offer <= state["max_unit_price"]
        and supplier_offer >= state["supplier_min_allowable_price"]
        and (buyer_accepted or state["current_turn"] >= state["max_turns"])
    ):
        state["negotiation_status"] = "DEAL_AGREED"
        state["agreed_unit_price"] = supplier_offer
        state["decision_summary"] = f"Deal agreed at ₹{supplier_offer:,.2f} per unit on turn {state['current_turn']}."
        return state

    # Max turns reached condition
    if state["current_turn"] >= state["max_turns"]:
        state["negotiation_status"] = "NEGOTIATION_FAILED"
        state["decision_summary"] = (
            f"Negotiation failed after reaching maximum allowed turns ({state['max_turns']}). "
            f"Final supplier counter ₹{supplier_offer:,.2f} remained above target/budget."
        )
    else:
        # Increment turn for next iteration
        state["current_turn"] += 1

    return state


def route_next_step(state: NegotiationStateDict) -> str:
    """Conditional routing function for LangGraph FSM."""
    status_val = state["negotiation_status"]
    if status_val in ["DEAL_AGREED", "NEGOTIATION_FAILED"]:
        return "end"
    elif status_val == "INITIALIZED" or status_val == "SUPPLIER_RESPONSE":
        return "buyer_turn"
    elif status_val == "BUYER_OFFER":
        return "supplier_turn"
    elif status_val == "EVALUATE_DEAL":
        return "buyer_turn"
    return "end"


def build_negotiation_graph() -> Any:
    """Construct LangGraph StateGraph workflow for multi-turn negotiation."""
    workflow = StateGraph(cast(Any, NegotiationStateDict))

    workflow.add_node("initialize", node_initialize)
    workflow.add_node("buyer_turn", node_buyer_turn)
    workflow.add_node("supplier_turn", node_supplier_turn)
    workflow.add_node("evaluate_deal", node_evaluate_deal)

    workflow.set_entry_point("initialize")

    workflow.add_conditional_edges(
        "initialize",
        route_next_step,
        {"end": END, "buyer_turn": "buyer_turn"}
    )
    workflow.add_edge("buyer_turn", "supplier_turn")
    workflow.add_edge("supplier_turn", "evaluate_deal")
    workflow.add_conditional_edges(
        "evaluate_deal",
        route_next_step,
        {"end": END, "buyer_turn": "buyer_turn"}
    )

    return workflow.compile()


async def run_negotiation(
    payload: NegotiateOfferRequest,
    db: Optional[Session] = None
) -> NegotiationResultResponse:
    """
    Execute stateful multi-turn negotiation workflow using LangGraph orchestration.
    Persists per-turn NegotiationTraces and AuditEvents to PostgreSQL.
    """
    offer = payload.offer
    constraints = payload.constraints
    request_id = payload.request_id

    # Baseline economic values
    base_price = offer.base_price
    min_allowable_price = offer.min_allowable_price
    max_unit_price = constraints.max_unit_price if constraints.max_unit_price is not None else base_price
    target_unit_price = constraints.target_unit_price

    initial_state: NegotiationStateDict = {
        "request_id": request_id,
        "product_id": offer.product_id,
        "vendor_id": offer.vendor_id,
        "quantity": constraints.quantity or 1,
        "target_unit_price": target_unit_price,
        "max_unit_price": max_unit_price,
        "supplier_base_price": base_price,
        "supplier_min_allowable_price": min_allowable_price,
        "current_buyer_offer": None,
        "current_supplier_offer": base_price,
        "current_turn": 1,
        "max_turns": MAX_TURNS,
        "negotiation_status": "INITIALIZED",
        "buyer_message": None,
        "supplier_message": None,
        "agreed_unit_price": None,
        "decision_summary": None,
        "trace": []
    }

    # Compile and execute LangGraph app
    app = build_negotiation_graph()
    final_state = await app.ainvoke(initial_state)

    status_result = final_state["negotiation_status"]
    agreed_price = final_state.get("agreed_unit_price") or final_state["current_supplier_offer"]
    turns_used = len(final_state["trace"])
    quantity = final_state["quantity"]

    total_amount = Decimal(str(round(quantity * agreed_price, 2)))
    savings_per_unit = max(Decimal("0"), base_price - agreed_price)
    total_savings = Decimal(str(round(quantity * savings_per_unit, 2)))

    # Persist traces & audit events if db and request_id exist
    if db is not None and request_id is not None:
        from app.models.order import Order as OrderModel, ApprovalStatus as OrderApprovalStatus, PaymentStatus as OrderPaymentStatus
        try:
            # Update ProcurementRequest execution status
            p_req = db.query(ProcurementRequest).filter_by(id=request_id).first()
            if p_req:
                if status_result == "DEAL_AGREED":
                    p_req.execution_status = ExecutionStatus.POLICY_CHECK.value
                else:
                    p_req.execution_status = ExecutionStatus.FAILED.value

            # Save per-turn NegotiationTraces
            for item in final_state["trace"]:
                trace_rec = NegotiationTrace(
                    request_id=request_id,
                    turn_number=item["turn_number"],
                    buyer_agent_message=item.get("buyer_agent_message"),
                    supplier_agent_message=item.get("supplier_agent_message"),
                    proposed_price=item.get("proposed_price"),
                    counter_price=item.get("counter_price"),
                    negotiation_status=item["negotiation_status"],
                    decision_summary=item.get("decision_summary")
                )
                db.add(trace_rec)

            # Persist/update Order record with negotiated deal
            if status_result == "DEAL_AGREED" and p_req:
                existing_order = db.query(OrderModel).filter_by(request_id=request_id).first()
                if existing_order:
                    existing_order.vendor_id = offer.vendor_id
                    existing_order.product_id = offer.product_id
                    existing_order.quantity = final_state["quantity"]
                    existing_order.negotiated_unit_price = agreed_price
                    existing_order.total_amount = total_amount
                else:
                    new_order = OrderModel(
                        request_id=request_id,
                        vendor_id=offer.vendor_id,
                        product_id=offer.product_id,
                        quantity=final_state["quantity"],
                        negotiated_unit_price=agreed_price,
                        total_amount=total_amount,
                        currency="INR",
                        approval_status=OrderApprovalStatus.PENDING.value,
                        payment_status=OrderPaymentStatus.NOT_STARTED.value,
                    )
                    db.add(new_order)

            # Log Audit Event
            audit_event = AuditEvent(
                request_id=request_id,
                event_type="DEAL_AGREED" if status_result == "DEAL_AGREED" else "NEGOTIATION_FAILED",
                actor=ActorType.NEGOTIATION_AGENT.value,
                event_data={
                    "status": status_result,
                    "product_id": offer.product_id,
                    "vendor_id": offer.vendor_id,
                    "turns_used": turns_used,
                    "final_unit_price": float(agreed_price),
                    "total_amount": float(total_amount),
                    "total_savings": float(total_savings)
                }
            )
            db.add(audit_event)
            db.commit()
            logger.info(f"Persisted {turns_used} negotiation traces and audit event for Request ID {request_id}")
        except Exception as db_err:
            db.rollback()
            logger.error(f"Failed to persist negotiation traces: {str(db_err)}")

    # Format trace output response
    trace_responses: List[NegotiationTurnTrace] = [
        NegotiationTurnTrace(
            turn_number=t["turn_number"],
            buyer_agent_message=t.get("buyer_agent_message"),
            supplier_agent_message=t.get("supplier_agent_message"),
            proposed_price=t.get("proposed_price"),
            counter_price=t.get("counter_price"),
            negotiation_status=t["negotiation_status"],
            decision_summary=t.get("decision_summary"),
            timestamp=t["timestamp"]
        ) for t in final_state["trace"]
    ]

    summary_text = (
        final_state.get("decision_summary") or
        f"Negotiation finished with status {status_result} after {turns_used} turns."
    )

    return NegotiationResultResponse(
        status=status_result,
        request_id=request_id,
        product_id=offer.product_id,
        vendor_id=offer.vendor_id,
        turns_used=turns_used,
        initial_price=base_price,
        final_unit_price=agreed_price,
        total_amount=total_amount,
        target_unit_price=target_unit_price,
        max_unit_price=max_unit_price,
        savings_per_unit=savings_per_unit,
        total_savings=total_savings,
        negotiation_summary=summary_text,
        trace=trace_responses
    )
