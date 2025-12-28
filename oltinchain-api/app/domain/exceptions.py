"""Domain exceptions for OltinChain."""


class DomainException(Exception):
    """Base domain exception."""

    pass


class AuthenticationError(DomainException):
    """Invalid credentials or token."""

    pass


class UserNotFoundError(DomainException):
    """User not found."""

    pass


class UserAlreadyExistsError(DomainException):
    """Phone already registered."""

    pass


class InsufficientBalanceError(DomainException):
    """Insufficient balance for operation."""

    pass


class OrderError(DomainException):
    """Order processing error."""

    pass


class BlockchainError(DomainException):
    """Blockchain operation error."""

    pass
