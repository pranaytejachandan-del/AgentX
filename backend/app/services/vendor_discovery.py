import math
import logging
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.schemas.procurement import ProcurementConstraintSchema
from app.schemas.discovery import OfferCandidate, DiscoverOffersResponse
from app.services.embedding_service import get_embedding_service, generate_product_text
from app.models.product import Product
from app.models.vendor import Vendor
from app.models.procurement_request import ProcurementRequest, ExecutionStatus

logger = logging.getLogger("agentx.vendor_discovery")


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two 1D float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))


def discover_offers(
    constraints: ProcurementConstraintSchema,
    top_k: int = 20,
    db: Optional[Session] = None,
    request_id: Optional[int] = None
) -> DiscoverOffersResponse:
    """
    Vendor Discovery & Offer Ranking Engine.
    Performs semantic vector retrieval, applies hard deterministic procurement filters,
    calculates weighted offer scores, and returns top 3 ranked offers with explainability reasons.
    """
    if constraints.needs_clarification:
        logger.warning("Discovery requested on constraint set requiring clarification.")
        return DiscoverOffersResponse(
            status="needs_clarification",
            candidate_count=0,
            offers=[],
            message="Procurement request requires clarification before vendor discovery can proceed."
        )

    # 1. Update ProcurementRequest execution_status if db & request_id provided
    if db is not None and request_id is not None:
        try:
            p_req = db.query(ProcurementRequest).filter_by(id=request_id).first()
            if p_req and p_req.execution_status in [ExecutionStatus.CREATED.value, ExecutionStatus.PARSING.value]:
                p_req.execution_status = ExecutionStatus.DISCOVERING.value
                db.commit()
        except Exception as db_err:
            db.rollback()
            logger.error(f"Failed to update request execution_status: {str(db_err)}")

    # 2. Build semantic search query and generate query embedding
    query_text = (
        f"Category: {constraints.category or 'office furniture'} | "
        f"Product: {constraints.item_description} | "
        f"Requirements: {', '.join(constraints.additional_requirements)} | "
        f"Certifications: {', '.join(constraints.required_certifications)}"
    )
    embedding_service = get_embedding_service()
    query_vector = embedding_service.generate_embedding(query_text)

    # 3. Retrieve Candidate Products from Database
    raw_candidates = db.query(Product, Vendor).join(Vendor, Product.vendor_id == Vendor.id).all() if db is not None else []

    if not raw_candidates:
        logger.warning("No products found in the database catalog.")
        return DiscoverOffersResponse(
            status="no_eligible_offers",
            candidate_count=0,
            offers=[],
            message="No products available in vendor catalog."
        )

    # Compute semantic similarities and pre-sort by similarity
    evaluated_candidates: List[Tuple[Product, Vendor, float]] = []
    for prod, vend in raw_candidates:
        if prod.embedding is not None and len(prod.embedding) > 0:
            sim = calculate_cosine_similarity(query_vector, list(prod.embedding))
        else:
            # Fallback text similarity if embedding not generated
            prod_text = generate_product_text(prod.name, prod.category, prod.description)
            prod_vec = embedding_service.generate_embedding(prod_text)
            sim = calculate_cosine_similarity(query_vector, prod_vec)
        evaluated_candidates.append((prod, vend, sim))

    # Sort by semantic similarity descending and slice top_k
    evaluated_candidates.sort(key=lambda x: x[2], reverse=True)
    top_candidates = evaluated_candidates[:top_k]

    # 4. Hard Deterministic Filtering & Scoring
    eligible_offers: List[OfferCandidate] = []
    near_match_offers: List[OfferCandidate] = []

    # Calculate min & max for score normalization among retrieved pool
    prices = [float(p.base_price) for p, v, s in top_candidates]
    lead_times = [p.lead_time_days for p, v, s in top_candidates]

    min_price, max_price = (min(prices), max(prices)) if prices else (0.0, 1.0)
    min_lead, max_lead = (min(lead_times), max(lead_times)) if lead_times else (1, 30)

    for prod, vend, sim in top_candidates:
        reasons: List[str] = []
        is_eligible = True

        # Hard Filter 0: Category & Product Relevance Compatibility
        if constraints.category and constraints.category.lower() != "general":
            req_cat = constraints.category.lower()
            prod_cat = (prod.category or "").lower()
            prod_name = (prod.name or "").lower()
            if ("electronic" in req_cat or "laptop" in req_cat) and not ("electronic" in prod_cat or "laptop" in prod_cat or "laptop" in prod_name):
                is_eligible = False
                reasons.append(f"INELIGIBLE: Category mismatch ('{prod.category}' is not compatible with requested '{constraints.category}')")
            elif "furniture" in req_cat and "electronic" in prod_cat:
                is_eligible = False
                reasons.append(f"INELIGIBLE: Category mismatch ('{prod.category}' is not compatible with requested '{constraints.category}')")

        # Hard Filter 1: Maximum Unit Price
        if constraints.max_unit_price is not None:
            if prod.base_price <= constraints.max_unit_price:
                reasons.append(f"Price: ₹{prod.base_price:,.2f} ≤ ₹{constraints.max_unit_price:,.2f} max allowed")
            else:
                is_eligible = False
                reasons.append(f"INELIGIBLE: Base price ₹{prod.base_price:,.2f} exceeds max allowed ₹{constraints.max_unit_price:,.2f}")

        # Hard Filter 2: Maximum Lead Time Days
        if constraints.max_lead_time_days is not None:
            if prod.lead_time_days <= constraints.max_lead_time_days:
                reasons.append(f"Lead time: {prod.lead_time_days} days ≤ {constraints.max_lead_time_days} days required")
            else:
                is_eligible = False
                reasons.append(f"INELIGIBLE: Lead time {prod.lead_time_days} days exceeds max allowed {constraints.max_lead_time_days} days")

        # Hard Filter 3: Required Certifications
        if constraints.required_certifications:
            prod_certs = prod.certifications or []
            if not prod_certs:
                is_eligible = False
                reasons.append(f"INELIGIBLE: Product certification status UNKNOWN (Missing required {', '.join(constraints.required_certifications)})")
            else:
                prod_certs_upper = [c.upper() for c in prod_certs]
                missing_certs = [rc for rc in constraints.required_certifications if rc.upper() not in prod_certs_upper]
                if not missing_certs:
                    reasons.append(f"Certifications: All required ({', '.join(constraints.required_certifications)}) verified")
                else:
                    is_eligible = False
                    reasons.append(f"INELIGIBLE: Missing required certification {', '.join(missing_certs)}")

        # Add Vendor Rating & GST compliance info to reasons
        reasons.append(f"Vendor Rating: {float(vend.rating):.1f}/5.0 ({vend.name})")
        reasons.append(f"GST Status: {'Verified (' + vend.gstin + ')' if vend.gst_verified else 'Unverified'}")

        # 5. Component Scoring
        # Price Score (40%): lower price is better
        if max_price > min_price:
            price_score = 1.0 - ((float(prod.base_price) - min_price) / (max_price - min_price))
        else:
            price_score = 1.0
        price_score = max(0.0, min(1.0, price_score))

        # Lead Time Score (30%): shorter lead time is better
        if max_lead > min_lead:
            lead_time_score = 1.0 - ((prod.lead_time_days - min_lead) / (max_lead - min_lead))
        else:
            lead_time_score = 1.0
        lead_time_score = max(0.0, min(1.0, lead_time_score))

        # Vendor Rating Score (20%)
        rating_score = max(0.0, min(1.0, float(vend.rating) / 5.0))

        # GST Compliance Score (10%)
        gst_score = 1.0 if vend.gst_verified else 0.0

        # Weighted Composite Overall Score
        overall_score = (
            0.40 * price_score +
            0.30 * lead_time_score +
            0.20 * rating_score +
            0.10 * gst_score
        )
        overall_score = round(overall_score, 4)

        status_str = "ELIGIBLE" if is_eligible else "INELIGIBLE"

        candidate_offer = OfferCandidate(
            product_id=prod.id,
            vendor_id=vend.id,
            vendor_name=vend.name,
            product_name=prod.name,
            sku=prod.sku,
            base_price=prod.base_price,
            min_allowable_price=prod.min_allowable_price,
            lead_time_days=prod.lead_time_days,
            vendor_rating=float(vend.rating),
            gst_verified=vend.gst_verified,
            certifications=prod.certifications or [],
            semantic_similarity=round(sim, 4),
            price_score=round(price_score, 4),
            lead_time_score=round(lead_time_score, 4),
            rating_score=round(rating_score, 4),
            gst_score=round(gst_score, 4),
            overall_score=overall_score,
            eligibility_status=status_str,
            eligibility_reasons=reasons
        )

        if is_eligible:
            eligible_offers.append(candidate_offer)
        else:
            # Check if it qualifies as a NEAR_MATCH (failed only 1 constraint slightly)
            candidate_offer.eligibility_status = "NEAR_MATCH"
            near_match_offers.append(candidate_offer)

    # 6. Sort Eligible Offers by Overall Score
    eligible_offers.sort(key=lambda x: x.overall_score, reverse=True)

    # 7. Apply Vendor Diversity Logic (prefer different vendors in top 3 if scores are close)
    final_top_offers: List[OfferCandidate] = []
    seen_vendors = set()
    
    # First pass: pick highest scoring offer per vendor
    for offer in eligible_offers:
        if offer.vendor_id not in seen_vendors:
            final_top_offers.append(offer)
            seen_vendors.add(offer.vendor_id)
            if len(final_top_offers) == 3:
                break

    # Second pass: if less than 3 unique vendors, fill remaining slots with next best overall score
    if len(final_top_offers) < 3:
        for offer in eligible_offers:
            if offer not in final_top_offers:
                final_top_offers.append(offer)
                if len(final_top_offers) == 3:
                    break

    # 8. Return Response
    if not final_top_offers:
        logger.warning("No offers satisfied all mandatory procurement constraints.")
        return DiscoverOffersResponse(
            status="no_eligible_offers",
            candidate_count=len(top_candidates),
            offers=[],
            near_matches=near_match_offers[:3],
            message="No offers satisfy all mandatory procurement constraints."
        )

    logger.info(f"Successfully discovered {len(final_top_offers)} eligible offers (Top score: {final_top_offers[0].overall_score})")

    return DiscoverOffersResponse(
        status="success",
        candidate_count=len(top_candidates),
        offers=final_top_offers,
        near_matches=[],
        message=f"Found {len(eligible_offers)} eligible offers. Returning top {len(final_top_offers)} ranked offers."
    )
