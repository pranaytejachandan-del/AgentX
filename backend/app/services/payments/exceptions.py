class PaymentException(Exception):
    """Base exception for payment errors."""
    pass


class InvalidPaymentStateException(PaymentException):
    """Raised when payment creation is requested for an order not ready for payment."""
    pass


class InvalidWebhookSignatureException(PaymentException):
    """Raised when HMAC-SHA256 signature verification fails."""
    pass


class PaymentAmountMismatchException(PaymentException):
    """Raised when paid webhook amount does not match expected order total."""
    pass


class DuplicateWebhookEventException(PaymentException):
    """Raised when a webhook event ID has already been processed."""
    pass
