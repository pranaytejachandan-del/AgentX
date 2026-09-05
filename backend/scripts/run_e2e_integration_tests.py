import sys
import os
import json
import hmac
import hashlib
from decimal import Decimal
from typing import Dict, Any

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database.base import Base
from app.database.connection import get_db
from app.models.user import User
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.order import Order, ApprovalStatus, PaymentStatus
from app.models.audit_event import AuditEvent
from app.models.negotiation_trace import NegotiationTrace

from app.services.embedding_service import get_embedding_service, generate_product_text

# 1. Setup isolated file-backed SQLite test database
TEST_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e_test.db")
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except Exception:
        pass

TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def seed_database():
    db = TestingSessionLocal()
    # Seed User
    user = User(id=1, name="Enterprise Buyer", email="buyer@corp.com", role="procurement_manager")
    db.add(user)

    # Seed Vendors
    v1 = Vendor(id=1, name="TechPro Systems India", rating=Decimal("4.8"), gstin="29AAAAA0001A1Z5", gst_verified=True)
    v2 = Vendor(id=2, name="Delta Laptops", rating=Decimal("3.9"), gstin="27BBBBB0002B2Z6", gst_verified=False) # Unverified
    v3 = Vendor(id=3, name="CyberTech Corp", rating=Decimal("4.6"), gstin="07CCCCC0003C3Z7", gst_verified=True)
    db.add_all([v1, v2, v3])
    db.commit()

    # Seed Products
    emb_service = get_embedding_service()

    p1_text = generate_product_text("Enterprise Laptop 16GB RAM", "Laptop", "High performance business laptop with 16GB RAM, 512GB SSD", certifications=["ISO-9001"])
    p1 = Product(
        id=101, vendor_id=1, sku="TPS-LAP-16", name="Enterprise Laptop 16GB RAM", category="Laptop",
        base_price=Decimal("68000.00"), min_allowable_price=Decimal("62000.00"), lead_time_days=5,
        certifications=["ISO-9001"], embedding=emb_service.generate_embedding(p1_text)
    )

    p2_text = generate_product_text("High-End Gaming Laptop", "Laptop", "Workstation laptop with 32GB RAM", certifications=["ISO-9001"])
    p2 = Product(
        id=102, vendor_id=1, sku="TPS-WORK-32", name="High-End Gaming Laptop", category="Laptop",
        base_price=Decimal("120000.00"), min_allowable_price=Decimal("110000.00"), lead_time_days=4,
        certifications=["ISO-9001"], embedding=emb_service.generate_embedding(p2_text)
    )

    p3_text = generate_product_text("Commercial Office Laptop 16GB", "Laptop", "Reliable 16GB RAM business laptop", certifications=["ISO-9001"])
    p3 = Product(
        id=103, vendor_id=3, sku="CTC-OFF-16", name="Commercial Office Laptop 16GB", category="Laptop",
        base_price=Decimal("65000.00"), min_allowable_price=Decimal("58000.00"), lead_time_days=7,
        certifications=["ISO-9001"], embedding=emb_service.generate_embedding(p3_text)
    )

    db.add_all([p1, p2, p3])
    db.commit()
    db.close()

seed_database()

client = TestClient(app)
results = []

def record(test_code: str, title: str, description: str, details: str, status: str):
    results.append({
        "code": test_code,
        "title": title,
        "description": description,
        "details": details,
        "status": status
    })
    print(f"[{status}] {test_code}: {title} | {details}")

def generate_webhook_signature(body: bytes) -> str:
    return hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

def run_e2e_suite():
    print("=" * 80)
    print("AGENTX END-TO-END INTEGRATION TEST SUITE (6 LIFE-CYCLE SCENARIOS)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # TEST CASE 1 — NORMAL PROCUREMENT LIFECYCLE
    # -------------------------------------------------------------------------
    print("\n--- TEST CASE 1: Normal Procurement Lifecycle ---")
    prompt_tc1 = "Need 50 enterprise laptops with 16GB RAM, preferably below ₹70,000 per unit, delivery within 10 days."

    # Step 1: Parse Prompt
    resp_parse = client.post("/api/procurement/parse", json={"prompt": prompt_tc1, "user_id": 1})
    assert resp_parse.status_code == 200, f"Parse failed: {resp_parse.text}"
    parse_data = resp_parse.json()
    req_id_tc1 = parse_data["request_id"]
    constraints_tc1 = parse_data["constraints"]

    if (parse_data["status"] == "parsed" and 
        constraints_tc1["quantity"] == 50 and 
        float(constraints_tc1["max_unit_price"]) == 70000.0 and
        constraints_tc1["max_lead_time_days"] == 10):
        record("TC1-01", "Intent & Constraint Parsing", "Extracts quantity=50, max_price=70000, lead_time=10", f"ID={req_id_tc1}, qty={constraints_tc1['quantity']}, price={constraints_tc1['max_unit_price']}", "PASS")
    else:
        record("TC1-01", "Intent & Constraint Parsing", "Extracts quantity=50, max_price=70000, lead_time=10", f"Failed parsing: {parse_data}", "FAIL")

    # Step 2: Discover Offers
    resp_disc = client.post("/api/procurement/discover", json={"request_id": req_id_tc1, "constraints": constraints_tc1, "top_k": 5})
    assert resp_disc.status_code == 200, f"Discovery failed: {resp_disc.text}"
    disc_data = resp_disc.json()

    if disc_data["status"] == "success" and disc_data["candidate_count"] > 0:
        top_offer_tc1 = disc_data["offers"][0]
        record("TC1-02", "Vendor/Product Discovery & Ranking", "Finds eligible laptop offers ranked by score", f"Offers found={disc_data['candidate_count']}, top_product={top_offer_tc1['product_name']}, top_score={top_offer_tc1['overall_score']}", "PASS")
    else:
        record("TC1-02", "Vendor/Product Discovery & Ranking", "Finds eligible laptop offers ranked by score", f"Discovery failed: {disc_data}", "FAIL")

    # Step 3: Negotiate Offer
    neg_payload_tc1 = {
        "request_id": req_id_tc1,
        "offer": top_offer_tc1,
        "constraints": constraints_tc1
    }
    resp_neg = client.post("/api/procurement/negotiate", json=neg_payload_tc1)
    assert resp_neg.status_code == 200, f"Negotiation failed: {resp_neg.text}"
    neg_data = resp_neg.json()

    if neg_data["status"] == "DEAL_AGREED" and neg_data["request_id"] is not None:
        final_price_tc1 = float(neg_data["final_unit_price"])
        record("TC1-03", "Negotiation Engine Execution", "Reaches DEAL_AGREED within budget bounds", f"Request ID={neg_data['request_id']}, final_price={final_price_tc1}, turns={neg_data['turns_used']}", "PASS")
    else:
        record("TC1-03", "Negotiation Engine Execution", "Reaches DEAL_AGREED within budget bounds", f"Negotiation failed: {neg_data}", "FAIL")

    # Step 4: Guardrail Policy Check
    resp_policy = client.post(f"/api/procurement/{req_id_tc1}/policy-check")
    assert resp_policy.status_code == 200, f"Policy check failed: {resp_policy.text}"
    pol_data = resp_policy.json()

    if pol_data["status"] == "APPROVAL_REQUIRED" and pol_data["approval_required"] is True:
        record("TC1-04", "Deterministic Guardrails & Approval Threshold Check", "Triggers APPROVAL_REQUIRED for total INR 32,50,000 > INR 1,00,000", f"Status={pol_data['status']}, approval_required={pol_data['approval_required']}", "PASS")
    else:
        record("TC1-04", "Deterministic Guardrails & Approval Threshold Check", "Triggers APPROVAL_REQUIRED", f"Policy check response: {pol_data}", "FAIL")

    # Step 5: Human Approval
    resp_app = client.post(f"/api/procurement/{req_id_tc1}/approve", json={"notes": "Approved by Procurement Director"})
    assert resp_app.status_code == 200, f"Approval failed: {resp_app.text}"
    app_data = resp_app.json()

    if app_data["approval_status"] == "APPROVED" and app_data["execution_status"] == "READY_FOR_PAYMENT":
        record("TC1-05", "Human Approval Execution", "Transitions deal to APPROVED and READY_FOR_PAYMENT", f"Approval={app_data['approval_status']}, Execution={app_data['execution_status']}", "PASS")
    else:
        record("TC1-05", "Human Approval Execution", "Transitions deal to APPROVED and READY_FOR_PAYMENT", f"Approval response: {app_data}", "FAIL")

    # Step 6: Create Payment Link
    resp_pay = client.post(f"/api/procurement/{req_id_tc1}/payment")
    assert resp_pay.status_code == 200, f"Payment link creation failed: {resp_pay.text}"
    pay_data = resp_pay.json()
    plink_id_tc1 = pay_data["razorpay_payment_link_id"]

    if pay_data["payment_status"] == "PAYMENT_PENDING" and plink_id_tc1.startswith("plink_"):
        record("TC1-06", "Razorpay TEST MODE Payment Link Creation", "Generates payment link with server-computed paise amount", f"Plink ID={plink_id_tc1}, amount_paise={pay_data['amount']}", "PASS")
    else:
        record("TC1-06", "Razorpay TEST MODE Payment Link Creation", "Generates payment link", f"Payment link response: {pay_data}", "FAIL")

    # Step 7: Process Authoritative Payment Webhook
    db_tc1 = TestingSessionLocal()
    order_tc1 = db_tc1.query(Order).filter_by(request_id=req_id_tc1).first()
    expected_paise_tc1 = int(order_tc1.total_amount * 100)
    db_tc1.close()

    webhook_body_tc1 = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": plink_id_tc1,
                    "amount_paid": expected_paise_tc1,
                    "reference_id": f"AGENTX-{order_tc1.id}"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_test_e2e_normal_101",
                    "amount": expected_paise_tc1,
                    "status": "captured"
                }
            }
        }
    }
    raw_wh_bytes_tc1 = json.dumps(webhook_body_tc1).encode("utf-8")
    wh_sig_tc1 = generate_webhook_signature(raw_wh_bytes_tc1)

    resp_wh = client.post(
        "/api/payments/webhook",
        content=raw_wh_bytes_tc1,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": wh_sig_tc1,
            "x-razorpay-event-id": "evt_e2e_normal_101"
        }
    )
    assert resp_wh.status_code == 200, f"Webhook failed: {resp_wh.text}"
    wh_data = resp_wh.json()

    if wh_data["status"] == "success":
        record("TC1-07", "Razorpay Webhook Processing", "Verifies HMAC signature and updates payment state", f"Webhook status={wh_data['status']}, event_id={wh_data['event_id']}", "PASS")
    else:
        record("TC1-07", "Razorpay Webhook Processing", "Verifies HMAC signature", f"Webhook response: {wh_data}", "FAIL")

    # Step 8: Complete Execution Trace & Audit Check
    db_tc1_chk = TestingSessionLocal()
    req_chk_tc1 = db_tc1_chk.query(ProcurementRequest).filter_by(id=req_id_tc1).first()
    order_chk_tc1 = db_tc1_chk.query(Order).filter_by(request_id=req_id_tc1).first()
    audits_tc1 = db_tc1_chk.query(AuditEvent).filter_by(request_id=req_id_tc1).all()
    db_tc1_chk.close()

    if (req_chk_tc1.execution_status == "PAID" and 
        order_chk_tc1.payment_status == "PAID" and 
        order_chk_tc1.razorpay_payment_id == "pay_test_e2e_normal_101" and 
        len(audits_tc1) >= 4):
        record("TC1-08", "Dashboard & Database Execution Trace", "Lifecycle state is PAID, Order is PAID, audit log complete", f"Execution={req_chk_tc1.execution_status}, Payment={order_chk_tc1.payment_status}, Audits={len(audits_tc1)}", "PASS")
    else:
        record("TC1-08", "Dashboard & Database Execution Trace", "Lifecycle state is PAID", f"Req={req_chk_tc1.execution_status}, Order={order_chk_tc1.payment_status}, Audits={len(audits_tc1)}", "FAIL")


    # -------------------------------------------------------------------------
    # TEST CASE 2 — NEGOTIATION FAILURE
    # -------------------------------------------------------------------------
    print("\n--- TEST CASE 2: Negotiation Failure ---")
    prompt_tc2 = "Need 10 enterprise laptops below ₹40,000 per unit." # Supplier min floor is ₹62,000
    resp_parse_tc2 = client.post("/api/procurement/parse", json={"prompt": prompt_tc2, "user_id": 1})
    req_id_tc2 = resp_parse_tc2.json()["request_id"]
    constraints_tc2 = resp_parse_tc2.json()["constraints"]

    resp_disc_tc2 = client.post("/api/procurement/discover", json={"request_id": req_id_tc2, "constraints": constraints_tc2, "top_k": 5})
    # If no eligible offers because 40000 < min price 62000
    offers_tc2 = resp_disc_tc2.json().get("offers", [])
    if not offers_tc2:
        # Use near match offer to trigger negotiation rejection
        offers_tc2 = resp_disc_tc2.json().get("near_matches", [])

    if offers_tc2:
        neg_payload_tc2 = {"request_id": req_id_tc2, "offer": offers_tc2[0], "constraints": constraints_tc2}
        resp_neg_tc2 = client.post("/api/procurement/negotiate", json=neg_payload_tc2)
        neg_data_tc2 = resp_neg_tc2.json()

        # Try calling payment creation API for failed negotiation
        resp_pay_fail = client.post(f"/api/procurement/{req_id_tc2}/payment")

        if neg_data_tc2["status"] == "NEGOTIATION_FAILED" and resp_pay_fail.status_code in [400, 404, 422]:
            record("TC2-01", "Negotiation Failure Guard", "Failed negotiation returns NEGOTIATION_FAILED and blocks payment creation", f"Status={neg_data_tc2['status']}, payment_http_code={resp_pay_fail.status_code}", "PASS")
        else:
            record("TC2-01", "Negotiation Failure Guard", "Failed negotiation blocks payment", f"Status={neg_data_tc2['status']}, payment_resp={resp_pay_fail.status_code}", "FAIL")
    else:
        record("TC2-01", "Negotiation Failure Guard", "No eligible offer discovered for low budget", f"Discovery status={resp_disc_tc2.json().get('status')}", "PASS")


    # -------------------------------------------------------------------------
    # TEST CASE 3 — GUARDRAIL FAILURE
    # -------------------------------------------------------------------------
    print("\n--- TEST CASE 3: Guardrail Failure ---")
    # Setup request with unverified vendor (Vendor 2) to force guardrail failure
    db_tc3 = TestingSessionLocal()
    req_tc3 = ProcurementRequest(
        id=301, user_id=1, raw_prompt="Buy 5 laptops from unverified supplier", execution_status=ExecutionStatus.NEGOTIATING.value,
        max_budget=Decimal("500000.00"), extracted_constraints={"item_description": "Laptop", "quantity": 5, "max_unit_price": "70000.00"}
    )
    db_tc3.add(req_tc3)
    order_tc3 = Order(
        request_id=301, vendor_id=2, product_id=101, quantity=5, negotiated_unit_price=Decimal("65000.00"), # Vendor 2 is unverified!
        total_amount=Decimal("325000.00"), currency="INR", approval_status=ApprovalStatus.NOT_REQUIRED.value, payment_status=PaymentStatus.NOT_STARTED.value
    )
    db_tc3.add(order_tc3)
    db_tc3.commit()
    db_tc3.close()

    resp_pol_tc3 = client.post("/api/procurement/301/policy-check")
    resp_pay_tc3 = client.post("/api/procurement/301/payment")

    db_tc3_chk = TestingSessionLocal()
    req_chk_tc3 = db_tc3_chk.query(ProcurementRequest).filter_by(id=301).first()
    order_chk_tc3 = db_tc3_chk.query(Order).filter_by(request_id=301).first()
    audit_tc3 = db_tc3_chk.query(AuditEvent).filter_by(request_id=301).all()
    db_tc3_chk.close()

    if (resp_pol_tc3.status_code == 200 and resp_pol_tc3.json()["status"] in ["POLICY_VIOLATION", "FAIL"] and
        resp_pay_tc3.status_code in [400, 422] and
        order_chk_tc3.payment_status == "NOT_STARTED" and
        len(audit_tc3) > 0):
        record("TC3-01", "Guardrail Policy Violation Enforcement", "Policy check fails, payment creation is blocked, audit event logged", f"Guardrail status={resp_pol_tc3.json()['status']}, payment_code={resp_pay_tc3.status_code}, payment_status={order_chk_tc3.payment_status}", "PASS")
    else:
        record("TC3-01", "Guardrail Policy Violation Enforcement", "Policy check fails", f"Policy resp={resp_pol_tc3.text}, Payment resp={resp_pay_tc3.text}", "FAIL")


    # -------------------------------------------------------------------------
    # TEST CASE 4 — HUMAN APPROVAL & ANTI-TAMPERING
    # -------------------------------------------------------------------------
    print("\n--- TEST CASE 4: Human Approval Threshold & Anti-Tampering ---")
    prompt_tc4 = "Need 10 laptops at ₹65,000 per unit." # Total 6,50,000 > 1,00,000 threshold
    resp_parse_tc4 = client.post("/api/procurement/parse", json={"prompt": prompt_tc4, "user_id": 1})
    req_id_tc4 = resp_parse_tc4.json()["request_id"]
    constraints_tc4 = resp_parse_tc4.json()["constraints"]

    resp_disc_tc4 = client.post("/api/procurement/discover", json={"request_id": req_id_tc4, "constraints": constraints_tc4, "top_k": 5})
    offer_tc4 = resp_disc_tc4.json()["offers"][0]

    resp_neg_tc4 = client.post("/api/procurement/negotiate", json={"request_id": req_id_tc4, "offer": offer_tc4, "constraints": constraints_tc4})
    resp_pol_tc4 = client.post(f"/api/procurement/{req_id_tc4}/policy-check")
    assert resp_pol_tc4.json()["status"] == "APPROVAL_REQUIRED"

    # Attempt human approval with client payload trying to override amount to ₹10,000 (Tampering test)
    tampered_payload = {"notes": "Approved", "override_total_amount": 10000.0}
    resp_app_tc4 = client.post(f"/api/procurement/{req_id_tc4}/approve", json=tampered_payload)

    db_tc4_chk = TestingSessionLocal()
    order_tc4_chk = db_tc4_chk.query(Order).filter_by(request_id=req_id_tc4).first()
    db_tc4_chk.close()

    # Verify server ignored client override and kept exact server total_amount (e.g. 6,50,000 or negotiated total)
    if (resp_app_tc4.status_code == 200 and
        order_tc4_chk.approval_status == "APPROVED" and
        float(order_tc4_chk.total_amount) > 100000.0):
        record("TC4-01", "Human Approval FSM & Client Anti-Tampering", "APPROVAL_REQUIRED -> APPROVED transition, client payload tampering ignored", f"Approval status={order_tc4_chk.approval_status}, total_amount={order_tc4_chk.total_amount}", "PASS")
    else:
        record("TC4-01", "Human Approval FSM & Client Anti-Tampering", "Human approval FSM", f"Approval resp: {resp_app_tc4.text}", "FAIL")


    # -------------------------------------------------------------------------
    # TEST CASE 5 — WEBHOOK DUPLICATION IDEMPOTENCY
    # -------------------------------------------------------------------------
    print("\n--- TEST CASE 5: Webhook Duplication Idempotency ---")
    # Send identical webhook payload from Test Case 1 again with same event_id
    resp_wh_dup = client.post(
        "/api/payments/webhook",
        content=raw_wh_bytes_tc1,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": wh_sig_tc1,
            "x-razorpay-event-id": "evt_e2e_normal_101" # Same event ID!
        }
    )
    assert resp_wh_dup.status_code == 200, f"Duplicate webhook failed: {resp_wh_dup.text}"
    dup_data = resp_wh_dup.json()

    if dup_data["status"] == "duplicate":
        record("TC5-01", "Webhook Idempotency Tracking", "Duplicate event delivery returns status 'duplicate' without duplicate state transition", f"Status={dup_data['status']}, event_id={dup_data['event_id']}", "PASS")
    else:
        record("TC5-01", "Webhook Idempotency Tracking", "Duplicate event delivery returns status 'duplicate'", f"Response={dup_data}", "FAIL")


    # -------------------------------------------------------------------------
    # TEST CASE 6 — PAYMENT FAILURE HANDLING
    # -------------------------------------------------------------------------
    print("\n--- TEST CASE 6: Payment Failure Handling ---")
    # Setup deal awaiting payment
    db_tc6 = TestingSessionLocal()
    req_tc6 = ProcurementRequest(
        id=601, user_id=1, raw_prompt="Buy 2 laptops", execution_status=ExecutionStatus.PAYMENT_PENDING.value,
        max_budget=Decimal("150000.00"), extracted_constraints={"item_description": "Laptop", "quantity": 2}
    )
    db_tc6.add(req_tc6)
    order_tc6 = Order(
        request_id=601, vendor_id=1, product_id=101, quantity=2, negotiated_unit_price=Decimal("65000.00"),
        total_amount=Decimal("130000.00"), currency="INR", approval_status=ApprovalStatus.NOT_REQUIRED.value,
        payment_status=PaymentStatus.NOT_STARTED.value, razorpay_payment_link_id="plink_fail_e2e_601"
    )
    db_tc6.add(order_tc6)
    db_tc6.commit()
    db_tc6.close()

    webhook_body_tc6 = {
        "event": "payment_link.cancelled",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_fail_e2e_601",
                    "reference_id": "AGENTX-601"
                }
            }
        }
    }
    raw_wh_bytes_tc6 = json.dumps(webhook_body_tc6).encode("utf-8")
    wh_sig_tc6 = generate_webhook_signature(raw_wh_bytes_tc6)

    resp_wh_tc6 = client.post(
        "/api/payments/webhook",
        content=raw_wh_bytes_tc6,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": wh_sig_tc6,
            "x-razorpay-event-id": "evt_e2e_canc_601"
        }
    )
    assert resp_wh_tc6.status_code == 200, f"Cancellation webhook failed: {resp_wh_tc6.text}"

    db_tc6_chk = TestingSessionLocal()
    req_chk_tc6 = db_tc6_chk.query(ProcurementRequest).filter_by(id=601).first()
    order_chk_tc6 = db_tc6_chk.query(Order).filter_by(request_id=601).first()
    db_tc6_chk.close()

    if order_chk_tc6.payment_status == "CANCELLED" and req_chk_tc6.execution_status == "CANCELLED":
        record("TC6-01", "Payment Cancellation/Failure Handling", "Payment link cancellation sets payment_status and execution_status to CANCELLED (does NOT complete order)", f"Payment status={order_chk_tc6.payment_status}, Execution status={req_chk_tc6.execution_status}", "PASS")
    else:
        record("TC6-01", "Payment Cancellation/Failure Handling", "Payment link cancellation sets status to CANCELLED", f"Payment status={order_chk_tc6.payment_status}, Execution={req_chk_tc6.execution_status}", "FAIL")


    # Summary
    print("\n" + "=" * 80)
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    failed_count = sum(1 for r in results if r["status"] == "FAIL")
    print(f"E2E TEST SUITE SUMMARY: TOTAL={len(results)} | PASSED={passed_count} | FAILED={failed_count}")
    print("=" * 80)

if __name__ == "__main__":
    run_e2e_suite()
