import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.procurement_request import ProcurementRequest


class NegotiationStatus(str, enum.Enum):
    OFFER = "OFFER"
    COUNTER_OFFER = "COUNTER_OFFER"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class NegotiationTrace(Base):
    __tablename__ = "negotiation_traces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("procurement_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_number: Mapped[int] = mapped_column(nullable=False)
    buyer_agent_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supplier_agent_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    counter_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    negotiation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decision_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    request: Mapped["ProcurementRequest"] = relationship("ProcurementRequest", back_populates="negotiation_traces")

    def __repr__(self) -> str:
        return f"<NegotiationTrace(id={self.id}, request_id={self.request_id}, turn={self.turn_number}, status='{self.negotiation_status}')>"

