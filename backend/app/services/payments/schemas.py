from typing import Optional
from pydantic import BaseModel, Field


class PaymentLinkResponse(BaseModel):
    request_id: int
    order_id: int
    payment_status: str
    razorpay_payment_link_id: str
    payment_url: str
    amount: int = Field(..., description="Amount in smallest currency unit (paise)")
    currency: str = "INR"


class WebhookProcessResponse(BaseModel):
    status: str
    event_id: Optional[str] = None
    message: str
