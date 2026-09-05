from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ProcurementConstraintSchema(BaseModel):
    """Strict machine-readable procurement constraints schema."""
    category: Optional[str] = Field(
        default=None,
        description="Broad category of product e.g. office furniture, electronics"
    )
    item_description: str = Field(
        ...,
        description="Required description of the requested product e.g. ergonomic office chair"
    )
    quantity: Optional[int] = Field(
        default=None,
        description="Number of units requested. Must be > 0 if specified."
    )
    target_unit_price: Optional[Decimal] = Field(
        default=None,
        description="Preferred/target unit price. Not necessarily the strict maximum."
    )
    max_unit_price: Optional[Decimal] = Field(
        default=None,
        description="Maximum allowable unit price ceiling."
    )
    currency: str = Field(
        default="INR",
        description="Normalized ISO currency code e.g. INR, USD, EUR"
    )
    max_lead_time_days: Optional[int] = Field(
        default=None,
        description="Maximum acceptable lead/delivery time in days."
    )
    required_certifications: List[str] = Field(
        default_factory=list,
        description="List of required industry or quality certifications e.g. BIFMA, ISO 9001"
    )
    additional_requirements: List[str] = Field(
        default_factory=list,
        description="List of additional features, specs or preferences e.g. mesh back, black color"
    )
    missing_required_fields: List[str] = Field(
        default_factory=list,
        description="Essential fields missing from prompt e.g. quantity, max_unit_price"
    )
    ambiguous_fields: List[str] = Field(
        default_factory=list,
        description="Fields whose numerical/textual values are soft or ambiguous e.g. 'around 500'"
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if important fields are missing, ambiguous, or inconsistent."
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than 0.")
        return v

    @field_validator("target_unit_price", "max_unit_price")
    @classmethod
    def validate_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative.")
        return v

    @field_validator("max_lead_time_days")
    @classmethod
    def validate_lead_time(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Lead time cannot be negative.")
        return v


class ParseProcurementRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        description="Natural language procurement requirement prompt"
    )
    user_id: Optional[int] = Field(
        default=None,
        description="Optional user ID submitting the procurement request"
    )


class ParseProcurementResponse(BaseModel):
    status: str = Field(
        ...,
        description="'parsed' or 'needs_clarification'"
    )
    request_id: Optional[int] = Field(
        default=None,
        description="Database ProcurementRequest ID if persisted"
    )
    constraints: ProcurementConstraintSchema
    missing_fields: List[str] = Field(
        default_factory=list,
        description="List of missing fields if clarification is required"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human readable explanation or clarification request message"
    )
