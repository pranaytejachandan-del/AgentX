import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.payments import WebhookService, WebhookProcessResponse
from app.services.payments.exceptions import (
    InvalidWebhookSignatureException,
    PaymentAmountMismatchException
)

logger = logging.getLogger("agentx.routes.payments")
router = APIRouter(prefix="/api/payments", tags=["Payments & Webhooks"])


@router.post(
    "/webhook",
    response_model=WebhookProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process raw Razorpay webhook events with HMAC-SHA256 signature verification"
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: Optional[str] = Header(None, alias="x-razorpay-event-id"),
    db: Session = Depends(get_db)
):
    """
    Receive raw Razorpay webhook events, compute HMAC-SHA256 signature over exact raw bytes,
    and process payment state updates idempotently.
    """
    if not x_razorpay_signature:
        logger.warning("Webhook request missing X-Razorpay-Signature header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header."
        )

    # Read raw body bytes directly for exact signature matching
    raw_body = await request.body()

    try:
        response = WebhookService.process_webhook(
            raw_body=raw_body,
            signature=x_razorpay_signature,
            event_id=x_razorpay_event_id,
            db=db
        )
        return response
    except InvalidWebhookSignatureException as e:
        logger.warning(f"Webhook signature failure: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except PaymentAmountMismatchException as e:
        logger.error(f"Payment amount mismatch in webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in payment webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while processing payment webhook."
        )


@router.get(
    "/callback",
    status_code=status.HTTP_200_OK,
    summary="Handle browser payment completion callback"
)
@router.post(
    "/callback",
    status_code=status.HTTP_200_OK,
    summary="Handle browser payment completion callback"
)
async def razorpay_callback(request: Request):
    """
    Browser redirect endpoint after user payment attempt.
    Note: Webhook verification remains the sole authoritative confirmation of payment status.
    """
    return {
        "status": "callback_received",
        "message": "Payment processing result will be authoritatively confirmed via server webhook."
    }
