from decimal import Decimal
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class RuleValidationResult(BaseModel):
    rule_name: str
    status: str = Field(..., description="PASS or FAIL")
    actual_value: Any
    expected_value: Any
    message: str


class PolicyViolation(BaseModel):
    rule_name: str
    reason: str
    actual_value: Any
    expected_value: Any
    severity: str = "HIGH"


class GuardrailResult(BaseModel):
    request_id: int
    order_id: Optional[int] = None
    status: str = Field(..., description="READY_FOR_PAYMENT, APPROVAL_REQUIRED, or POLICY_VIOLATION")
    all_rules_passed: bool
    approval_required: bool
    total_amount: Decimal
    currency: str = "INR"
    rules: List[RuleValidationResult]
    violations: List[PolicyViolation]
    policy_version: str
    validated_at: datetime


class ApprovalActionRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Optional administrative notes for approval/rejection")


class ApprovalActionResponse(BaseModel):
    request_id: int
    order_id: int
    approval_status: str
    execution_status: str
    message: str
