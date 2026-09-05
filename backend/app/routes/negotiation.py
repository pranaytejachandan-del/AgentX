import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.negotiation import NegotiateOfferRequest, NegotiationResultResponse
from app.services.negotiation_engine import run_negotiation
from app.database.connection import get_db

logger = logging.getLogger("agentx.routes.negotiation")
router = APIRouter(prefix="/api/procurement", tags=["Negotiation Engine"])


@router.post(
    "/negotiate",
    response_model=NegotiationResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute bounded multi-turn negotiation between Buyer Agent and Supplier Simulator"
)
async def negotiate_offer(
    payload: NegotiateOfferRequest,
    db: Session = Depends(get_db)
):
    """
    Orchestrate bounded stateful multi-turn negotiation using LangGraph FSM (max 4 turns).
    Enforces strict buyer ceiling (max_unit_price) and synthetic supplier floor (min_allowable_price),
    persisting per-turn traces and audit events to PostgreSQL.
    """
    try:
        response = await run_negotiation(
            payload=payload,
            db=db
        )
        return response
    except Exception as e:
        logger.error(f"Unexpected error in /api/procurement/negotiate: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during offer negotiation."
        )
