import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.user import User
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.order import Order, ApprovalStatus, PaymentStatus
from app.models.audit_event import AuditEvent
from app.models.negotiation_trace import NegotiationTrace

from app.services.guardrails.engine import GuardrailEngine
from app.services.guardrails.rules import (
    validate_max_unit_price,
    validate_max_budget,
    validate_quantity_integrity,
    validate_delivery_time,
    validate_certifications,
    validate_gst_verification,
    validate_currency_consistency,
    validate_entity_integrity
)
from app.services.guardrails.exceptions import (
    PolicyViolationException,
    InvalidApprovalStateException,
    DealTamperedException
)


@pytest.fixture(scope="function")
def db():
    """Create an isolated in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed core test user
    user = User(id=1, name="Test Procurement Manager", email="manager@company.com", role="procurement_manager")
    session.add(user)

    # Seed core test vendor (GST verified)
    vendor = Vendor(
        id=1,
        name="ErgoWorks Corp",
        gstin="29AAAAA0000A1Z5",
        gst_verified=True,
        rating=Decimal("4.8")
    )
    session.add(vendor)

    # Seed unverified vendor
    unverified_vendor = Vendor(
        id=2,
        name="Unverified Supplier",
        gstin="29BBB00000A1Z5",
        gst_verified=False,
        rating=Decimal("3.5")
    )
    session.add(unverified_vendor)

    # Seed core test product
    product = Product(
        id=101,
        vendor_id=1,
        sku="EW-MESH-01",
        name="Ergonomic Mesh Chair",
        category="Furniture",
        base_price=Decimal("15000.00"),
        min_allowable_price=Decimal("11000.00"),
        lead_time_days=5,
        certifications=["ISO 14001", "FSC", "BIFMA"]
    )
    session.add(product)

    # Seed product with missing certifications
    uncertified_product = Product(
        id=102,
        vendor_id=1,
        sku="BASIC-CHAIR-01",
        name="Basic Chair",
        category="Furniture",
        base_price=Decimal("5000.00"),
        min_allowable_price=Decimal("4000.00"),
        lead_time_days=10,
        certifications=[]
    )
    session.add(uncertified_product)

    session.commit()
    yield session
    session.close()


def create_sample_request(db_session, req_id=10, quantity=10, max_unit_price="14000.00", max_budget="150000.00", max_lead_time_days=7, req_certs=None):
    """Helper to create a ProcurementRequest in DB."""
    p_req = ProcurementRequest(
        id=req_id,
        user_id=1,
        raw_prompt="Source chairs",
        execution_status=ExecutionStatus.NEGOTIATING.value,
        max_budget=Decimal(max_budget) if max_budget else None,
        extracted_constraints={
            "item_description": "Ergonomic Chair",
            "quantity": quantity,
            "max_unit_price": max_unit_price,
            "max_budget": max_budget,
            "max_lead_time_days": max_lead_time_days,
            "required_certifications": req_certs or ["BIFMA"]
        }
    )
    db_session.add(p_req)

    # Add a negotiation trace log
    trace = NegotiationTrace(
        request_id=req_id,
        turn_number=1,
        counter_price=Decimal("12000.00"),
        negotiation_status="DEAL_AGREED",
        decision_summary="Deal agreed at 12000 per unit."
    )
    db_session.add(trace)

    # Add audit event for deal agreed
    audit = AuditEvent(
        request_id=req_id,
        event_type="DEAL_AGREED",
        actor="NEGOTIATION_AGENT",
        event_data={
            "product_id": 101,
            "vendor_id": 1,
            "final_unit_price": 12000.0,
            "status": "DEAL_AGREED"
        }
    )
    db_session.add(audit)
    db_session.commit()
    return p_req


# --- TEST 1: Negotiated price within max ---
def test_1_negotiated_price_within_max():
    res, viol = validate_max_unit_price(Decimal("12000.00"), Decimal("14000.00"))
    assert res.status == "PASS"
    assert viol is None


# --- TEST 2: Negotiated price above max ---
def test_2_negotiated_price_above_max():
    res, viol = validate_max_unit_price(Decimal("15000.00"), Decimal("14000.00"))
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.rule_name == "Maximum Unit Price"


# --- TEST 3: Total exceeds max budget ---
def test_3_total_exceeds_max_budget():
    res, viol = validate_max_budget(Decimal("160000.00"), Decimal("150000.00"))
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.rule_name == "Maximum Budget"


# --- TEST 4: Quantity mismatch ---
def test_4_quantity_mismatch():
    res, viol = validate_quantity_integrity(550, 500)
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.actual_value == 550
    assert viol.expected_value == 500


# --- TEST 5: Delivery time exceeds limit ---
def test_5_delivery_exceeds_limit():
    res, viol = validate_delivery_time(10, 7)
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.rule_name == "Delivery Time"


# --- TEST 6: Missing required certification ---
def test_6_missing_required_certification():
    res, viol = validate_certifications([], ["ISO 14001", "FSC"])
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.rule_name == "Required Certifications"


# --- TEST 7: GST verification failure ---
def test_7_gst_verification_failure():
    res, viol = validate_gst_verification(False)
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.rule_name == "Vendor GST Verification"


# --- TEST 8: Currency mismatch ---
def test_8_currency_mismatch():
    res, viol = validate_currency_consistency("USD", "INR", "INR")
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.rule_name == "Currency Consistency"


# --- TEST 9: Total ₹99,999 -> approval_required = false ---
def test_9_total_99999_no_approval_required(db):
    create_sample_request(db, req_id=901, quantity=1, max_unit_price="99999.00", max_budget="99999.00")
    # Override negotiated price to 99999
    res = GuardrailEngine.run_policy_check(
        request_id=901,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("99999.00"), "quantity": 1}
    )
    assert res.all_rules_passed is True
    assert res.total_amount == Decimal("99999.00")
    assert res.approval_required is False
    assert res.status == "READY_FOR_PAYMENT"


# --- TEST 10: Total ₹100,000 -> approval_required = false ---
def test_10_total_100000_no_approval_required(db):
    create_sample_request(db, req_id=902, quantity=1, max_unit_price="100000.00", max_budget="100000.00")
    res = GuardrailEngine.run_policy_check(
        request_id=902,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("100000.00"), "quantity": 1}
    )
    assert res.all_rules_passed is True
    assert res.total_amount == Decimal("100000.00")
    assert res.approval_required is False
    assert res.status == "READY_FOR_PAYMENT"


# --- TEST 11: Total ₹100,001 -> approval_required = true ---
def test_11_total_100001_approval_required(db):
    create_sample_request(db, req_id=903, quantity=1, max_unit_price="100001.00", max_budget="100001.00")
    res = GuardrailEngine.run_policy_check(
        request_id=903,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("100001.00"), "quantity": 1}
    )
    assert res.all_rules_passed is True
    assert res.total_amount == Decimal("100001.00")
    assert res.approval_required is True
    assert res.status == "APPROVAL_REQUIRED"


# --- TEST 12: Client attempts to change total amount during approval ---
def test_12_client_cannot_change_amount_during_approval(db):
    create_sample_request(db, req_id=904, quantity=10, max_unit_price="14000.00", max_budget="150000.00")
    res = GuardrailEngine.run_policy_check(
        request_id=904,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("12000.00"), "quantity": 10}
    )
    assert res.status == "APPROVAL_REQUIRED"  # 120,000 > 100,000

    # Approval call takes no price/amount override parameters
    app_res = GuardrailEngine.approve_deal(request_id=904, db=db, notes="Admin approved")
    assert app_res.approval_status == "APPROVED"
    assert app_res.execution_status == "READY_FOR_PAYMENT"

    # Verify order amount in DB was strictly calculated by backend (120,000)
    order = db.query(Order).filter_by(request_id=904).first()
    assert order.total_amount == Decimal("120000.00")


# --- TEST 13: Client attempts to change product/vendor ---
def test_13_entity_mismatch_rejected(db):
    res, viol = validate_entity_integrity(10, 101, 1, 10, 999, 1)
    assert res.status == "FAIL"
    assert viol is not None
    assert viol.rule_name == "Product/Vendor Entity Integrity"


# --- TEST 14: Deal modified after validation ---
def test_14_tampered_deal_fails_revalidation(db):
    create_sample_request(db, req_id=905, quantity=10, max_unit_price="14000.00", max_budget="150000.00")
    GuardrailEngine.run_policy_check(
        request_id=905,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("12000.00"), "quantity": 10}
    )

    # Tamper with order record in DB manually
    order = db.query(Order).filter_by(request_id=905).first()
    order.quantity = 20  # Tampered quantity

    with pytest.raises(DealTamperedException):
        GuardrailEngine.approve_deal(request_id=905, db=db)


# --- TEST 15: Approval succeeds -> READY_FOR_PAYMENT ---
def test_15_approval_succeeds(db):
    create_sample_request(db, req_id=906, quantity=10, max_unit_price="14000.00", max_budget="150000.00")
    GuardrailEngine.run_policy_check(
        request_id=906,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("12000.00"), "quantity": 10}
    )

    app_res = GuardrailEngine.approve_deal(request_id=906, db=db, notes="Budget approved")
    assert app_res.approval_status == "APPROVED"
    assert app_res.execution_status == "READY_FOR_PAYMENT"


# --- TEST 16: Approval rejection ---
def test_16_approval_rejection(db):
    create_sample_request(db, req_id=907, quantity=10, max_unit_price="14000.00", max_budget="150000.00")
    GuardrailEngine.run_policy_check(
        request_id=907,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("12000.00"), "quantity": 10}
    )

    rej_res = GuardrailEngine.reject_deal(request_id=907, db=db, notes="Too expensive")
    assert rej_res.approval_status == "REJECTED"
    assert rej_res.execution_status == "CANCELLED"


# --- TEST 17: Duplicate approval -> Idempotent ---
def test_17_duplicate_approval_idempotent(db):
    create_sample_request(db, req_id=908, quantity=10, max_unit_price="14000.00", max_budget="150000.00")
    GuardrailEngine.run_policy_check(
        request_id=908,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("12000.00"), "quantity": 10}
    )

    app_res_1 = GuardrailEngine.approve_deal(request_id=908, db=db)
    assert app_res_1.approval_status == "APPROVED"

    # Second approval call
    app_res_2 = GuardrailEngine.approve_deal(request_id=908, db=db)
    assert app_res_2.approval_status == "APPROVED"
    assert "already approved" in app_res_2.message.lower()


# --- TEST 18: Policy audit events created ---
def test_18_policy_audit_events_created(db):
    create_sample_request(db, req_id=909, quantity=10, max_unit_price="14000.00", max_budget="150000.00")
    GuardrailEngine.run_policy_check(
        request_id=909,
        db=db,
        override_deal={"product_id": 101, "vendor_id": 1, "negotiated_unit_price": Decimal("12000.00"), "quantity": 10}
    )

    events = db.query(AuditEvent).filter_by(request_id=909).all()
    event_types = [e.event_type for e in events]

    assert "POLICY_CHECK_STARTED" in event_types
    assert "POLICY_CHECK_COMPLETED" in event_types
    assert "APPROVAL_REQUIRED" in event_types
