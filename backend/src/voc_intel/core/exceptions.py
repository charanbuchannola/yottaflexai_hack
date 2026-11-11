"""Domain-level exceptions mapped cleanly by API presentation layer."""


class DomainError(Exception):
    """Base domain exception."""


class ResourceNotFoundError(DomainError):
    """Raised when a requested domain entity or report cannot be located."""


class InvalidStateTransitionError(DomainError):
    """Raised when an FSM lifecycle transition violates allowed rules."""

