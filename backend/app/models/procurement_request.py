import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.negotiation_trace import NegotiationTrace
    from app.models.audit_event import AuditEvent
    from app.models.order import Order


class ExecutionStatus(str, enum.Enum):
    CREATED = "CREATED"
    PARSING = "PARSING"
    DISCOVERING = "DISCOVERING"
    NEGOTIATING = "NEGOTIATING"
    POLICY_CHECK = "POLICY_CHECK"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    READY_FOR_PAYMENT = "READY_FOR_PAYMENT"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProcurementRequest(Base):
    __tablename__ = "procurement_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_constraints: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    execution_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ExecutionStatus.CREATED.value,
        index=True
    )
    max_budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="procurement_requests")
    negotiation_traces: Mapped[List["NegotiationTrace"]] = relationship(
        "NegotiationTrace",
        back_populates="request",
        cascade="all, delete-orphan"
    )
    audit_events: Mapped[List["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="request",
        cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="request",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProcurementRequest(id={self.id}, user_id={self.user_id}, status='{self.execution_status}')>"

