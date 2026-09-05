import enum
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.procurement_request import ProcurementRequest


class ActorType(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    INTENT_AGENT = "INTENT_AGENT"
    DISCOVERY_AGENT = "DISCOVERY_AGENT"
    NEGOTIATION_AGENT = "NEGOTIATION_AGENT"
    GUARDRAIL_ENGINE = "GUARDRAIL_ENGINE"
    HUMAN_ADMIN = "HUMAN_ADMIN"
    PAYMENT_SERVICE = "PAYMENT_SERVICE"
    WEBHOOK = "WEBHOOK"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("procurement_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    request: Mapped["ProcurementRequest"] = relationship("ProcurementRequest", back_populates="audit_events")

    def __repr__(self) -> str:
        return f"<AuditEvent(id={self.id}, request_id={self.request_id}, event_type='{self.event_type}', actor='{self.actor}')>"

