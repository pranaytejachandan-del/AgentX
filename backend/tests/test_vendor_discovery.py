import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.user import User
from app.models.vendor import Vendor
from app.models.product import Product
from app.schemas.procurement import ProcurementConstraintSchema
from app.services.vendor_discovery import discover_offers
from app.services.embedding_service import get_embedding_service, generate_product_text


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed test vendors
    v1 = Vendor(id=1, name="ErgoWorks India", rating=Decimal("4.8"), gstin="29AAAAA0001A1Z5", gst_verified=True)
    v2 = Vendor(id=2, name="OfficePro Supplies", rating=Decimal("4.2"), gstin="27BBBBB0002B2Z6", gst_verified=False)
    v3 = Vendor(id=3, name="Premium Furnishers", rating=Decimal("4.5"), gstin="07CCCCC0003C3Z7", gst_verified=True)
    session.add_all([v1, v2, v3])
    session.commit()

    emb_service = get_embedding_service()

    # Seed test products
    # Product 1: Eligible ergonomic chair
    p1_text = generate_product_text("Ergonomic Mesh Chair", "Office Chair", "Adjustable lumbar chair", certifications=["BIFMA", "ISO-9001"])
    p1 = Product(
        id=1, vendor_id=1, sku="EWI-001", name="Ergonomic Mesh Chair", category="Office Chair",
        base_price=Decimal("7500.00"), min_allowable_price=Decimal("6500.00"), lead_time_days=5,
        certifications=["BIFMA", "ISO-9001"], embedding=emb_service.generate_embedding(p1_text)
    )

    # Product 2: High price (> 8000)
    p2_text = generate_product_text("Executive Ergonomic Chair", "Office Chair", "Premium executive leather chair", certifications=["BIFMA"])
    p2 = Product(
        id=2, vendor_id=2, sku="OPS-002", name="Executive Ergonomic Chair", category="Office Chair",
        base_price=Decimal("12000.00"), min_allowable_price=Decimal("10000.00"), lead_time_days=4,
        certifications=["BIFMA"], embedding=emb_service.generate_embedding(p2_text)
    )

    # Product 3: Long lead time (14 days > 7)
    p3_text = generate_product_text("Ergo Flex Chair", "Office Chair", "Flexible ergonomic task chair", certifications=["BIFMA"])
    p3 = Product(
        id=3, vendor_id=3, sku="PF-003", name="Ergo Flex Chair", category="Office Chair",
        base_price=Decimal("7200.00"), min_allowable_price=Decimal("6000.00"), lead_time_days=14,
        certifications=["BIFMA"], embedding=emb_service.generate_embedding(p3_text)
    )

    # Product 4: Missing certification
    p4_text = generate_product_text("Basic Task Chair", "Office Chair", "Standard task chair", certifications=[])
    p4 = Product(
        id=4, vendor_id=2, sku="OPS-004", name="Basic Task Chair", category="Office Chair",
        base_price=Decimal("5000.00"), min_allowable_price=Decimal("4000.00"), lead_time_days=3,
        certifications=[], embedding=emb_service.generate_embedding(p4_text)
    )

    # Product 5: Another eligible ergonomic chair from Vendor 3
    p5_text = generate_product_text("Ergonomic Task Stool", "Office Chair", "Comfortable task stool", certifications=["BIFMA"])
    p5 = Product(
        id=5, vendor_id=3, sku="PF-005", name="Ergonomic Task Stool", category="Office Chair",
        base_price=Decimal("7800.00"), min_allowable_price=Decimal("6800.00"), lead_time_days=6,
        certifications=["BIFMA"], embedding=emb_service.generate_embedding(p5_text)
    )

    session.add_all([p1, p2, p3, p4, p5])
    session.commit()

    yield session
    session.close()


def test_relevant_product_retrieval(db_session):
    """Test 1 — Relevant product retrieval for ergonomic chairs."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic office chair",
        max_unit_price=Decimal("15000"),
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.status == "success"
    assert res.candidate_count > 0
    assert any("Ergonomic" in o.product_name for o in res.offers)


def test_price_filtering(db_session):
    """Test 2 — Price filtering excludes products exceeding max_unit_price."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic office chair",
        max_unit_price=Decimal("8000"),
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.status == "success"
    for offer in res.offers:
        assert offer.base_price <= Decimal("8000")
        assert offer.product_id != 2  # Product 2 costs 12000


def test_lead_time_filtering(db_session):
    """Test 3 — Lead-time filtering excludes products exceeding max_lead_time_days."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic office chair",
        max_lead_time_days=7,
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.status == "success"
    for offer in res.offers:
        assert offer.lead_time_days <= 7
        assert offer.product_id != 3  # Product 3 has 14 days lead time


def test_certification_filtering(db_session):
    """Test 4 — Certification filtering excludes products missing BIFMA."""
    constraints = ProcurementConstraintSchema(
        item_description="office chair",
        required_certifications=["BIFMA"],
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.status == "success"
    for offer in res.offers:
        assert "BIFMA" in offer.certifications
        assert offer.product_id != 4  # Product 4 has no certifications


def test_combined_constraints(db_session):
    """Test 5 — Combined constraints enforcement."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic office chair",
        max_unit_price=Decimal("8000"),
        max_lead_time_days=7,
        required_certifications=["BIFMA"],
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.status == "success"
    assert len(res.offers) >= 1
    top_offer = res.offers[0]
    assert top_offer.base_price <= Decimal("8000")
    assert top_offer.lead_time_days <= 7
    assert "BIFMA" in top_offer.certifications
    assert top_offer.eligibility_status == "ELIGIBLE"


def test_scoring_and_ranking(db_session):
    """Test 6 — Scoring and ranking formula produces expected order."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic office chair",
        max_unit_price=Decimal("8000"),
        max_lead_time_days=7,
        required_certifications=["BIFMA"],
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.status == "success"
    offers = res.offers
    if len(offers) > 1:
        assert offers[0].overall_score >= offers[1].overall_score


def test_gst_ranking(db_session):
    """Test 7 — GST verified vendors receive full GST score."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic office chair",
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    for offer in res.offers:
        if offer.gst_verified:
            assert offer.gst_score == 1.0
        else:
            assert offer.gst_score == 0.0


def test_no_eligible_offers(db_session):
    """Test 8 — No eligible offers handling when constraints are too strict."""
    constraints = ProcurementConstraintSchema(
        item_description="ergonomic office chair",
        max_unit_price=Decimal("3000"),  # Impossibly low price
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.status == "no_eligible_offers"
    assert len(res.offers) == 0
    assert len(res.near_matches) > 0


def test_unknown_certification(db_session):
    """Test 9 — Unknown certification data is excluded from eligible set."""
    constraints = ProcurementConstraintSchema(
        item_description="task chair",
        required_certifications=["ISO 9001"],
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    for offer in res.offers:
        assert "ISO 9001" in [c.upper() for c in offer.certifications]


def test_semantic_retrieval(db_session):
    """Test 10 — Semantic retrieval finds conceptually related products."""
    constraints = ProcurementConstraintSchema(
        item_description="mesh task seating",
        needs_clarification=False
    )
    res = discover_offers(constraints, top_k=20, db=db_session)
    assert res.candidate_count > 0
    assert len(res.offers) > 0
