class GuardrailException(Exception):
    """Base exception for all guardrail and policy errors."""
    pass


from typing import Optional, List, Any


class PolicyViolationException(GuardrailException):
    """Raised when a hard financial or business policy rule fails."""
    def __init__(self, message: str, violations: Optional[List[Any]] = None):
        super().__init__(message)
        self.violations = violations or []


class InvalidApprovalStateException(GuardrailException):
    """Raised when an approval/rejection is attempted on a request not awaiting approval."""
    pass


class DealTamperedException(GuardrailException):
    """Raised when deal attributes differ from the validated database snapshot."""
    pass
