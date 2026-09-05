import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.schemas.procurement import (
    ProcurementConstraintSchema,
    ParseProcurementResponse
)
from app.services.llm_provider import get_llm_provider
from app.exceptions.intent_exceptions import IncompletePromptException
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.user import User

logger = logging.getLogger("agentx.intent_parser")


async def parse_procurement_prompt(
    prompt: str,
    user_id: Optional[int] = None,
    db: Optional[Session] = None
) -> ParseProcurementResponse:
    """
    Parse a natural language procurement request into strict ProcurementConstraintSchema,
    run validation and normalization, and optionally persist to PostgreSQL.
    """
    if not prompt or not prompt.strip():
        logger.error("Received empty procurement prompt.")
        raise IncompletePromptException("Procurement prompt cannot be empty.")

    clean_prompt = prompt.strip()
    logger.info(f"Parsing procurement prompt: '{clean_prompt[:60]}...'")

    # 1. Get configured LLM provider and extract constraints
    provider = get_llm_provider()
    constraints = await provider.extract_constraints(clean_prompt)

    # 2. Perform post-extraction normalization & consistency validation
    # Deduplicate certifications
    if constraints.required_certifications:
        seen = set()
        deduped = []
        for cert in constraints.required_certifications:
            clean_cert = cert.strip().upper()
            if clean_cert not in seen:
                seen.add(clean_cert)
                deduped.append(clean_cert)
        constraints.required_certifications = deduped

    # Price consistency check
    if (
        constraints.target_unit_price is not None
        and constraints.max_unit_price is not None
        and constraints.target_unit_price > constraints.max_unit_price
    ):
        logger.warning(
            f"Invalid price relationship: target ({constraints.target_unit_price}) > max ({constraints.max_unit_price})"
        )
        constraints.needs_clarification = True
        if "target_unit_price" not in constraints.ambiguous_fields:
            constraints.ambiguous_fields.append("target_unit_price")
        if "max_unit_price" not in constraints.ambiguous_fields:
            constraints.ambiguous_fields.append("max_unit_price")

    # Check missing required fields
    missing_fields = list(constraints.missing_required_fields)
    if constraints.quantity is None and "quantity" not in missing_fields:
        missing_fields.append("quantity")
    if (
        constraints.target_unit_price is None
        and constraints.max_unit_price is None
        and "max_unit_price" not in missing_fields
    ):
        missing_fields.append("max_unit_price")

    if missing_fields:
        constraints.missing_required_fields = missing_fields
        constraints.needs_clarification = True

    # Determine status & human readable message
    if constraints.needs_clarification:
        status_text = "needs_clarification"
        msg_parts = []
        if constraints.missing_required_fields:
            msg_parts.append(f"Missing required fields: {', '.join(constraints.missing_required_fields)}")
        if constraints.ambiguous_fields:
            msg_parts.append(f"Ambiguous or inconsistent fields: {', '.join(constraints.ambiguous_fields)}")
        message = "Please clarify your procurement requirements. " + " ".join(msg_parts)
    else:
        status_text = "parsed"
        message = "Procurement constraints successfully parsed and validated."

    # 3. Optional DB Persistence
    request_id: Optional[int] = None
    if db is not None:
        try:
            # Resolve user_id or use default user
            target_user_id = user_id
            if not target_user_id:
                default_user = db.query(User).filter_by(email="manager@company.com").first()
                if default_user:
                    target_user_id = default_user.id
                else:
                    # Fallback to first user in database
                    first_user = db.query(User).first()
                    target_user_id = first_user.id if first_user else 1

            # Calculate total max budget if quantity and max price available
            max_budget = None
            if constraints.quantity and constraints.max_unit_price:
                max_budget = constraints.quantity * constraints.max_unit_price

            procurement_req = ProcurementRequest(
                user_id=target_user_id,
                raw_prompt=clean_prompt,
                extracted_constraints=constraints.model_dump(mode="json"),
                execution_status=ExecutionStatus.CREATED.value,
                max_budget=max_budget
            )
            db.add(procurement_req)
            db.commit()
            db.refresh(procurement_req)
            request_id = procurement_req.id
            logger.info(f"Persisted ProcurementRequest record (ID: {request_id}) with status '{procurement_req.execution_status}'")
        except Exception as db_err:
            db.rollback()
            logger.error(f"Failed to persist ProcurementRequest record: {str(db_err)}")

    return ParseProcurementResponse(
        status=status_text,
        request_id=request_id,
        constraints=constraints,
        missing_fields=constraints.missing_required_fields if constraints.needs_clarification else [],
        message=message
    )
