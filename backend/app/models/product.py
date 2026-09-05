from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, CheckConstraint, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.vendor import Vendor
    from app.models.order import Order


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Flexible JSON fields for specs & certifications
    specifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    certifications: Mapped[Optional[List[str]]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    
    # Financial & Delivery fields
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_allowable_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(nullable=False)
    
    # pgvector embedding placeholder for semantic search (1536 dims for OpenAI embeddings)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536).with_variant(JSON(), "sqlite"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("min_allowable_price <= base_price", name="check_min_price_le_base_price"),
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="products")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}', base_price={self.base_price})>"

