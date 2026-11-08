"""Non-sensitive exception types exposed by the service boundary."""


class ServiceError(Exception):
    """Base exception for business-service failures."""


class InvalidPricingInputError(ServiceError):
    """Raised when pricing receives an invalid amount or line collection."""

    def __init__(self, reason: str = "invalid pricing input") -> None:
        self.reason = reason
        super().__init__(reason)


class InvalidQuantityError(InvalidPricingInputError):
    """Raised when a line quantity is not a strict positive integer."""

    def __init__(self) -> None:
        super().__init__("quantity must be a positive integer")


class InvalidMonetaryAmountError(InvalidPricingInputError):
    """Raised when an amount is not a finite, non-negative Decimal."""

    def __init__(self) -> None:
        super().__init__("amount must be a finite non-negative Decimal")


class PricingComputationError(ServiceError):
    """Raised when a valid pricing calculation cannot be completed safely."""

    def __init__(self) -> None:
        super().__init__("pricing calculation could not be completed")


class OrderNotFoundError(ServiceError):
    """Raised when the requested order does not exist."""

    def __init__(self) -> None:
        super().__init__("order not found")


class ProductNotFoundError(ServiceError):
    """Raised when an order line references an unavailable product."""

    def __init__(self) -> None:
        super().__init__("referenced product not found")


class OrderDataIntegrityError(ServiceError):
    """Raised when validated repositories return inconsistent order data."""

    def __init__(self) -> None:
        super().__init__("order data is inconsistent")
