from decimal import Decimal
from typing import Optional, List, Tuple, Set, Any
from app.services.guardrails.schemas import RuleValidationResult, PolicyViolation


def validate_max_unit_price(
    negotiated_unit_price: Decimal,
    max_unit_price: Optional[Decimal]
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Maximum Unit Price"
    if max_unit_price is None:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"₹{negotiated_unit_price:,.2f}",
                expected_value="No Limit",
                message="No maximum unit price specified in constraints."
            ),
            None
        )

    if negotiated_unit_price <= max_unit_price:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"₹{negotiated_unit_price:,.2f}",
                expected_value=f"≤ ₹{max_unit_price:,.2f}",
                message=f"Negotiated price ₹{negotiated_unit_price:,.2f} is within maximum ceiling ₹{max_unit_price:,.2f}."
            ),
            None
        )
    else:
        msg = f"Negotiated unit price ₹{negotiated_unit_price:,.2f} exceeds maximum ceiling ₹{max_unit_price:,.2f}."
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=f"₹{negotiated_unit_price:,.2f}",
                expected_value=f"≤ ₹{max_unit_price:,.2f}",
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=float(negotiated_unit_price),
                expected_value=float(max_unit_price),
                severity="HIGH"
            )
        )


def validate_max_budget(
    total_amount: Decimal,
    max_budget: Optional[Decimal]
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Maximum Budget"
    if max_budget is None:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"₹{total_amount:,.2f}",
                expected_value="No Limit",
                message="No maximum budget specified."
            ),
            None
        )

    if total_amount <= max_budget:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"₹{total_amount:,.2f}",
                expected_value=f"≤ ₹{max_budget:,.2f}",
                message=f"Negotiated total amount ₹{total_amount:,.2f} is within budget cap ₹{max_budget:,.2f}."
            ),
            None
        )
    else:
        msg = f"Negotiated total amount ₹{total_amount:,.2f} exceeds budget cap ₹{max_budget:,.2f}."
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=f"₹{total_amount:,.2f}",
                expected_value=f"≤ ₹{max_budget:,.2f}",
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=float(total_amount),
                expected_value=float(max_budget),
                severity="HIGH"
            )
        )


def validate_quantity_integrity(
    negotiated_quantity: int,
    requested_quantity: int
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Quantity Integrity"
    if negotiated_quantity == requested_quantity:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=negotiated_quantity,
                expected_value=requested_quantity,
                message=f"Negotiated quantity ({negotiated_quantity}) matches requested quantity."
            ),
            None
        )
    else:
        msg = f"Negotiated quantity ({negotiated_quantity}) does not match requested quantity ({requested_quantity})."
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=negotiated_quantity,
                expected_value=requested_quantity,
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=negotiated_quantity,
                expected_value=requested_quantity,
                severity="HIGH"
            )
        )


def validate_delivery_time(
    supplier_lead_time_days: int,
    max_lead_time_days: Optional[int]
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Delivery Time"
    if max_lead_time_days is None:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"{supplier_lead_time_days} days",
                expected_value="No Limit",
                message="No maximum lead time specified."
            ),
            None
        )

    if supplier_lead_time_days <= max_lead_time_days:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"{supplier_lead_time_days} days",
                expected_value=f"≤ {max_lead_time_days} days",
                message=f"Supplier lead time ({supplier_lead_time_days} days) satisfies requirement ({max_lead_time_days} days)."
            ),
            None
        )
    else:
        msg = f"Supplier lead time ({supplier_lead_time_days} days) exceeds maximum requirement ({max_lead_time_days} days)."
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=f"{supplier_lead_time_days} days",
                expected_value=f"≤ {max_lead_time_days} days",
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=supplier_lead_time_days,
                expected_value=max_lead_time_days,
                severity="HIGH"
            )
        )


def validate_certifications(
    product_certifications: Optional[Any],
    required_certifications: Optional[List[str]]
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Required Certifications"
    if not required_certifications:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=product_certifications or [],
                expected_value="None Required",
                message="No certifications required."
            ),
            None
        )

    # Normalize product certifications
    prod_certs: Set[str] = set()
    if isinstance(product_certifications, list):
        prod_certs = {str(c).strip().upper() for c in product_certifications}
    elif isinstance(product_certifications, str):
        prod_certs = {product_certifications.strip().upper()}

    req_certs = {str(c).strip().upper() for c in required_certifications}
    missing = req_certs - prod_certs

    if not missing:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=sorted(list(prod_certs)),
                expected_value=sorted(list(req_certs)),
                message=f"Product satisfies all required certifications: {', '.join(required_certifications)}."
            ),
            None
        )
    else:
        msg = f"Product is missing required certifications: {', '.join(sorted(list(missing)))}."
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=sorted(list(prod_certs)),
                expected_value=sorted(list(req_certs)),
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=sorted(list(prod_certs)),
                expected_value=sorted(list(req_certs)),
                severity="HIGH"
            )
        )


def validate_gst_verification(
    vendor_gst_verified: bool
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Vendor GST Verification"
    if vendor_gst_verified:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=True,
                expected_value=True,
                message="Vendor GST is verified."
            ),
            None
        )
    else:
        msg = "Vendor is not GST verified."
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=False,
                expected_value=True,
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=False,
                expected_value=True,
                severity="HIGH"
            )
        )


def validate_currency_consistency(
    procurement_currency: str,
    deal_currency: str,
    order_currency: str = "INR"
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Currency Consistency"
    p_curr = (procurement_currency or "INR").upper()
    d_curr = (deal_currency or "INR").upper()
    o_curr = (order_currency or "INR").upper()

    if p_curr == d_curr == o_curr:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"Procurement: {p_curr}, Deal: {d_curr}, Order: {o_curr}",
                expected_value=f"All {p_curr}",
                message=f"Currency consistency verified ({p_curr})."
            ),
            None
        )
    else:
        msg = f"Currency mismatch detected: Procurement ({p_curr}), Deal ({d_curr}), Order ({o_curr})."
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=f"{p_curr} / {d_curr} / {o_curr}",
                expected_value="Matching Currencies",
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=f"{p_curr}/{d_curr}/{o_curr}",
                expected_value="Matching Currencies",
                severity="HIGH"
            )
        )


def validate_entity_integrity(
    request_id: int,
    product_id: int,
    vendor_id: int,
    expected_request_id: int,
    expected_product_id: int,
    expected_vendor_id: int
) -> Tuple[RuleValidationResult, Optional[PolicyViolation]]:
    rule_name = "Product/Vendor Entity Integrity"
    match = (
        request_id == expected_request_id and
        product_id == expected_product_id and
        vendor_id == expected_vendor_id
    )
    if match:
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="PASS",
                actual_value=f"Req: {request_id}, Prod: {product_id}, Vend: {vendor_id}",
                expected_value=f"Req: {expected_request_id}, Prod: {expected_product_id}, Vend: {expected_vendor_id}",
                message="Entity integrity verified against negotiation context."
            ),
            None
        )
    else:
        msg = (
            f"Entity mismatch: Received (Req: {request_id}, Prod: {product_id}, Vend: {vendor_id}) "
            f"vs Expected (Req: {expected_request_id}, Prod: {expected_product_id}, Vend: {expected_vendor_id})."
        )
        return (
            RuleValidationResult(
                rule_name=rule_name,
                status="FAIL",
                actual_value=f"Req: {request_id}, Prod: {product_id}, Vend: {vendor_id}",
                expected_value=f"Req: {expected_request_id}, Prod: {expected_product_id}, Vend: {expected_vendor_id}",
                message=msg
            ),
            PolicyViolation(
                rule_name=rule_name,
                reason=msg,
                actual_value=f"{request_id}/{product_id}/{vendor_id}",
                expected_value=f"{expected_request_id}/{expected_product_id}/{expected_vendor_id}",
                severity="HIGH"
            )
        )
