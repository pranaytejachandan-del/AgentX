from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.schemas.procurement import ProcurementConstraintSchema
from app.schemas.discovery import OfferCandidate


class BuyerNegotiationAction(BaseModel):
    """Structured action proposed by Buyer Agent."""
    action: str = Field(..., description="'COUNTER_OFFER', 'ACCEPT', or 'WALK_AWAY'")
    proposed_unit_price: Decimal = Field(..., description="Proposed buyer price per unit")
    message: str = Field(..., description="Natural language negotiation pitch message")
    reason: str = Field(..., description="Strategic reasoning for the action")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in ["COUNTER_OFFER", "ACCEPT", "WALK_AWAY"]:
            raise ValueError(f"Invalid action '{v}'. Must be COUNTER_OFFER, ACCEPT, or WALK_AWAY.")
        return upper


class NegotiationTurnTrace(BaseModel):
    """Per-turn trace item of a negotiation session."""
    turn_number: int
    buyer_agent_message: Optional[str] = None
    supplier_agent_message: Optional[str] = None
    proposed_price: Optional[Decimal] = None
    counter_price: Optional[Decimal] = None
    negotiation_status: str
    decision_summary: Optional[str] = None
    timestamp: str


class NegotiateOfferRequest(BaseModel):
    """Request payload for multi-turn offer negotiation."""
    request_id: Optional[int] = Field(default=None, description="Associated ProcurementRequest ID")
    offer: OfferCandidate = Field(..., description="Top offer candidate to negotiate")
    constraints: ProcurementConstraintSchema = Field(..., description="User's validated procurement constraints")


class NegotiationResultResponse(BaseModel):
    """Final negotiation result response."""
    status: str = Field(..., description="'DEAL_AGREED' or 'NEGOTIATION_FAILED'")
    request_id: Optional[int] = None
    product_id: int
    vendor_id: int
    turns_used: int
    initial_price: Decimal
    final_unit_price: Decimal
    total_amount: Decimal
    target_unit_price: Optional[Decimal] = None
    max_unit_price: Decimal
    savings_per_unit: Decimal
    total_savings: Decimal
    negotiation_summary: str
    trace: List[NegotiationTurnTrace] = Field(default_factory=list)
