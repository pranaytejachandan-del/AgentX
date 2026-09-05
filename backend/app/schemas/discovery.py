from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.procurement import ProcurementConstraintSchema


class OfferCandidate(BaseModel):
    """Schema representing an evaluated product/vendor offer candidate."""
    product_id: int
    vendor_id: int
    vendor_name: str
    product_name: str
    sku: str
    base_price: Decimal
    min_allowable_price: Decimal
    lead_time_days: int
    vendor_rating: float
    gst_verified: bool
    certifications: List[str] = Field(default_factory=list)
    semantic_similarity: float = Field(..., description="Cosine semantic similarity score (0.0 to 1.0)")
    
    # Normalized component scores (0.0 to 1.0)
    price_score: float = Field(..., description="Normalized price score (40% weight)")
    lead_time_score: float = Field(..., description="Normalized lead time score (30% weight)")
    rating_score: float = Field(..., description="Normalized vendor rating score (20% weight)")
    gst_score: float = Field(..., description="Normalized GST compliance score (10% weight)")
    overall_score: float = Field(..., description="Weighted composite offer score")
    
    eligibility_status: str = Field(..., description="'ELIGIBLE', 'INELIGIBLE', or 'NEAR_MATCH'")
    eligibility_reasons: List[str] = Field(default_factory=list, description="Machine-readable evaluation reasons")


class DiscoverOffersRequest(BaseModel):
    """Request payload for vendor offer discovery."""
    constraints: ProcurementConstraintSchema
    top_k: int = Field(default=20, ge=1, le=100, description="Number of candidate vector matches to fetch")
    request_id: Optional[int] = Field(default=None, description="Optional associated ProcurementRequest ID")


class DiscoverOffersResponse(BaseModel):
    """Response payload returned by vendor discovery service."""
    status: str = Field(..., description="'success' or 'no_eligible_offers'")
    candidate_count: int = Field(..., description="Number of candidates retrieved from vector search")
    offers: List[OfferCandidate] = Field(default_factory=list, description="Top ranked ELIGIBLE offers (up to 3)")
    near_matches: List[OfferCandidate] = Field(default_factory=list, description="Optional near-match offers if eligible pool is small")
    message: Optional[str] = Field(default=None, description="Summary or explanation message")
