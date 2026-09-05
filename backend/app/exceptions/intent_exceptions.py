class IntentParserException(Exception):
    """Base exception class for intent parser failures."""
    pass


class IncompletePromptException(IntentParserException):
    """Raised when prompt is empty or completely unparseable."""
    pass


class InvalidConstraintException(IntentParserException):
    """Raised when constraint rules or data validation fail catastrophically."""
    pass
