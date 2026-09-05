import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.discovery import DiscoverOffersRequest, DiscoverOffersResponse
from app.services.vendor_discovery import discover_offers
from app.database.connection import get_db

logger = logging.getLogger("agentx.routes.discovery")
router = APIRouter(prefix="/api/procurement", tags=["Vendor Discovery Engine"])


@router.post(
    "/discover",
    response_model=DiscoverOffersResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover, hard-filter, score, and rank top product/vendor offers"
)
def discover_vendor_offers(
    payload: DiscoverOffersRequest,
    db: Session = Depends(get_db)
):
    """
    Search product catalog using pgvector, apply deterministic hard procurement constraints,
    calculate weighted offer scores (Price 40%, Lead Time 30%, Vendor Rating 20%, GST 10%),
    and return top-ranked eligible offers.
    """
    try:
        response = discover_offers(
            constraints=payload.constraints,
            top_k=payload.top_k,
            db=db,
            request_id=payload.request_id
        )
        return response
    except Exception as e:
        logger.error(f"Unexpected error in /api/procurement/discover: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while discovering vendor offers."
        )
