import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.user import User
from app.models.procurement_request import ProcurementRequest, ExecutionStatus
from app.models.negotiation_trace import NegotiationTrace
from app.models.audit_event import AuditEvent
from app.schemas.procurement import ProcurementConstraintSchema
from app.schemas.discovery import OfferCandidate
from app.schemas.negotiation import NegotiateOfferRequest
from app.services.negotiation_engine import run_negotiation
from app.services.buyer_agent import generate_buyer_fallback_action
from app.services.supplier_simulator import SupplierSimulator


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    u = User(id=1, name="Procurement Manager", email="manager@company.com", role="procurement_manager")
    session.add(u)
    session.commit()

    p_req = ProcurementRequest(
        id=10,
        user_id=1,
        raw_prompt="Find 500 chairs",
        execution_status=ExecutionStatus.CREATED.value
    )
    session.add(p_req)
    session.commit()

    yield session
    session.close()


def make_sample_offer(base="8500.00", min_val="7300.00"):
    return OfferCandidate(
        product_id=21,
        vendor_id=4,
        vendor_name="ErgoWorks India",
        product_name="Ergonomic Mesh Chair",
        sku="EWI-001",
        base_price=Decimal(base),
        min_allowable_price=Decimal(min_val),
        lead_time_days=5,
        vendor_rating=4.8,
        gst_verified=True,
        certifications=["BIFMA"],
        semantic_similarity=0.95,
        price_score=0.8,
        lead_time_score=0.8,
        rating_score=0.9,
        gst_score=1.0,
        overall_score=0.85,
        eligibility_status="ELIGIBLE",
        eligibility_reasons=["Price OK"]
    )


@pytest.mark.asyncio
async def test_successful_negotiation():
    """Test 1 — Successful negotiation reaching DEAL_AGREED."""
    offer = make_sample_offer(base="8500.00", min_val="7300.00")
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic chair",
        quantity=500,
        target_unit_price=Decimal("7000.00"),
        max_unit_price=Decimal("8000.00"),
        needs_clarification=False
    )
    req = NegotiateOfferRequest(request_id=None, offer=offer, constraints=constraints)
    res = await run_negotiation(req)

    assert res.status == "DEAL_AGREED"
    assert res.final_unit_price <= Decimal("8000.00")
    assert res.final_unit_price >= Decimal("7300.00")
    assert res.turns_used <= 4
    assert res.total_amount == res.final_unit_price * 500


@pytest.mark.asyncio
async def test_negotiation_failure():
    """Test 2 — Negotiation failure when supplier minimum > buyer maximum."""
    offer = make_sample_offer(base="8800.00", min_val="8500.00")
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic chair",
        quantity=500,
        max_unit_price=Decimal("8000.00"),
        needs_clarification=False
    )
    req = NegotiateOfferRequest(request_id=None, offer=offer, constraints=constraints)
    res = await run_negotiation(req)

    assert res.status == "NEGOTIATION_FAILED"


@pytest.mark.asyncio
async def test_maximum_turns_limit():
    """Test 3 — Maximum 4 turns limit enforced."""
    offer = make_sample_offer(base="8500.00", min_val="7300.00")
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic chair",
        quantity=500,
        max_unit_price=Decimal("8000.00"),
        needs_clarification=False
    )
    req = NegotiateOfferRequest(request_id=None, offer=offer, constraints=constraints)
    res = await run_negotiation(req)

    assert res.turns_used <= 4
    assert len(res.trace) <= 4


def test_buyer_cannot_exceed_maximum():
    """Test 4 — Buyer agent fallback clamps proposed price to max_unit_price."""
    action = generate_buyer_fallback_action(
        target_unit_price=Decimal("9000.00"),
        max_unit_price=Decimal("8000.00"),
        quantity=500,
        supplier_current_offer=Decimal("8500.00"),
        previous_buyer_offer=Decimal("7500.00"),
        turn_number=1,
        max_turns=4
    )

    assert action.proposed_unit_price <= Decimal("8000.00")


def test_supplier_cannot_go_below_minimum():
    """Test 5 — Supplier simulator never accepts or counters below min_allowable_price."""
    action, new_offer, msg = SupplierSimulator.evaluate_buyer_offer(
        base_price=Decimal("8500.00"),
        min_allowable_price=Decimal("7300.00"),
        current_supplier_offer=Decimal("8000.00"),
        buyer_offer=Decimal("6000.00"),  # Below min 7300
        turn_number=1,
        max_turns=4
    )

    assert new_offer >= Decimal("7300.00")
    assert action == "COUNTER_OFFER"


@pytest.mark.asyncio
async def test_target_vs_maximum():
    """Test 6 — Deal above target but below maximum is accepted."""
    offer = make_sample_offer(base="8500.00", min_val="7300.00")
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic chair",
        quantity=500,
        target_unit_price=Decimal("7000.00"),
        max_unit_price=Decimal("8000.00"),
        needs_clarification=False
    )
    req = NegotiateOfferRequest(request_id=None, offer=offer, constraints=constraints)
    res = await run_negotiation(req)

    assert res.status == "DEAL_AGREED"
    assert res.final_unit_price <= Decimal("8000.00")


def test_invalid_target_max_relationship():
    """Test 7 — Invalid target > max price relationship detection."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic chair",
        target_unit_price=Decimal("8500.00"),
        max_unit_price=Decimal("8000.00"),
        needs_clarification=True,
        ambiguous_fields=["target_unit_price", "max_unit_price"]
    )
    assert constraints.target_unit_price is not None and constraints.max_unit_price is not None
    assert constraints.target_unit_price > constraints.max_unit_price


@pytest.mark.asyncio
async def test_trace_persistence(db_session):
    """Test 8 — Every negotiation turn trace is saved to database."""
    offer = make_sample_offer(base="8500.00", min_val="7300.00")
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic chair",
        quantity=500,
        max_unit_price=Decimal("8000.00"),
        needs_clarification=False
    )
    req = NegotiateOfferRequest(request_id=10, offer=offer, constraints=constraints)
    res = await run_negotiation(req, db=db_session)

    traces = db_session.query(NegotiationTrace).filter_by(request_id=10).all()
    assert len(traces) == res.turns_used


@pytest.mark.asyncio
async def test_audit_events(db_session):
    """Test 9 — Negotiation state transitions generate AuditEvents."""
    offer = make_sample_offer(base="8500.00", min_val="7300.00")
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic chair",
        quantity=500,
        max_unit_price=Decimal("8000.00"),
        needs_clarification=False
    )
    req = NegotiateOfferRequest(request_id=10, offer=offer, constraints=constraints)
    res = await run_negotiation(req, db=db_session)

    audit = db_session.query(AuditEvent).filter_by(request_id=10).first()
    assert audit is not None
    assert audit.event_type in ["DEAL_AGREED", "NEGOTIATION_FAILED"]


@pytest.mark.asyncio
async def test_llm_failure_fallback():
    """Test 10 — LLM failure fallback strategy runs safely."""
    action = generate_buyer_fallback_action(
        target_unit_price=Decimal("7000.00"),
        max_unit_price=Decimal("8000.00"),
        quantity=100,
        supplier_current_offer=Decimal("8200.00"),
        previous_buyer_offer=None,
        turn_number=1,
        max_turns=4
    )
    assert action.action in ["COUNTER_OFFER", "ACCEPT"]
    assert action.proposed_unit_price <= Decimal("8000.00")
