import os
import sys
import logging
from decimal import Decimal

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import SessionLocal, engine
from app.database.base import Base
from app.models.user import User
from app.models.vendor import Vendor
from app.models.product import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentx.seed")


VENDORS_DATA = [
    {
        "name": "OfficePro Supplies",
        "rating": Decimal("4.80"),
        "gstin": "27AAAAA0001A1Z5",
        "gst_verified": True,
    },
    {
        "name": "ErgoWorks India",
        "rating": Decimal("4.60"),
        "gstin": "29BBBBB0002B2Z6",
        "gst_verified": True,
    },
    {
        "name": "UrbanDesk Solutions",
        "rating": Decimal("4.30"),
        "gstin": "07CCCCC0003C3Z7",
        "gst_verified": True,
    },
    {
        "name": "PrimeOffice Furnishers",
        "rating": Decimal("4.50"),
        "gstin": "33DDDDD0004D4Z8",
        "gst_verified": True,
    },
    {
        "name": "WorkSpace Direct",
        "rating": Decimal("3.90"),
        "gstin": "19EEEEE0005E5Z9",
        "gst_verified": False,
    },
    {
        "name": "ComfortSeat Industries",
        "rating": Decimal("4.70"),
        "gstin": "24FFFFF0006F6Z0",
        "gst_verified": True,
    },
    {
        "name": "SmartOffice Traders",
        "rating": Decimal("4.10"),
        "gstin": "06GGGGG0007G7Z1",
        "gst_verified": False,
    },
    {
        "name": "Elite Furnitech",
        "rating": Decimal("4.90"),
        "gstin": "36HHHHH0008H8Z2",
        "gst_verified": True,
    },
    {
        "name": "DeskHub Suppliers",
        "rating": Decimal("4.20"),
        "gstin": "09IIIII0009I9Z3",
        "gst_verified": True,
    },
    {
        "name": "Corporate Furniture Co.",
        "rating": Decimal("4.40"),
        "gstin": "10JJJJJ0010J0Z4",
        "gst_verified": False,
    },
]

PRODUCTS_CATALOG = [
    # OfficePro Supplies (Vendor 1)
    {"vendor_idx": 0, "sku": "OPS-CHR-001", "name": "Ergonomic Pro Mesh Chair", "category": "Office Chair", "base": "8500.00", "min": "7200.00", "lead": 5, "specs": {"material": "Mesh", "armrest": "3D Adjustable", "weight_capacity_kg": 120}, "certs": ["ISO-9001", "BIFMA"]},
    {"vendor_idx": 0, "sku": "OPS-DSK-002", "name": "Executive L-Shape Desk", "category": "Executive Desk", "base": "24000.00", "min": "20500.00", "lead": 7, "specs": {"material": "Engineered Wood", "finish": "Walnut", "drawers": 3}, "certs": ["ISO-9001"]},
    {"vendor_idx": 0, "sku": "OPS-CAB-003", "name": "3-Drawer Mobile Pedestal Cabinet", "category": "Filing Cabinet", "base": "5500.00", "min": "4800.00", "lead": 3, "specs": {"material": "Cold-Rolled Steel", "lock": "Central Key Lock"}, "certs": ["ISO-9001"]},
    
    # ErgoWorks India (Vendor 2)
    {"vendor_idx": 1, "sku": "EWI-CHR-001", "name": "ErgoFlex High Back Chair", "category": "Office Chair", "base": "12500.00", "min": "10800.00", "lead": 4, "specs": {"lumbar_support": "Dynamic", "recline_angle": "135 deg"}, "certs": ["BIFMA Gold", "GreenGuard"]},
    {"vendor_idx": 1, "sku": "EWI-ST-002", "name": "Electric Motorized Standing Desk", "category": "Standing Desk", "base": "28500.00", "min": "24000.00", "lead": 6, "specs": {"height_range_cm": "65-125", "motor": "Dual Motor", "memory_presets": 4}, "certs": ["CE", "UL", "BIFMA"]},
    {"vendor_idx": 1, "sku": "EWI-CHR-003", "name": "Active Balance Task Stool", "category": "Task Stool", "base": "6800.00", "min": "5900.00", "lead": 4, "specs": {"height_adjustable": True, "swivel_360": True}, "certs": ["BIFMA"]},

    # UrbanDesk Solutions (Vendor 3)
    {"vendor_idx": 2, "sku": "UDS-DSK-001", "name": "Minimalist Workstation Desk", "category": "Workstation Desk", "base": "9500.00", "min": "8000.00", "lead": 5, "specs": {"frame": "Steel", "top": "Laminated MDF", "cable_management": True}, "certs": ["ISO-14001"]},
    {"vendor_idx": 2, "sku": "UDS-CHR-002", "name": "Urban Mesh Visitor Chair", "category": "Visitor Chair", "base": "4200.00", "min": "3600.00", "lead": 3, "specs": {"stackable": True, "frame": "Chrome"}, "certs": ["ISO-9001"]},
    {"vendor_idx": 2, "sku": "UDS-TBL-003", "name": "Compact 4-Person Meeting Table", "category": "Conference Table", "base": "14000.00", "min": "11800.00", "lead": 7, "specs": {"shape": "Rectangular", "seating": 4}, "certs": ["ISO-9001"]},

    # PrimeOffice Furnishers (Vendor 4)
    {"vendor_idx": 3, "sku": "POF-CHR-001", "name": "Presidential Leatherette Chair", "category": "Executive Office Chair", "base": "18900.00", "min": "16000.00", "lead": 6, "specs": {"material": "PU Leather", "padding": "High Density Foam"}, "certs": ["BIFMA", "ISO-9001"]},
    {"vendor_idx": 3, "sku": "POF-TBL-002", "name": "Grand 10-Person Conference Table", "category": "Conference Table", "base": "45000.00", "min": "38500.00", "lead": 10, "specs": {"length_feet": 10, "pop_up_grommets": 2}, "certs": ["ISO-9001"]},
    {"vendor_idx": 3, "sku": "POF-CAB-003", "name": "Lateral Steel Storage Cabinet", "category": "Office Filing Cabinet", "base": "11200.00", "min": "9500.00", "lead": 5, "specs": {"shelves": 4, "door": "Sliding Glass"}, "certs": ["ISO-9001"]},

    # WorkSpace Direct (Vendor 5)
    {"vendor_idx": 4, "sku": "WSD-CHR-001", "name": "Budget Mesh Office Chair", "category": "Office Chair", "base": "5800.00", "min": "4900.00", "lead": 4, "specs": {"tilt": "Basic Synchro", "base": "Nylon"}, "certs": []},
    {"vendor_idx": 4, "sku": "WSD-DSK-002", "name": "Folding Training Room Desk", "category": "Computer Desk", "base": "7200.00", "min": "6100.00", "lead": 4, "specs": {"wheels": True, "foldable": True}, "certs": []},
    {"vendor_idx": 4, "sku": "WSD-CHR-003", "name": "Fabric Stackable Guest Chair", "category": "Visitor Chair", "base": "3100.00", "min": "2650.00", "lead": 2, "specs": {"material": "Fabric", "frame": "Powder Coated"}, "certs": []},

    # ComfortSeat Industries (Vendor 6)
    {"vendor_idx": 5, "sku": "CSI-CHR-001", "name": "Ultimate Comfort Lumbar Chair", "category": "Ergonomic Office Chair", "base": "15800.00", "min": "13500.00", "lead": 5, "specs": {"lumbar": "4D Inflatable Cushion", "headrest": "Adjustable"}, "certs": ["BIFMA Gold", "GreenGuard", "ISO-9001"]},
    {"vendor_idx": 5, "sku": "CSI-CHR-002", "name": "High-Back Gaming & Work Chair", "category": "Office Chair", "base": "13200.00", "min": "11000.00", "lead": 4, "specs": {"footrest": True, "recline": "180 deg"}, "certs": ["BIFMA"]},
    {"vendor_idx": 5, "sku": "CSI-ST-003", "name": "Ergo Drafting Chair with Foot Ring", "category": "Task Stool", "base": "8900.00", "min": "7500.00", "lead": 5, "specs": {"foot_ring": "Chrome Adjustable", "extended_height": True}, "certs": ["ISO-9001"]},

    # SmartOffice Traders (Vendor 7)
    {"vendor_idx": 6, "sku": "SOT-MOD-001", "name": "4-Person Modular Pod Workstation", "category": "Workstation Desk", "base": "36000.00", "min": "31000.00", "lead": 8, "specs": {"partition_height_cm": 120, "power_sockets_per_user": 3}, "certs": ["ISO-9001"]},
    {"vendor_idx": 6, "sku": "SOT-CAB-002", "name": "2-Door Metal Storage Locker", "category": "Office Filing Cabinet", "base": "8400.00", "min": "7100.00", "lead": 4, "specs": {"compartments": 2, "ventilation": True}, "certs": []},
    {"vendor_idx": 6, "sku": "SOT-CHR-003", "name": "Mid-Back Fabric Task Chair", "category": "Mesh Office Chair", "base": "4900.00", "min": "4100.00", "lead": 3, "specs": {"color": "Black", "gas_lift": "Class 3"}, "certs": []},

    # Elite Furnitech (Vendor 8)
    {"vendor_idx": 7, "sku": "EFT-DSK-001", "name": "Elite Walnut Executive Suite", "category": "Executive Office Chair", "base": "52000.00", "min": "44000.00", "lead": 12, "specs": {"wood": "Veneer Walnut", "credenza_included": True}, "certs": ["FSC Certified", "ISO-9001", "BIFMA"]},
    {"vendor_idx": 7, "sku": "EFT-POD-002", "name": "Acoustic Solo Phone Booth / Pod", "category": "Acoustic Pod", "base": "145000.00", "min": "125000.00", "lead": 14, "specs": {"sound_reduction_db": 32, "ventilation_fan": True, "power": True}, "certs": ["CE", "ISO-9001"]},
    {"vendor_idx": 7, "sku": "EFT-CHR-003", "name": "Nappa Leather Boss Chair", "category": "Executive Office Chair", "base": "27500.00", "min": "23500.00", "lead": 7, "specs": {"leather": "Genuine Nappa", "base": "Polished Aluminum"}, "certs": ["BIFMA Platinum", "ISO-9001"]},

    # DeskHub Suppliers (Vendor 9)
    {"vendor_idx": 8, "sku": "DHS-ST-001", "name": "Pneumatic Sit-Stand Desk Converter", "category": "Standing Desk", "base": "11500.00", "min": "9800.00", "lead": 4, "specs": {"keyboard_tray": True, "max_load_kg": 15}, "certs": ["ISO-9001"]},
    {"vendor_idx": 8, "sku": "DHS-TBL-002", "name": "Modular Flip-Top Conference Table", "category": "Conference Table", "base": "16500.00", "min": "14000.00", "lead": 6, "specs": {"castors": True, "nestable": True}, "certs": ["BIFMA"]},
    {"vendor_idx": 8, "sku": "DHS-CHR-003", "name": "Ergonomic Mesh Task Chair", "category": "Ergonomic Office Chair", "base": "7900.00", "min": "6700.00", "lead": 4, "specs": {"lumbar": "Adjustable", "base": "Nylon Reinforced"}, "certs": ["ISO-9001"]},

    # Corporate Furniture Co. (Vendor 10)
    {"vendor_idx": 9, "sku": "CFC-REC-001", "name": "Modern Curved Reception Desk", "category": "Reception Desk", "base": "32000.00", "min": "27500.00", "lead": 9, "specs": {"led_lighting": True, "countertop": "Quartz finish"}, "certs": ["ISO-9001"]},
    {"vendor_idx": 9, "sku": "CFC-CHR-002", "name": "Executive High-Back Mesh Chair", "category": "Executive Office Chair", "base": "10500.00", "min": "8900.00", "lead": 5, "specs": {"headrest": "2D", "synchro_tilt": True}, "certs": ["BIFMA"]},
    {"vendor_idx": 9, "sku": "CFC-CAB-003", "name": "Steel Tambour Door Storage Unit", "category": "Office Filing Cabinet", "base": "14800.00", "min": "12400.00", "lead": 6, "specs": {"door": "Sliding Plastic Slats", "shelves": 4}, "certs": ["ISO-9001"]},
    
    # Extra products to ensure > 30 products overall
    {"vendor_idx": 0, "sku": "OPS-CHR-004", "name": "Ergonomic Heavy-Duty Task Chair", "category": "Ergonomic Office Chair", "base": "9800.00", "min": "8300.00", "lead": 4, "specs": {"weight_capacity_kg": 150}, "certs": ["BIFMA"]},
    {"vendor_idx": 1, "sku": "EWI-DSK-004", "name": "Manual Crank Height Adjustable Desk", "category": "Standing Desk", "base": "18000.00", "min": "15200.00", "lead": 5, "specs": {"crank_side": "Right", "range_cm": "70-115"}, "certs": ["ISO-9001"]},
    {"vendor_idx": 5, "sku": "CSI-CHR-004", "name": "Ergo Mesh Drafter Stool with Armrests", "category": "Task Stool", "base": "9200.00", "min": "7800.00", "lead": 4, "specs": {"armrest": "Adjustable", "gas_lift": "Extended"}, "certs": ["BIFMA"]},

    # Enterprise Laptops & Electronics for Buildathon Demo
    {"vendor_idx": 0, "sku": "TECH-LAP-001", "name": "Enterprise Laptop 16GB RAM", "category": "Electronics", "base": "68500.00", "min": "58000.00", "lead": 5, "specs": {"ram": "16GB", "storage": "512GB SSD", "processor": "Intel i7"}, "certs": ["ISO-9001", "CE"]},
    {"vendor_idx": 1, "sku": "TECH-LAP-002", "name": "Executive Business Laptop 16GB", "category": "Electronics", "base": "78000.00", "min": "65000.00", "lead": 7, "specs": {"ram": "16GB", "storage": "1TB SSD", "processor": "Intel i7"}, "certs": ["ISO-9001", "CE", "EnergyStar"]},
    {"vendor_idx": 6, "sku": "TECH-LAP-003", "name": "SlimBook Pro 16GB RAM", "category": "Electronics", "base": "82000.00", "min": "71000.00", "lead": 4, "specs": {"ram": "16GB", "storage": "512GB SSD", "processor": "AMD Ryzen 7"}, "certs": ["CE"]},
]


def seed_database(session=None):
    """Seed the database with default user, 10 synthetic vendors, and 30+ products."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        logger.info("Checking existing database seed status...")
        
        # 1. Seed User
        existing_user = session.query(User).filter_by(email="manager@company.com").first()
        if not existing_user:
            user = User(
                name="Procurement Manager",
                email="manager@company.com",
                role="procurement_manager"
            )
            session.add(user)
            session.flush()
            logger.info(f"Created default user: {user.email}")
        else:
            logger.info(f"Default user already exists: {existing_user.email}")

        # 2. Seed Vendors
        created_vendors = []
        for v_data in VENDORS_DATA:
            existing_vendor = session.query(Vendor).filter_by(gstin=v_data["gstin"]).first()
            if not existing_vendor:
                vendor = Vendor(
                    name=v_data["name"],
                    rating=v_data["rating"],
                    gstin=v_data["gstin"],
                    gst_verified=v_data["gst_verified"]
                )
                session.add(vendor)
                session.flush()
                created_vendors.append(vendor)
                logger.info(f"Created Vendor: {vendor.name} (GSTIN: {vendor.gstin})")
            else:
                created_vendors.append(existing_vendor)
                logger.info(f"Vendor already exists: {existing_vendor.name}")

        # 3. Seed Products
        product_count = 0
        for p_data in PRODUCTS_CATALOG:
            vendor = created_vendors[p_data["vendor_idx"]]
            existing_prod = session.query(Product).filter_by(sku=p_data["sku"]).first()
            if not existing_prod:
                base_price = Decimal(p_data["base"])
                min_price = Decimal(p_data["min"])
                
                # Sanity check constraint min_allowable_price <= base_price
                if min_price > base_price:
                    raise ValueError(f"Invalid seed data for {p_data['sku']}: min_price {min_price} > base_price {base_price}")

                product = Product(
                    vendor_id=vendor.id,
                    sku=p_data["sku"],
                    name=p_data["name"],
                    category=p_data["category"],
                    description=f"{p_data['name']} - Premium commercial office furniture supplied by {vendor.name}.",
                    specifications=p_data["specs"],
                    base_price=base_price,
                    min_allowable_price=min_price,
                    lead_time_days=p_data["lead"],
                    certifications=p_data["certs"],
                    embedding=None # Vector embedding to be populated in Feature 2/3
                )
                session.add(product)
                product_count += 1
                logger.info(f"Created Product: [{product.sku}] {product.name} (₹{product.base_price})")
            else:
                logger.info(f"Product already exists: {existing_prod.sku}")

        session.commit()
        logger.info("Successfully seeded database with vendors and products!")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to seed database: {str(e)}")
        raise
    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    seed_database()
