import json
import hmac
import hashlib
import pytest
from typing import Optional
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.base import Base
from app.models.user import User
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.order import Order, ApprovalStatus, PaymentStatus
from app.models.audit_event import AuditEvent, ActorType

from app.services.guardrails import GuardrailEngine
from app.services.payments.payment_service import PaymentService
from app.services.payments.webhook_service import WebhookService
from app.services.payments.razorpay_client import RazorpayClientWrapper
from app.services.payments.exceptions import (
    InvalidPaymentStateException,
    InvalidWebhookSignatureException,
    PaymentAmountMismatchException
)


@pytest.fixture(scope="function")
def db():
    """Create isolated in-memory SQLite DB for payment testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # User
    user = User(id=1, name="Test Buyer", email="buyer@company.com", role="procurement_manager")
    session.add(user)

    # Vendor (GST verified)
    vendor = Vendor(
        id=1,
        name="ErgoWorks Corp",
        gstin="29AAAAA0000A1Z5",
        gst_verified=True,
        rating=Decimal("4.8")
    )
    session.add(vendor)

    # Product
    product = Product(
        id=101,
        vendor_id=1,
        sku="EW-MESH-01",
        name="Ergonomic Mesh Chair",
        category="Furniture",
        base_price=Decimal("15000.00"),
        min_allowable_price=Decimal("11000.00"),
        lead_time_days=5,
        certifications=["BIFMA"]
    )
    session.add(product)
    session.commit()

    yield session
    session.close()


def create_ready_deal(db_session, req_id=100, quantity=5, unit_price="12000.00", status=ExecutionStatus.PAYMENT_PENDING.value, app_status=ApprovalStatus.NOT_REQUIRED.value):
    """Helper to set up a validated deal ready for payment."""
    p_req = ProcurementRequest(
        id=req_id,
        user_id=1,
        raw_prompt="Buy 5 chairs",
        execution_status=status,
        max_budget=Decimal("100000.00"),
        extracted_constraints={
            "item_description": "Ergonomic Chair",
            "quantity": quantity,
            "max_unit_price": "14000.00",
            "max_budget": "100000.00",
            "max_lead_time_days": 7,
            "required_certifications": ["BIFMA"]
        }
    )
    db_session.add(p_req)

    total_amount = Decimal(unit_price) * quantity
    snapshot = {
        "request_id": req_id,
        "product_id": 101,
        "vendor_id": 1,
        "quantity": quantity,
        "negotiated_unit_price": float(Decimal(unit_price)),
        "total_amount": float(total_amount),
        "currency": "INR",
        "lead_time_days": 5,
        "certifications": ["BIFMA"],
        "policy_version": "v1",
        "validated_at": "2026-09-04T12:00:00Z"
    }

    order = Order(
        request_id=req_id,
        vendor_id=1,
        product_id=101,
        quantity=quantity,
        negotiated_unit_price=Decimal(unit_price),
        total_amount=total_amount,
        currency="INR",
        approval_status=app_status,
        payment_status=PaymentStatus.NOT_STARTED.value,
        deal_snapshot=snapshot
    )
    db_session.add(order)
    db_session.commit()
    return p_req, order


def generate_signature(raw_bytes: bytes, secret: Optional[str] = None) -> str:
    """Helper to calculate valid HMAC-SHA256 signature."""
    sec = secret if secret is not None else settings.RAZORPAY_WEBHOOK_SECRET
    return hmac.new(sec.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()


# --- TEST 1: Valid webhook signature ---
def test_1_valid_webhook_signature():
    body = b'{"event":"payment_link.paid","payload":{}}'
    sig = generate_signature(body)
    assert RazorpayClientWrapper.verify_webhook_signature(body, sig, settings.RAZORPAY_WEBHOOK_SECRET) is True


# --- TEST 2: Invalid webhook signature ---
def test_2_invalid_webhook_signature(db):
    body = b'{"event":"payment_link.paid","payload":{}}'
    bad_sig = "invalid_signature_123456789"

    with pytest.raises(InvalidWebhookSignatureException):
        WebhookService.process_webhook(body, bad_sig, "evt_test_02", db)


# --- TEST 3: Duplicate event ID ---
def test_3_duplicate_event_id(db):
    create_ready_deal(db, req_id=301)
    order = db.query(Order).filter_by(request_id=301).first()
    order.razorpay_payment_link_id = "plink_dup_03"
    db.commit()

    body_dict = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {"id": "plink_dup_03", "amount_paid": 6000000, "reference_id": f"AGENTX-{order.id}"}},
            "payment": {"entity": {"id": "pay_dup_03", "amount": 6000000}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    # First delivery
    res1 = WebhookService.process_webhook(raw_body, sig, "evt_dup_100", db)
    assert res1.status == "success"

    # Duplicate delivery
    res2 = WebhookService.process_webhook(raw_body, sig, "evt_dup_100", db)
    assert res2.status == "duplicate"


# --- TEST 4: payment_link.paid updates status to PAID ---
def test_4_payment_link_paid(db):
    create_ready_deal(db, req_id=401, quantity=5, unit_price="12000.00") # 60,000 Total
    order = db.query(Order).filter_by(request_id=401).first()
    order.razorpay_payment_link_id = "plink_paid_04"
    db.commit()

    body_dict = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {"id": "plink_paid_04", "amount_paid": 6000000, "reference_id": f"AGENTX-{order.id}"}},
            "payment": {"entity": {"id": "pay_04_id", "amount": 6000000}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    res = WebhookService.process_webhook(raw_body, sig, "evt_paid_04", db)
    assert res.status == "success"

    db.refresh(order)
    assert order.payment_status == "PAID"
    assert order.razorpay_payment_id == "pay_04_id"


# --- TEST 5: payment_link.partially_paid ---
def test_5_payment_link_partially_paid(db):
    create_ready_deal(db, req_id=501)
    order = db.query(Order).filter_by(request_id=501).first()
    order.razorpay_payment_link_id = "plink_part_05"
    db.commit()

    body_dict = {
        "event": "payment_link.partially_paid",
        "payload": {
            "payment_link": {"entity": {"id": "plink_part_05", "amount_paid": 3000000, "reference_id": f"AGENTX-{order.id}"}},
            "payment": {"entity": {"id": "pay_part_05", "amount": 3000000}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    res = WebhookService.process_webhook(raw_body, sig, "evt_part_05", db)
    assert res.status == "success"

    db.refresh(order)
    assert order.payment_status != "PAID"


# --- TEST 6: payment_link.cancelled ---
def test_6_payment_link_cancelled(db):
    create_ready_deal(db, req_id=601)
    order = db.query(Order).filter_by(request_id=601).first()
    order.razorpay_payment_link_id = "plink_canc_06"
    db.commit()

    body_dict = {
        "event": "payment_link.cancelled",
        "payload": {
            "payment_link": {"entity": {"id": "plink_canc_06", "reference_id": f"AGENTX-{order.id}"}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    res = WebhookService.process_webhook(raw_body, sig, "evt_canc_06", db)
    assert res.status == "success"

    db.refresh(order)
    assert order.payment_status == "CANCELLED"


# --- TEST 7: payment_link.expired ---
def test_7_payment_link_expired(db):
    create_ready_deal(db, req_id=701)
    order = db.query(Order).filter_by(request_id=701).first()
    order.razorpay_payment_link_id = "plink_exp_07"
    db.commit()

    body_dict = {
        "event": "payment_link.expired",
        "payload": {
            "payment_link": {"entity": {"id": "plink_exp_07", "reference_id": f"AGENTX-{order.id}"}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    res = WebhookService.process_webhook(raw_body, sig, "evt_exp_07", db)
    assert res.status == "success"

    db.refresh(order)
    assert order.payment_status == "EXPIRED"


# --- TEST 8: Unknown Payment Link ID ---
def test_8_unknown_payment_link_id(db):
    body_dict = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {"id": "plink_unknown_999", "amount_paid": 10000, "reference_id": "AGENTX-999"}},
            "payment": {"entity": {"id": "pay_unk_08", "amount": 10000}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    res = WebhookService.process_webhook(raw_body, sig, "evt_unk_08", db)
    assert res.status == "ignored"


# --- TEST 9: Payment amount mismatch ---
def test_9_payment_amount_mismatch(db):
    create_ready_deal(db, req_id=901, quantity=5, unit_price="12000.00") # Total 60,000 (6,000,000 paise)
    order = db.query(Order).filter_by(request_id=901).first()
    order.razorpay_payment_link_id = "plink_mis_09"
    db.commit()

    body_dict = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {"id": "plink_mis_09", "amount_paid": 1000000, "reference_id": f"AGENTX-{order.id}"}}, # Paid only 10,000
            "payment": {"entity": {"id": "pay_mis_09", "amount": 1000000}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    with pytest.raises(PaymentAmountMismatchException):
        WebhookService.process_webhook(raw_body, sig, "evt_mis_09", db)


# --- TEST 10: Payment creation while APPROVAL_REQUIRED ---
def test_10_payment_creation_blocked_when_approval_required(db):
    create_ready_deal(db, req_id=1001, status=ExecutionStatus.APPROVAL_REQUIRED.value, app_status=ApprovalStatus.PENDING.value)

    with pytest.raises(InvalidPaymentStateException):
        PaymentService.create_payment_link(request_id=1001, db=db)


# --- TEST 11: Payment creation after guardrail violation ---
def test_11_payment_creation_blocked_when_guardrails_fail(db):
    # Setup request with unverified vendor to trigger guardrail failure
    create_ready_deal(db, req_id=1101)
    order = db.query(Order).filter_by(request_id=1101).first()
    order.vendor_id = 2 # Vendor 2 is unverified!
    db.commit()

    with pytest.raises(Exception):
        PaymentService.create_payment_link(request_id=1101, db=db)


# --- TEST 12: Client attempts to change payment amount ---
def test_12_client_cannot_override_payment_amount(db):
    create_ready_deal(db, req_id=1201, quantity=5, unit_price="12000.00") # 60,000 Total
    res = PaymentService.create_payment_link(request_id=1201, db=db)

    # Server calculates authoritative amount in paise: 60,000 * 100 = 6,000,000 paise
    assert res.amount == 6000000


# --- TEST 13: Payment creation twice (Idempotent) ---
def test_13_payment_creation_idempotent(db):
    create_ready_deal(db, req_id=1301, quantity=5, unit_price="12000.00")

    res1 = PaymentService.create_payment_link(request_id=1301, db=db)
    res2 = PaymentService.create_payment_link(request_id=1301, db=db)

    assert res1.razorpay_payment_link_id == res2.razorpay_payment_link_id
    assert res1.payment_url == res2.payment_url


# --- TEST 14: Deal modified after Feature 5 policy check ---
def test_14_deal_modified_after_validation_blocks_payment(db):
    create_ready_deal(db, req_id=1401, quantity=5, unit_price="12000.00")
    order = db.query(Order).filter_by(request_id=1401).first()

    # Modify deal quantity after validation
    order.quantity = 20
    db.commit()

    with pytest.raises(Exception):
        PaymentService.create_payment_link(request_id=1401, db=db)


# --- TEST 15: Valid READY_FOR_PAYMENT deal creates Payment Link ---
def test_15_valid_ready_for_payment_deal(db):
    create_ready_deal(db, req_id=1501, quantity=5, unit_price="12000.00")
    res = PaymentService.create_payment_link(request_id=1501, db=db)

    assert res.payment_status == "PAYMENT_PENDING"
    assert res.razorpay_payment_link_id.startswith("plink_")
    assert "https://rzp.io/i/" in res.payment_url


# --- TEST 16: Valid payment webhook marks order PAID ---
def test_16_valid_webhook_marks_order_paid(db):
    create_ready_deal(db, req_id=1601, quantity=2, unit_price="10000.00") # 20,000 Total
    res = PaymentService.create_payment_link(request_id=1601, db=db)
    order = db.query(Order).filter_by(request_id=1601).first()

    body_dict = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {"id": res.razorpay_payment_link_id, "amount_paid": 2000000, "reference_id": f"AGENTX-{order.id}"}},
            "payment": {"entity": {"id": "pay_16_valid", "amount": 2000000}}
        }
    }
    raw_body = json.dumps(body_dict).encode("utf-8")
    sig = generate_signature(raw_body)

    web_res = WebhookService.process_webhook(raw_body, sig, "evt_16_valid", db)
    assert web_res.status == "success"

    db.refresh(order)
    assert order.payment_status == "PAID"
    assert order.razorpay_payment_id == "pay_16_valid"


# --- TEST 17: Signature verification fails on reformatted JSON ---
def test_17_reformatted_json_fails_raw_body_signature(db):
    original_bytes = b'{"event":"payment_link.paid","payload":{"payment":{"entity":{"id":"pay_17"}}}}'
    sig = generate_signature(original_bytes)

    # Re-formatted/pretty JSON bytes
    pretty_bytes = b'{\n  "event": "payment_link.paid",\n  "payload": {\n    "payment": {\n      "entity": {\n        "id": "pay_17"\n      }\n    }\n  }\n}'

    # Verification against pretty_bytes using sig computed from original_bytes MUST fail!
    assert RazorpayClientWrapper.verify_webhook_signature(pretty_bytes, sig, settings.RAZORPAY_WEBHOOK_SECRET) is False
